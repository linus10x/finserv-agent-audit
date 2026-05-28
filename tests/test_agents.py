"""Smoke tests for the reference agent topology.

The reference agents (audit, monitor, orchestrator) are thin stubs that
demonstrate how to wire AuditConsumer in a system. These tests verify
the interfaces load cleanly, role names are stable, and the agents
compose against the real AuditChain.
"""

from __future__ import annotations

from pathlib import Path

from finserv_agent_audit.agents.audit import AuditAgent, AuditQuery
from finserv_agent_audit.agents.monitor import MonitorAgent
from finserv_agent_audit.agents.orchestrator import OrchestratorAgent
from finserv_agent_audit.schemas.audit_event import (
    AuditChain,
    AuditEventType,
    AutonomyLevel,
)


def _chain(tmp_path: Path, name: str = "audit.jsonl") -> AuditChain:
    return AuditChain(log_file=tmp_path / name)


def test_agent_roles_have_canonical_names(tmp_path: Path) -> None:
    assert AuditAgent(audit_chain=_chain(tmp_path)).role == "audit"
    assert MonitorAgent.role == "monitor"
    assert OrchestratorAgent().role == "orchestrator"


def test_audit_agent_filters_chain_by_event_type(tmp_path: Path) -> None:
    chain = _chain(tmp_path)
    chain.append(
        event_type=AuditEventType.DECISION_MADE,
        autonomy_level=AutonomyLevel.A2,
        agent_id="strategy",
        payload={"action": "buy"},
    )
    chain.append(
        event_type=AuditEventType.COMPLIANCE_CHECK,
        autonomy_level=AutonomyLevel.A3,
        agent_id="sentinel",
        payload={"check": "kyc"},
    )
    agent = AuditAgent(audit_chain=chain)
    events = agent.process(AuditQuery(event_type=AuditEventType.DECISION_MADE.value))
    assert len(events) == 1
    assert events[0].event_type is AuditEventType.DECISION_MADE


def test_audit_agent_filters_by_agent_id(tmp_path: Path) -> None:
    chain = _chain(tmp_path)
    chain.append(
        event_type=AuditEventType.DECISION_MADE,
        autonomy_level=AutonomyLevel.A2,
        agent_id="strategy_v1",
        payload={"a": 1},
    )
    chain.append(
        event_type=AuditEventType.RISK_ESCALATION,
        autonomy_level=AutonomyLevel.A1,
        agent_id="defcon",
        payload={"to": "DEFCON_3"},
    )
    agent = AuditAgent(audit_chain=chain)
    events = agent.process(AuditQuery(agent_id="strategy_v1"))
    assert len(events) == 1
    assert events[0].agent_id == "strategy_v1"


def test_audit_agent_filters_by_since_index(tmp_path: Path) -> None:
    chain = _chain(tmp_path)
    for i in range(3):
        chain.append(
            event_type=AuditEventType.COMPLIANCE_CHECK,
            autonomy_level=AutonomyLevel.A3,
            agent_id="sentinel",
            payload={"i": i},
        )
    agent = AuditAgent(audit_chain=chain)
    events = agent.process(AuditQuery(since_index=2))
    assert len(events) == 1


def test_orchestrator_accepts_all_optional_subagents(tmp_path: Path) -> None:
    chain = _chain(tmp_path)
    orchestrator = OrchestratorAgent(
        audit=AuditAgent(audit_chain=chain),
        monitor=MonitorAgent(audit_chain=chain),
        audit_chain=chain,
    )
    assert orchestrator.process({}) is None  # reference stub


def test_reference_stubs_return_safe_defaults(tmp_path: Path) -> None:
    assert (
        MonitorAgent(audit_chain=_chain(tmp_path)).process(
            AuditChain(log_file=tmp_path / "other.jsonl")
        )
        == ()
    )
    assert OrchestratorAgent().process({}) is None
