"""Autonomy Ladder A0 → A4 — ADR-0004 (paired with ADR-0007 SR 11-7 overlay).

Five named maturity tiers and an explicit A2 → A3 promotion gate. The
A2 → A3 promotion is the regulator-visible boundary: it requires the
sovereign-veto layer load-tested under representative traffic, the
audit ledger running for ≥ 90 days, the shadow mode running for ≥ 30
days with no material divergence, and a circuit-breaker tested at
least quarterly.

The promotion gate is the work, not the framework. This module
codifies the *check*; the *evidence* for each criterion is gathered by
the first-line program team, the second-line model-validation team
(SR 11-7), and the third-line internal-audit team, and supplied as a
``PromotionRequirements`` record to ``check_a2_to_a3_promotion``.

Why tiers and not a binary. Regulators (EU AI Act Article 14 — human
oversight, NIST AI RMF Govern function, FRB SR 11-7 three-lines-of-
defense), institutional investors, and internal risk committees all
distinguish between tiers of autonomy with different controls at each
tier. A program at full autonomy on a low-risk read-only task is
shipping. A program at full autonomy on a model whose SR 11-7
validation report flags material limitations is a settlement waiting
to happen.

This module also cross-references the ``AutonomyLevel`` enum in
``schemas/audit_event.py`` — that enum is the value written to the
audit ledger on each decision (A0..A4 short codes), this module is
the runtime semantic that says *what each tier permits*.

Regulatory anchors:
    - **EU AI Act Article 14** — human oversight; tiers map to the
      depth of human involvement required at each stage.
    - **NIST AI RMF — Govern function** — accountability structures
      vary by autonomy tier; A2→A3 is the promotion gate where the
      structure shifts from approval-by-default to exception-only.
    - **FRB SR 11-7 / OCC Bulletin 2011-12** — three-lines-of-defense
      apply at every tier; second-line model validation and third-line
      internal audit independence are the load-bearing controls at
      A3 and A4.
    - **CFPB Circular 2022-03** — adverse-action notice explainability
      is required at every tier; A4 deployments without an
      individual-decision explainer are a known enforcement target.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import Enum


class AutonomyTier(Enum):
    """Five-tier Autonomy Ladder runtime scaffold.

    Each tier carries semantic flags read by the orchestrator and
    surfaced on the audit ledger. Tier objects are intentionally
    lightweight — they describe *what the tier permits*, not *how to
    implement* it. The implementation is the deployer's; the tier is
    the contract.

    Cross-reference: ``AutonomyLevel`` in
    ``finserv_agent_audit.schemas.audit_event`` is the short-code
    (A0..A4) variant written into each audit ledger entry. This enum
    carries the semantics; that enum carries the wire format.
    """

    A0_INFORMATIONAL = "A0"
    """Agent reads. Agent recommends. No write authority.

    Example FSI use: model-flagged exception flagging for credit
    officer review; trade-idea surfacing to a portfolio manager."""

    A1_ASSISTED = "A1"
    """Agent reads. Agent drafts. Human approves every write.

    Example FSI use: KYC/AML adjudication drafts presented for analyst
    signature; pre-trade order suggestions presented to a trader."""

    A2_DELEGATED = "A2"
    """Agent reads and writes for low-risk decisions inside a hard
    pre-defined envelope. Human approves a sampled subset and all
    out-of-envelope decisions.

    Example FSI use: routine alert disposition in transaction
    monitoring within a calibrated suppression band; rebalancing
    execution within a pre-approved drift band on a model portfolio.

    A2 → A3 is the regulator-visible boundary."""

    A3_SUPERVISED_AUTONOMOUS = "A3"
    """Agent reads and writes for in-scope decision class autonomously.
    Sovereign-veto layer is non-overridable. Audit ledger is live.
    Human supervises by exception, not by approval.

    Example FSI use: pre-trade risk envelope enforcement on
    agent-generated orders under SR 11-7 second-line oversight;
    sanctions screening with EDD-band veto."""

    A4_PRODUCTION_AUTONOMOUS = "A4"
    """A3 plus inter-agent orchestration, monitor-led promotion of
    new capabilities, and operator-validated escalation paths.

    Example FSI use: portfolio-wide rebalancing across strategies with
    sovereign veto on concentration, borrowing-exposure, and ECOA-
    style constraint violations."""

    @property
    def can_write(self) -> bool:
        """True at every tier above A0 — A0 is read-only by design."""
        return self is not AutonomyTier.A0_INFORMATIONAL

    @property
    def requires_human_approval(self) -> bool:
        """Every write requires explicit human approval before commit.

        True only at A1. At A2 the envelope is the contract; at A3+
        supervision is by exception only.
        """
        return self is AutonomyTier.A1_ASSISTED

    @property
    def requires_envelope(self) -> bool:
        """Writes must live inside a hard pre-defined envelope.

        True only at A2. The envelope is the load-bearing control that
        bounds the radius of an autonomous error before the second-
        line review samples it.
        """
        return self is AutonomyTier.A2_DELEGATED

    @property
    def requires_sampled_review(self) -> bool:
        """Human reviews a sampled subset of in-envelope decisions;
        all out-of-envelope decisions are reviewed individually.

        True only at A2.
        """
        return self is AutonomyTier.A2_DELEGATED

    @property
    def requires_human_exception_supervision(self) -> bool:
        """A3+ — humans supervise by exception, not by approval.

        The audit ledger plus the sovereign veto are the controls
        that make exception-only supervision defensible to a
        regulator.
        """
        return self in (
            AutonomyTier.A3_SUPERVISED_AUTONOMOUS,
            AutonomyTier.A4_PRODUCTION_AUTONOMOUS,
        )


@dataclass(frozen=True)
class PromotionRequirements:
    """Evidence required to clear the A2 → A3 promotion gate.

    Each field corresponds 1:1 to a criterion in ADR-0004's "promotion
    requires" list. The four criteria are the minimum bar at which a
    regulator-visible boundary can be crossed without a documented
    second-line model-validation exception.
    """

    sovereign_veto_load_tested: bool
    """Sovereign-veto layer has been load-tested under representative
    production traffic (not a smoke test on a dev queue). Required
    because the sovereign veto is the last line of defense at A3+."""

    audit_ledger_running_for: timedelta
    """How long the hash-chained audit ledger has been writing for the
    decision class being promoted. Minimum 90 days so the second-line
    model-validation team has a non-trivial window of evidence to
    challenge."""

    shadow_mode_running_for: timedelta
    """How long the challenger has been running in shadow mode (ADR-
    0006) against the production live path. Minimum 30 days so
    divergence has settled past initial warm-up."""

    circuit_breaker_test_recent: bool
    """Runtime circuit-breaker has been tested in the last quarter and
    the test record is on file. Knight Capital is the canonical lesson
    on autonomy without a working circuit-breaker."""


class PromotionGateNotMet(RuntimeError):  # noqa: N818 - public parity with cre-agent-audit naming
    """Raised by ``PromotionGateReport.raise_if_blocked`` on a failed gate."""


@dataclass(frozen=True)
class PromotionGateReport:
    """Structured result of the A2 → A3 promotion gate check.

    ``failures`` is a tuple of short human-readable strings — one per
    failed criterion. ``passed`` is True only when ``failures`` is
    empty. Every failure is enumerated so the program team sees every
    gap in one pass rather than discovering them one-at-a-time across
    multiple submission cycles.
    """

    passed: bool
    failures: tuple[str, ...]

    def raise_if_blocked(self) -> None:
        if not self.passed:
            raise PromotionGateNotMet(
                "A2 → A3 promotion gate not met: " + " · ".join(self.failures)
            )


_MIN_AUDIT_LEDGER_DAYS = 90
_MIN_SHADOW_MODE_DAYS = 30


def check_a2_to_a3_promotion(requirements: PromotionRequirements) -> PromotionGateReport:
    """Evaluate the four A2 → A3 promotion criteria.

    Returns a report with the full list of failures (not just the
    first one) so the program team, second-line model-validation team,
    and third-line internal audit see every gap in one pass.
    """
    failures: list[str] = []
    if not requirements.sovereign_veto_load_tested:
        failures.append("sovereign_veto not load-tested under representative traffic")
    if requirements.audit_ledger_running_for < timedelta(days=_MIN_AUDIT_LEDGER_DAYS):
        days = requirements.audit_ledger_running_for.days
        failures.append(
            f"audit_ledger has been running for {days}d; minimum is {_MIN_AUDIT_LEDGER_DAYS}d"
        )
    if requirements.shadow_mode_running_for < timedelta(days=_MIN_SHADOW_MODE_DAYS):
        days = requirements.shadow_mode_running_for.days
        failures.append(
            f"shadow_mode has been running for {days}d; minimum is {_MIN_SHADOW_MODE_DAYS}d"
        )
    if not requirements.circuit_breaker_test_recent:
        failures.append("circuit_breaker test not recent (must be tested at least quarterly)")

    return PromotionGateReport(passed=not failures, failures=tuple(failures))
