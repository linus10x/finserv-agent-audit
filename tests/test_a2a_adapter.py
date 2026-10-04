"""Tests for the A2A (Agent2Agent) protocol audit adapter (v2.0)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from finserv_agent_audit.governance.audit_chain import AuditChain
from finserv_agent_audit.governance.sovereign_veto import (
    SovereignVeto,
    VetoBlockedError,
    VetoReason,
)
from finserv_agent_audit.integrations import a2a_adapter
from finserv_agent_audit.integrations.a2a_adapter import (
    A2AAuditAdapter,
    A2ATaskState,
)
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)

# --------------------------------------------------------------------------- #
# Spy chain — records every appended event without touching disk              #
# --------------------------------------------------------------------------- #


@dataclass
class _SpyChain:
    """Stand-in for ``AuditChain`` that records appends in memory.

    The real ``AuditChain`` requires a writable log file. The adapters
    only depend on the ``.append`` keyword surface, so a spy is enough
    for adapter-level tests.
    """

    appended: list[dict[str, Any]] = field(default_factory=list)

    def append(
        self,
        event_type: AuditEventType,
        autonomy_level: AutonomyLevel,
        agent_id: str,
        payload: dict[str, Any],
        actor_id: str | None = None,
    ) -> AuditEvent:
        record = {
            "event_type": event_type,
            "autonomy_level": autonomy_level,
            "agent_id": agent_id,
            "payload": payload,
            "actor_id": actor_id,
        }
        self.appended.append(record)
        return AuditEvent(
            event_type=event_type,
            autonomy_level=autonomy_level,
            agent_id=agent_id,
            payload=payload,
            prev_hash="0" * 64,
            actor_id=actor_id,
        )


# --------------------------------------------------------------------------- #
# Graceful degradation — adapter must construct without a2a-sdk installed     #
# --------------------------------------------------------------------------- #


class TestGracefulDegradation:
    def test_has_a2a_flag_is_boolean(self) -> None:
        assert isinstance(a2a_adapter.HAS_A2A, bool)

    def test_adapter_constructs_without_a2a_sdk(self) -> None:
        chain = _SpyChain()
        adapter = A2AAuditAdapter(audit_chain=chain, agent_id="zeus:a2a")
        assert adapter.agent_id == "zeus:a2a"

    def test_record_task_event_no_chain_is_no_op(self) -> None:
        # Caller may pass audit_chain=None for shadow / dry-run mode.
        adapter = A2AAuditAdapter(audit_chain=None, agent_id="zeus:a2a")
        # Must not raise; must return None.
        assert (
            adapter.record_task_event(
                task_id="task-1",
                state=A2ATaskState.CREATED,
                message_classification="quote-request",
            )
            is None
        )


# --------------------------------------------------------------------------- #
# Happy-path event capture                                                    #
# --------------------------------------------------------------------------- #


class TestEventCapture:
    def test_task_create_records_decision_made(self) -> None:
        chain = _SpyChain()
        adapter = A2AAuditAdapter(audit_chain=chain, agent_id="zeus:a2a")
        adapter.record_task_event(
            task_id="task-001",
            state=A2ATaskState.CREATED,
            message_classification="payment-instruction",
        )
        assert len(chain.appended) == 1
        entry = chain.appended[0]
        assert entry["event_type"] == AuditEventType.DECISION_MADE
        assert entry["agent_id"] == "zeus:a2a"
        assert entry["payload"]["a2a_task_id"] == "task-001"
        assert entry["payload"]["a2a_state"] == "created"
        assert entry["payload"]["message_classification"] == "payment-instruction"

    def test_task_update_complete_cancel_each_recorded(self) -> None:
        chain = _SpyChain()
        adapter = A2AAuditAdapter(audit_chain=chain, agent_id="zeus:a2a")
        for state in (
            A2ATaskState.CREATED,
            A2ATaskState.UPDATED,
            A2ATaskState.COMPLETED,
        ):
            adapter.record_task_event(
                task_id="task-001",
                state=state,
                message_classification="quote",
            )
        assert len(chain.appended) == 3
        assert [e["payload"]["a2a_state"] for e in chain.appended] == [
            "created",
            "updated",
            "completed",
        ]

    def test_message_exchange_captured(self) -> None:
        chain = _SpyChain()
        adapter = A2AAuditAdapter(audit_chain=chain, agent_id="zeus:a2a")
        adapter.record_message(
            task_id="task-001",
            peer_agent_id="peer-agent:a2a",
            direction="outbound",
            message_classification="settlement-request",
            payload_size=512,
        )
        entry = chain.appended[0]
        assert entry["payload"]["a2a_peer_agent_id"] == "peer-agent:a2a"
        assert entry["payload"]["a2a_direction"] == "outbound"
        assert entry["payload"]["payload_size"] == 512

    def test_autonomy_level_default_is_a2(self) -> None:
        chain = _SpyChain()
        adapter = A2AAuditAdapter(audit_chain=chain, agent_id="zeus:a2a")
        adapter.record_task_event(
            task_id="task-1",
            state=A2ATaskState.CREATED,
            message_classification="any",
        )
        assert chain.appended[0]["autonomy_level"] == AutonomyLevel.A2

    def test_autonomy_level_override_propagates(self) -> None:
        chain = _SpyChain()
        adapter = A2AAuditAdapter(
            audit_chain=chain,
            agent_id="zeus:a2a",
            autonomy_level=AutonomyLevel.A3,
        )
        adapter.record_task_event(
            task_id="task-1",
            state=A2ATaskState.CREATED,
            message_classification="any",
        )
        assert chain.appended[0]["autonomy_level"] == AutonomyLevel.A3

    def test_extra_payload_fields_passed_through(self) -> None:
        chain = _SpyChain()
        adapter = A2AAuditAdapter(audit_chain=chain, agent_id="zeus:a2a")
        adapter.record_task_event(
            task_id="task-001",
            state=A2ATaskState.COMPLETED,
            message_classification="settlement",
            extra={"counterparty_id": "broker-7", "instrument": "SPY"},
        )
        entry = chain.appended[0]
        assert entry["payload"]["counterparty_id"] == "broker-7"
        assert entry["payload"]["instrument"] == "SPY"


# --------------------------------------------------------------------------- #
# Sovereign-veto wiring                                                       #
# --------------------------------------------------------------------------- #


class TestSovereignVetoWiring:
    def test_veto_blocks_task_event_emission(self) -> None:
        chain = _SpyChain()
        veto = SovereignVeto(agent_id="zeus:a2a")
        adapter = A2AAuditAdapter(
            audit_chain=chain,
            agent_id="zeus:a2a",
            veto=veto,
        )
        veto.trigger(
            VetoReason.RISK_LIMIT_BREACH,
            triggered_by="risk_monitor",
            description="VaR breach",
        )
        with pytest.raises(VetoBlockedError):
            adapter.record_task_event(
                task_id="task-1",
                state=A2ATaskState.CREATED,
                message_classification="payment-instruction",
            )
        # The veto blocks BEFORE the chain entry is written.
        assert chain.appended == []

    def test_no_veto_no_block(self) -> None:
        chain = _SpyChain()
        veto = SovereignVeto(agent_id="zeus:a2a")
        adapter = A2AAuditAdapter(
            audit_chain=chain,
            agent_id="zeus:a2a",
            veto=veto,
        )
        adapter.record_task_event(
            task_id="task-1",
            state=A2ATaskState.CREATED,
            message_classification="ok",
        )
        assert len(chain.appended) == 1


# --------------------------------------------------------------------------- #
# Demo entrypoint                                                             #
# --------------------------------------------------------------------------- #


class TestDemoEntrypoint:
    def test_demo_does_not_raise(self, capsys: pytest.CaptureFixture[str]) -> None:
        a2a_adapter._run_demo()
        out = capsys.readouterr().out
        assert "HAS_A2A" in out


# --------------------------------------------------------------------------- #
# Real AuditChain integration smoke (no a2a-sdk required)                     #
# --------------------------------------------------------------------------- #


class TestRealAuditChainIntegration:
    def test_emits_into_real_chain(self, tmp_path: Any) -> None:
        chain = AuditChain(log_file=tmp_path / "a2a_audit.jsonl")
        adapter = A2AAuditAdapter(audit_chain=chain, agent_id="zeus:a2a")
        adapter.record_task_event(
            task_id="task-1",
            state=A2ATaskState.CREATED,
            message_classification="ok",
        )
        adapter.record_task_event(
            task_id="task-1",
            state=A2ATaskState.COMPLETED,
            message_classification="ok",
        )
        assert chain.verify() is True
        assert len(chain._events) == 2
