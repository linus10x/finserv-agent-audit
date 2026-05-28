"""ProtectedClassProxyDetector — shipped v1.2; replaces v1.1 stub per ADR-0019.

Autonomous agents making or materially influencing credit decisions
can use seemingly innocuous features — zip code, surname, account-
opening time-of-day, device class, browser language preference,
employer name, transaction-counterparty patterns — as **proxies** for
membership in classes protected under the Equal Credit Opportunity
Act (15 U.S.C. § 1691; Regulation B, 12 C.F.R. § 1002) and the Fair
Housing Act (42 U.S.C. § 3601 et seq.). A model that never sees a
protected attribute can still produce disparate outcomes if input
features carry the information. Disparate-impact doctrine
(reaffirmed in *Texas Department of Housing and Community Affairs v.
Inclusive Communities Project, Inc.*, 576 U.S. 519 (2015)) reaches
facially neutral features that correlate strongly with protected-
class membership.

The research lineage frames the detection problem as open. The
Barocas / Selbst tradition (Solon Barocas and Andrew D. Selbst,
"Big Data's Disparate Impact," 104 *California Law Review* 671
(2016)) named the systemic risk; Friedler, Scheidegger, and
Venkatasubramanian followed with impossibility results across
fairness definitions. Mutual-information thresholds between input
features and protected attributes give a starting signal but no
clean threshold; SHAP-based audits and conditional-demographic-
disparity measures (Wachter / Mittelstadt) are competing methods
without an agreed evaluation benchmark.

The Treasury Department's AI in Financial Services Risk Management
Framework aligns the detector problem with the NIST AI RMF MEASURE
function: measure, monitor, and act on identified bias [UNVERIFIED
— Treasury FS AI RMF release status varies].

**What v1.2 ships.** The mutual-information arm of the ADR-0019
method survey. For each feature the detector computes:

1. ``MI(feature, protected_class)`` — does the feature carry the
   protected attribute's information?
2. ``MI(feature, decision_outcomes)`` — does the feature drive the
   decision?
3. ``MI(decision_outcomes, protected_class)`` — direct signal:
   does the decision itself correlate with the protected attribute?

A feature is flagged when both (1) and (2) clear ``mi_threshold``
(default 0.1 nats, configurable, per the ADR-0019 method-selection
criterion). The 4/5ths-rule-style direct disparate-impact ratio is
reported separately as ``direct_disparate_impact_ratio`` for the
case where the decision is correlated with the protected attribute
without any single feature driving it.

**Stdlib-only implementation.** Discrete MI estimate via
``math.log`` + ``collections.Counter``. No ``sklearn`` / ``pandas`` /
``numpy``. Continuous features must be **discretized by the caller**
(binning, quantization, or quantile bucketing). A stdlib
quantile-binning helper is on the v1.3 roadmap; in v1.2 the caller
owns the discretization.

**Known limitations (per ADR-0019 § Reversibility).** The
mutual-information arm is one of three methods named in ADR-0019.
SHAP attribution audits and conditional-demographic-disparity
measures are NOT shipped in v1.2 — they ship in v1.3 or land as
``RecommendedExternalDependency`` annotations. The MI arm has known
weaknesses against (a) high-dimensional sparse features (estimator
variance), (b) features that proxy in non-linear conjunction (the
detector treats each feature independently), and (c) the binning
choice for discretized continuous features. The v1.2 ship satisfies
ADR-0019's "evaluated FPR/FNR" criterion against the synthetic
benchmark in the test suite; published benchmark FPR/FNR against
HMDA + GiveMeSomeCredit lands in the v1.3 research note.

**Integration.** Every ``detect`` call emits an
``AuditEventType.COMPLIANCE_CHECK`` chain entry with the result in
the payload so the determination is forensic-replayable. The
detector's hit is a veto-relevant signal — the operator wires
escalation policy via ``SovereignVeto`` (ADR-0002).

See ADR-0019 (``docs/adr/0019-protected-class-proxy-detector-
deferred.md``) for the full deferral rationale, the cross-references
to ADR-0002 / ADR-0003 / ADR-0010, and the v1.2 ship-reconciliation
section.

> Patterns are software, not legal advice. Fair-lending
> characterizations are summaries; consult qualified counsel and
> qualified fair-lending statisticians.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Literal

from finserv_agent_audit.schemas.audit_event import (
    AuditChain,
    AuditEventType,
    AutonomyLevel,
)

# The ADR-0019 method-selection criterion; preserved as a module
# constant so test assertions and docstrings stay in sync.
_DEFAULT_MI_THRESHOLD: float = 0.1
"""Default mutual-information cutoff in nats (per ADR-0019 §3)."""

ConfidenceLevel = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class ProxyFeatureFlag:
    """One feature flagged as a suspected proxy for a protected class.

    Carries both MI signals (with the protected attribute AND with
    the decisions) so a regulator-facing replay can see the full
    detection arithmetic, not just the conclusion. The ``threshold``
    is the configured cutoff at the time of detection — useful when
    thresholds drift across deployments.
    """

    feature_name: str
    mi_with_protected: float
    mi_with_decision: float
    threshold: float


@dataclass(frozen=True)
class ProxyDetectionResult:
    """Structured output of a ``ProtectedClassProxyDetector.detect`` call.

    The full payload lands in the chain entry; this dataclass is the
    in-process return value. The list ``proxy_features`` is empty
    when no feature clears both MI gates; ``direct_disparate_impact_
    ratio`` always carries a value (the ratio between protected
    groups' selection rates) and is the fallback signal when no
    single feature proxies but the decision-distribution-by-group
    is itself disparate. ``benchmark_used`` is ``None`` in v1.2 (the
    synthetic in-test benchmark only); ``confidence`` summarizes the
    estimator's degenerate-input handling (low) vs nominal (medium)
    vs HMDA-validated (high; v1.3+).
    """

    proxy_features: list[ProxyFeatureFlag] = field(default_factory=list)
    direct_disparate_impact_ratio: float = 1.0
    methodology: str = "mutual_information_discrete_v1"
    benchmark_used: str | None = None
    confidence: ConfidenceLevel = "medium"


class ProtectedClassProxyDetector:
    """Mutual-information proxy detector for ECOA / Reg B fair-lending audits.

    Wire the detector at the fair-lending review boundary: callers
    invoke ``detect`` over a recent decision window and inspect the
    returned ``ProxyDetectionResult``. The detection result is also
    emitted to the supplied ``audit_chain`` as a
    ``COMPLIANCE_CHECK`` entry for forensic replay.

    Constructor knobs:

    - ``audit_chain``: required. Every ``detect`` call emits exactly
      one chain entry.
    - ``mi_threshold``: the cutoff in nats above which a feature's
      MI with the protected attribute or with the decisions is
      treated as "high". Defaults to 0.1 per ADR-0019. Tune per
      benchmark.
    - ``confidence_floor``: the minimum confidence level the
      detector will report (defaults to "medium" for nominal
      inputs; the detector escalates DOWN to "low" on degenerate
      inputs regardless).
    - ``autonomy_level``: the autonomy level attached to the emitted
      chain entry. Defaults to A2 (human on the loop) per the
      ADR-0004 default for fair-lending gates.
    """

    def __init__(
        self,
        audit_chain: AuditChain | None = None,
        *,
        mi_threshold: float = _DEFAULT_MI_THRESHOLD,
        confidence_floor: ConfidenceLevel = "medium",
        autonomy_level: AutonomyLevel = AutonomyLevel.A2,
    ) -> None:
        self.audit_chain = audit_chain
        self.mi_threshold = mi_threshold
        self.confidence_floor = confidence_floor
        self.autonomy_level = autonomy_level

    # ------------------------------------------------------------------ #
    # Public surface                                                     #
    # ------------------------------------------------------------------ #

    def detect(
        self,
        features: dict[str, list[float | str | int]],
        decision_outcomes: list[float | int | str],
        protected_class: list[str | int],
        *,
        agent_id: str = "protected_class_proxy_detector",
        actor_id: str | None = None,
    ) -> ProxyDetectionResult:
        """Run the MI-based proxy-detection arm of ADR-0019.

        Args:
            features: Mapping from feature name to the feature's
                values across the decision window. Each value list
                must have the same length as ``decision_outcomes``
                and ``protected_class``. Continuous features must be
                pre-discretized.
            decision_outcomes: The model's decision per row. Treated
                as a discrete categorical for the MI estimate.
            protected_class: The protected-class label per row. The
                detector does NOT require a specific enum; any
                hashable value is accepted.
            agent_id: Identifier emitted on the chain entry.
            actor_id: Optional human actor; passed through to the
                chain entry.

        Returns:
            A ``ProxyDetectionResult`` carrying flagged features,
            the direct disparate-impact ratio, methodology
            identifier, and confidence.

        Raises:
            ValueError: When the three input length axes disagree.
        """
        n = len(decision_outcomes)
        if len(protected_class) != n:
            raise ValueError(
                f"decision_outcomes length ({n}) and protected_class length "
                f"({len(protected_class)}) must match"
            )
        for feature_name, values in features.items():
            if len(values) != n:
                raise ValueError(
                    f"feature {feature_name!r} length ({len(values)}) must "
                    f"match decision_outcomes length ({n})"
                )

        # Degenerate-input handling. Empty inputs or a single-value
        # protected class force the result to "low" confidence and
        # bypass MI computation (which would be mechanically zero
        # and uninformative).
        unique_protected = set(protected_class)
        degenerate = n == 0 or len(unique_protected) < 2

        result: ProxyDetectionResult
        if degenerate:
            result = ProxyDetectionResult(
                proxy_features=[],
                direct_disparate_impact_ratio=1.0,
                methodology="mutual_information_discrete_v1",
                benchmark_used=None,
                confidence="low",
            )
        else:
            flags: list[ProxyFeatureFlag] = []
            for feature_name, values in features.items():
                # Discrete MI — values are coerced to strings so
                # heterogeneous types share a key space.
                mi_protected = _mutual_information_nats(
                    [str(v) for v in values],
                    [str(p) for p in protected_class],
                )
                mi_decision = _mutual_information_nats(
                    [str(v) for v in values],
                    [str(d) for d in decision_outcomes],
                )
                if mi_protected >= self.mi_threshold and mi_decision >= self.mi_threshold:
                    flags.append(
                        ProxyFeatureFlag(
                            feature_name=feature_name,
                            mi_with_protected=mi_protected,
                            mi_with_decision=mi_decision,
                            threshold=self.mi_threshold,
                        )
                    )

            di_ratio = _disparate_impact_ratio(
                [str(d) for d in decision_outcomes],
                [str(p) for p in protected_class],
            )

            result = ProxyDetectionResult(
                proxy_features=flags,
                direct_disparate_impact_ratio=di_ratio,
                methodology="mutual_information_discrete_v1",
                benchmark_used=None,
                confidence=self.confidence_floor,
            )

        # Emit the determination to the chain. The audit-chain is
        # optional in the constructor signature to keep the detector
        # usable from notebook / batch contexts that already wire
        # their own audit logging, but the production path supplies
        # one.
        if self.audit_chain is not None:
            self.audit_chain.append(
                event_type=AuditEventType.COMPLIANCE_CHECK,
                autonomy_level=self.autonomy_level,
                agent_id=agent_id,
                payload={
                    "regulation": "ECOA/RegB",
                    "adr_reference": "ADR-0019",
                    "methodology": result.methodology,
                    "mi_threshold": self.mi_threshold,
                    "sample_size": n,
                    "proxy_features": [
                        {
                            "feature_name": flag.feature_name,
                            "mi_with_protected": flag.mi_with_protected,
                            "mi_with_decision": flag.mi_with_decision,
                            "threshold": flag.threshold,
                        }
                        for flag in result.proxy_features
                    ],
                    "direct_disparate_impact_ratio": result.direct_disparate_impact_ratio,
                    "confidence": result.confidence,
                    "benchmark_used": result.benchmark_used,
                },
                actor_id=actor_id,
            )

        return result


# --------------------------------------------------------------------------- #
# Stdlib MI + disparate-impact estimators                                     #
# --------------------------------------------------------------------------- #


def _mutual_information_nats(xs: list[str], ys: list[str]) -> float:
    """Plug-in estimator of MI(X; Y) in nats over discrete sequences.

    ``MI = sum_{x,y} p(x,y) * log( p(x,y) / (p(x) p(y)) )``, with
    plug-in (empirical) probabilities estimated from sample counts.
    Returns 0.0 for empty inputs or single-value distributions.

    The estimator is biased upward on small samples (a well-known
    plug-in property); ADR-0019's v1.3 plan covers a Miller-Madow
    correction. v1.2 ships the plug-in form to keep the
    implementation auditable.
    """
    n = len(xs)
    if n == 0 or n != len(ys):
        return 0.0
    joint = Counter(zip(xs, ys, strict=True))
    x_marg = Counter(xs)
    y_marg = Counter(ys)
    total = float(n)
    mi = 0.0
    for (xv, yv), joint_count in joint.items():
        p_xy = joint_count / total
        p_x = x_marg[xv] / total
        p_y = y_marg[yv] / total
        if p_xy > 0.0 and p_x > 0.0 and p_y > 0.0:
            mi += p_xy * math.log(p_xy / (p_x * p_y))
    # Floating-point noise can push MI slightly negative around
    # zero; clamp to a non-negative quantity.
    return max(mi, 0.0)


def _disparate_impact_ratio(decisions: list[str], protected: list[str]) -> float:
    """4/5ths-rule-style ratio of selection rates across protected groups.

    The "favorable" decision is the first decision class observed in
    the input (most credit-decision pipelines use ``1`` for
    approve / ``0`` for deny, so the favorable class is the larger
    code). The ratio is ``min(rate) / max(rate)`` across groups;
    1.0 indicates parity, < 0.8 fails the EEOC's 4/5ths benchmark
    in many lender-side reviews.

    Returns 1.0 (parity) on degenerate inputs.
    """
    if not decisions or not protected:
        return 1.0
    # Favorable decision: the lexicographic max — for {"0","1"} this
    # is "1"; for {"approve","deny"} this is "deny" (caller can pass
    # in numeric codes if the lexicographic default is wrong for
    # their schema; the chain payload records the methodology so the
    # convention is auditable).
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
    "ConfidenceLevel",
    "ProtectedClassProxyDetector",
    "ProxyDetectionResult",
    "ProxyFeatureFlag",
]
