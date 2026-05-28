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


class AutonomyLevel(Enum):
    """
    Autonomy classification per the A0->A4 ladder.
    Maps to human oversight requirements at each level.
    """

    A0 = "A0"  # Human decides — agent proposes only
    A1 = "A1"  # Human in loop — agent proposes, human confirms
    A2 = "A2"  # Human on loop — agent executes, human can override
    A3 = "A3"  # Human notified — agent executes, human alerted
    A4 = "A4"  # Autonomous — agent executes, audit trail only


@dataclass
class AuditEvent:
    """
    Immutable audit record. Hash is computed on construction.

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
    event_hash: str = field(init=False)

    def __post_init__(self) -> None:
        self.event_hash = self._compute_hash()

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
