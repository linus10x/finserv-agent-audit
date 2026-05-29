"""
Tests for the SovereignVeto pattern.
"""

from __future__ import annotations

import pytest

from patterns.sovereign_veto import (
    SovereignVeto,
    VetoBlockedError,
    VetoReason,
    VetoRecord,
)


@pytest.fixture
def veto() -> SovereignVeto:
    return SovereignVeto(agent_id="test-agent")


class TestVetoGate:
    def test_allows_execution_when_no_veto(self, veto: SovereignVeto) -> None:
        assert veto.allow_execution() is True
        assert veto.is_vetoed is False

    def test_blocks_execution_after_trigger(self, veto: SovereignVeto) -> None:
        veto.trigger(VetoReason.RISK_LIMIT_BREACH, "risk_monitor", "ALERT threshold")
        assert veto.allow_execution() is False
        assert veto.is_vetoed is True

    def test_trigger_returns_veto_record(self, veto: SovereignVeto) -> None:
        record = veto.trigger(VetoReason.MANUAL_OPERATOR, "cto", "Suspicious pattern")
        assert isinstance(record, VetoRecord)
        assert record.is_active is True
        assert record.reason == VetoReason.MANUAL_OPERATOR

    def test_multiple_vetos_stack(self, veto: SovereignVeto) -> None:
        veto.trigger(VetoReason.RISK_LIMIT_BREACH, "risk_monitor", "drawdown")
        veto.trigger(VetoReason.POLICY_VIOLATION, "policy_engine", "position limit")
        assert len(veto.active_vetos()) == 2

    def test_clear_all_removes_block(self, veto: SovereignVeto) -> None:
        veto.trigger(VetoReason.RISK_LIMIT_BREACH, "risk_monitor", "drawdown")
        veto.clear("operator_001", "Reviewed — within policy")
        assert veto.allow_execution() is True
        assert veto.is_vetoed is False

    def test_clear_specific_veto_by_id(self, veto: SovereignVeto) -> None:
        r1 = veto.trigger(VetoReason.RISK_LIMIT_BREACH, "risk_monitor", "drawdown")
        r2 = veto.trigger(VetoReason.POLICY_VIOLATION, "policy_engine", "limit")
        veto.clear("operator_001", "Reviewed r1", veto_id=r1.veto_id)
        assert not r1.is_active
        assert r2.is_active
        assert veto.is_vetoed is True

    def test_clear_records_operator_and_reason(self, veto: SovereignVeto) -> None:
        record = veto.trigger(VetoReason.ANOMALY_DETECTED, "sentinel", "anomaly")
        veto.clear("risk_officer_007", "False positive confirmed")
        assert record.cleared_by == "risk_officer_007"
        assert record.clear_reason == "False positive confirmed"
        assert record.cleared_at is not None

    def test_history_preserves_cleared_vetos(self, veto: SovereignVeto) -> None:
        veto.trigger(VetoReason.COMPLIANCE_FLAG, "compliance_engine", "flag")
        veto.clear("operator_001", "Reviewed")
        assert len(veto.history()) == 1
        assert veto.history()[0].is_active is False

    def test_on_veto_callback_fires(self) -> None:
        fired = []
        v = SovereignVeto(agent_id="zeus", on_veto=lambda r: fired.append(r))
        v.trigger(VetoReason.PEER_AGENT_CHALLENGE, "shadow_agent", "challenge")
        assert len(fired) == 1

    def test_on_clear_callback_fires(self) -> None:
        cleared = []
        v = SovereignVeto(agent_id="zeus", on_clear=lambda r: cleared.append(r))
        v.trigger(VetoReason.MANUAL_OPERATOR, "cto", "manual")
        v.clear("operator_001", "OK")
        assert len(cleared) == 1

    def test_veto_blocked_error_pattern(self, veto: SovereignVeto) -> None:
        veto.trigger(VetoReason.RISK_LIMIT_BREACH, "risk_monitor", "halt")
        with pytest.raises(VetoBlockedError):
            if not veto.allow_execution():
                raise VetoBlockedError("Execution blocked by sovereign veto")


# --------------------------------------------------------------------------- #
# CR-12 — Authorizer protocol gates clear() + self-clear rule                 #
# --------------------------------------------------------------------------- #


class TestAuthorizer:
    def test_no_authorizer_logs_warning_on_construction(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        from finserv_agent_audit.governance.sovereign_veto import SovereignVeto

        with caplog.at_level("WARNING"):
            SovereignVeto(agent_id="zeus")
        assert any("Authorizer" in rec.message for rec in caplog.records)

    def test_authorizer_can_block_clear(self) -> None:
        from finserv_agent_audit.governance.sovereign_veto import (
            SovereignVeto,
            VetoBlockedError,
            VetoReason,
        )

        class DenyAll:
            def authorize(self, operator_id: str, action: str, context: dict[str, object]) -> bool:
                return False

        veto = SovereignVeto(agent_id="zeus", authorizer=DenyAll())
        veto.trigger(VetoReason.RISK_LIMIT_BREACH, "risk_monitor", "drawdown")
        with pytest.raises(VetoBlockedError, match="Authorizer rejected"):
            veto.clear(operator_id="operator-001", reason="reviewed")
        # Still vetoed since clear was rejected.
        assert veto.is_vetoed is True

    def test_authorizer_allows_clear(self) -> None:
        from finserv_agent_audit.governance.sovereign_veto import (
            SovereignVeto,
            VetoReason,
        )

        class AllowAll:
            def authorize(self, operator_id: str, action: str, context: dict[str, object]) -> bool:
                return True

        veto = SovereignVeto(agent_id="zeus", authorizer=AllowAll())
        veto.trigger(VetoReason.RISK_LIMIT_BREACH, "risk_monitor", "drawdown")
        veto.clear(operator_id="operator-001", reason="reviewed")
        assert veto.is_vetoed is False

    def test_self_clearing_rule_blocks_agent_clearing_own_veto(self) -> None:
        from finserv_agent_audit.governance.sovereign_veto import (
            SovereignVeto,
            VetoBlockedError,
            VetoReason,
        )

        class AllowAll:
            def authorize(self, operator_id: str, action: str, context: dict[str, object]) -> bool:
                return True

        veto = SovereignVeto(agent_id="zeus", authorizer=AllowAll())
        veto.trigger(VetoReason.RISK_LIMIT_BREACH, "risk_monitor", "drawdown")
        # Even though the Authorizer would allow, operator_id == agent_id is
        # blocked by the self-clearing rule.
        with pytest.raises(VetoBlockedError, match="self-clearing"):
            veto.clear(operator_id="zeus", reason="self-clear attempt")
        assert veto.is_vetoed is True
