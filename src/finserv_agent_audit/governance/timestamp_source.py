"""Trusted timestamp Protocol + reference implementations for audit attestation.

By default, audit entries in `finserv-agent-audit` are stamped with the local
system clock. For financial-services audit posture under

- **SEC 17a-4(f)** (broker-dealer electronic records — non-rewriteable,
  non-erasable, with a verifiable time anchor),
- **eIDAS Regulation (EU 910/2014) Article 42** (qualified electronic
  timestamps carry legal presumption of accuracy across the EU), and
- **Federal Reserve SR 11-7 (2011) — Model Risk Management** (model
  validation evidence must be retained with trusted time anchoring so the
  validator can demonstrate when a given model decision was made),

deployers can inject an `RFC3161Source` (this module) that obtains a signed
timestamp from a trusted Timestamp Authority (TSA) and stores the opaque
token alongside the parsed time. The token can later be re-verified against
the TSA's signing-cert chain by the heavier `cryptography`-backed verifier.

Stdlib-only network code. No `requests`, no `urllib3`, no `pyca/cryptography`.
RFC 3161 DER codec lives in `rfc3161_codec.py`. Full signature verification
is intentionally out of scope here — the opaque TSR is preserved verbatim.
"""

from __future__ import annotations

import base64
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class TrustedTimestamp:
    """A timestamp + optional TSA attestation."""

    asserted_at: datetime
    tsa_url: str | None
    tsr_token_b64: str | None
    hash_algorithm: str = "sha256"


class TimestampSource(Protocol):
    """Protocol — returns a `TrustedTimestamp` for a payload digest."""

    def stamp(self, payload_digest: bytes) -> TrustedTimestamp: ...


class LocalClock:
    """Default — uses `datetime.now(timezone.utc)`; no TSA attestation.

    Suitable for development and for audit chains where the trust anchor is
    the broker-dealer's WORM storage rather than a TSA signature. Production
    FSI deployments handling SEC 17a-4 or eIDAS-grade evidence should inject
    an `RFC3161Source` instead.
    """

    def stamp(self, payload_digest: bytes) -> TrustedTimestamp:
        return TrustedTimestamp(
            asserted_at=datetime.now(UTC),
            tsa_url=None,
            tsr_token_b64=None,
        )


# Backwards-compatible alias — earlier drafts named the local impl after the
# pattern, the v1.1 parity port shortens it to `LocalClock` to match cre's
# naming convention while keeping the longer name resolvable.
LocalClockTimestampSource = LocalClock


@dataclass
class RFC3161Source:
    """RFC 3161 client — sends a TSQ, receives a TSR, parses the GenTime.

    On TSA failure, falls back to local clock by default so a TSA outage
    cannot stall the audit pipeline. The fallback fires the `on_fallback`
    callback so the deployer can alert (FFIEC examiners will want evidence
    that the fallback was observed and remediated, not silently absorbed).
    Set `fallback_to_local_on_failure=False` to fail-closed instead — the
    right posture for SEC 17a-4(f) WORM-attested records where a missing
    TSA signature is a hard compliance gap.
    """

    tsa_url: str  # e.g., "https://freetsa.org/tsr"
    timeout_s: float = 5.0
    fallback_to_local_on_failure: bool = True
    on_fallback: Callable[[Exception], None] | None = None

    def stamp(self, payload_digest: bytes) -> TrustedTimestamp:
        # Validate scheme up front so callers see a clear error even when the
        # URL is wrong by configuration (not by network outage).
        url = urlparse(self.tsa_url)
        if url.scheme not in ("http", "https"):
            raise ValueError(f"tsa_url must be http or https; got {url.scheme!r}")

        from finserv_agent_audit.governance.rfc3161_codec import (
            build_timestamp_request,
            parse_timestamp_response,
        )

        tsq = build_timestamp_request(payload_digest)
        try:
            tsr_bytes = self._post(tsq)
            asserted_at = parse_timestamp_response(tsr_bytes)
            return TrustedTimestamp(
                asserted_at=asserted_at,
                tsa_url=self.tsa_url,
                tsr_token_b64=base64.b64encode(tsr_bytes).decode("ascii"),
            )
        except Exception as exc:
            if self.fallback_to_local_on_failure:
                if self.on_fallback is not None:
                    self.on_fallback(exc)
                return LocalClock().stamp(payload_digest)
            # urllib.error.URLError inherits from OSError on CPython, so
            # callers asserting `pytest.raises(OSError)` continue to match
            # both DNS failures (gaierror) and HTTP-layer URLErrors.
            if isinstance(exc, URLError) and not isinstance(exc, OSError):
                raise OSError(str(exc)) from exc
            raise

    def _post(self, tsq_bytes: bytes) -> bytes:
        req = Request(
            self.tsa_url,
            data=tsq_bytes,
            headers={
                "Content-Type": "application/timestamp-query",
                "Content-Length": str(len(tsq_bytes)),
            },
            method="POST",
        )
        with urlopen(req, timeout=self.timeout_s) as resp:  # noqa: S310 - scheme validated above  # nosec B310 — scheme validated to http/https in stamp() before _post is called
            if resp.status != 200:
                raise RuntimeError(f"TSA returned HTTP {resp.status}")
            body: bytes = resp.read()
            return body


# Backwards-compatible alias matching the cre naming.
RFC3161TimestampSource = RFC3161Source
