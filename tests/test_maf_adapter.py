"""Tests for the Microsoft Agent Framework (MAF) audit adapter (v2.0)."""

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
from finserv_agent_audit.integrations import maf_adapter
from finserv_agent_audit.integrations.maf_adapter import (
    MAFAuditAdapter,
    MAFEventKind,
    MAFInteropProtocol,
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
    def test_has_maf_flag_is_boolean(self) -> None:
        assert isinstance(maf_adapter.HAS_MAF, bool)

    def test_adapter_constructs_without_maf(self) -> None:
        adapter = MAFAuditAdapter(audit_chain=_SpyChain(), agent_id="zeus:maf")
        assert adapter.agent_id == "zeus:maf"

    def test_record_no_chain_is_no_op(self) -> None:
        adapter = MAFAuditAdapter(audit_chain=None, agent_id="zeus:maf")
        assert (
            adapter.record_conversation_event(
                conversation_id="conv-1",
                kind=MAFEventKind.MESSAGE_RECEIVED,
                summary={"role": "user"},
            )
            is None
        )


# --------------------------------------------------------------------------- #
# Conversation events                                                         #
# --------------------------------------------------------------------------- #


class TestConversationEvents:
    def test_message_received_recorded(self) -> None:
        chain = _SpyChain()
        adapter = MAFAuditAdapter(audit_chain=chain, agent_id="zeus:maf")
        adapter.record_conversation_event(
            conversation_id="conv-1",
            kind=MAFEventKind.MESSAGE_RECEIVED,
            summary={"role": "user", "len": 142},
        )
        entry = chain.appended[0]
        assert entry["event_type"] == AuditEventType.DECISION_MADE
        assert entry["payload"]["maf_event_kind"] == "message_received"
        assert entry["payload"]["conversation_id"] == "conv-1"
        assert entry["payload"]["summary"] == {"role": "user", "len": 142}

    def test_tool_call_recorded(self) -> None:
        chain = _SpyChain()
        adapter = MAFAuditAdapter(audit_chain=chain, agent_id="zeus:maf")
        adapter.record_tool_call(
            conversation_id="conv-1",
            tool_name="lookup_account",
            arguments_summary={"account_id_hash": "abc123"},
        )
        entry = chain.appended[0]
        assert entry["payload"]["maf_event_kind"] == "tool_call"
        assert entry["payload"]["tool_name"] == "lookup_account"
        assert entry["payload"]["arguments_summary"] == {"account_id_hash": "abc123"}

    def test_workflow_step_recorded(self) -> None:
        chain = _SpyChain()
        adapter = MAFAuditAdapter(audit_chain=chain, agent_id="zeus:maf")
        adapter.record_workflow_step(
            workflow_id="wf-1",
            step_name="risk_check",
            status="completed",
        )
        entry = chain.appended[0]
        assert entry["payload"]["maf_event_kind"] == "workflow_step"
        assert entry["payload"]["workflow_id"] == "wf-1"
        assert entry["payload"]["step_name"] == "risk_check"
        assert entry["payload"]["status"] == "completed"


# --------------------------------------------------------------------------- #
# Cross-protocol (A2A + MCP) capture                                          #
# --------------------------------------------------------------------------- #


class TestCrossProtocol:
    def test_a2a_interop_event_recorded(self) -> None:
        chain = _SpyChain()
        adapter = MAFAuditAdapter(audit_chain=chain, agent_id="zeus:maf")
        adapter.record_interop_event(
            protocol=MAFInteropProtocol.A2A,
            conversation_id="conv-1",
            peer_id="counterparty:agent-7",
            summary={"task_id": "t-7"},
        )
        entry = chain.appended[0]
        assert entry["payload"]["maf_event_kind"] == "interop"
        assert entry["payload"]["interop_protocol"] == "a2a"
        assert entry["payload"]["peer_id"] == "counterparty:agent-7"

    def test_mcp_interop_event_recorded(self) -> None:
        chain = _SpyChain()
        adapter = MAFAuditAdapter(audit_chain=chain, agent_id="zeus:maf")
        adapter.record_interop_event(
            protocol=MAFInteropProtocol.MCP,
            conversation_id="conv-1",
            peer_id="mcp:filesystem",
            summary={"resource": "policy.md"},
        )
        entry = chain.appended[0]
        assert entry["payload"]["interop_protocol"] == "mcp"
        assert entry["payload"]["peer_id"] == "mcp:filesystem"


# --------------------------------------------------------------------------- #
# Sovereign-veto wiring                                                       #
# --------------------------------------------------------------------------- #


class TestSovereignVetoWiring:
    def test_veto_blocks_tool_call(self) -> None:
        chain = _SpyChain()
        veto = SovereignVeto(agent_id="zeus:maf")
        adapter = MAFAuditAdapter(
            audit_chain=chain,
            agent_id="zeus:maf",
            veto=veto,
        )
        veto.trigger(
            VetoReason.POLICY_VIOLATION,
            triggered_by="policy_engine",
            description="banned tool",
        )
        with pytest.raises(VetoBlockedError):
            adapter.record_tool_call(
                conversation_id="conv-1",
                tool_name="lookup_account",
                arguments_summary={},
            )
        assert chain.appended == []


# --------------------------------------------------------------------------- #
# Real AuditChain integration smoke                                           #
# --------------------------------------------------------------------------- #


class TestRealAuditChainIntegration:
    def test_emits_into_real_chain(self, tmp_path: Any) -> None:
        chain = AuditChain(log_file=tmp_path / "maf_audit.jsonl")
        adapter = MAFAuditAdapter(audit_chain=chain, agent_id="zeus:maf")
        adapter.record_conversation_event(
            conversation_id="conv-1",
            kind=MAFEventKind.MESSAGE_RECEIVED,
            summary={"role": "user"},
        )
        adapter.record_tool_call(
            conversation_id="conv-1",
            tool_name="lookup_policy",
            arguments_summary={"policy_id": "p1"},
        )
        adapter.record_interop_event(
            protocol=MAFInteropProtocol.A2A,
            conversation_id="conv-1",
            peer_id="counterparty:agent-7",
            summary={},
        )
        assert chain.verify() is True
        assert len(chain._events) == 3


# --------------------------------------------------------------------------- #
# Demo entrypoint                                                             #
# --------------------------------------------------------------------------- #


class TestDemoEntrypoint:
    def test_demo_does_not_raise(self, capsys: pytest.CaptureFixture[str]) -> None:
        maf_adapter._run_demo()
        out = capsys.readouterr().out
        assert "HAS_MAF" in out
