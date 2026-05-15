"""
Tests for the DEFCON state machine reference implementation.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from examples.defcon_state_machine import (
    DEFCON,
    DEFCONMachine,
    HYSTERESIS_CONFIRMATIONS,
    RiskMetrics,
)


@pytest.fixture
def tmp_machine(tmp_path: Path) -> DEFCONMachine:
    return DEFCONMachine(
        state_file=tmp_path / "state.json",
        audit_file=tmp_path / "audit.jsonl",
    )


class TestEscalation:
    def test_normal_to_caution(self, tmp_machine: DEFCONMachine) -> None:
        metrics = RiskMetrics(portfolio_drawdown=0.08, daily_loss=0.01, consecutive_losses=0)
        level = tmp_machine.evaluate(metrics)
        assert level == DEFCON.CAUTION

    def test_immediate_halt(self, tmp_machine: DEFCONMachine) -> None:
        metrics = RiskMetrics(portfolio_drawdown=0.25, daily_loss=0.01, consecutive_losses=0)
        level = tmp_machine.evaluate(metrics)
        assert level == DEFCON.HALT

    def test_escalation_is_immediate(self, tmp_machine: DEFCONMachine) -> None:
        """Single evaluation at a higher risk level triggers immediate escalation."""
        tmp_machine.evaluate(RiskMetrics(0.01, 0.01, 0))  # NORMAL
        assert tmp_machine.level == DEFCON.NORMAL
        tmp_machine.evaluate(RiskMetrics(0.16, 0.01, 0))  # -> DANGER immediately
        assert tmp_machine.level == DEFCON.DANGER


class TestDeEscalation:
    def test_hysteresis_requires_n_confirmations(self, tmp_machine: DEFCONMachine) -> None:
        """De-escalation requires HYSTERESIS_CONFIRMATIONS consecutive evals."""
        # Escalate to ALERT
        tmp_machine.evaluate(RiskMetrics(0.11, 0.01, 0))
        assert tmp_machine.level == DEFCON.ALERT

        # Below-alert metrics — should NOT de-escalate until N confirmations
        below_alert = RiskMetrics(0.08, 0.01, 0)  # -> targets CAUTION
        for i in range(HYSTERESIS_CONFIRMATIONS - 1):
            tmp_machine.evaluate(below_alert)
            assert tmp_machine.level == DEFCON.ALERT, f"Should still be ALERT after {i+1} eval(s)"

        # N-th confirmation triggers de-escalation
        tmp_machine.evaluate(below_alert)
        assert tmp_machine.level == DEFCON.CAUTION

    def test_hysteresis_resets_on_different_target(self, tmp_machine: DEFCONMachine) -> None:
        """Pending de-escalation resets if the target level changes."""
        tmp_machine.evaluate(RiskMetrics(0.11, 0.01, 0))  # -> ALERT
        tmp_machine.evaluate(RiskMetrics(0.08, 0.01, 0))  # pending CAUTION, count=1
        tmp_machine.evaluate(RiskMetrics(0.01, 0.01, 0))  # pending NORMAL, count resets to 1
        assert tmp_machine.level == DEFCON.ALERT  # still ALERT — confirmation count reset


class TestHalt:
    def test_halt_blocks_evaluation(self, tmp_machine: DEFCONMachine) -> None:
        """HALT blocks all automatic evaluation."""
        tmp_machine.evaluate(RiskMetrics(0.25, 0.01, 0))  # -> HALT
        level = tmp_machine.evaluate(RiskMetrics(0.01, 0.01, 0))  # stays HALT
        assert level == DEFCON.HALT

    def test_manual_override_clears_halt(self, tmp_machine: DEFCONMachine) -> None:
        """Human manual_override() is required to exit HALT."""
        tmp_machine.evaluate(RiskMetrics(0.25, 0.01, 0))  # -> HALT
        assert tmp_machine.level == DEFCON.HALT
        tmp_machine.manual_override(
            target=DEFCON.CAUTION,
            operator_id="risk_officer_001",
            reason="Reviewed P&L. Drawdown was mark-to-market; position has recovered.",
        )
        assert tmp_machine.level == DEFCON.CAUTION


class TestAuditChain:
    def test_audit_file_created_on_transition(self, tmp_machine: DEFCONMachine, tmp_path: Path) -> None:
        tmp_machine.evaluate(RiskMetrics(0.11, 0.01, 0))  # -> ALERT: writes audit entry
        audit_file = tmp_path / "audit.jsonl"
        assert audit_file.exists()
        lines = audit_file.read_text().strip().splitlines()
        assert len(lines) == 1

    def test_hash_chain_integrity(self, tmp_machine: DEFCONMachine, tmp_path: Path) -> None:
        import json, hashlib
        tmp_machine.evaluate(RiskMetrics(0.08, 0.01, 0))   # CAUTION
        tmp_machine.evaluate(RiskMetrics(0.11, 0.01, 0))   # ALERT
        audit_file = tmp_path / "audit.jsonl"
        events = [json.loads(ln) for ln in audit_file.read_text().splitlines() if ln.strip()]
        assert len(events) == 2
        # First event's prev_hash is the genesis hash
        assert events[0]["prev_hash"] == "0" * 64
        # Second event's prev_hash matches first event's hash
        assert events[1]["prev_hash"] == events[0]["event_hash"]


class TestStatePersistence:
    def test_state_persists_across_instances(self, tmp_path: Path) -> None:
        """State file allows machine to reload its last confirmed level on restart."""
        m1 = DEFCONMachine(state_file=tmp_path / "s.json", audit_file=tmp_path / "a.jsonl")
        m1.evaluate(RiskMetrics(0.16, 0.01, 0))  # -> DANGER
        assert m1.level == DEFCON.DANGER

        # Simulate restart
        m2 = DEFCONMachine(state_file=tmp_path / "s.json", audit_file=tmp_path / "a.jsonl")
        assert m2.level == DEFCON.DANGER  # reloaded from disk
