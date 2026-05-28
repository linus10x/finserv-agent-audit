"""Internally-Consistent Hash-Chained Audit Ledger — ADR-0003.

Every governance event is appended to a chain where each entry contains
the SHA-256 hash of the previous entry. Modifying any past entry breaks
the SHA-256 link at the modified point and every entry that follows —
detectable by an honest holder of the current chain head.

**Important framing.** This ledger is an *internally consistent*
hash-chain by construction (SHA-256 prev-hash links provide detection
but not prevention within the trust boundary). It is **not
adversarially tamper-evident on its own** as a hash-chain mechanism: an
attacker with full write access to the storage layer can regenerate the
entire chain end-to-end, and the regenerated chain will pass ``verify()``.
For adversarial integrity, the chain head must be periodically anchored
to an **external witness register** that the deployer does not control
alone: OpenTimestamps, Sigstore Rekor, a regulator-side append-only log,
or a notarized blockchain anchor. See ADR-0014 and the
``WitnessRegister`` Protocol in ``witness_anchor.py``.

For FSI deployments handling SEC 17a-4 (broker-dealer electronic records
— non-rewriteable, non-erasable), pair this chain with a WORM-backed
``LedgerStore`` (see ``ledger_store_worm.py``) and an RFC 3161 trusted
timestamp source (see ``timestamp_source.py``).

v1.1 extraction note. In v1.0 the ``AuditChain`` class lived inside
``schemas/audit_event.py`` and wrote to a JSONL file directly. In v1.1
the chain logic is extracted to this module so it can consume the four
Protocol seams shipped under Tranche 2:

    - ``LedgerStore`` — pluggable storage (in-memory, JSONL, SQLite, WORM)
    - ``TimestampSource`` — pluggable time anchor (LocalClock or RFC 3161 TSA)
    - ``WitnessRegister`` — optional external witness for adversarial evidence
    - ``MIProxy`` — optional verifier attestation (out-of-band integrity)

Defaults preserve v1.0 behavior. Passing no seams gives you the original
JSONL-file-backed chain with local-clock timestamps and no witness/MI.

See ADR-0003 for the audit-evidence framing under SOC 2 CC7.2 / SOX 404
ITGC / FFIEC IT examination handbook, and ADR-0017 for the retention,
privilege, and discovery posture.

The implementation is stdlib-only — the governance ledger keeps writing
even when the rest of the system is in DEFCON-1 (per ADR-0001).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)

if TYPE_CHECKING:
    from finserv_agent_audit.governance.ledger_store import LedgerStore
    from finserv_agent_audit.governance.mi_proxy import MIProxy
    from finserv_agent_audit.governance.timestamp_source import TimestampSource
    from finserv_agent_audit.governance.witness_anchor import WitnessRegister


VERIFIER_COMPONENT_ID = "finserv_agent_audit.governance.audit_chain"
"""Stable identifier for this verifier; passed to ``MIProxy.attest``."""

GENESIS_HASH = "0" * 64
"""Sentinel value for the first entry's ``prev_hash``. SHA-256 zeroes."""


class AuditChainTamperError(RuntimeError):
    """Raised by ``AuditChain.verify_strict`` when a mismatch is detected.

    Names the failing sequence index and the failure mode (event_hash
    mismatch vs prev_hash mismatch) so a regulator-facing investigation
    can pinpoint the corruption window.
    """


