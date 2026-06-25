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

import hashlib
import json
import sys
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

# CR-4 — POSIX-only file-lock import. On Windows ``fcntl`` is
# unavailable; the v1.0 default-mode JSONL writes fall back to the
# in-process append_lock alone. See ``ledger_store_jsonl`` module
# docstring for the documented Windows caveat.
if sys.platform != "win32":
    import fcntl
else:  # pragma: no cover - exercised on Windows hosts only
    fcntl = None  # type: ignore[assignment]

from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)

SCHEMA_VERSION = "1.0.0"
"""Default schema version stamped on events the chain constructs."""

if TYPE_CHECKING:
    from finserv_agent_audit.governance.ledger_store import LedgerStore
    from finserv_agent_audit.governance.mi_proxy import MIProxy
    from finserv_agent_audit.governance.timestamp_source import TimestampSource
    from finserv_agent_audit.governance.witness_anchor import WitnessRegister


VERIFIER_COMPONENT_ID = "finserv_agent_audit.governance.audit_chain"
"""Stable identifier for this verifier; passed to ``MIProxy.attest``."""

GENESIS_HASH = "0" * 64
"""Legacy sentinel value for the first entry's ``prev_hash``.

CR-7 (v2.0) — chains now derive a per-deployer genesis hash via
``_compute_genesis_hash(deployer_id, chain_creation_iso)``; the SHA-256
zeroes sentinel is retained only for backward-compat detection of
pre-CR-7 chains and for callers that still import the symbol. New
chains MUST use the deployer-keyed derivation; loading a legacy chain
whose first event's ``prev_hash`` equals this sentinel emits a
``DeprecationWarning`` recommending re-creation with an explicit
``deployer_id``.
"""

GENESIS_DOMAIN_SEPARATOR = "finserv-agent-audit/genesis/v1"
"""Domain-separation tag for ``_compute_genesis_hash``.

Bumping the ``v1`` suffix is a chain-format break: a chain seeded
under ``v1`` will not re-verify against a chain seeded under ``v2``
even when ``deployer_id`` and ``chain_creation_iso`` are unchanged.
The version is baked into the seed so deployers can audit the
genesis discipline by inspecting the on-disk event #0 payload.
"""

GENESIS_AGENT_ID = "finserv-audit-chain"
"""``agent_id`` carried on the GENESIS event #0.

A fixed identifier so verifiers can locate the genesis event by name
without scanning. Tested in
``tests/test_genesis_domain_separation.py``.
"""

GENESIS_VERSION = "v1"
"""Stamped on event #0 payload so verifiers can branch on format."""


