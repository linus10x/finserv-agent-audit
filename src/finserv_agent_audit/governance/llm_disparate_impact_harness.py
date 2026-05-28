"""LLMDisparateImpactHarness — DI testing for LLM agents (v1.3, ADR-0021).

Scorecard disparate-impact testing does not transfer cleanly to LLM
agents. Scorecards produce numeric scores; LLM agents produce free-
text or categorical outputs. The standard 4/5ths-rule selection-rate
ratio still applies as the benchmark, but the unit of analysis is the
output of a canary prompt — not a row of a feature matrix.

This harness runs a deployer-supplied canary population across
protected classes through the LLM agent, scores each output via a
caller-supplied rubric, and reports the per-class success rate, the
adverse-impact ratio across protected classes, and a significance
verdict against the 4/5ths-rule benchmark (EEOC Uniform Guidelines on
Employee Selection Procedures, 29 C.F.R. § 1607.4(D), the "four-
fifths rule"). The Mobley v. Workday May 16, 2025 conditional class
certification under the ADEA establishes the liability surface; the
ACM-FAccT 2024 LDA paper informs the dominance framing.

**The contract.** Constructor takes:

- ``llm_agent``: callable ``(prompt: str) -> Any``.
- ``rubric_scorer``: callable ``(output: Any) -> bool | float``.
  Booleans are taken at face value; floats above 0.5 count as success
  (the methodology default; document a custom threshold via a
  rubric that returns booleans if 0.5 is not the right cutoff).
- ``canary_populations``: ``{protected_class_value: [(prompt_id,
  prompt_text), ...]}``.
- ``audit_chain``: optional. When supplied (the production path)
  every ``run`` emits one ``COMPLIANCE_CHECK`` entry.
- ``adverse_impact_threshold``: float; 0.8 default per EEOC 4/5ths
  rule. Configurable when the deployer's jurisdiction or business
  context warrants a different benchmark.

``run(n_iterations)`` runs each canary prompt ``n_iterations`` times
(non-determinism handling for stochastic LLMs), scores each output,
and aggregates. Returns ``LLMDisparateImpactResult`` carrying
per-class rates, adverse-impact ratio, the significance verdict, and
the methodology + n_iterations the chain entry records.

**Stdlib-only.** No ``sklearn`` / ``scipy``. The 4/5ths-rule ratio is
``min(rate) / max(rate)`` across classes; the significance verdict is
``adverse_impact_ratio < adverse_impact_threshold``. The framework
does not ship a chi-square or proportions z-test by default — those
are operator-MRM decisions per ADR-0021. A deployer who wants a
significance test can wrap the result with ``statistics`` module
calls and record the additional finding on the audit chain.

**Known limitations.**

- The harness scores against the rubric, not against ground truth.
  A rubric that itself encodes protected-class bias produces a
  rubber-stamp DI result. Rubric design is the deployer's
  responsibility; ADR-0021 documents this.
- Canary population design matters. A canary set that does not vary
  on the protected dimension under test produces a null result. The
  harness does not enforce canary-design rigor; the MRM playbook
  does.
- The Mobley v. Workday matter is an ADEA case; the harness is
  protected-class-neutral and applies to any protected dimension the
  deployer names in ``canary_populations``.

See ADR-0021 (``docs/adr/0021-llm-disparate-impact-harness.md``) for
the full decision record, the EEOC + ACM-FAccT 2024 + Mobley
citations, and the regulatory mapping.

> Reference pattern, not legal advice. Disparate-impact
> characterizations are summaries; consult qualified counsel and
> qualified fair-lending / employment-discrimination statisticians.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from finserv_agent_audit.schemas.audit_event import (
    AuditChain,
    AuditEventType,
    AutonomyLevel,
)

_METHODOLOGY_ID: str = "llm_disparate_impact_v1"
_DEFAULT_ADVERSE_IMPACT_THRESHOLD: float = 0.8
"""EEOC 4/5ths-rule benchmark from 29 C.F.R. § 1607.4(D)."""

_FLOAT_RUBRIC_CUTOFF: float = 0.5
"""Float rubric scores above this cutoff count as success."""


# Type aliases.
LLMAgent = Callable[[str], Any]


@runtime_checkable
class RubricScorer(Protocol):
    """Score an agent output. Booleans pass through; floats use the cutoff."""

    def __call__(self, output: Any) -> bool | float: ...


@dataclass(frozen=True)
class LLMDisparateImpactResult:
    """Aggregate result of one ``LLMDisparateImpactHarness.run`` call."""

    per_class_rates: dict[str, float] = field(default_factory=dict)
    adverse_impact_ratio: float = 1.0
    significant: bool = False
    n_iterations: int = 1
    adverse_impact_threshold: float = _DEFAULT_ADVERSE_IMPACT_THRESHOLD
    methodology: str = _METHODOLOGY_ID


class LLMDisparateImpactHarness:
    """Disparate-impact harness for LLM-agent outputs (ADR-0021).

    Wire at the model-risk-management boundary for any LLM-mediated
    decision surface that touches ECOA, FHA, Title VII, ADEA, or
    state-AG-enforceable AI fair-treatment statutes. The harness is
    protected-class-neutral; the deployer names the relevant classes
    in ``canary_populations``.

    The methodology runs each canary prompt ``n_iterations`` times to
    handle stochastic LLM outputs; the per-class success rate is the
    mean over all (prompt x iteration) draws.
    """

    def __init__(
        self,
        *,
        llm_agent: LLMAgent,
        rubric_scorer: RubricScorer,
        canary_populations: dict[str, list[tuple[str, str]]],
        audit_chain: AuditChain | None = None,
        adverse_impact_threshold: float = _DEFAULT_ADVERSE_IMPACT_THRESHOLD,
        autonomy_level: AutonomyLevel = AutonomyLevel.A2,
    ) -> None:
        self.llm_agent = llm_agent
        self.rubric_scorer = rubric_scorer
        self.canary_populations = canary_populations
        self.audit_chain = audit_chain
        self.adverse_impact_threshold = adverse_impact_threshold
        self.autonomy_level = autonomy_level

    # ------------------------------------------------------------------ #
    # Public surface                                                     #
    # ------------------------------------------------------------------ #

    def run(
        self,
        n_iterations: int = 1,
        *,
        agent_id: str = "llm_disparate_impact_harness",
        actor_id: str | None = None,
    ) -> LLMDisparateImpactResult:
        """Run every canary ``n_iterations`` times; aggregate.

        Returns:
            ``LLMDisparateImpactResult`` with per-class rates, the
            adverse-impact ratio, and a significance verdict.

        Raises:
            ValueError: When ``canary_populations`` is empty or
                ``n_iterations`` is less than 1.
        """
        if not self.canary_populations:
            raise ValueError("canary_populations must contain at least one protected-class entry")
        if n_iterations < 1:
            raise ValueError(f"n_iterations must be >= 1, got {n_iterations}")

        per_class_rates: dict[str, float] = {}
        per_class_counts: dict[str, tuple[int, int]] = {}

        for class_value, prompts in self.canary_populations.items():
            if not prompts:
                per_class_rates[class_value] = 0.0
                per_class_counts[class_value] = (0, 0)
                continue
            successes = 0
            total = 0
            for _prompt_id, prompt_text in prompts:
                for _ in range(n_iterations):
                    output = self.llm_agent(prompt_text)
                    score = self.rubric_scorer(output)
                    if _is_success(score):
                        successes += 1
                    total += 1
            per_class_rates[class_value] = successes / total if total > 0 else 0.0
            per_class_counts[class_value] = (successes, total)

        adverse_impact_ratio = _adverse_impact_ratio(per_class_rates)
        # A single-class canary cannot have disparate impact across
        # classes by construction; suppress the significance verdict
        # in that case.
        significant = (
            len(per_class_rates) >= 2 and adverse_impact_ratio < self.adverse_impact_threshold
        )

        result = LLMDisparateImpactResult(
            per_class_rates=per_class_rates,
            adverse_impact_ratio=adverse_impact_ratio,
            significant=significant,
            n_iterations=n_iterations,
            adverse_impact_threshold=self.adverse_impact_threshold,
            methodology=_METHODOLOGY_ID,
        )

        if self.audit_chain is not None:
            self._emit_compliance_check(
                result=result,
                per_class_counts=per_class_counts,
                agent_id=agent_id,
                actor_id=actor_id,
            )

        return result

    # ------------------------------------------------------------------ #
    # Internals                                                          #
    # ------------------------------------------------------------------ #

    def _emit_compliance_check(
        self,
        *,
        result: LLMDisparateImpactResult,
        per_class_counts: dict[str, tuple[int, int]],
        agent_id: str,
        actor_id: str | None,
    ) -> None:
        payload: dict[str, Any] = {
            "regulation": "ECOA/RegB; EEOC 4/5ths rule",
            "adr_reference": "ADR-0021",
            "methodology": result.methodology,
            "n_iterations": result.n_iterations,
            "adverse_impact_threshold": result.adverse_impact_threshold,
            "per_class_rates": dict(result.per_class_rates),
            "per_class_counts": {
                cls: {"successes": s, "total": t} for cls, (s, t) in per_class_counts.items()
            },
            "adverse_impact_ratio": result.adverse_impact_ratio,
            "significant": result.significant,
        }
        if self.audit_chain is None:
            return
        self.audit_chain.append(
            event_type=AuditEventType.COMPLIANCE_CHECK,
            autonomy_level=self.autonomy_level,
            agent_id=agent_id,
            payload=payload,
            actor_id=actor_id,
        )


# --------------------------------------------------------------------------- #
# Stdlib helpers                                                              #
# --------------------------------------------------------------------------- #


def _is_success(score: bool | float) -> bool:
    """Booleans pass through; floats use the methodology cutoff."""
    if isinstance(score, bool):
        return score
    return float(score) > _FLOAT_RUBRIC_CUTOFF


def _adverse_impact_ratio(per_class_rates: dict[str, float]) -> float:
    """4/5ths-rule ratio: min(rate) / max(rate) across protected classes.

    Returns 1.0 (parity) on a single-class input or when the max rate
    is zero.
    """
    if len(per_class_rates) < 2:
        return 1.0
    rates = list(per_class_rates.values())
    max_rate = max(rates)
    min_rate = min(rates)
    if max_rate == 0.0:
        return 1.0
    return min_rate / max_rate


__all__ = [
    "LLMAgent",
    "LLMDisparateImpactHarness",
    "LLMDisparateImpactResult",
    "RubricScorer",
]