class AuditChain:
    """Append-only, hash-chained audit ledger.

    v1.0 backward-compatible. The constructor accepts a ``log_file``
    (preserving the original JSONL-on-disk behavior) OR a fully-injected
    set of Protocol seams. When a ``ledger_store`` is supplied, the
    ``log_file`` argument is ignored — the store owns persistence.

    Usage (v1.0 compatible)::

        chain = AuditChain(log_file=Path("audit.jsonl"))
        event = chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="zeus",
            payload={"action": "enter_position", "ticker": "SPY"},
        )
        assert chain.verify()  # True if untampered

    Usage (v1.1 with Protocol seams)::

        chain = AuditChain(
            ledger_store=WORMLedgerStore(...),
            timestamp_source=RFC3161Source(tsa_url="https://freetsa.org/tsr"),
            witness_register=RekorWitness(),
            mi_proxy=LocalMIProxy.from_env(),
        )
    """

    GENESIS_HASH = GENESIS_HASH

    def __init__(
        self,
        log_file: Path | None = None,
        ledger_store: LedgerStore | None = None,
        timestamp_source: TimestampSource | None = None,
        witness_register: WitnessRegister | None = None,
        mi_proxy: MIProxy | None = None,
    ) -> None:
        # Resolve seams with v1.0-preserving defaults. The
        # InMemoryLedgerStore + JSONL-file pair preserves the original
        # behavior: events are kept in memory for fast iteration AND
        # written to a JSONL file for replay across process boundaries.
        from finserv_agent_audit.governance.ledger_store import (
            InMemoryLedgerStore,
        )
        from finserv_agent_audit.governance.timestamp_source import LocalClock

        self._external_store: bool = ledger_store is not None
        self._store: LedgerStore = ledger_store or InMemoryLedgerStore()
        self._timestamp_source: TimestampSource = timestamp_source or LocalClock()
        self._witness_register: WitnessRegister | None = witness_register
        self._mi_proxy: MIProxy | None = mi_proxy

        # Only honor the legacy JSONL log-file path when no external store
        # is supplied. Stores own their own persistence — mixing both
        # would write each event twice.
        self.log_file: Path | None
        if self._external_store:
            self.log_file = None
        else:
            self.log_file = log_file or Path("output/audit_chain.jsonl")

        # Replay any existing JSONL log into the in-memory store so the
        # chain head is correct across restarts (v1.0 contract).
        if not self._external_store and self.log_file is not None:
            self._load_existing()

    # ------------------------------------------------------------------ #
    # v1.0-compatible accessors                                          #
    # ------------------------------------------------------------------ #

    @property
    def _events(self) -> list[AuditEvent]:
        """Backward-compat accessor — tests reach into this list.

        Returns a live reference when the store is the in-memory
        reference; for external stores returns a materialized list.
        """
        from finserv_agent_audit.governance.ledger_store import (
            InMemoryLedgerStore,
        )

        if isinstance(self._store, InMemoryLedgerStore):
            return self._store._events
        return list(self._store)

    @property
    def _prev_hash(self) -> str:
        """Current chain head; ``GENESIS_HASH`` for an empty chain."""
        return self._store.head_event_hash()

    # ------------------------------------------------------------------ #
    # Append + verify                                                    #
    # ------------------------------------------------------------------ #

    def append(
        self,
        event_type: AuditEventType,
        autonomy_level: AutonomyLevel,
        agent_id: str,
        payload: dict[str, Any],
        actor_id: str | None = None,
    ) -> AuditEvent:
        """Append a new event to the chain and persist it."""
        # Pull the trusted timestamp first so it can be folded into the
        # event payload. LocalClock is free; RFC3161Source crosses the
        # network. We accept the cost so the trusted time is bound into
        # the chained hash, not appended after the fact.
        timestamp_iso = self._timestamp_source.stamp(b"").asserted_at.isoformat()

        event = AuditEvent(
            event_type=event_type,
            autonomy_level=autonomy_level,
            agent_id=agent_id,
            payload=payload,
            prev_hash=self._store.head_event_hash(),
            actor_id=actor_id,
            timestamp=timestamp_iso,
        )
        self._store.append(event)

        # Mirror to JSONL only when running in v1.0 default mode (no
        # external store supplied). External stores persist on append().
        if not self._external_store and self.log_file is not None:
            self._write(event)
        return event

    def verify(self) -> bool:
        """Replay the chain and verify every hash. Returns False if tampered.

        Soft-failure variant — preserves the v1.0 return contract.
        For strict (raise on tamper) plus optional MI Proxy verifier
        attestation, call ``verify_strict``.
        """
        prev = GENESIS_HASH
        for event in self._store:
            expected = event._compute_hash()
            if event.event_hash != expected:
                return False
            if event.prev_hash != prev:
                return False
            prev = event.event_hash
        return True

    def verify_strict(self, *, mi_proxy: MIProxy | None = None) -> None:
        """Raise ``AuditChainTamperError`` on any inconsistency.

        Two in-chain failure modes are detected:

        - ``event_hash mismatch`` — the entry's stored ``event_hash``
          does not match a freshly-computed hash of its fields (something
          inside the entry was changed after writing).
        - ``prev_hash mismatch`` — the entry's ``prev_hash`` does not
          match the previous entry's ``event_hash`` (chain link broken).

        When ``mi_proxy`` is supplied (ADR-0015), the verifier's own
        integrity is checked first. Fail-closed — the chain is not
        walked when the verifier itself cannot be attested. If no proxy
        is passed explicitly, the constructor-injected proxy is used.
        """
        proxy = mi_proxy if mi_proxy is not None else self._mi_proxy
        if proxy is not None:
            from finserv_agent_audit.governance.mi_proxy import (
                IntegrityVerificationError,
            )

            attestation = proxy.attest(VERIFIER_COMPONENT_ID)
            if not proxy.verify_attestation(attestation):
                raise IntegrityVerificationError(
                    f"MI Proxy attestation failed for "
                    f"{VERIFIER_COMPONENT_ID!r}; refusing to return "
                    "a verified result"
                )

        prev = GENESIS_HASH
        for index, event in enumerate(self._store):
            expected = event._compute_hash()
            if event.event_hash != expected:
                raise AuditChainTamperError(
                    f"event_hash mismatch at index {index} (event_id={event.event_id!r})"
                )
            if event.prev_hash != prev:
                raise AuditChainTamperError(
                    f"prev_hash mismatch at index {index} "
                    f"(event_id={event.event_id!r}): "
                    f"expected {prev!r}, got {event.prev_hash!r}"
                )
            prev = event.event_hash

    def chain_head(self) -> str:
        """Return the chain head — the current ``event_hash`` of the last entry.

        Publish this value periodically to an external witness register
        (OpenTimestamps, Sigstore Rekor, regulator log) to convert the
        internally-consistent hash-chain into an adversarially
        tamper-evident (hash-chain mechanism) record. Returns the
        genesis sentinel for an empty chain.
        """
        return self._store.head_event_hash()

    def anchor_to_witness(self) -> AuditEvent | None:
        """Anchor the current chain head to the injected witness register.

        Writes the receipt back to the chain as a
        ``AuditEventType.WITNESS_ANCHOR`` event so the receipt is itself
        hash-chained — tampering with the receipt requires tampering
        with every entry after it. Returns the receipt-bearing event,
        or ``None`` when no witness register is configured.

        Convenience wrapper over the standalone ``anchor_to_witness``
        helper in ``witness_anchor.py``.
        """
        if self._witness_register is None:
            return None
        from finserv_agent_audit.governance.witness_anchor import (
            anchor_to_witness as _anchor,
        )

        return _anchor(audit_chain=self, witness=self._witness_register)

    # ------------------------------------------------------------------ #
    # JSONL persistence (v1.0 default-mode only)                         #
    # ------------------------------------------------------------------ #

    def _write(self, event: AuditEvent) -> None:
        if self.log_file is None:
            return
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_file, "a", encoding="utf-8") as fh:
            fh.write(event.to_jsonl() + "\n")

    def _load_existing(self) -> None:
        if self.log_file is None:
            return
        p = Path(self.log_file)
        if not p.exists():
            return
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            event = AuditEvent(
                event_type=AuditEventType(data["event_type"]),
                autonomy_level=AutonomyLevel(data["autonomy_level"]),
                agent_id=data["agent_id"],
                payload=data["payload"],
                prev_hash=data["prev_hash"],
                event_id=data["event_id"],
                timestamp=data["timestamp"],
                actor_id=data.get("actor_id"),
                schema_version=data.get("schema_version", "1.0.0"),
            )
            # Round-trip preserves the stored event_hash; in deterministic
            # cases recomputation yields the same value, but we explicitly
            # restore for fidelity with on-disk records.
            event.event_hash = data["event_hash"]
            self._store.append(event)
