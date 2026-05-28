"""Tests for the CrewAI audit adapter (v2.0)."""

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
from finserv_agent_audit.integrations import crewai_adapter
from finserv_agent_audit.integrations.crewai_adapter import (
    CrewAIAuditAdapter,
    CrewAIEventKind,
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
    def test_has_crewai_flag_is_boolean(self) -> None:
        assert isinstance(crewai_adapter.HAS_CREWAI, bool)

    def test_adapter_constructs_without_crewai(self) -> None:
        adapter = CrewAIAuditAdapter(audit_chain=_SpyChain(), crew_id="research-crew")
        assert adapter.crew_id == "research-crew"

    def test_record_no_chain_is_no_op(self) -> None:
        adapter = CrewAIAuditAdapter(audit_chain=None, crew_id="research-crew")
        assert (
            adapter.record_task_start(
                task_id="task-1",
                task_description="research X",
                role="Senior Researcher",
            )
            is None
        )


# --------------------------------------------------------------------------- #
# Task lifecycle                                                              #
# --------------------------------------------------------------------------- #


class TestTaskLifecycle:
    def test_task_start_recorded(self) -> None:
        chain = _SpyChain()
        adapter = CrewAIAuditAdapter(audit_chain=chain, crew_id="research-crew")
        adapter.record_task_start(
            task_id="task-1",
            task_description="summarize SR 11-7 changes",
            role="Senior Researcher",
        )
        entry = chain.appended[0]
        assert entry["event_type"] == AuditEventType.DECISION_MADE
        # Role becomes the agent_id (per CrewAI's role-based model).
        assert entry["agent_id"] == "research-crew:Senior Researcher"
        assert entry["payload"]["crewai_event_kind"] == "task_start"
        assert entry["payload"]["task_id"] == "task-1"
        assert entry["payload"]["task_description"] == "summarize SR 11-7 changes"
        assert entry["payload"]["role"] == "Senior Researcher"
        assert entry["payload"]["crew_id"] == "research-crew"

    def test_task_complete_recorded(self) -> None:
        chain = _SpyChain()
        adapter = CrewAIAuditAdapter(audit_chain=chain, crew_id="research-crew")
        adapter.record_task_complete(
            task_id="task-1",
            role="Senior Researcher",
            output_summary={"length": 1200, "citations": 4},
        )
        entry = chain.appended[0]
        assert entry["payload"]["crewai_event_kind"] == "task_complete"
        assert entry["payload"]["output_summary"] == {"length": 1200, "citations": 4}


# --------------------------------------------------------------------------- #
# Crew-level events                                                           #
# --------------------------------------------------------------------------- #


class TestCrewEvents:
    def test_crew_kickoff_recorded(self) -> None:
        chain = _SpyChain()
        adapter = CrewAIAuditAdapter(audit_chain=chain, crew_id="research-crew")
        adapter.record_crew_kickoff(agent_roles=["Senior Researcher", "Analyst", "Writer"])
        entry = chain.appended[0]
        # Crew-level events use the crew_id as agent_id.
        assert entry["agent_id"] == "research-crew"
        assert entry["payload"]["crewai_event_kind"] == "crew_kickoff"
        assert entry["payload"]["agent_roles"] == [
            "Senior Researcher",
            "Analyst",
            "Writer",
        ]

    def test_crew_result_recorded(self) -> None:
        chain = _SpyChain()
        adapter = CrewAIAuditAdapter(audit_chain=chain, crew_id="research-crew")
        adapter.record_crew_result(result_summary={"tasks_completed": 3, "total_tokens": 4221})
        entry = chain.appended[0]
        assert entry["agent_id"] == "research-crew"
        assert entry["payload"]["crewai_event_kind"] == "crew_result"
        assert entry["payload"]["result_summary"] == {
            "tasks_completed": 3,
            "total_tokens": 4221,
        }


# --------------------------------------------------------------------------- #
# Multi-agent crews (sequence of distinct roles)                              #
# --------------------------------------------------------------------------- #


class TestMultiAgentCrews:
    def test_three_role_sequence_recorded(self) -> None:
        chain = _SpyChain()
        adapter = CrewAIAuditAdapter(audit_chain=chain, crew_id="research-crew")
        for i, role in enumerate(["Researcher", "Analyst", "Writer"]):
            adapter.record_task_start(
                task_id=f"task-{i}",
                task_description=f"work for {role}",
                role=role,
            )
            adapter.record_task_complete(
                task_id=f"task-{i}",
                role=role,
                output_summary={"len": 100 * (i + 1)},
            )
        assert len(chain.appended) == 6
        # Each task pair carries the role as agent_id.
        observed_roles = {e["agent_id"] for e in chain.appended if "agent_id" in e}
        assert observed_roles == {
            "research-crew:Researcher",
            "research-crew:Analyst",
            "research-crew:Writer",
        }


# --------------------------------------------------------------------------- #
# Sovereign-veto wiring                                                       #
# --------------------------------------------------------------------------- #


class TestSovereignVetoWiring:
    def test_veto_blocks_task_start(self) -> None:
        chain = _SpyChain()
        veto = SovereignVeto(agent_id="research-crew")
        adapter = CrewAIAuditAdapter(
            audit_chain=chain,
            crew_id="research-crew",
            veto=veto,
        )
        veto.trigger(
            VetoReason.POLICY_VIOLATION,
            triggered_by="policy_engine",
            description="banned topic",
        )
        with pytest.raises(VetoBlockedError):
            adapter.record_task_start(
                task_id="task-1",
                task_description="any",
                role="Researcher",
            )
        assert chain.appended == []


# --------------------------------------------------------------------------- #
# Real AuditChain integration smoke                                           #
# --------------------------------------------------------------------------- #


class TestRealAuditChainIntegration:
    def test_emits_into_real_chain(self, tmp_path: Any) -> None:
        chain = AuditChain(log_file=tmp_path / "crewai_audit.jsonl")
        adapter = CrewAIAuditAdapter(audit_chain=chain, crew_id="research-crew")
        adapter.record_crew_kickoff(agent_roles=["Researcher"])
        adapter.record_task_start(
            task_id="task-1",
            task_description="research",
            role="Researcher",
        )
        adapter.record_task_complete(
            task_id="task-1",
            role="Researcher",
            output_summary={"len": 100},
        )
        adapter.record_crew_result(result_summary={"tasks_completed": 1})
        assert chain.verify() is True
        assert len(chain._events) == 4


# --------------------------------------------------------------------------- #
# Demo entrypoint                                                             #
# --------------------------------------------------------------------------- #


class TestDemoEntrypoint:
    def test_demo_does_not_raise(self, capsys: pytest.CaptureFixture[str]) -> None:
        crewai_adapter._run_demo()
        out = capsys.readouterr().out
        assert "HAS_CREWAI" in out


class TestEventKindEnum:
    def test_all_event_kinds_have_unique_values(self) -> None:
        values = [k.value for k in CrewAIEventKind]
        assert len(values) == len(set(values))
