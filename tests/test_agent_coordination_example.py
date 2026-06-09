"""Tests for the domain-agnostic agent-coordination reference example.

Covers the example in CI so the README's "Run in 60 seconds" claim stays true:
the swarm exercises the sovereign veto, the hard envelope, the hash-chained
audit ledger, and autonomy-rung demotion — with no financial domain.
"""

from __future__ import annotations

from examples.agent_coordination.coordination import main, run_pipeline
from finserv_agent_audit.governance.autonomy_ladder import AutonomyTier
from finserv_agent_audit.schemas.audit_event import AuditEventType


def test_pipeline_audit_chain_verifies() -> None:
    chain = run_pipeline()
    # The hash-chain ledger is tamper-evident within-trust-boundary.
    assert chain.verify() is True


def test_pipeline_vetoes_irreversible_action() -> None:
    chain = run_pipeline()
    veto_events = [e for e in chain._events if e.event_type is AuditEventType.DECISION_VETOED]
    # Both irreversible 'dispatch' attempts were vetoed and routed to a human.
    assert len(veto_events) == 2
    assert all(e.payload["in_envelope"] is False for e in veto_events)
    assert all(e.payload["routed_to"] == "operator_alex" for e in veto_events)


def test_pipeline_demotes_on_drift() -> None:
    chain = run_pipeline()
    demotions = [
        e
        for e in chain._events
        if e.event_type is AuditEventType.RISK_ESCALATION
        and e.payload.get("event") == "autonomy_demotion"
    ]
    # Drift (repeated out-of-envelope attempts) demotes the agent one rung.
    assert len(demotions) == 1
    assert demotions[0].payload["from_tier"] == AutonomyTier.A3_SUPERVISED_AUTONOMOUS.value
    assert demotions[0].payload["to_tier"] == AutonomyTier.A2_DELEGATED.value


def test_main_runs_clean(capsys: object) -> None:
    # The script entry point runs end to end without raising (its closing
    # assert confirms the audit chain verified).
    main()
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "verify() = True" in out
    assert "[VETO]" in out
    assert "[DEMOTE]" in out
