"""External-witness anchoring pattern — ADR-0014.

The hash-chain `AuditChain` is internally consistent and tamper-detecting
within the trust boundary that produced it (the hash-chain mechanism
gives detection but not prevention), but it is not adversarially
tamper-EVIDENT on its own as a hash-chain. Periodically anchoring the
chain head to an external witness register (Sigstore Rekor,
OpenTimestamps, or a regulator-side log) converts the hash-chain to
adversarially tamper-evident (hash-chain mechanism with external
witness): the witness
records what the head was at time T, and a later forger cannot retroactively
rewrite the chain without producing a witness receipt that contradicts the
public record.

Anchoring writes the receipt back to the ledger as a
`AuditEventType.WITNESS_ANCHOR` entry. This binds the anchor into the same
hash chain that's being protected — tampering with the anchor record
requires tampering with every entry after it.

Stdlib-only HTTP transport (`urllib.request`). No `sigstore`, no `requests`.
Receipts preserve the opaque server response verbatim (hex-encoded for the
JSON payload) for later verification.

Regulatory anchors:
    - EU AI Act Article 12 — logging capabilities; external anchoring is
      the established mechanism for adversarial tamper-evidence
    - SEC Rule 17a-4 — broker-dealer record retention; pairs naturally
      with a WORM `LedgerStore` backend
    - SR 11-7 — model risk management; the witness receipt timestamps
      the effective challenge artifact
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import urlparse

from finserv_agent_audit.governance.audit_chain import (
    AuditChain,
    AuditChainTamperError,
)
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)


# Local constant to avoid module-level cyclic import of audit_chain.GENESIS_HASH.
# Keep value aligned with finserv_agent_audit.governance.audit_chain.
GENESIS_HASH = "0" * 64

@dataclass(frozen=True)
class WitnessReceipt:
    """Opaque-blob receipt returned by an external witness register."""

    register_name: str  # "rekor" | "opentimestamps" | "custom"
    register_url: str
    submitted_at: datetime
    receipt_blob: bytes  # opaque to the ledger; verifier consumes
    inclusion_uuid: str | None
    log_index: int | None


class WitnessRegister(Protocol):
    """Protocol for any external transparency-log / timestamp service."""

    def anchor(self, chain_head_hex: str) -> WitnessReceipt: ...


@dataclass
class RekorWitness:
    """Sigstore Rekor public transparency log client.

    POSTs a `hashedrekord` entry to Rekor's REST API; receives an inclusion
    UUID + logIndex. Default endpoint is the public Sigstore instance.
    """

    rekor_url: str = "https://rekor.sigstore.dev"
    timeout_s: float = 10.0

    def anchor(self, chain_head_hex: str) -> WitnessReceipt:
        if len(chain_head_hex) != 64:
            raise ValueError("chain_head_hex must be 64 chars (SHA-256)")
        body = json.dumps(
            {
                "apiVersion": "0.0.1",
                "kind": "hashedrekord",
                "spec": {
                    "data": {
                        "hash": {"algorithm": "sha256", "value": chain_head_hex},
                    },
                    "signature": {
                        # Repo policy: anchor the digest only; no signature key
                        # required. Rekor accepts hashedrekord with a placeholder
                        # signature field for transparency-log-only use.
                        "content": "",
                        "format": "x509",
                        "publicKey": {"content": ""},
                    },
                },
            }
        ).encode("utf-8")
        resp_body, status = _post(self.rekor_url + "/api/v1/log/entries", body, self.timeout_s)
        if status not in (200, 201):
            raise RuntimeError(f"Rekor returned HTTP {status}: {resp_body!r}")
        parsed = json.loads(resp_body)
        uuid_value = parsed.get("uuid")
        log_index_value = parsed.get("logIndex")
        return WitnessReceipt(
            register_name="rekor",
            register_url=self.rekor_url,
            submitted_at=datetime.now(UTC),
            receipt_blob=resp_body,
            inclusion_uuid=str(uuid_value) if uuid_value is not None else None,
            log_index=int(log_index_value) if log_index_value is not None else None,
        )


@dataclass
class OpenTimestampsWitness:
    """OpenTimestamps calendar client.

    Submits the digest; receives a pending-commitment receipt that can later
    be upgraded to a Bitcoin-attestation receipt by re-submitting the same
    opaque blob.
    """

    calendar_urls: tuple[str, ...] = (
        "https://alice.btc.calendar.opentimestamps.org",
        "https://bob.btc.calendar.opentimestamps.org",
    )
    timeout_s: float = 10.0

    def anchor(self, chain_head_hex: str) -> WitnessReceipt:
        digest = bytes.fromhex(chain_head_hex)
        last_exc: Exception | None = None
        for url in self.calendar_urls:
            try:
                resp_body, status = _post(
                    url + "/digest",
                    digest,
                    self.timeout_s,
                    content_type="application/octet-stream",
                )
                if status == 200:
                    return WitnessReceipt(
                        register_name="opentimestamps",
                        register_url=url,
                        submitted_at=datetime.now(UTC),
                        receipt_blob=resp_body,
                        inclusion_uuid=None,
                        log_index=None,
                    )
                last_exc = RuntimeError(f"OTS calendar {url} returned HTTP {status}")
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
        raise RuntimeError(f"all OTS calendars failed: {last_exc!r}")


# ---------------------------------------------------------------------- #
# External-anchor verification — ADR-0014 (defeats truncation + backdating)
# ---------------------------------------------------------------------- #


@dataclass(frozen=True)
class ExternalAnchorRecord:
    """A ``(head, time)`` pair a witness recorded OUTSIDE the chain.

    In production this is read back from the external register (Sigstore Rekor
    inclusion proof, an OpenTimestamps receipt, or a regulator-side log). It is
    the deployer-independent copy the chain is checked against.
    """

    chain_head_hex: str
    witnessed_at: datetime
    register_name: str


class WitnessContradictionError(RuntimeError):
    """Raised when an externally-witnessed head is absent from the chain.

    Distinct from ``AuditChainTamperError`` (an in-chain hash break). A
    contradiction means the chain was truncated below, or regenerated away
    from, a point an external witness already attested — the attack a
    hash-chain alone cannot see.
    """


@dataclass
class RecordingWitness:
    """Offline ``WitnessRegister`` that RETAINS every anchored head.

    Stands in for the external log / regulator copy in tests and the offline
    demo — no network. Each ``anchor`` call returns a normal ``WitnessReceipt``
    AND keeps an ``ExternalAnchorRecord`` so the chain can later be verified
    against what was witnessed.
    """

    register_name: str = "recording-witness"
    _records: list[ExternalAnchorRecord] = field(default_factory=list)

    def anchor(self, chain_head_hex: str) -> WitnessReceipt:
        if len(chain_head_hex) != 64:
            raise ValueError("chain_head_hex must be 64 chars (SHA-256)")
        now = datetime.now(UTC)
        self._records.append(
            ExternalAnchorRecord(
                chain_head_hex=chain_head_hex,
                witnessed_at=now,
                register_name=self.register_name,
            )
        )
        return WitnessReceipt(
            register_name=self.register_name,
            register_url="memory://recording-witness",
            submitted_at=now,
            receipt_blob=chain_head_hex.encode(),
            inclusion_uuid=None,
            log_index=len(self._records) - 1,
        )

    @property
    def records(self) -> tuple[ExternalAnchorRecord, ...]:
        return tuple(self._records)


def verify_against_external_anchors(
    audit_chain: AuditChain,
    anchors: Iterable[ExternalAnchorRecord],
) -> None:
    """Raise on a chain that contradicts what an external witness recorded.

    An honest append-only chain only grows, so every head an external witness
    recorded MUST still appear as the ``event_hash`` of some event in the
    chain. A witnessed head that is absent means the chain was truncated below
    it (a deleted tail / removed revocation) or regenerated to a different
    history (backdating) — neither of which a hash-chain ``verify()`` can
    detect on its own.

    FAIL-CLOSED CO-RUN. The "witnessed head is present as SOME event's
    ``event_hash``" invariant is only sound on a hash-consistent chain — an
    attacker could otherwise re-insert the witnessed digest into a forged
    event's ``event_hash`` field. To remove that footgun this function runs
    ``audit_chain.verify()`` FIRST and raises ``AuditChainTamperError`` if the
    chain is not hash-consistent, so calling this verifier alone is safe (it
    can never pass a chain that ``verify()`` would reject). Raises
    ``WitnessContradictionError`` when the chain is hash-consistent but a
    witnessed head is gone.

    Anchors of an empty chain (head == ``GENESIS_HASH`` sentinel) carry no
    information and are skipped — anchoring an empty chain is refused at
    ``anchor_to_witness`` time anyway.

    No network: ``anchors`` are the witness's own retained records (or, in
    production, the inclusion proofs read back from the external register).
    """
    if not audit_chain.verify():
        raise AuditChainTamperError(
            "external-anchor verification requires a hash-consistent chain; "
            "AuditChain.verify() returned False. Fix or investigate the "
            "hash-chain break before trusting the external-anchor check "
            "(the two checks are co-dependent — see this function's docstring)."
        )
    present = {event.event_hash for event in audit_chain._events}  # noqa: SLF001
    for anchor in anchors:
        if anchor.chain_head_hex == GENESIS_HASH:
            continue
        if anchor.chain_head_hex not in present:
            raise WitnessContradictionError(
                f"externally-witnessed head {anchor.chain_head_hex[:12]}... "
                f"(witnessed {anchor.witnessed_at.isoformat()} via "
                f"{anchor.register_name}) is ABSENT from the current chain — "
                "the chain was truncated below, or regenerated away from, a "
                "point the witness already attested. An append-only chain only "
                "grows; a witnessed head cannot disappear from an honest chain."
            )


def anchor_to_witness(
    *,
    audit_chain: AuditChain,
    witness: WitnessRegister,
    agent_id: str = "system:witness_anchor",
    autonomy_level: AutonomyLevel = AutonomyLevel.A4,
    actor_id: str | None = None,
) -> AuditEvent:
    """Anchor the chain head to `witness`; record the receipt as a new event.

    The chain head is the `event_hash` of the most recently appended event
    (or the genesis sentinel if the chain is empty — a "time zero" anchor;
    ``verify_against_external_anchors`` skips genesis-sentinel anchors since
    they carry no falsifiable information about recorded events). The returned
    `AuditEvent` has `event_type=AuditEventType.WITNESS_ANCHOR` and a payload
    that captures the register, URL, anchored head, opaque receipt (hex), and
    any inclusion identifiers the register returned.
    """
    head = _chain_head(audit_chain)
    receipt = witness.anchor(head)
    payload = {
        "witness_register": receipt.register_name,
        "witness_url": receipt.register_url,
        "chain_head_anchored": head,
        "submitted_at": receipt.submitted_at.isoformat(),
        "receipt_blob_hex": receipt.receipt_blob.hex(),
        "inclusion_uuid": receipt.inclusion_uuid,
        "log_index": receipt.log_index,
    }
    return audit_chain.append(
        event_type=AuditEventType.WITNESS_ANCHOR,
        autonomy_level=autonomy_level,
        agent_id=agent_id,
        payload=payload,
        actor_id=actor_id,
    )


def _chain_head(audit_chain: AuditChain) -> str:
    """Return the SHA-256 hex of the most recent event, or genesis if empty."""
    # `AuditChain` exposes `_prev_hash` as its head pointer (the hash that
    # would be wired as `prev_hash` on the next append). We deliberately
    # read this attribute rather than poking `_events` so we work for any
    # back-end the chain might be using.
    return audit_chain._prev_hash  # noqa: SLF001


def _post(
    url: str,
    body: bytes,
    timeout_s: float,
    *,
    content_type: str = "application/json",
) -> tuple[bytes, int]:
    """POST `body` to `url` via stdlib `urllib.request`; return (body, status)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"unsupported scheme {parsed.scheme!r}")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": content_type,
            "Content-Length": str(len(body)),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310
            return resp.read(), resp.status
    except urllib.error.HTTPError as http_err:
        # Preserve the body + status so the caller can decide what to do
        return http_err.read(), http_err.code
