"""Shadow Mode Rollout — ADR-0006.

Routes a regulated FSI decision through both a **live** production agent
path and a **shadow** challenger agent path on the same input. The live
path executes; the shadow path is recorded but silent. A divergence
monitor compares the two paths and surfaces:

- Aggregate divergence rate
- Veto direction (shadow more conservative · shadow more aggressive · equivalent)
- Cohort-specific divergence (disparate-impact on the divergence itself,
  with named ECOA-protected cohorts for credit and FINRA customer
  categories for trading surfaces)
- Promotion verdict against the ADR-0006 promotion-gate matrix

Regulatory anchors:
    - **SR 11-7 § V — Model Implementation, Use, and Change** names
      parallel running of a new model alongside production as the
      expected pre-promotion practice. This module is the runtime
      reference for that expectation.
    - **OCC Bulletin 2011-12** — pairs with SR 11-7; the FFIEC
      examination handbook treats shadow runs as evidence of
      "effective challenge" against the model in production.
    - **CFPB Circular 2022-03** — adverse-action notices on credit
      decisions must be defensible per individual decision; shadow
      runs detect a challenger that vetoes a protected cohort more
      than the live path *before* the challenger is promoted.
    - **EU AI Act Article 9 (risk management) and Article 17
      (quality management)** — pre-deployment testing under production
      conditions is the article-level expectation; shadow mode is the
      concrete control.

The shadow run logs to the same hash-chained audit ledger as the live
run (ADR-0003), with the shadow path flagged in payload so the
divergence monitor can replay it after the fact.

See ``docs/adr/0006-shadow-mode-rollout.md`` for the full decision
record and the promotion-gate matrix.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class VetoDirection(Enum):
    """Sign of the veto-rate divergence between live and shadow paths."""

    SHADOW_MORE_CONSERVATIVE = "shadow_more_conservative"
    """Shadow vetoes more often than live → reconsider before promotion."""

    SHADOW_MORE_AGGRESSIVE = "shadow_more_aggressive"
    """Shadow vetoes less often than live → never promote without explicit
    second-line risk-owner sign-off (SR 11-7 Section V)."""

    EQUIVALENT = "equivalent"
    """Veto rates are equal (within float tolerance)."""


class DecisionClass(Enum):
    """Per-class promotion-gate thresholds per ADR-0006.

    Each tier matches a regulator-examinable surface. Thresholds
    tighten as the surface moves closer to customer impact (credit,
    suitability, surveillance) and the regulatory cost of a worse-
    direction error increases.
    """

    INFORMATIONAL = "informational"
    """Classification or flagging with no client impact — e.g., an
    internal exception queue ranked for analyst review."""

    TRADE_EXECUTION = "trade_execution"
    """Order routing, execution-quality decisions, market-making
    quote logic — Reg NMS / Reg SHO / FINRA Rule 5310 surface."""

    CREDIT_DECISIONING = "credit_decisioning"
    """Credit scoring, line management, adverse-action decisions —
    ECOA / Reg B / FCRA / Reg V / CFPB Circular 2022-03 surface."""

    AML_SURVEILLANCE = "aml_surveillance"
    """Transaction-monitoring alert disposition, sanctions screening —
    BSA / FinCEN SAR surface."""

    CAPITAL_LIQUIDITY = "capital_liquidity"
    """Inputs to capital adequacy, liquidity coverage, stress-test
    scenarios — Basel III / CCAR / DFAST surface."""


@dataclass(frozen=True)
class _GateConfig:
    min_shadow_duration: timedelta
    max_aggregate_divergence: float
    require_zero_worse_direction_per_cohort: bool = False


_GATE_MATRIX: dict[DecisionClass, _GateConfig] = {
    DecisionClass.INFORMATIONAL: _GateConfig(
        min_shadow_duration=timedelta(days=7),
        max_aggregate_divergence=0.05,
    ),
    DecisionClass.TRADE_EXECUTION: _GateConfig(
        min_shadow_duration=timedelta(days=30),
        max_aggregate_divergence=0.01,
        require_zero_worse_direction_per_cohort=True,
    ),
    DecisionClass.CREDIT_DECISIONING: _GateConfig(
        min_shadow_duration=timedelta(days=60),
        max_aggregate_divergence=0.01,
        require_zero_worse_direction_per_cohort=True,
    ),
    DecisionClass.AML_SURVEILLANCE: _GateConfig(
        min_shadow_duration=timedelta(days=60),
        max_aggregate_divergence=0.005,
    ),
    DecisionClass.CAPITAL_LIQUIDITY: _GateConfig(
        min_shadow_duration=timedelta(days=90),
        max_aggregate_divergence=0.005,
    ),
}


@dataclass(frozen=True)
class DecisionOutcome:
    """Generic outcome shape both paths must agree on for divergence comparison.

    ``outcome`` is one of:
        - ``"APPROVE"`` — the agent action is permitted
        - ``"DENY"`` — the agent action is rejected for cause
        - ``"REVIEW"`` — escalated for second-line human disposition
        - ``"VETO"`` — sovereign-veto layer blocked the action (ADR-0002)

    ``veto_reason_code`` is an opaque short code — e.g., "FCRA-AANOTICE"
    for an adverse-action notice gap, "AML-WATCHLIST" for a sanctions
    hit, "REGBI-BEST-INTEREST" for an SEC Reg-BI suitability concern.

    ``cohort`` is the comparison cohort label — an ECOA-protected class
    bucket for credit decisions, a customer category for trading.
    """

    outcome: str
    veto_reason_code: str | None = None
    cohort: str | None = None


@dataclass(frozen=True)
class _Observation:
    when: datetime
    live: DecisionOutcome
    shadow: DecisionOutcome


@dataclass(frozen=True)
class PromotionVerdict:
    """Structured result of a shadow-to-live promotion check.

    ``failures`` is a tuple of short human-readable strings — one per
    failed gate criterion. ``passed`` is True only when ``failures`` is
    empty.
    """

    passed: bool
    failures: tuple[str, ...]


AgentFn = Callable[..., DecisionOutcome]


@dataclass
class ShadowRouter:
    """Routes one input through both the live and shadow agent paths.

    The router is deliberately stateless aside from the observation
    log. There is no implicit time source — callers pass ``now`` on
    each ``route`` call so tests can drive time deterministically and
    so production callers can use whatever trusted timestamp source
    the rest of the audit chain uses (LocalClock or RFC 3161 TSA).
    """

    live_fn: AgentFn
    shadow_fn: AgentFn
    observations: list[_Observation] = field(default_factory=list, init=False, repr=False)

    def route(self, action: object, *, now: datetime) -> DecisionOutcome:
        """Run both paths. Record the observation. Return the *live* outcome.

        Only the live outcome is dispatched — the shadow outcome is
        silently recorded for divergence analysis. This is the SR 11-7
        Section V expectation: the production decision is the live
        path, the challenger runs in parallel without crossing the
        action surface.
        """
        live = self.live_fn(action, now=now)
        shadow = self.shadow_fn(action, now=now)
        self.observations.append(_Observation(when=now, live=live, shadow=shadow))
        return live

    # ----------------------------- metrics ------------------------------ #

    def _entries_in_window(self, *, now: datetime, window: timedelta | None) -> list[_Observation]:
        if window is None:
            return list(self.observations)
        cutoff = now - window
        return [o for o in self.observations if o.when >= cutoff]

    def aggregate_divergence_rate(
        self,
        *,
        now: datetime | None = None,
        window: timedelta | None = None,
    ) -> float:
        """Share of observations where live and shadow disagreed on outcome.

        When ``window`` is supplied, restrict to observations within
        ``[now - window, now]``. ``window`` requires ``now``.
        """
        if not self.observations:
            return 0.0
        if window is not None and now is None:
            raise ValueError("window requires now")
        entries = (
            self._entries_in_window(now=now, window=window)  # type: ignore[arg-type]
            if window is not None
            else list(self.observations)
        )
        if not entries:
            return 0.0
        disagreements = sum(1 for e in entries if e.live.outcome != e.shadow.outcome)
        return disagreements / len(entries)

    def veto_direction(self) -> VetoDirection:
        """Sign of the veto-rate divergence over all observations."""
        if not self.observations:
            return VetoDirection.EQUIVALENT
        live_vetoes = sum(1 for e in self.observations if e.live.outcome == "VETO")
        shadow_vetoes = sum(1 for e in self.observations if e.shadow.outcome == "VETO")
        if shadow_vetoes > live_vetoes:
            return VetoDirection.SHADOW_MORE_CONSERVATIVE
        if shadow_vetoes < live_vetoes:
            return VetoDirection.SHADOW_MORE_AGGRESSIVE
        return VetoDirection.EQUIVALENT

    def cohort_divergence_rate(self, cohort: str) -> float:
        """Share of cohort-tagged observations where the two paths disagreed.

        Used for ECOA disparate-impact analysis on the divergence
        itself — a shadow that vetoes a protected cohort more often
        than the live path is a fair-lending concern even if the
        aggregate divergence is within tolerance.
        """
        cohort_entries = [
            e for e in self.observations if (e.live.cohort == cohort or e.shadow.cohort == cohort)
        ]
        if not cohort_entries:
            return 0.0
        disagreements = sum(1 for e in cohort_entries if e.live.outcome != e.shadow.outcome)
        return disagreements / len(cohort_entries)

    def shadow_time_in_state(self, *, now: datetime) -> timedelta:
        """Elapsed time since the first observation was recorded."""
        if not self.observations:
            return timedelta(0)
        first = min(o.when for o in self.observations)
        return now - first

    # ---------------------------- promotion ----------------------------- #

    def promotion_check(self, decision_class: DecisionClass, *, now: datetime) -> PromotionVerdict:
        """Evaluate the ADR-0006 promotion gate for the given decision class.

        Returns a verdict with every failed criterion enumerated so the
        first-line owner, second-line model-validation team, and Fair
        Lending / BSA / CRO sign-off chain sees every gap in one pass.
        """
        config = _GATE_MATRIX[decision_class]
        failures: list[str] = []

        duration = self.shadow_time_in_state(now=now)
        if duration < config.min_shadow_duration:
            failures.append(
                f"shadow duration {duration.days}d below minimum shadow duration "
                f"{config.min_shadow_duration.days}d for {decision_class.value}"
            )

        divergence = self.aggregate_divergence_rate()
        if divergence > config.max_aggregate_divergence:
            failures.append(
                f"aggregate divergence {divergence:.4f} exceeds threshold "
                f"{config.max_aggregate_divergence:.4f} for {decision_class.value}"
            )

        if config.require_zero_worse_direction_per_cohort:
            # Credit / trade-execution rule: zero shadow-more-conservative
            # vetoes on any protected cohort. A worse-direction veto on a
            # protected cohort is itself an ECOA / Reg B (credit) or
            # customer-protection (trading) concern.
            cohorts: set[str] = {
                o.live.cohort for o in self.observations if o.live.cohort is not None
            } | {o.shadow.cohort for o in self.observations if o.shadow.cohort is not None}
            for cohort in cohorts:
                live_vetoes = sum(
                    1
                    for o in self.observations
                    if o.live.cohort == cohort and o.live.outcome == "VETO"
                )
                shadow_vetoes = sum(
                    1
                    for o in self.observations
                    if o.shadow.cohort == cohort and o.shadow.outcome == "VETO"
                )
                if shadow_vetoes > live_vetoes:
                    failures.append(
                        f"protected cohort {cohort!r} has {shadow_vetoes} shadow "
                        f"vetoes vs {live_vetoes} live vetoes (worse direction)"
                    )

        return PromotionVerdict(passed=not failures, failures=tuple(failures))
