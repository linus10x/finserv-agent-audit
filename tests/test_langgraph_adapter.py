"""Tests for the LangGraph audit callback (v2.0)."""

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
from finserv_agent_audit.integrations import langgraph_adapter
from finserv_agent_audit.integrations.langgraph_adapter import (
    LangGraphAuditCallback,
    LangGraphEventKind,
)
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)

# --------------------------------------------------------------------------- #
# Spy chain                                                                   #
# --------------------------------------------------------------------------- #


@dataclass
class _SpyChain:
    appended: list[dict[str, Any]] = field(default_factory=list)

    def append(
        self,
        event_type: AuditEventType,
        autonomy_level: AutonomyLevel,
        agent_id: str,
        payload: dict[str, Any],
        actor_id: str | None = None,
    ) -> AuditEvent:
        self.appended.append(
            {
                "event_type": event_type,
                "autonomy_level": autonomy_level,
                "agent_id": agent_id,
                "payload": payload,
                "actor_id": actor_id,
            }
        )
        return AuditEvent(
            event_type=event_type,
            autonomy_level=autonomy_level,
            agent_id=agent_id,
            payload=payload,
            prev_hash="0" * 64,
            actor_id=actor_id,
        )


# --------------------------------------------------------------------------- #
# Graceful degradation                                                        #
# --------------------------------------------------------------------------- #


class TestGracefulDegradation:
    def test_has_langgraph_flag_is_boolean(self) -> None:
        assert isinstance(langgraph_adapter.HAS_LANGGRAPH, bool)

    def test_callback_constructs_without_langgraph(self) -> None:
        callback = LangGraphAuditCallback(audit_chain=_SpyChain(), agent_id="zeus:lg")
        assert callback.agent_id == "zeus:lg"

    def test_record_no_chain_is_no_op(self) -> None:
        callback = LangGraphAuditCallback(audit_chain=None, agent_id="zeus:lg")
        assert callback.on_node_start(node_name="planner", run_id="run-1") is None


# --------------------------------------------------------------------------- #
# Node lifecycle                                                              #
# --------------------------------------------------------------------------- #


class TestNodeLifecycle:
    def test_on_node_start_emits_event(self) -> None:
        chain = _SpyChain()
        callback = LangGraphAuditCallback(audit_chain=chain, agent_id="zeus:lg")
        callback.on_node_start(node_name="planner", run_id="run-1")
        entry = chain.appended[0]
        assert entry["event_type"] == AuditEventType.DECISION_MADE
        assert entry["payload"]["langgraph_event_kind"] == LangGraphEventKind.NODE_START.value
        assert entry["payload"]["node_name"] == "planner"
        assert entry["payload"]["run_id"] == "run-1"

    def test_on_node_end_emits_event(self) -> None:
        chain = _SpyChain()
        callback = LangGraphAuditCallback(audit_chain=chain, agent_id="zeus:lg")
        callback.on_node_end(
            node_name="planner",
            run_id="run-1",
            output_summary={"decision": "buy"},
        )
        entry = chain.appended[0]
        assert entry["payload"]["langgraph_event_kind"] == LangGraphEventKind.NODE_END.value
        assert entry["payload"]["output_summary"] == {"decision": "buy"}

    def test_on_edge_traversal_emits_event(self) -> None:
        chain = _SpyChain()
        callback = LangGraphAuditCallback(audit_chain=chain, agent_id="zeus:lg")
        callback.on_edge_traversal(
            from_node="planner",
            to_node="executor",
            run_id="run-1",
        )
        entry = chain.appended[0]
        assert entry["payload"]["langgraph_event_kind"] == LangGraphEventKind.EDGE.value
        assert entry["payload"]["from_node"] == "planner"
        assert entry["payload"]["to_node"] == "executor"


# --------------------------------------------------------------------------- #
# State and checkpoint                                                        #
# --------------------------------------------------------------------------- #


class TestStateAndCheckpoint:
    def test_on_state_transition_emits_event(self) -> None:
        chain = _SpyChain()
        callback = LangGraphAuditCallback(audit_chain=chain, agent_id="zeus:lg")
        callback.on_state_transition(
            run_id="run-1",
            channel="messages",
            updates_summary={"appended_count": 2},
        )
        entry = chain.appended[0]
        assert entry["payload"]["langgraph_event_kind"] == LangGraphEventKind.STATE_TRANSITION.value
        assert entry["payload"]["channel"] == "messages"
        assert entry["payload"]["updates_summary"] == {"appended_count": 2}

    def test_on_checkpoint_emits_event(self) -> None:
        chain = _SpyChain()
        callback = LangGraphAuditCallback(audit_chain=chain, agent_id="zeus:lg")
        callback.on_checkpoint(
            run_id="run-1",
            checkpoint_id="ckpt-7",
            thread_id="thread-A",
        )
        entry = chain.appended[0]
        assert entry["payload"]["langgraph_event_kind"] == LangGraphEventKind.CHECKPOINT.value
        assert entry["payload"]["checkpoint_id"] == "ckpt-7"
        assert entry["payload"]["thread_id"] == "thread-A"


# --------------------------------------------------------------------------- #
# Sovereign-veto wiring                                                       #
# --------------------------------------------------------------------------- #


class TestSovereignVetoWiring:
    def test_veto_blocks_node_entry(self) -> None:
        chain = _SpyChain()
        veto = SovereignVeto(agent_id="zeus:lg")
        callback = LangGraphAuditCallback(
            audit_chain=chain,
            agent_id="zeus:lg",
            veto=veto,
        )
        veto.trigger(
            VetoReason.RISK_LIMIT_BREACH,
            triggered_by="risk_monitor",
            description="VaR breach",
        )
        with pytest.raises(VetoBlockedError):
            callback.on_node_start(node_name="planner", run_id="run-1")
        assert chain.appended == []

    def test_no_veto_no_block(self) -> None:
        chain = _SpyChain()
        veto = SovereignVeto(agent_id="zeus:lg")
        callback = LangGraphAuditCallback(
            audit_chain=chain,
            agent_id="zeus:lg",
            veto=veto,
        )
        callback.on_node_start(node_name="planner", run_id="run-1")
        assert len(chain.appended) == 1


# --------------------------------------------------------------------------- #
# Real AuditChain integration smoke                                           #
# --------------------------------------------------------------------------- #


class TestRealAuditChainIntegration:
    def test_emits_into_real_chain(self, tmp_path: Any) -> None:
        chain = AuditChain(log_file=tmp_path / "lg_audit.jsonl")
        callback = LangGraphAuditCallback(audit_chain=chain, agent_id="zeus:lg")
        callback.on_node_start(node_name="planner", run_id="run-1")
        callback.on_node_end(
            node_name="planner",
            run_id="run-1",
            output_summary={"decision": "hold"},
        )
        callback.on_checkpoint(run_id="run-1", checkpoint_id="ckpt-1", thread_id="thread-A")
        assert chain.verify() is True
        assert len(chain._events) == 3


# --------------------------------------------------------------------------- #
# Demo entrypoint                                                             #
# --------------------------------------------------------------------------- #


class TestDemoEntrypoint:
    def test_demo_does_not_raise(self, capsys: pytest.CaptureFixture[str]) -> None:
        langgraph_adapter._run_demo()
        out = capsys.readouterr().out
        assert "HAS_LANGGRAPH" in out
