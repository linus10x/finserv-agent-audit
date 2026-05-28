"""Tests for Autonomy Ladder A0 -> A4 — ADR-0004 (paired with ADR-0007)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from finserv_agent_audit.governance.autonomy_ladder import (
    AutonomyTier,
    PromotionGateNotMet,
    PromotionGateReport,
    PromotionRequirements,
    check_a2_to_a3_promotion,
)
from finserv_agent_audit.schemas.audit_event import AutonomyLevel


class TestTierLevels:
    def test_a0_has_no_write_authority(self) -> None:
        assert AutonomyTier.A0_INFORMATIONAL.can_write is False

    def test_a1_requires_human_approval_for_writes(self) -> None:
        assert AutonomyTier.A1_ASSISTED.can_write is True
        assert AutonomyTier.A1_ASSISTED.requires_human_approval is True

    def test_a2_writes_inside_envelope_with_sampling(self) -> None:
        tier = AutonomyTier.A2_DELEGATED
        assert tier.can_write is True
        assert tier.requires_human_approval is False
        assert tier.requires_sampled_review is True
        assert tier.requires_envelope is True

    def test_a3_is_supervised_autonomous(self) -> None:
        tier = AutonomyTier.A3_SUPERVISED_AUTONOMOUS
        assert tier.can_write is True
        assert tier.requires_human_approval is False
        assert tier.requires_sampled_review is False
        # A3 supervision is by-exception only.
        assert tier.requires_human_exception_supervision is True

    def test_a4_is_production_autonomous(self) -> None:
        assert AutonomyTier.A4_PRODUCTION_AUTONOMOUS.can_write is True
        assert AutonomyTier.A4_PRODUCTION_AUTONOMOUS.requires_human_exception_supervision is True

    def test_a0_does_not_require_envelope_or_sampling(self) -> None:
        tier = AutonomyTier.A0_INFORMATIONAL
        assert tier.requires_envelope is False
        assert tier.requires_sampled_review is False
        assert tier.requires_human_approval is False
        assert tier.requires_human_exception_supervision is False

    def test_tiers_ordered_a0_through_a4(self) -> None:
        tiers = list(AutonomyTier)
        assert tiers[0] is AutonomyTier.A0_INFORMATIONAL
        assert tiers[-1] is AutonomyTier.A4_PRODUCTION_AUTONOMOUS


class TestCrossReferenceWithAuditEventEnum:
    """AutonomyTier (this module) and AutonomyLevel (schemas) carry the
    same A0..A4 short codes. AutonomyTier carries the runtime semantics;
    AutonomyLevel is the wire format written into every audit entry.
    The two must stay in lockstep across the five tiers."""

    def test_short_codes_match_audit_level_enum(self) -> None:
        assert AutonomyTier.A0_INFORMATIONAL.value == AutonomyLevel.A0.value
        assert AutonomyTier.A1_ASSISTED.value == AutonomyLevel.A1.value
        assert AutonomyTier.A2_DELEGATED.value == AutonomyLevel.A2.value
        assert AutonomyTier.A3_SUPERVISED_AUTONOMOUS.value == AutonomyLevel.A3.value
        assert AutonomyTier.A4_PRODUCTION_AUTONOMOUS.value == AutonomyLevel.A4.value


class TestA2ToA3PromotionGate:
    def _passing_requirements(self) -> PromotionRequirements:
        return PromotionRequirements(
            sovereign_veto_load_tested=True,
            audit_ledger_running_for=timedelta(days=95),
            shadow_mode_running_for=timedelta(days=35),
            circuit_breaker_test_recent=True,
        )

    def test_all_criteria_met_returns_pass(self) -> None:
        report = check_a2_to_a3_promotion(self._passing_requirements())
        assert isinstance(report, PromotionGateReport)
        assert report.passed is True
        assert report.failures == ()

    def test_sovereign_veto_not_load_tested_blocks(self) -> None:
        reqs = self._passing_requirements()
        reqs = PromotionRequirements(**{**reqs.__dict__, "sovereign_veto_load_tested": False})
        report = check_a2_to_a3_promotion(reqs)
        assert report.passed is False
        assert any("sovereign_veto" in failure for failure in report.failures)

    def test_audit_ledger_under_90_days_blocks(self) -> None:
        reqs = self._passing_requirements()
        reqs = PromotionRequirements(
            **{**reqs.__dict__, "audit_ledger_running_for": timedelta(days=89)}
        )
        report = check_a2_to_a3_promotion(reqs)
        assert report.passed is False
        assert any("audit_ledger" in failure for failure in report.failures)

    def test_shadow_mode_under_30_days_blocks(self) -> None:
        reqs = self._passing_requirements()
        reqs = PromotionRequirements(
            **{**reqs.__dict__, "shadow_mode_running_for": timedelta(days=29)}
        )
        report = check_a2_to_a3_promotion(reqs)
        assert report.passed is False
        assert any("shadow_mode" in failure for failure in report.failures)

    def test_circuit_breaker_not_tested_blocks(self) -> None:
        reqs = self._passing_requirements()
        reqs = PromotionRequirements(**{**reqs.__dict__, "circuit_breaker_test_recent": False})
        report = check_a2_to_a3_promotion(reqs)
        assert report.passed is False
        assert any("circuit_breaker" in failure for failure in report.failures)

    def test_multiple_failures_all_reported(self) -> None:
        reqs = PromotionRequirements(
            sovereign_veto_load_tested=False,
            audit_ledger_running_for=timedelta(days=10),
            shadow_mode_running_for=timedelta(days=5),
            circuit_breaker_test_recent=False,
        )
        report = check_a2_to_a3_promotion(reqs)
        assert report.passed is False
        assert len(report.failures) == 4

    def test_raise_if_blocked_does_nothing_on_pass(self) -> None:
        report = check_a2_to_a3_promotion(self._passing_requirements())
        report.raise_if_blocked()  # must not raise

    def test_raise_if_blocked_raises_on_failure(self) -> None:
        reqs = PromotionRequirements(
            sovereign_veto_load_tested=False,
            audit_ledger_running_for=timedelta(days=10),
            shadow_mode_running_for=timedelta(days=5),
            circuit_breaker_test_recent=False,
        )
        report = check_a2_to_a3_promotion(reqs)
        with pytest.raises(PromotionGateNotMet):
            report.raise_if_blocked()

    def test_boundary_90_days_audit_ledger_passes(self) -> None:
        reqs = PromotionRequirements(
            sovereign_veto_load_tested=True,
            audit_ledger_running_for=timedelta(days=90),
            shadow_mode_running_for=timedelta(days=30),
            circuit_breaker_test_recent=True,
        )
        report = check_a2_to_a3_promotion(reqs)
        assert report.passed is True
