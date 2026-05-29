"""CR-5 regression — DEFCONMachine MUST include metrics_snapshot in the hash.

Pre-fix, both ``examples/defcon_state_machine.py`` and
``src/finserv_agent_audit/governance/defcon.py`` shipped their own
local ``AuditEvent`` class whose ``_compute_hash`` payload OMITTED
the ``metrics_snapshot`` field. An attacker with write access to the
JSONL could rewrite ``metrics_snapshot`` (turning a 50% drawdown into
a 5% drawdown) and the chain still verified — the rewritten field
was never folded into the hash.

The fix replaces the duplicate ``AuditEvent`` with the canonical one
from ``schemas/audit_event.py`` and folds the metrics_snapshot into
the canonical ``payload`` field. The canonical AuditEvent's
``_compute_hash`` covers the full payload, so any post-hoc metrics
rewrite changes the recomputed hash and fails ``from_jsonl`` /
``verify``.

These tests assert:

  * Two events that differ only in ``metrics_snapshot.drawdown``
    (0.05 vs 0.50) produce DIFFERENT ``event_hash`` values.
  * A tampered JSONL line where ``metrics_snapshot`` is rewritten
    fails the canonical replay gate (``from_jsonl``) — same
    contract the rest of the chain uses.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from finserv_agent_audit.governance.audit_chain import AuditChainTamperError
from finserv_agent_audit.governance.defcon import (
    DEFCON,
    DEFCONMachine,
    RiskMetrics,
)
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)


def _make_event_with_metric(drawdown: float) -> AuditEvent:
    """Construct an AuditEvent identical in every field except
    metrics_snapshot.portfolio_drawdown — the controlled-pair fixture.
    """
    return AuditEvent.create(
        event_type=AuditEventType.RISK_ESCALATION,
        autonomy_level=AutonomyLevel.A2,
        agent_id="defcon-state-machine",
        payload={
            "from_level": "NORMAL",
            "to_level": "CAUTION",
            "trigger": "escalation",
            "metrics_snapshot": {
                "portfolio_drawdown": drawdown,
                "daily_loss": 0.01,
                "consecutive_losses": 0,
            },
        },
        prev_hash="0" * 64,
        event_id="evt-fixed",
        timestamp="2026-05-28T00:00:00+00:00",
    )


class TestMetricsSnapshotIsHashCovered:
    """Two events differing only in metrics_snapshot MUST produce different hashes."""

    def test_controlled_pair_differs_only_in_drawdown(self) -> None:
        evt_low = _make_event_with_metric(0.05)
        evt_high = _make_event_with_metric(0.50)
        assert evt_low.event_hash != evt_high.event_hash, (
            "Two events differing ONLY in metrics_snapshot.drawdown "
            "MUST produce different event_hash values — otherwise a "
            "post-hoc rewrite of the metric is undetectable"
        )

    def test_governance_defcon_persists_metrics_in_payload(self, tmp_path: Path) -> None:
        machine = DEFCONMachine(
            state_file=tmp_path / "state.json",
            audit_file=tmp_path / "audit.jsonl",
        )
        # 0.08 sits between DRAWDOWN_CAUTION (0.07) and DRAWDOWN_ALERT
        # (0.10) so the transition is NORMAL -> CAUTION.
        machine.evaluate(
            RiskMetrics(portfolio_drawdown=0.08, daily_loss=0.01, consecutive_losses=0)
        )
        line = (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()[0]
        evt = json.loads(line)

        # metrics_snapshot MUST live inside the canonical payload —
        # that's the field _compute_hash covers.
        assert "payload" in evt
        assert "metrics_snapshot" in evt["payload"]
        snap = evt["payload"]["metrics_snapshot"]
        assert snap["portfolio_drawdown"] == 0.08
        assert snap["daily_loss"] == 0.01
        assert snap["consecutive_losses"] == 0

        # And the persisted event MUST replay cleanly through the
        # canonical AuditEvent.from_jsonl gate (proves the recompute
        # matches the stored hash with metrics_snapshot folded in).
        AuditEvent.from_jsonl(evt)


class TestTamperedMetricsFailsReplay:
    """A JSONL line whose metrics_snapshot is rewritten MUST fail replay."""

    def test_rewriting_metrics_breaks_canonical_replay(self, tmp_path: Path) -> None:
        machine = DEFCONMachine(
            state_file=tmp_path / "state.json",
            audit_file=tmp_path / "audit.jsonl",
        )
        # Trigger a HALT transition with a high drawdown value we'll
        # try to rewrite. 0.50 drawdown is way above DRAWDOWN_HALT
        # (0.20) so the transition is NORMAL -> HALT.
        machine.evaluate(
            RiskMetrics(portfolio_drawdown=0.50, daily_loss=0.02, consecutive_losses=0)
        )
        assert machine.level == DEFCON.HALT

        line = (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()[0]
        evt = json.loads(line)

        # Attacker rewrites the drawdown to a benign value but leaves
        # the event_hash unchanged (the attacker has no key, only
        # write access). With metrics_snapshot now folded into the
        # canonical payload, the recompute disagrees with the stored
        # hash — ``from_jsonl`` raises.
        evt["payload"]["metrics_snapshot"]["portfolio_drawdown"] = 0.05

        with pytest.raises(AuditChainTamperError, match="event_hash mismatch"):
            AuditEvent.from_jsonl(evt)


class TestExamplesDefconMetricsCovered:
    """The examples/defcon_state_machine.py demo MUST share the discipline."""

    def test_examples_demo_metrics_in_hash(self, tmp_path: Path) -> None:
        from examples.defcon_state_machine import DEFCON as DEMO_DEFCON
        from examples.defcon_state_machine import (
            DEFCONMachine as DemoDEFCONMachine,
        )
        from examples.defcon_state_machine import (
            RiskMetrics as DemoRiskMetrics,
        )

        # Two machines, same transition, different drawdown.
        a = DemoDEFCONMachine(
            state_file=tmp_path / "a.json",
            audit_file=tmp_path / "a.jsonl",
        )
        b = DemoDEFCONMachine(
            state_file=tmp_path / "b.json",
            audit_file=tmp_path / "b.jsonl",
        )
        # 0.08 and 0.09 both sit between DRAWDOWN_CAUTION (0.07) and
        # DRAWDOWN_ALERT (0.10) so both transitions are NORMAL ->
        # CAUTION but the metric snapshots differ.
        a.evaluate(DemoRiskMetrics(0.08, 0.01, 0))  # -> CAUTION
        b.evaluate(DemoRiskMetrics(0.09, 0.01, 0))  # -> CAUTION
        assert a.level == DEMO_DEFCON.CAUTION
        assert b.level == DEMO_DEFCON.CAUTION

        line_a = (tmp_path / "a.jsonl").read_text(encoding="utf-8").splitlines()[0]
        line_b = (tmp_path / "b.jsonl").read_text(encoding="utf-8").splitlines()[0]
        evt_a = json.loads(line_a)
        evt_b = json.loads(line_b)

        # Different drawdown -> different event_hash. Pre-fix the
        # event_hash was computed over a payload that excluded
        # metrics_snapshot, so the two hashes were identical for
        # the same transition regardless of drawdown.
        assert evt_a["event_hash"] != evt_b["event_hash"], (
            "Two demo events differing ONLY in metrics_snapshot "
            "must produce different event_hash values"
        )

    def test_examples_demo_tampered_metrics_fails_replay(self, tmp_path: Path) -> None:
        from examples.defcon_state_machine import (
            DEFCONMachine as DemoDEFCONMachine,
        )
        from examples.defcon_state_machine import (
            RiskMetrics as DemoRiskMetrics,
        )

        machine = DemoDEFCONMachine(
            state_file=tmp_path / "state.json",
            audit_file=tmp_path / "audit.jsonl",
        )
        machine.evaluate(DemoRiskMetrics(0.50, 0.02, 0))  # -> HALT

        line = (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()[0]
        evt = json.loads(line)
        evt["payload"]["metrics_snapshot"]["portfolio_drawdown"] = 0.05

        with pytest.raises(AuditChainTamperError, match="event_hash mismatch"):
            AuditEvent.from_jsonl(evt)