def _compute_genesis_hash(deployer_id: str, chain_creation_iso: str) -> str:
    """CR-7 — Deployer-keyed seed for the genesis event's ``prev_hash``.

    The seed is ``SHA-256(domain_separator/deployer_id/chain_creation_iso)``
    where the domain separator is the constant ``GENESIS_DOMAIN_SEPARATOR``.
    The seed is the genesis event #0's ``prev_hash``; the event itself
    has an ``event_hash`` computed over its full fields (including the
    seed-as-prev_hash). Subsequent events derive their ``prev_hash``
    from the genesis event's ``event_hash``.

    Two chains with different ``deployer_id`` produce different seeds;
    two chains with different ``chain_creation_iso`` produce different
    seeds. An attacker without the deployer's identity cannot
    regenerate a chain from scratch and have it match an existing
    deployer's head.
    """
    payload = f"{GENESIS_DOMAIN_SEPARATOR}/{deployer_id}/{chain_creation_iso}".encode()
    return hashlib.sha256(payload).hexdigest()


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
        deployer_id: str | None = None,
        chain_creation_iso: str | None = None,
    ) -> None:
        """CR-7 — chains are seeded with a deployer-keyed genesis event.

        New parameters:

          * ``deployer_id`` — string the deployer uses to identify
            their environment (e.g. ``"acme-bank-prod"``). Folded into
            the genesis seed so an attacker who can rewrite the
            storage layer cannot regenerate a chain from scratch and
            have it match the legitimate deployer's chain head. When
            omitted, a hostname-based default is used and the chain
            is still domain-separated, but the deployer is encouraged
            to pass an explicit value.

          * ``chain_creation_iso`` — ISO-8601 UTC timestamp folded
            into the seed alongside the deployer_id. When omitted,
            ``datetime.now(UTC).isoformat()`` is used at construction
            time. Passing an explicit value makes the seed
            reproducible across hosts (useful for cross-deployment
            verification tests).

        Backward compat: when a JSONL log is replayed and the FIRST
        event's ``prev_hash`` equals the legacy ``"0"*64`` sentinel,
        the chain is accepted with a ``DeprecationWarning`` rather
        than rebuilt; the deployer is told to re-create the chain
        with an explicit deployer_id.
        """
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

        # CR-4 — serialize append + verify against TOCTOU on head_event_hash.
        # An ``RLock`` is used (not a plain ``Lock``) because
        # ``anchor_to_witness`` re-enters ``append`` to record the
        # witness receipt as its own chained event. A plain Lock would
        # deadlock; the re-entrant Lock honors the same-thread
        # re-acquire semantics.
        self._append_lock = threading.RLock()

        # CR-7 — resolve the deployer identity. An explicit value
        # wins; ``deployer_id=None`` (the v1.x call signature) is
        # honored as legacy mode: no event #0 is prepended and the
        # chain seeds from the legacy ``"0"*64`` sentinel. v2.0
        # callers SHOULD pass an explicit ``deployer_id`` to engage
        # the domain-separated genesis seed; on the next major
        # version bump this fallback will be removed.
        self._deployer_id: str | None = deployer_id
        # When the caller passes a deployer_id but no creation_iso,
        # we resolve a wall-clock value so the seed is well-defined.
        # When the caller passes neither, we leave the creation_iso
        # at None and stay in legacy mode.
        self._chain_creation_iso: str | None
        if deployer_id is not None:
            self._chain_creation_iso = chain_creation_iso or datetime.now(UTC).isoformat()
        else:
            self._chain_creation_iso = chain_creation_iso

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

        # CR-7 — seed the genesis event #0 if the caller explicitly
        # passed a ``deployer_id`` AND the chain is empty. We do this
        # AFTER ``_load_existing`` so a re-opened chain preserves its
        # original genesis event rather than getting a new one
        # prepended. External stores that ship with their own events
        # (e.g. SQLite restored from backup) also skip this path. The
        # ``deployer_id is None`` fallback is the v1.x legacy mode and
        # is documented as deprecated; new callers MUST pass a
        # deployer_id.
        if deployer_id is not None and len(self._store) == 0:
            self._seed_genesis_event()

    # ------------------------------------------------------------------ #
    # Genesis seeding                                                    #
    # ------------------------------------------------------------------ #

    def _seed_genesis_event(self) -> None:
        """CR-7 — Write event #0 to a freshly-created chain.

        The genesis event carries the deployer identity + creation
        timestamp + genesis-format version in its payload, and uses
        the deployer-keyed seed as its ``prev_hash``. Its
        ``event_hash`` is the SHA-256 of the genesis event's fields
        (including the seed-as-prev_hash). Event #1 (the first
        non-genesis event) chains off the genesis event's
        ``event_hash``.

        The genesis event is FULLY deterministic given
        ``deployer_id + chain_creation_iso``:

          * ``event_id`` is a deterministic UUIDv5 derived from the
            same domain separator + deployer + creation_iso so two
            independent constructions of the same logical chain
            produce the same event #0.
          * ``timestamp`` is the supplied ``chain_creation_iso`` (no
            wall-clock read).
          * ``prev_hash`` is the deployer-keyed seed.

        This determinism is what lets a regulator on a different host
        re-derive the exact event #0 from the deployer's published
        ``deployer_id`` and ``chain_creation_iso`` — useful for
        cross-host verification under SR 11-7 effective challenge.
        """
        # Both fields are guaranteed non-None by the caller (only
        # invoked when ``deployer_id`` was explicitly supplied).
        # Local copies + asserts give mypy --strict a non-Optional
        # type to work with.
        assert self._deployer_id is not None
        assert self._chain_creation_iso is not None
        deployer_id = self._deployer_id
        chain_creation_iso = self._chain_creation_iso

        seed = _compute_genesis_hash(deployer_id, chain_creation_iso)
        # Deterministic UUIDv5 — same deployer + same creation_iso ->
        # same event_id. The namespace is a stable random UUID baked
        # into the source so a future format change can rotate it.
        genesis_namespace = uuid.UUID("8b1d0a2c-1b8a-4f5d-9d2f-7c0e5a1b3a4c")
        event_id = str(
            uuid.uuid5(
                genesis_namespace,
                f"{GENESIS_DOMAIN_SEPARATOR}/{deployer_id}/{chain_creation_iso}",
            )
        )
        genesis_payload: dict[str, Any] = {
            "deployer_id": deployer_id,
            "chain_creation_iso": chain_creation_iso,
            "genesis_version": GENESIS_VERSION,
        }
        # Use ``chain_creation_iso`` as the genesis event's timestamp
        # so the event is fully deterministic. The TSA call still
        # happens — its token rides along in the payload as side-
        # channel evidence — but the canonical event timestamp
        # IS the deployer-declared creation_iso.
        timestamp_iso = chain_creation_iso
        canonical_pre_timestamp = json.dumps(
            {
                "event_id": event_id,
                "event_type": AuditEventType.AGENT_STARTED.value,
                "autonomy_level": AutonomyLevel.A0.value,
                "agent_id": GENESIS_AGENT_ID,
                "payload": genesis_payload,
                "actor_id": None,
                "prev_hash": seed,
                "schema_version": SCHEMA_VERSION,
            },
            sort_keys=True,
        ).encode()
        pre_digest = hashlib.sha256(canonical_pre_timestamp).digest()
        # The TSA is still consulted so its messageImprint binds the
        # TSA-asserted time to the genesis event's pre-digest. The
        # asserted_at is intentionally NOT folded back into the
        # canonical timestamp — that would defeat determinism — but
        # the TSR token is stashed in the payload so a verifier can
        # re-check ``messageImprint == pre_digest``.
        ts_response = self._timestamp_source.stamp(pre_digest)
        payload = genesis_payload
        if ts_response.tsr_token_b64 is not None:
            payload = {**genesis_payload, "_tsr_token_b64": ts_response.tsr_token_b64}

        genesis_event = AuditEvent.create(
            event_type=AuditEventType.AGENT_STARTED,
            autonomy_level=AutonomyLevel.A0,
            agent_id=GENESIS_AGENT_ID,
            payload=payload,
            prev_hash=seed,
            event_id=event_id,
            timestamp=timestamp_iso,
            schema_version=SCHEMA_VERSION,
        )
        self._store.append(genesis_event)
        if not self._external_store and self.log_file is not None:
            self._write(genesis_event)

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

    def _expected_chain_seed(self) -> str:
        """The ``prev_hash`` the FIRST event must carry — the chain's seed.

        CR-7 consistency fix. ``verify`` / ``verify_strict`` walk from this
        seed instead of hard-coding the legacy sentinel, so a deployer-keyed
        chain (whose genesis ``prev_hash`` is the deployer seed, not
        ``"0"*64``) verifies as honest rather than tripping a false
        prev_hash-mismatch at index 0.

          - empty chain                -> the legacy GENESIS sentinel;
          - deployer-keyed genesis     -> the seed RECOMPUTED from the genesis
            event's declared ``deployer_id`` + ``chain_creation_iso`` (so a
            genesis whose seed was altered to disagree with its declared
            deployer identity is caught — an added check, not a relaxation);
          - legacy first event         -> the GENESIS sentinel.
        """
        first = next(iter(self._store), None)
        if first is None:
            return GENESIS_HASH
        if (
            first.event_type is AuditEventType.AGENT_STARTED
            and first.agent_id == GENESIS_AGENT_ID
            and "deployer_id" in first.payload
            and "chain_creation_iso" in first.payload
        ):
            return _compute_genesis_hash(
                str(first.payload["deployer_id"]),
                str(first.payload["chain_creation_iso"]),
            )
        return GENESIS_HASH

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
        """Append a new event to the chain and persist it.

        CR-3 — the TSA stamp is bound to a *canonical pre-timestamp
        digest* of the event's identifying fields, not to empty bytes.
        The flow is:

          1. Generate the event_id up front (so it can be folded into
             the pre-digest).
          2. Compute a SHA-256 over the JSON of
             ``{event_id, event_type, autonomy_level, agent_id,
                payload, actor_id, prev_hash, schema_version}``
             (every field that uniquely identifies the event EXCEPT
             timestamp + event_hash, which depend on the TSA call).
          3. Pass that 32-byte digest to ``stamp(pre_digest)``.
          4. The TSA's ``messageImprint`` field now binds the
             attested time to the specific event; a TSR copied from
             a different event will not re-verify against the new
             event's pre-digest.

        When the timestamp source returns a TSR token (``RFC3161Source``
        does; ``LocalClock`` returns ``None``), the token is stashed
        in ``payload["_tsr_token_b64"]`` so a verifier can re-check
        ``messageImprint == pre_digest`` from the on-disk event alone.

        CR-4 — the body is wrapped in ``self._append_lock`` to close
        the TOCTOU window between
        ``self._store.head_event_hash()`` and
        ``self._store.append(event)``. Without the lock two threads
        both observe the same head, both build events with the same
        ``prev_hash``, and the chain forks silently — ``verify()``
        then returns False on the second branch.
        """
        with self._append_lock:
            # 1. Stable identifying fields, computed once.
            event_id = str(uuid.uuid4())
            prev_hash = self._store.head_event_hash()

            # 2. Canonical pre-timestamp digest. The serialization must
            #    use ``sort_keys=True`` so the verifier (which may not
            #    know the original dict-insertion order) re-derives the
            #    same bytes.
            canonical_pre_timestamp = json.dumps(
                {
                    "event_id": event_id,
                    "event_type": event_type.value,
                    "autonomy_level": autonomy_level.value,
                    "agent_id": agent_id,
                    "payload": payload,
                    "actor_id": actor_id,
                    "prev_hash": prev_hash,
                    "schema_version": SCHEMA_VERSION,
                },
                sort_keys=True,
            ).encode()
            pre_digest = hashlib.sha256(canonical_pre_timestamp).digest()

            # 3. Pull the trusted timestamp, binding the TSA-asserted time
            #    to the pre-digest. LocalClock is free; RFC3161Source
            #    crosses the network. We accept the cost so the trusted
            #    time is bound to the event, not to b"".
            ts_response = self._timestamp_source.stamp(pre_digest)
            timestamp_iso = ts_response.asserted_at.isoformat()

            # 4. Stash the TSR token (if any) in the payload so a verifier
            #    can re-check ``messageImprint == pre_digest`` from the
            #    on-disk event alone. ``LocalClock`` returns ``None`` for
            #    ``tsr_token_b64`` — no side-channel key is injected when
            #    no TSA was contacted.
            if ts_response.tsr_token_b64 is not None:
                # Defensive copy so the caller's dict is not mutated under
                # them. The TSR token is a side-channel that belongs to
                # this specific event.
                payload = {**payload, "_tsr_token_b64": ts_response.tsr_token_b64}

            # 5. Construct the event with the bound timestamp. The
            #    event_id passed here MUST equal the one folded into the
            #    pre-digest, otherwise the TSR's messageImprint does not
            #    re-verify against the stored event.
            event = AuditEvent.create(
                event_type=event_type,
                autonomy_level=autonomy_level,
                agent_id=agent_id,
                payload=payload,
                prev_hash=prev_hash,
                event_id=event_id,
                actor_id=actor_id,
                timestamp=timestamp_iso,
                schema_version=SCHEMA_VERSION,
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

        CR-4 — held under ``self._append_lock`` so a concurrent
        ``append`` cannot mutate the underlying store mid-walk
        (which would raise ``RuntimeError: list modified during
        iteration`` on the InMemoryLedgerStore or yield a torn-tail
        False on the JSONL store). The RLock allows a single thread
        to hold ``append`` and ``verify`` simultaneously when the
        verifier is invoked from within an append path
        (e.g. ``anchor_to_witness``).
        """
        with self._append_lock:
            prev = self._expected_chain_seed()
            for event in self._store:
                # A forged event whose payload cannot be canonicalized to JSON
                # (e.g. a non-serializable object planted by a storage-layer
                # attacker) is a tamper, not a crash: verify()'s contract is
                # "returns False if tampered", so a hashing failure is False.
                try:
                    expected = event._compute_hash()
                except (TypeError, ValueError):
                    return False
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

        # CR-4 — hold the append lock for the duration of the walk so
        # an in-flight append can't tear the iteration. See
        # ``verify`` for the soft-failure variant.
        with self._append_lock:
            prev = self._expected_chain_seed()
            for index, event in enumerate(self._store):
                # A non-serializable forged payload is a tamper verdict, not an
                # uncaught TypeError (which would turn a tamper attempt into a
                # verifier crash / DoS).
                try:
                    expected = event._compute_hash()
                except (TypeError, ValueError) as exc:
                    raise AuditChainTamperError(
                        f"event at index {index} (event_id={event.event_id!r}) "
                        "has a payload that cannot be canonicalized to JSON; "
                        "its hash cannot be recomputed — treated as tampered"
                    ) from exc
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
        # CR-4 — same fcntl-flock discipline as JsonlLedgerStore so
        # the v1.0 default-mode JSONL writes are cross-process safe
        # when multiple writers share the file. The append_lock
        # already serializes within-process callers; the flock
        # extends serialization to the file-system layer.
        with open(self.log_file, "a", encoding="utf-8") as fh:
            if fcntl is not None:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                fh.write(event.to_jsonl() + "\n")
                fh.flush()
            finally:
                if fcntl is not None:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    def _load_existing(self) -> None:
        if self.log_file is None:
            return
        p = Path(self.log_file)
        if not p.exists():
            return
        first_event_loaded: AuditEvent | None = None
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            # CR-2 — replay through ``from_jsonl`` so the recomputed
            # hash is checked against the stored hash at load time.
            # A tampered on-disk line raises ``AuditChainTamperError``
            # before the event reaches the in-memory store; the chain
            # is self-verifying on load rather than only on explicit
            # ``verify()``.
            event = AuditEvent.from_jsonl(data)
            if first_event_loaded is None:
                first_event_loaded = event
            self._store.append(event)

        # CR-7 — back-compat detection. A chain whose first event's
        # ``prev_hash`` is the legacy ``"0"*64`` sentinel was created
        # before deployer-keyed genesis was introduced. Accept it
        # (the per-line ``from_jsonl`` check has already validated
        # internal integrity) but flag the deprecation so the
        # deployer can plan a re-create with an explicit deployer_id.
        if first_event_loaded is not None and first_event_loaded.prev_hash == GENESIS_HASH:
            import warnings

            warnings.warn(
                f"AuditChain loaded from {str(p)!r} uses the legacy "
                "GENESIS_HASH sentinel (prev_hash='0'*64) as its "
                "chain seed. v2.0 derives a per-deployer genesis "
                "hash so an attacker cannot regenerate an entire "
                "chain from scratch. Re-create this chain with an "
                "explicit deployer_id to upgrade.",
                DeprecationWarning,
                stacklevel=3,
            )
