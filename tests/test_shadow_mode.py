"""Tests for Shadow Mode Rollout — ADR-0006."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from finserv_agent_audit.governance.shadow_mode import (
    DecisionClass,
    DecisionOutcome,
    ShadowRouter,
    VetoDirection,
)


def _ts(offset_days: int = 0) -> datetime:
    return datetime(2026, 5, 28, 12, 0, 0, tzinfo=UTC) + timedelta(days=offset_days)


def _outcome(kind: str, *, cohort: str | None = None, reason: str | None = None) -> DecisionOutcome:
    return DecisionOutcome(outcome=kind, veto_reason_code=reason, cohort=cohort)


class TestRouting:
    def test_route_returns_live_outcome(self) -> None:
        live = _outcome("APPROVE", cohort="A")
        shadow = _outcome("APPROVE", cohort="A")
        router = ShadowRouter(
            live_fn=lambda action, *, now=None: live,
            shadow_fn=lambda action, *, now=None: shadow,
        )
        result = router.route(action="any", now=_ts())
        assert result is live

    def test_route_records_both_paths(self) -> None:
        router = ShadowRouter(
            live_fn=lambda action, *, now=None: _outcome("APPROVE", cohort="A"),
            shadow_fn=lambda action, *, now=None: _outcome("DENY", cohort="A"),
        )
        router.route(action="a1", now=_ts())
        router.route(action="a2", now=_ts())
        assert len(router.observations) == 2

    def test_route_uses_injected_now(self) -> None:
        router = ShadowRouter(
            live_fn=lambda action, *, now=None: _outcome("APPROVE"),
            shadow_fn=lambda action, *, now=None: _outcome("APPROVE"),
        )
        router.route(action="x", now=_ts(-10))
        assert router.observations[0].when == _ts(-10)


class TestAggregateDivergenceRate:
    def test_zero_divergence_when_paths_always_agree(self) -> None:
        router = ShadowRouter(
            live_fn=lambda action, *, now=None: _outcome("APPROVE"),
            shadow_fn=lambda action, *, now=None: _outcome("APPROVE"),
        )
        for _ in range(10):
            router.route(action="x", now=_ts())
        assert router.aggregate_divergence_rate() == 0.0

    def test_full_divergence_when_paths_always_disagree(self) -> None:
        router = ShadowRouter(
            live_fn=lambda action, *, now=None: _outcome("APPROVE"),
            shadow_fn=lambda action, *, now=None: _outcome("DENY"),
        )
        for _ in range(10):
            router.route(action="x", now=_ts())
        assert router.aggregate_divergence_rate() == 1.0

    def test_partial_divergence_rate(self) -> None:
        state = {"count": 0}

        def shadow_fn(action: str, *, now: datetime | None = None) -> DecisionOutcome:  # noqa: ARG001
            state["count"] += 1
            return _outcome("DENY") if state["count"] % 4 == 0 else _outcome("APPROVE")

        router = ShadowRouter(
            live_fn=lambda action, *, now=None: _outcome("APPROVE"),
            shadow_fn=shadow_fn,
        )
        for _ in range(8):
            router.route(action="x", now=_ts())
        # 2 of 8 disagreements -> 0.25
        assert router.aggregate_divergence_rate() == pytest.approx(0.25)

    def test_empty_router_returns_zero(self) -> None:
        router = ShadowRouter(
            live_fn=lambda action, *, now=None: _outcome("APPROVE"),
            shadow_fn=lambda action, *, now=None: _outcome("APPROVE"),
        )
        assert router.aggregate_divergence_rate() == 0.0

    def test_window_requires_now(self) -> None:
        router = ShadowRouter(
            live_fn=lambda action, *, now=None: _outcome("APPROVE"),
            shadow_fn=lambda action, *, now=None: _outcome("DENY"),
        )
        router.route(action="x", now=_ts())
        with pytest.raises(ValueError, match="window requires now"):
            router.aggregate_divergence_rate(window=timedelta(days=1))

    def test_window_filters_to_recent_observations(self) -> None:
        router = ShadowRouter(
            live_fn=lambda action, *, now=None: _outcome("APPROVE"),
            shadow_fn=lambda action, *, now=None: _outcome("DENY"),
        )
        # Old observation outside the window.
        router.route(action="old", now=_ts(-30))
        # Recent observations inside the window.
        for _ in range(3):
            router.route(action="x", now=_ts(-1))
        # Aggregate is 4 disagreements / 4 = 1.0; window of 7d filters
        # to the 3 recent, also 1.0.
        rate = router.aggregate_divergence_rate(now=_ts(), window=timedelta(days=7))
        assert rate == 1.0


class TestVetoDirection:
    def test_shadow_more_conservative(self) -> None:
        # Live approves; shadow vetoes some -> shadow is more conservative.
        state = {"i": 0}

        def shadow_fn(action: str, *, now: datetime | None = None) -> DecisionOutcome:  # noqa: ARG001
            state["i"] += 1
            return (
                _outcome("VETO", reason="FCRA-AANOTICE")
                if state["i"] % 2 == 0
                else _outcome("APPROVE")
            )

        router = ShadowRouter(
            live_fn=lambda action, *, now=None: _outcome("APPROVE"),
            shadow_fn=shadow_fn,
        )
        for _ in range(10):
            router.route(action="x", now=_ts())
        assert router.veto_direction() is VetoDirection.SHADOW_MORE_CONSERVATIVE

    def test_shadow_more_aggressive(self) -> None:
        # Live vetoes everything; shadow approves -> shadow is more aggressive.
        router = ShadowRouter(
            live_fn=lambda action, *, now=None: _outcome("VETO", reason="AML-WATCHLIST"),
            shadow_fn=lambda action, *, now=None: _outcome("APPROVE"),
        )
        for _ in range(10):
            router.route(action="x", now=_ts())
        assert router.veto_direction() is VetoDirection.SHADOW_MORE_AGGRESSIVE

    def test_equivalent_when_veto_rates_match(self) -> None:
        router = ShadowRouter(
            live_fn=lambda action, *, now=None: _outcome("VETO", reason="X"),
            shadow_fn=lambda action, *, now=None: _outcome("VETO", reason="X"),
        )
        for _ in range(10):
            router.route(action="x", now=_ts())
        assert router.veto_direction() is VetoDirection.EQUIVALENT

    def test_empty_router_is_equivalent(self) -> None:
        router = ShadowRouter(
            live_fn=lambda action, *, now=None: _outcome("APPROVE"),
            shadow_fn=lambda action, *, now=None: _outcome("APPROVE"),
        )
        assert router.veto_direction() is VetoDirection.EQUIVALENT


class TestCohortDivergence:
    def test_cohort_specific_divergence_isolated_per_cohort(self) -> None:
        # Live approves all; shadow vetoes only cohort B (an ECOA-
        # protected class bucket in this hypothetical).
        def shadow_fn(action: str, *, now: datetime | None = None) -> DecisionOutcome:  # noqa: ARG001
            cohort = "B" if "B" in action else "A"
            if cohort == "B":
                return _outcome("VETO", cohort="B", reason="ECOA-PROXY")
            return _outcome("APPROVE", cohort="A")

        def live_fn(action: str, *, now: datetime | None = None) -> DecisionOutcome:  # noqa: ARG001
            cohort = "B" if "B" in action else "A"
            return _outcome("APPROVE", cohort=cohort)

        router = ShadowRouter(live_fn=live_fn, shadow_fn=shadow_fn)
        for _ in range(5):
            router.route(action="cohortA-x", now=_ts())
        for _ in range(5):
            router.route(action="cohortB-x", now=_ts())
        assert router.cohort_divergence_rate("A") == 0.0
        assert router.cohort_divergence_rate("B") == 1.0

    def test_unknown_cohort_returns_zero(self) -> None:
        router = ShadowRouter(
            live_fn=lambda action, *, now=None: _outcome("APPROVE", cohort="A"),
            shadow_fn=lambda action, *, now=None: _outcome("APPROVE", cohort="A"),
        )
        router.route(action="x", now=_ts())
        assert router.cohort_divergence_rate("nonexistent") == 0.0


class TestPromotionGate:
    def _approving_router(self, days: int) -> ShadowRouter:
        router = ShadowRouter(
            live_fn=lambda action, *, now=None: _outcome("APPROVE"),
            shadow_fn=lambda action, *, now=None: _outcome("APPROVE"),
        )
        for d in range(days):
            router.route(action="x", now=_ts(-d))
        return router

    def test_informational_promotion_passes_after_7_days_zero_divergence(self) -> None:
        router = self._approving_router(days=8)
        verdict = router.promotion_check(DecisionClass.INFORMATIONAL, now=_ts())
        assert verdict.passed is True

    def test_informational_promotion_blocks_under_7_days(self) -> None:
        router = self._approving_router(days=5)
        verdict = router.promotion_check(DecisionClass.INFORMATIONAL, now=_ts())
        assert verdict.passed is False
        assert "minimum shadow duration" in " ".join(verdict.failures).lower()

    def test_trade_execution_promotion_requires_30_days(self) -> None:
        router = self._approving_router(days=20)
        verdict = router.promotion_check(DecisionClass.TRADE_EXECUTION, now=_ts())
        assert verdict.passed is False

    def test_credit_decisioning_promotion_requires_60_days(self) -> None:
        router = self._approving_router(days=45)
        verdict = router.promotion_check(DecisionClass.CREDIT_DECISIONING, now=_ts())
        assert verdict.passed is False

    def test_aml_surveillance_promotion_requires_60_days(self) -> None:
        router = self._approving_router(days=45)
        verdict = router.promotion_check(DecisionClass.AML_SURVEILLANCE, now=_ts())
        assert verdict.passed is False

    def test_capital_liquidity_promotion_requires_90_days(self) -> None:
        router = self._approving_router(days=80)
        verdict = router.promotion_check(DecisionClass.CAPITAL_LIQUIDITY, now=_ts())
        assert verdict.passed is False

    def test_credit_decisioning_zero_worse_direction_veto_required(self) -> None:
        # 60+ days passed, divergence under 1%, BUT shadow vetoes the
        # protected cohort more often than the live path. The credit-
        # decisioning gate requires ZERO worse-direction veto on any
        # ECOA-protected cohort.
        def live_fn(action: str, *, now: datetime | None = None) -> DecisionOutcome:  # noqa: ARG001
            return _outcome("APPROVE", cohort="protected_B")

        state = {"i": 0}

        def shadow_fn(action: str, *, now: datetime | None = None) -> DecisionOutcome:  # noqa: ARG001
            state["i"] += 1
            # 1 of 210 = ~0.5% divergence rate (under 1% threshold)
            if state["i"] == 1:
                return _outcome("VETO", cohort="protected_B", reason="ECOA-PROXY")
            return _outcome("APPROVE", cohort="protected_B")

        router = ShadowRouter(live_fn=live_fn, shadow_fn=shadow_fn)
        for d in range(70):
            for _ in range(3):
                router.route(action="x", now=_ts(-d))
        verdict = router.promotion_check(DecisionClass.CREDIT_DECISIONING, now=_ts())
        # Aggregate is under 1% but shadow vetoes a protected cohort
        # MORE than live -> credit gate fails on zero-worse-direction.
        assert verdict.passed is False
        assert any("protected cohort" in f.lower() for f in verdict.failures)

    def test_promotion_passes_with_long_history_and_no_divergence(self) -> None:
        router = self._approving_router(days=95)
        verdict = router.promotion_check(DecisionClass.CAPITAL_LIQUIDITY, now=_ts())
        assert verdict.passed is True
        assert verdict.failures == ()
