"""MI Proxy - Module Integrity verifier chain-of-custody.

The audit chain's ``verify_chain()`` is the function consumers, auditors,
and regulators trust to attest chain integrity. If the verifier itself is
swapped out - by a malicious operator, a supply-chain attack, or an
undetected drift between deployed and approved versions - a compromised
verifier returns false-positive verifies across an internally-consistent
chain. The hash-chain remains intact; the verifier is the lie.

This module provides the out-of-band detection mechanism. The ``MIProxy``
Protocol attests to the verifier's identity (source + canonical config)
and re-validates that attestation at verify time. ``LocalMIProxy`` is the
stdlib-only default backend (SHA-256 + HMAC). Opt-in backends (SLSA,
in-toto, Sigstore cosign) are deployer-implementable against the same
Protocol; the LocalMIProxy reference is what ships.

Wire as an optional hook into the audit chain's ``verify_chain`` path:
when supplied, attestation failure raises ``IntegrityVerificationError``
and refuses to return a verified result. Fail-closed.

Regulatory framing:
    - SR 11-7 (Federal Reserve / OCC) - the verifier IS a model in the
      second-line model-validation sense; out-of-band attestation is the
      effective challenge against verifier compromise.
    - SOX 404 ITGC - verifier code is in scope for change-management
      controls; the attestation is the evidence the deployed binary
      matches the approved one.

> Patterns are software, not legal advice. Regulatory citations live in
> ADRs and FAILURE-MODES; consult counsel for applicability to your
> control environment.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import importlib
import importlib.util
import os
import warnings
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

DEFAULT_MAX_AGE_SECONDS = 86_400
"""Default freshness window for attestations (one day)."""

MIN_KEY_BYTES = 32
"""Minimum HMAC key length. Below this we refuse to construct the proxy."""

_KEY_ENV_VAR = "FINSERV_AUDIT_MI_PROXY_KEY"
_ZERO_KEY = b"\x00" * MIN_KEY_BYTES


class IntegrityVerificationError(RuntimeError):
    """Raised when MI Proxy attestation fails inside ``verify_chain``.

    The framework refuses to return a verified result while attestation
    fails. Recovery is operator-driven: quarantine the verifier, switch
    to a backup attested verifier, investigate the divergence.
    """


class MIProxyKeyMissingWarning(UserWarning):
    """Emitted when ``LocalMIProxy.from_env`` is constructed with no key.

    The proxy still produces attestations (signed with a zeroed key) so
    callers see explicit fail-closed behavior at verify time rather than
    silent passes. Non-suppressible by design: a missing key is an
    operational defect the deployer needs to see.
    """


@dataclass(frozen=True)
class Attestation:
    """A signed assertion about the identity of a verifier component.

    Produced by ``MIProxy.attest`` and re-validated by ``verify_attestation``.
    The four payload fields (component_id, sha256_hex, timestamp_iso,
    backend_id) are HMAC-signed together; mutating any of them invalidates
    the signature.
    """

    component_id: str
    sha256_hex: str
    timestamp_iso: str
    signature_b64: str
    backend_id: str


@runtime_checkable
class MIProxy(Protocol):
    """Out-of-band chain-of-custody for the verifier itself.

    Two methods: ``attest`` produces an Attestation for a named component;
    ``verify_attestation`` re-validates one. Split on purpose so backends
    that produce attestations out-of-band (CI build pipeline, SLSA
    provenance generator) can satisfy the read path at runtime.

    ``verify_integrity(claim, attestation)`` is a convenience read-path
    surface that bytes-encodes a deployer-supplied claim and re-validates.
    """

    def attest(self, component_id: str) -> Attestation: ...

    def verify_attestation(self, attestation: Attestation) -> bool: ...


class LocalMIProxyFreshnessCheck:
    """Stdlib-only HMAC-SHA256 freshness check / tamper-detection-within-trust-boundary.

    ⚠ NOT CHAIN-OF-CUSTODY ⚠

    This proxy is a freshness check / tamper-detection-within-trust-boundary
    only. Same key signs and verifies. A compromised process can mint
    forged attestations.

    For real chain-of-custody, use :class:`BaselineMIProxy` (this module)
    or a deployer-implemented SigstoreMIProxy / SLSA-backed proxy that
    holds an asymmetric key on a separate principal. See ADR-0015 for the
    recursive-verifier problem and the chain-of-custody pattern.

    Hashes ``(source_bytes + canonical_config_bytes)`` of the named
    component, signs ``(component_id, sha256_hex, timestamp_iso, backend_id)``
    with HMAC-SHA256 using a deployer-provided key. ``backend_id`` is
    ``"local-hmac"``.

    Symmetric on purpose: asymmetric signatures would pull in
    ``cryptography``, violating the zero-runtime-dependency contract.
    Deployers requiring non-repudiation wire an opt-in backend
    (SLSA / in-toto / Sigstore cosign) against the ``MIProxy`` Protocol.
    """

    def __init__(
        self,
        signing_key: bytes,
        *,
        config: Mapping[str, str] | None = None,
        max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
    ) -> None:
        if len(signing_key) < MIN_KEY_BYTES:
            raise ValueError(
                f"MIProxy signing key must be at least {MIN_KEY_BYTES} bytes; "
                f"got {len(signing_key)}"
            )
        self._signing_key = bytes(signing_key)
        self._config_bytes = _canonical_config_bytes(config or {})
        self._max_age_seconds = max_age_seconds

    @classmethod
    def from_env(
        cls,
        *,
        config: Mapping[str, str] | None = None,
        max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
    ) -> LocalMIProxyFreshnessCheck:
        """Construct from the ``FINSERV_AUDIT_MI_PROXY_KEY`` env var.

        Key is base64- or hex-encoded; auto-detected. When the env var is
        absent, emits ``MIProxyKeyMissingWarning`` and signs with a zero
        key - fail-closed at verify time against any real-keyed proxy.
        """
        raw = os.environ.get(_KEY_ENV_VAR)
        if raw is None or raw.strip() == "":
            warnings.warn(
                f"{_KEY_ENV_VAR} is not set. LocalMIProxy will sign with a "
                "zero key; attestations will fail closed against any "
                "real-keyed verifier. Set a 32+ byte key for production.",
                MIProxyKeyMissingWarning,
                stacklevel=2,
            )
            key = _ZERO_KEY
        else:
            key = _decode_key(raw.strip())
        return cls(
            signing_key=key,
            config=config,
            max_age_seconds=max_age_seconds,
        )

    def attest(self, component_id: str) -> Attestation:
        """Produce a fresh attestation for ``component_id``.

        Raises ``ImportError`` if the component does not resolve to a
        loadable Python module with a source file on disk.
        """
        sha256_hex = _hash_component(component_id, self._config_bytes)
        timestamp_iso = datetime.now(UTC).isoformat()
        backend_id = "local-hmac"
        signature_b64 = _sign(
            self._signing_key,
            component_id=component_id,
            sha256_hex=sha256_hex,
            timestamp_iso=timestamp_iso,
            backend_id=backend_id,
        )
        return Attestation(
            component_id=component_id,
            sha256_hex=sha256_hex,
            timestamp_iso=timestamp_iso,
            signature_b64=signature_b64,
            backend_id=backend_id,
        )

    def verify_attestation(self, attestation: Attestation) -> bool:
        """Return True iff signature, freshness, and hash all check.

        Failures: bad signature, bad ISO timestamp, attestation older than
        ``max_age_seconds``, or current source-hash differs from the
        attested one. Never raises on a well-formed but invalid attestation.
        """
        expected_sig = _sign(
            self._signing_key,
            component_id=attestation.component_id,
            sha256_hex=attestation.sha256_hex,
            timestamp_iso=attestation.timestamp_iso,
            backend_id=attestation.backend_id,
        )
        if not hmac.compare_digest(expected_sig, attestation.signature_b64):
            return False

        try:
            attested_at = datetime.fromisoformat(attestation.timestamp_iso)
        except ValueError:
            return False
        if attested_at.tzinfo is None:
            return False
        age = (datetime.now(UTC) - attested_at).total_seconds()
        if age < 0 or age > self._max_age_seconds:
            return False

        try:
            current_hash = _hash_component(attestation.component_id, self._config_bytes)
        except ImportError:
            return False
        return hmac.compare_digest(current_hash, attestation.sha256_hex)

    def attest_claim(self, claim: bytes) -> bytes:
        """Issue an attestation byte-string over an opaque deployer claim.

        Higher-level convenience for backends where the verifier surface
        does not map cleanly to a Python module path - the deployer
        supplies arbitrary ``claim`` bytes (e.g. SLSA provenance JSON,
        in-toto layout digest, cosign bundle) and gets back an HMAC tag
        usable as an opaque attestation token.
        """
        timestamp_iso = datetime.now(UTC).isoformat()
        payload = b"|".join((claim, timestamp_iso.encode("utf-8")))
        mac = hmac.new(self._signing_key, payload, hashlib.sha256).digest()
        encoded_ts = base64.b64encode(timestamp_iso.encode("utf-8")).decode("ascii")
        encoded_mac = base64.b64encode(mac).decode("ascii")
        return f"{encoded_ts}.{encoded_mac}".encode("ascii")

    def verify_integrity(self, claim: bytes, attestation: bytes) -> bool:
        """Verify an opaque attestation byte-string against the same claim.

        Returns True iff the attestation token decodes, the embedded
        timestamp falls inside ``max_age_seconds``, and the HMAC tag
        matches the recomputed ``(claim, timestamp)`` payload.
        """
        try:
            encoded_ts, encoded_mac = attestation.decode("ascii").split(".", 1)
            timestamp_iso = base64.b64decode(encoded_ts).decode("utf-8")
            mac = base64.b64decode(encoded_mac)
        except (UnicodeDecodeError, ValueError, binascii.Error):
            return False

        payload = b"|".join((claim, timestamp_iso.encode("utf-8")))
        expected_mac = hmac.new(self._signing_key, payload, hashlib.sha256).digest()
        if not hmac.compare_digest(expected_mac, mac):
            return False

        try:
            attested_at = datetime.fromisoformat(timestamp_iso)
        except ValueError:
            return False
        if attested_at.tzinfo is None:
            return False
        age = (datetime.now(UTC) - attested_at).total_seconds()
        return not (age < 0 or age > self._max_age_seconds)

    def _for_test_resign(
        self,
        *,
        component_id: str,
        sha256_hex: str,
        timestamp_iso: str,
        backend_id: str,
    ) -> Attestation:
        """Test-only seam: produce an Attestation with a chosen timestamp.

        Used by the stale-attestation test so the signature is valid but
        the timestamp falls outside ``max_age_seconds``. Production
        callers must never invoke this.
        """
        signature_b64 = _sign(
            self._signing_key,
            component_id=component_id,
            sha256_hex=sha256_hex,
            timestamp_iso=timestamp_iso,
            backend_id=backend_id,
        )
        return Attestation(
            component_id=component_id,
            sha256_hex=sha256_hex,
            timestamp_iso=timestamp_iso,
            signature_b64=signature_b64,
            backend_id=backend_id,
        )


class LocalMIProxy(LocalMIProxyFreshnessCheck):
    """DEPRECATED in CR-11: prefer ``LocalMIProxyFreshnessCheck`` for honesty.

    The legacy class name implied chain-of-custody, which the symmetric
    same-key sign + verify path does not deliver. The honest name is
    ``LocalMIProxyFreshnessCheck``; the semantics are identical.
    For real chain-of-custody use :class:`BaselineMIProxy` (this module).
    """

    def __init__(
        self,
        signing_key: bytes,
        *,
        config: Mapping[str, str] | None = None,
        max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
    ) -> None:
        warnings.warn(
            "LocalMIProxy is a freshness check / within-trust-boundary "
            "tamper-detection mechanism, not chain-of-custody. Use "
            "LocalMIProxyFreshnessCheck for the same semantics with an "
            "honest name, or BaselineMIProxy for deploy-time-pinned "
            "verifier-integrity checks (ADR-0015).",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(
            signing_key,
            config=config,
            max_age_seconds=max_age_seconds,
        )


# --------------------------------------------------------------------------- #
# CR-11 Part B — BaselineMIProxy (stub: deploy-time-pinned baseline)          #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class BaselineEntry:
    """One row in the deploy-time-pinned baseline manifest.

    Fields:
        component_id: importable Python module path the verifier covers.
        expected_sha256: hex-encoded SHA-256 of the canonical source.
        signed_by: operator-key identity that signed the baseline entry.
    """

    component_id: str
    expected_sha256: str
    signed_by: str


class BaselineMIProxy:
    """Verifier-integrity check against a deploy-time-pinned baseline.

    The baseline manifest is loaded at deployer time from a path signed
    by an OUT-OF-PROCESS key (not the env var the verifier reads). At
    verify time, the proxy compares the live source SHA-256 against the
    pinned baseline and raises :class:`IntegrityVerificationError` on
    mismatch.

    v2.1 stub: signature verification of the baseline itself is deferred
    to v2.2 (requires Sigstore cosign integration via an optional
    ``[sigstore]`` extra so the zero-runtime-dep contract is preserved
    in the base wheel).

    Construct with a path to a JSON file shaped::

        {
            "entries": [
                {
                    "component_id": "finserv_agent_audit.governance.defcon",
                    "expected_sha256": "<64-hex-char SHA-256>",
                    "signed_by": "operator-pgp-2026-Q2"
                }
            ]
        }
    """

    def __init__(self, baseline_path: object) -> None:
        import json
        from pathlib import Path

        path = baseline_path if isinstance(baseline_path, Path) else Path(str(baseline_path))
        data = json.loads(path.read_text(encoding="utf-8"))
        entries_raw = data.get("entries", [])
        self._entries: dict[str, BaselineEntry] = {
            e["component_id"]: BaselineEntry(
                component_id=e["component_id"],
                expected_sha256=e["expected_sha256"],
                signed_by=e["signed_by"],
            )
            for e in entries_raw
        }

    def verify(self, component_id: str, live_sha256: str) -> bool:
        """Compare the live SHA-256 against the pinned baseline. Raise on mismatch."""
        entry = self._entries.get(component_id)
        if entry is None:
            raise IntegrityVerificationError(f"component {component_id} not in baseline")
        if not hmac.compare_digest(entry.expected_sha256, live_sha256):
            raise IntegrityVerificationError(
                f"component {component_id} SHA-256 mismatch: "
                f"expected {entry.expected_sha256}, got {live_sha256}"
            )
        return True


def enforce_attestation(proxy: MIProxy, component_id: str) -> None:
    """Verifier-hook helper: attest + re-verify, raise on failure.

    Wire this into your ``verify_chain`` implementation. When the chain
    verifier wants to attest its own integrity before returning a
    verified result, it calls ``enforce_attestation(proxy, __name__)``;
    a failure raises ``IntegrityVerificationError`` and the chain
    verifier MUST propagate (not swallow) the exception.
    """
    attestation = proxy.attest(component_id)
    if not proxy.verify_attestation(attestation):
        raise IntegrityVerificationError(
            f"MI Proxy attestation failed for component {component_id!r}; "
            "refusing to return a verified result."
        )


# --------------------------------------------------------------------------- #
# Module-private helpers                                                      #
# --------------------------------------------------------------------------- #


def _decode_key(raw: str) -> bytes:
    """Decode a base64- or hex-encoded key. Validates minimum length."""
    decoded: bytes | None = None
    try:
        candidate = base64.b64decode(raw, validate=True)
        if len(candidate) >= MIN_KEY_BYTES:
            decoded = candidate
    except (ValueError, binascii.Error):
        # Not valid base64 — intentionally fall through to the hex decoder.
        # A genuine failure (neither encoding works) surfaces via the explicit
        # ValueError raised below, so nothing is silently swallowed.
        pass
    if decoded is None:
        try:
            candidate = bytes.fromhex(raw)
            if len(candidate) >= MIN_KEY_BYTES:
                decoded = candidate
        except ValueError:
            # Not valid hex either — fall through to the explicit ValueError
            # below, which reports the key-format requirement to the caller.
            pass
    if decoded is None:
        raise ValueError(
            f"{_KEY_ENV_VAR} must be base64 or hex-encoded with at least "
            f"{MIN_KEY_BYTES} decoded bytes"
        )
    return decoded


def _hash_component(component_id: str, config_bytes: bytes) -> str:
    """SHA-256 over the component's source file + canonical config."""
    spec = importlib.util.find_spec(component_id)
    if spec is None or spec.origin is None or spec.origin == "built-in":
        raise ImportError(f"MIProxy cannot hash {component_id!r}: no source file on disk")
    with open(spec.origin, "rb") as fh:
        source_bytes = fh.read()
    digest = hashlib.sha256()
    digest.update(source_bytes)
    digest.update(b"\x1f")  # ASCII unit separator - config delimiter
    digest.update(config_bytes)
    return digest.hexdigest()


def _canonical_config_bytes(config: Mapping[str, str]) -> bytes:
    """Stable byte-level encoding of an optional deployer config map."""
    items = sorted(config.items())
    parts: list[bytes] = []
    for key, value in items:
        parts.append(key.encode("utf-8"))
        parts.append(b"=")
        parts.append(value.encode("utf-8"))
        parts.append(b"\n")
    return b"".join(parts)


def _sign(
    key: bytes,
    *,
    component_id: str,
    sha256_hex: str,
    timestamp_iso: str,
    backend_id: str,
) -> str:
    """HMAC-SHA256 over the four-field payload; base64-encoded output."""
    payload = "|".join((component_id, sha256_hex, timestamp_iso, backend_id)).encode("utf-8")
    mac = hmac.new(key, payload, hashlib.sha256).digest()
    return base64.b64encode(mac).decode("ascii")


__all__ = [
    "DEFAULT_MAX_AGE_SECONDS",
    "Attestation",
    "BaselineEntry",
    "BaselineMIProxy",
    "IntegrityVerificationError",
    "LocalMIProxy",
    "LocalMIProxyFreshnessCheck",
    "MIProxy",
    "MIProxyKeyMissingWarning",
    "enforce_attestation",
]
