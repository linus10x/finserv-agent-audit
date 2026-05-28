"""LDASearchHarness — Less Discriminatory Alternative search (v1.3, ADR-0020).

Operationalizes the ACM-FAccT 2024 paper "Operationalizing the Search
for Less Discriminatory Alternatives in Fair Lending" (Black, Gillis,
Hall, Schrag, Singh, Yadav). LDA search is regulatory-grade
methodology in 2026: CFPB Circular 2023-09 and the May 2026 CFPB
final rule expect lenders to demonstrate they searched for less-
discriminatory alternatives, not merely that their primary model
passes a disparate-impact threshold. The Massachusetts AG's July 10,
2025 settlement of the first state-AG fair-lending action against an
AI underwriting model is the state-AG fact pattern that raises the
floor of expected diligence; with CFPB federal enforcement scaled
back, state AGs and private class actions now drive the floor.

**The contract.** The harness takes a primary scoring model and a
generator of LDA candidates. For each candidate it computes:

1. ``accuracy_delta`` — candidate accuracy vs primary accuracy on
   the same labeled dataset.
2. ``di_ratio_delta`` — candidate's 4/5ths-rule disparate-impact
   ratio minus primary's. Positive means the candidate is fairer.
3. ``dominates_primary`` — True iff the candidate is at least as
   accurate AND strictly less discriminatory (di_ratio_delta > 0
   while accuracy_delta >= 0). This is the FAccT-2024 dominance
   criterion; a candidate that dominates the primary is a documented
   LDA the institution must consider per the CFPB final rule.

Every ``search`` call emits one ``AuditEventType.COMPLIANCE_CHECK``
chain entry carrying the methodology identifier, sample size, and
per-candidate report. Forensic-replayable under ADR-0003.

**Stdlib-only.** No ``sklearn`` / ``pandas`` / ``numpy``. The DI ratio
is the 4/5ths-rule selection-rate ratio computed with stdlib
``set`` + ``zip``. The harness does not score the candidate against
the primary directly — it scores both against the supplied labeled
dataset and reports the deltas.

**Known limitations.**

- Candidate generation is the caller's responsibility. The framework
  does not enumerate the FAccT-2024 search-space construction
  (model-class sweeps, feature-subset sweeps, regularization sweeps);
  those are operator-specific.
- The dominance criterion does not encode the FAccT-2024 statistical-
  significance tests on the accuracy delta; an institution applying
  this harness for regulatory diligence should pair it with the
  significance-test arm in their MRM playbook.
- The harness does not promote a dominating LDA into production. The
  promotion decision is a model-risk-management decision under
  SR 11-7 / OCC 2011-12; this harness produces evidence the MRM
  function uses.

See ADR-0020 (``docs/adr/0020-lda-search.md``) for the full decision
record, the FAccT-2024 citation, and the regulatory mapping.

> Reference pattern, not legal advice. Fair-lending characterizations
> are summaries; consult qualified counsel and qualified fair-lending
> statisticians.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

from finserv_agent_audit.schemas.audit_event import (
    AuditChain,
    AuditEventType,
    AutonomyLevel,
)

# The methodology identifier the chain payload records. Bumped on
# breaking-change releases per ADR-0020.
_METHODOLOGY_ID: str = "lda_search_v1"

# Type aliases — kept readable for the audit-chain payload that quotes
# them.
FeatureRow = dict[str, float | int | str]
ScoringModel = Callable[[FeatureRow], int]
CandidateGenerator = Callable[[], Iterator[tuple[str, ScoringModel]]]


@dataclass(frozen=True)
class LDACandidateReport:
    """One LDA candidate's report. Carries the deltas + the verdict.

    ``accuracy_delta`` is candidate-minus-primary. ``di_ratio_delta``
    is candidate-minus-primary. ``dominates_primary`` is the FAccT-2024
    dominance verdict: equal-or-better accuracy AND strictly-better
    (higher) DI ratio.
    """

    name: str
    accuracy_delta: float
    di_ratio_delta: float
    dominates_primary: bool
    methodology: str
    n_samples: int


@dataclass(frozen=True)
class LDASearchResult:
    """Aggregate result of one ``LDASearchHarness.search`` call."""

    candidates: list[LDACandidateReport] = field(default_factory=list)
    primary_accuracy: float = 0.0
    primary_di_ratio: float = 1.0
    n_samples: int = 0
    methodology: str = _METHODOLOGY_ID


class LDASearchHarness:
    """Less-Discriminatory-Alternative search harness (ADR-0020).

    Wire at the model-risk-management boundary: an MRM analyst supplies
    the primary scoring model and a generator of LDA candidates, runs
    ``search`` over a labeled dataset, and inspects the returned
    ``LDASearchResult``. Every call emits a chain entry for forensic
    replay so the regulator-side question "Did you search for an
    LDA?" has an answer with a hash-chained receipt.

    Constructor knobs:

    - ``primary_model``: the production scoring callable.
    - ``candidate_generator``: zero-arg callable that returns an
      iterator of ``(candidate_name, candidate_callable)`` tuples.
      Called fresh on every ``search`` so the iterator is not
      exhausted across calls.
    - ``audit_chain``: optional. When supplied (the production path)
      every search emits one ``COMPLIANCE_CHECK`` entry.
    - ``autonomy_level``: the autonomy level recorded on the chain
      entry. Defaults to A2 (human on the loop) per the ADR-0004
      default for fair-lending governance.
    """

    def __init__(
        self,
        *,
        primary_model: ScoringModel,
        candidate_generator: CandidateGenerator,
        audit_chain: AuditChain | None = None,
        autonomy_level: AutonomyLevel = AutonomyLevel.A2,
    ) -> None:
        self.primary_model = primary_model
        self.candidate_generator = candidate_generator
        self.audit_chain = audit_chain
        self.autonomy_level = autonomy_level

    # ------------------------------------------------------------------ #
    # Public surface                                                     #
    # ------------------------------------------------------------------ #

    def search(
        self,
        *,
        features_dataset: list[FeatureRow],
        decisions_actual: list[int],
        protected_class: list[str | int],
        agent_id: str = "lda_search_harness",
        actor_id: str | None = None,
    ) -> LDASearchResult:
        """Run the search. Returns a structured per-candidate report.

        Args:
            features_dataset: One feature row per applicant. Each row
                is passed to the primary + each candidate as-is.
            decisions_actual: Ground-truth labels (1 = favorable,
                0 = unfavorable) used for accuracy scoring.
            protected_class: Per-row protected-class label used for
                the 4/5ths-rule DI computation.
            agent_id: Emitted on the chain entry.
            actor_id: Optional human actor; passed through.

        Returns:
            ``LDASearchResult`` with per-candidate reports.

        Raises:
            ValueError: When the three input length axes disagree.
        """
        n = len(features_dataset)
        if len(decisions_actual) != n:
            raise ValueError(
                f"features_dataset length ({n}) and decisions_actual length "
                f"({len(decisions_actual)}) must match"
            )
        if len(protected_class) != n:
            raise ValueError(
                f"features_dataset length ({n}) and protected_class length "
                f"({len(protected_class)}) must match"
            )

        primary_predictions = [self.primary_model(row) for row in features_dataset]
        primary_accuracy = _accuracy(primary_predictions, decisions_actual)
        primary_di = _di_ratio(
            [str(p) for p in primary_predictions],
            [str(g) for g in protected_class],
        )

        reports: list[LDACandidateReport] = []
        for name, candidate in self.candidate_generator():
            cand_predictions = [candidate(row) for row in features_dataset]
            cand_accuracy = _accuracy(cand_predictions, decisions_actual)
            cand_di = _di_ratio(
                [str(p) for p in cand_predictions],
                [str(g) for g in protected_class],
            )
            accuracy_delta = cand_accuracy - primary_accuracy
            di_delta = cand_di - primary_di
            # Dominance: equal-or-better accuracy AND strictly-better
            # DI. A zero-sample dataset cannot establish dominance.
            dominates = n > 0 and accuracy_delta >= 0 and di_delta > 0
            reports.append(
                LDACandidateReport(
                    name=name,
                    accuracy_delta=accuracy_delta,
                    di_ratio_delta=di_delta,
                    dominates_primary=dominates,
                    methodology=_METHODOLOGY_ID,
                    n_samples=n,
                )
            )

        result = LDASearchResult(
            candidates=reports,
            primary_accuracy=primary_accuracy,
            primary_di_ratio=primary_di,
            n_samples=n,
            methodology=_METHODOLOGY_ID,
        )

        if self.audit_chain is not None:
            self._emit_compliance_check(
                result=result,
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
        result: LDASearchResult,
        agent_id: str,
        actor_id: str | None,
    ) -> None:
        payload: dict[str, Any] = {
            "regulation": "ECOA/RegB",
            "adr_reference": "ADR-0020",
            "methodology": result.methodology,
            "n_samples": result.n_samples,
            "primary_accuracy": result.primary_accuracy,
            "primary_di_ratio": result.primary_di_ratio,
            "candidates": [
                {
                    "name": r.name,
                    "accuracy_delta": r.accuracy_delta,
                    "di_ratio_delta": r.di_ratio_delta,
                    "dominates_primary": r.dominates_primary,
                }
                for r in result.candidates
            ],
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
# Stdlib accuracy + disparate-impact estimators                               #
# --------------------------------------------------------------------------- #


def _accuracy(predictions: list[int], labels: list[int]) -> float:
    """Fraction of predictions that equal the corresponding label."""
    if not predictions or not labels:
        return 0.0
    if len(predictions) != len(labels):
        return 0.0
    correct = sum(1 for p, y in zip(predictions, labels, strict=True) if p == y)
    return correct / len(predictions)


def _di_ratio(decisions: list[str], protected: list[str]) -> float:
    """4/5ths-rule selection-rate ratio across protected groups.

    Mirrors the helper in ``protected_class_proxy_detector`` so the
    semantics are identical: favorable = lexicographic max of the
    observed decision values; ratio = min(rate) / max(rate) across
    groups; 1.0 on degenerate inputs.
    """
    if not decisions or not protected:
        return 1.0
    decision_values = set(decisions)
    if len(decision_values) < 2:
        return 1.0
    favorable = max(decision_values)
    groups = set(protected)
    if len(groups) < 2:
        return 1.0
    rates: list[float] = []
    for group in groups:
        members = [d for d, p in zip(decisions, protected, strict=True) if p == group]
        if not members:
            continue
        rate = sum(1 for d in members if d == favorable) / len(members)
        rates.append(rate)
    if not rates:
        return 1.0
    max_rate = max(rates)
    min_rate = min(rates)
    if max_rate == 0.0:
        return 1.0
    return min_rate / max_rate


__all__ = [
    "CandidateGenerator",
    "FeatureRow",
    "LDACandidateReport",
    "LDASearchHarness",
    "LDASearchResult",
    "ScoringModel",
]
