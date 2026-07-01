"""
Tests for AuditEvent schema and AuditChain hash-chain integrity.
"""

from __future__ import annotations

import json
from pathlib import Path

from schemas.audit_event import (
    AuditChain,
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)

GENESIS = "0" * 64


def make_event(prev_hash: str = GENESIS) -> AuditEvent:
    return AuditEvent(
        event_type=AuditEventType.DECISION_MADE,
        autonomy_level=AutonomyLevel.A2,
        agent_id="test-agent",
        payload={"action": "enter_position", "ticker": "SPY"},
        prev_hash=prev_hash,
    )


class TestAuditEvent:
    def test_hash_computed_on_construction(self) -> None:
        event = make_event()
        assert len(event.event_hash) == 64
        assert event.event_hash != GENESIS

    def test_hash_is_deterministic_for_same_fields(self) -> None:
        e1 = make_event()
        e2 = AuditEvent(
            event_type=e1.event_type,
            autonomy_level=e1.autonomy_level,
            agent_id=e1.agent_id,
            payload=e1.payload,
            prev_hash=e1.prev_hash,
            event_id=e1.event_id,
            timestamp=e1.timestamp,
        )
        assert e1.event_hash == e2.event_hash

    def test_different_payload_produces_different_hash(self) -> None:
        e1 = make_event()
        e2 = AuditEvent(
            event_type=AuditEventType.DECISION_VETOED,
            autonomy_level=AutonomyLevel.A1,
            agent_id="test-agent",
            payload={"action": "exit_position"},
            prev_hash=GENESIS,
        )
        assert e1.event_hash != e2.event_hash

    def test_to_dict_roundtrip(self) -> None:
        event = make_event()
        d = event.to_dict()
        assert d["event_type"] == AuditEventType.DECISION_MADE.value
        assert d["autonomy_level"] == AutonomyLevel.A2.value
        assert d["event_hash"] == event.event_hash

    def test_to_jsonl_is_valid_json(self) -> None:
        event = make_event()
        line = event.to_jsonl()
        parsed = json.loads(line)
        assert parsed["agent_id"] == "test-agent"

    def test_prev_hash_genesis_for_first_event(self) -> None:
        event = make_event()
        assert event.prev_hash == GENESIS

    def test_actor_id_optional(self) -> None:
        event = make_event()
        assert event.actor_id is None

    def test_schema_version_default(self) -> None:
        event = make_event()
        assert event.schema_version == "1.0.0"


class TestAuditChain:
    def test_chain_appends_event(self, tmp_path: Path) -> None:
        chain = AuditChain(log_file=tmp_path / "audit.jsonl")
        event = chain.append(
            event_type=AuditEventType.AGENT_STARTED,
            autonomy_level=AutonomyLevel.A0,
            agent_id="zeus",
            payload={"version": "1.0.0"},
        )
        assert event.prev_hash == GENESIS
        assert len(chain._events) == 1

    def test_chain_links_events(self, tmp_path: Path) -> None:
        chain = AuditChain(log_file=tmp_path / "audit.jsonl")
        e1 = chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="zeus",
            payload={"action": "buy"},
        )
        e2 = chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="zeus",
            payload={"action": "sell"},
        )
        assert e2.prev_hash == e1.event_hash

    def test_verify_clean_chain(self, tmp_path: Path) -> None:
        chain = AuditChain(log_file=tmp_path / "audit.jsonl")
        for i in range(5):
            chain.append(
                event_type=AuditEventType.COMPLIANCE_CHECK,
                autonomy_level=AutonomyLevel.A3,
                agent_id="sentinel",
                payload={"check": i},
            )
        assert chain.verify() is True

    def test_verify_detects_tampering(self, tmp_path: Path) -> None:
        log_file = tmp_path / "audit.jsonl"
        chain = AuditChain(log_file=log_file)
        chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="zeus",
            payload={"action": "buy"},
        )
        # CR-2 — ``AuditEvent`` is frozen post-construction. Tampering
        # is simulated by mutating the dict-typed ``payload`` (the
        # dict reference is frozen, the dict contents are not); the
        # stored ``event_hash`` no longer matches a freshly-computed
        # hash, so ``verify()`` returns False.
        chain._events[0].payload["action"] = "sell"
        assert chain.verify() is False

    def test_chain_writes_jsonl_file(self, tmp_path: Path) -> None:
        log_file = tmp_path / "audit.jsonl"
        chain = AuditChain(log_file=log_file)
        chain.append(
            event_type=AuditEventType.HALT_TRIGGERED,
            autonomy_level=AutonomyLevel.A4,
            agent_id="agent-01",
            payload={"reason": "drawdown"},
        )
        assert log_file.exists()
        lines = log_file.read_text().strip().splitlines()
        assert len(lines) == 1

    def test_chain_reloads_from_disk(self, tmp_path: Path) -> None:
        log_file = tmp_path / "audit.jsonl"
        c1 = AuditChain(log_file=log_file)
        e1 = c1.append(
            event_type=AuditEventType.AGENT_STARTED,
            autonomy_level=AutonomyLevel.A1,
            agent_id="zeus",
            payload={},
        )
        c2 = AuditChain(log_file=log_file)
        assert len(c2._events) == 1
        assert c2._events[0].event_hash == e1.event_hash

    def test_actor_id_persisted(self, tmp_path: Path) -> None:
        chain = AuditChain(log_file=tmp_path / "audit.jsonl")
        event = chain.append(
            event_type=AuditEventType.HUMAN_OVERRIDE,
            autonomy_level=AutonomyLevel.A0,
            agent_id="zeus",
            payload={"override": "halt_cleared"},
            actor_id="risk_officer_001",
        )
        assert event.actor_id == "risk_officer_001"
