"""
Audit Event Schema — Tamper-Evident Hash-Chain Logging
=======================================================

Defines the canonical schema for audit events in regulated AI agent systems.
Each event is chained to the previous via SHA-256 hash, making any retroactive
tampering detectable during verification.

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
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
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
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
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


class AuditChain:
    """
    Append-only audit chain. Verifies integrity of the full event sequence.

    Usage::

        chain = AuditChain(log_file=Path("audit.jsonl"))
        event = chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="zeus",
            payload={"action": "enter_position", "ticker": "SPY"},
        )
        assert chain.verify()  # True if untampered
    """

    GENESIS_HASH = "0" * 64

    def __init__(self, log_file: Path | None = None) -> None:
        self.log_file: Path = log_file or Path("output/audit_chain.jsonl")
        self._prev_hash: str = self.GENESIS_HASH
        self._events: list[AuditEvent] = []
        self._load_existing()

    def append(
        self,
        event_type: AuditEventType,
        autonomy_level: AutonomyLevel,
        agent_id: str,
        payload: dict[str, Any],
        actor_id: str | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_type=event_type,
            autonomy_level=autonomy_level,
            agent_id=agent_id,
            payload=payload,
            prev_hash=self._prev_hash,
            actor_id=actor_id,
        )
        self._prev_hash = event.event_hash
        self._events.append(event)
        self._write(event)
        return event

    def verify(self) -> bool:
        """Replay the chain and verify every hash. Returns False if tampered."""
        prev = self.GENESIS_HASH
        for event in self._events:
            expected = event._compute_hash()
            if event.event_hash != expected:
                return False
            if event.prev_hash != prev:
                return False
            prev = event.event_hash
        return True

    def _write(self, event: AuditEvent) -> None:
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_file, "a", encoding="utf-8") as fh:
            fh.write(event.to_jsonl() + "\n")

    def _load_existing(self) -> None:
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
            self._events.append(event)
        if self._events:
            self._prev_hash = self._events[-1].event_hash
