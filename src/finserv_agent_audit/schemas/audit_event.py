"""
Audit Event Schema — Tamper-Detecting Hash-Chain Logging (within-trust-boundary)
================================================================================

Defines the canonical schema for audit events in regulated AI agent systems.
Each event is chained to the previous via SHA-256 hash, making any retroactive
tampering detectable during verification within the trust boundary that produced
the chain.

For external tamper-EVIDENCE (cryptographic anchoring to a third-party witness
register such as Sigstore Rekor or OpenTimestamps), see the witness pattern
shipping in v1.1 (ADR-0014).

Design principles:
    - Every agent action that changes system state produces an audit event
    - Events are append-only — never mutated after creation
    - Hash chain: event_hash = SHA-256(event_payload + prev_hash)
    - Verifier can replay the chain and detect any inserted/modified event
    - Schema is intentionally minimal — extend per your compliance requirements

Compliance notes:
    - EU AI Act Article 12: "Logging capabilities" for high-risk AI systems
    - SEC Rule 17a-4: Electronic records retention (adapt retention policy)
    - SOC 2 CC7.2: System monitoring and anomaly detection

v1.1 note. The ``AuditChain`` class was moved to
``finserv_agent_audit.governance.audit_chain`` so it can consume the
Tranche 2 Protocol seams (``LedgerStore``, ``TimestampSource``,
``WitnessRegister``, ``MIProxy``). It is re-exported here for backward
compatibility — existing imports from ``schemas.audit_event`` continue
to resolve unchanged.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class AuditEventType(Enum):
    """Classification of audit events by category."""

    # Agent lifecycle
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    AGENT_ERROR = "agent.error"

    # Decision events
    DECISION_MADE = "decision.made"
    DECISION_VETOED = "decision.vetoed"
    DECISION_OVERRIDDEN = "decision.overridden"

    # Risk events
    RISK_ESCALATION = "risk.escalation"
    RISK_DEESCALATION = "risk.deescalation"
    HALT_TRIGGERED = "risk.halt"

    # Human-in-the-loop
    HUMAN_APPROVED = "human.approved"
    HUMAN_REJECTED = "human.rejected"
    HUMAN_OVERRIDE = "human.override"

    # Governance
    VETO_APPLIED = "governance.veto"
    POLICY_VIOLATION = "governance.policy_violation"
    COMPLIANCE_CHECK = "governance.compliance_check"

    # Authority lifecycle (v2.2 — demotion-gated control surface, ADR-0026)
    # The falsifiable-under-audit claim rests on these three: authority is
    # GRANTED only against evidence, the grant is EXAMINED by an independent
    # finding, and authority is REVOKED/demoted recorded against the grant +
    # the finding that triggered it.
    AUTHORITY_GRANTED = "authority.granted"
    AUTHORITY_EXAMINED = "authority.examined"
    AUTHORITY_REVOKED = "authority.revoked"

    # Vendor-mediated AI (v1.1 — VendorScoreGate, ADR-0016)
    VENDOR_SCORE_RECORDED = "vendor.score_recorded"
    VENDOR_SCORE_DRIFT_DETECTED = "vendor.score_drift_detected"

    # External anchoring (v1.1 — WitnessRegister, ADR-0014)
    WITNESS_ANCHOR = "audit_chain.witness_anchor"

    # FSI-specific (v1.1)
    MODEL_VALIDATED = "fsi.model_validated"  # SR 11-7 — ADR-0007
    ADVERSE_ACTION_TAKEN = "fsi.adverse_action_taken"  # FCRA + CFPB Circular — ADR-0009
    SAR_FILED = "fsi.sar_filed"  # BSA/AML — ADR-0011
    BEST_INTEREST_CHECKED = "fsi.best_interest_checked"  # SEC Reg-BI — ADR-0013

    # Vendor surface (v1.3 — DeprecationWatch, ADR-0025)
    DEPRECATION_ALERT = "vendor.deprecation_alert"


class AutonomyLevel(Enum):
    """
    Autonomy classification per the A0->A4 ladder.
    Maps to human oversight requirements at each level.
    """

    A0 = "A0"  # Informational — agent reads and recommends, no write authority
    A1 = "A1"  # Assisted — agent drafts, human approves every write
    A2 = "A2"  # Delegated — agent writes in a hard envelope, sampled review
    A3 = "A3"  # Supervised Autonomous — in-scope autonomous writes, sovereign veto, live ledger
    A4 = "A4"  # Production Autonomous — A3 plus orchestration and operator-validated escalation


@dataclass(frozen=True)
class AuditEvent:
    """
    Immutable audit record. Hash is computed on construction.

    CR-2 (v2.0). The dataclass is ``frozen=True`` — every field is
    read-only post-construction. The old impl declared ``event_hash``
    via ``field(init=False)`` and set it inside ``__post_init__``,
    which left the attribute freely re-assignable. Replay paths
    exploited that to "restore" the on-disk stored hash, which masked
    tampering: an attacker who edited a JSONL line could leave the
    chain replay consistent because the re-loaded ``event_hash`` was
    simply overwritten with whatever the tampered line claimed.

    Two construction paths now exist:

      * ``AuditEvent.create(...)`` — for *new* events. Computes the
        hash from the field values and freezes the result. Use this
        wherever code previously called ``AuditEvent(...)``.

      * ``AuditEvent.from_jsonl(dict)`` — for *replay* of stored
        events. Reconstructs the event with the stored ``event_hash``,
        recomputes the hash against the reconstructed fields, and
        raises ``AuditChainTamperError`` on mismatch. The chain is
        self-verifying on load, not just on explicit ``verify()``.

    The bare ``AuditEvent(...)`` constructor still works for backward
    compatibility — if no ``event_hash`` keyword is supplied, the
    constructor computes one (matching pre-CR-2 behavior). Replay
    code that passes a stored ``event_hash`` MUST instead call
    ``from_jsonl`` so the recomputation gate fires.

    Fields:
        event_id:       UUID4 uniquely identifying this event
        event_type:     Classification from AuditEventType
        autonomy_level: A0->A4 level at which this decision was made
        agent_id:       Identifier of the agent that generated this event
        timestamp:      UTC ISO-8601 timestamp
        payload:        Arbitrary event-specific data (keep minimal)
        actor_id:       Human actor if applicable (manual overrides)
        prev_hash:      SHA-256 hash of the previous event (genesis = 64 zeros)
        event_hash:     SHA-256 hash of this event + prev_hash (computed)
        schema_version: Schema version for forward compatibility
    """

    event_type: AuditEventType
    autonomy_level: AutonomyLevel
    agent_id: str
    payload: dict[str, Any]
    prev_hash: str

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    actor_id: str | None = None
    schema_version: str = "1.0.0"
    # ``event_hash`` is now a regular field with a sentinel default so
    # the v1.x construction call site (``AuditEvent(...)`` with no
    # ``event_hash`` kwarg) continues to work. ``__post_init__``
    # fills in the computed value via ``object.__setattr__`` (the
    # only permitted post-init write on a frozen dataclass).
    event_hash: str = ""

    def __post_init__(self) -> None:
        # On a frozen dataclass we cannot do ``self.event_hash = ...``
        # at any time, including ``__post_init__``. The canonical
        # workaround is ``object.__setattr__``. We only compute a new
        # hash when the caller did not supply one — replay paths
        # construct via ``from_jsonl`` which passes the stored hash
        # AND validates the recomputation independently.
        if not self.event_hash:
            object.__setattr__(self, "event_hash", self._compute_hash())

    # ------------------------------------------------------------------ #
    # Construction classmethods                                          #
    # ------------------------------------------------------------------ #

    @classmethod
    def create(
        cls,
        *,
        event_type: AuditEventType,
        autonomy_level: AutonomyLevel,
        agent_id: str,
        payload: dict[str, Any],
        prev_hash: str,
        event_id: str | None = None,
        timestamp: str | None = None,
        actor_id: str | None = None,
        schema_version: str = "1.0.0",
    ) -> AuditEvent:
        """Construct a *new* event. Computes ``event_hash`` and freezes."""
        kwargs: dict[str, Any] = {
            "event_type": event_type,
            "autonomy_level": autonomy_level,
            "agent_id": agent_id,
            "payload": payload,
            "prev_hash": prev_hash,
            "actor_id": actor_id,
            "schema_version": schema_version,
        }
        if event_id is not None:
            kwargs["event_id"] = event_id
        if timestamp is not None:
            kwargs["timestamp"] = timestamp
        return cls(**kwargs)

    @classmethod
    def from_jsonl(cls, data: dict[str, Any]) -> AuditEvent:
        """Replay a stored event. Recomputes and raises on mismatch.

        ``data`` is the dict form written by ``to_dict`` /
        ``to_jsonl``. The replay path reconstructs the event with the
        STORED ``event_hash``, then computes a fresh hash from the
        reconstructed fields. A mismatch means the on-disk line was
        tampered with — the stored hash does not match the fields it
        claims to summarize — and raises
        ``AuditChainTamperError``.

        Note: the exception is raised *during construction* of the
        replay path, before the event is returned, so the caller can
        never accidentally proceed with a tampered event.
        """
        # Lazy import — ``audit_chain`` imports ``schemas.audit_event``
        # at module load time, so the reverse import has to stay lazy
        # to avoid a circular import at package init.
        from finserv_agent_audit.governance.audit_chain import (
            AuditChainTamperError,
        )

        stored_event_hash = str(data["event_hash"])
        event = cls(
            event_type=AuditEventType(data["event_type"]),
            autonomy_level=AutonomyLevel(data["autonomy_level"]),
            agent_id=str(data["agent_id"]),
            payload=dict(data["payload"]),
            prev_hash=str(data["prev_hash"]),
            event_id=str(data["event_id"]),
            timestamp=str(data["timestamp"]),
            actor_id=None if data.get("actor_id") is None else str(data["actor_id"]),
            schema_version=str(data.get("schema_version", "1.0.0")),
            event_hash=stored_event_hash,
        )
        recomputed = event._compute_hash()
        if recomputed != stored_event_hash:
            raise AuditChainTamperError(
                f"event_hash mismatch on replay (event_id={event.event_id!r}): "
                f"stored={stored_event_hash!r}, recomputed={recomputed!r} — "
                "the on-disk line has been modified after writing"
            )
        return event

    def _compute_hash(self) -> str:
        payload = {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "autonomy_level": self.autonomy_level.value,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "actor_id": self.actor_id,
            "prev_hash": self.prev_hash,
            "schema_version": self.schema_version,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "autonomy_level": self.autonomy_level.value,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "actor_id": self.actor_id,
            "prev_hash": self.prev_hash,
            "event_hash": self.event_hash,
            "schema_version": self.schema_version,
        }

    def to_jsonl(self) -> str:
        """Single JSONL line for append-only log files."""
        return json.dumps(self.to_dict(), sort_keys=True)


# ---------------------------------------------------------------------- #
# Backward-compat re-export                                              #
# ---------------------------------------------------------------------- #
# The AuditChain class was moved to governance/audit_chain.py in v1.1 so
# it could consume the Protocol seams (LedgerStore, TimestampSource,
# WitnessRegister, MIProxy). It is re-exported here so the v1.0 imports
# `from finserv_agent_audit.schemas.audit_event import AuditChain` and
# `from schemas.audit_event import AuditChain` continue to resolve.
# Lazy via module __getattr__ to avoid a circular import when the
# governance package is loaded first.


def __getattr__(name: str) -> Any:
    if name == "AuditChain":
        from finserv_agent_audit.governance.audit_chain import AuditChain

        return AuditChain
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["AuditChain", "AuditEvent", "AuditEventType", "AutonomyLevel"]  # noqa: F822  # AuditChain resolved via __getattr__
