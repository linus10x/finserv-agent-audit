"""ProtectedClassProxyDetector — ADR-0019 deferred-implementation stub.

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

**Why this module is a stub.** ADR-0019 makes the deliberate
decision to defer a runtime answer rather than ship a single-
threshold mutual-information detector without an evaluated
false-positive / false-negative rate against a defined benchmark.
A detector that has not cleared that bar becomes a liability shield
more than a real safeguard; worse than absent. The stub signals
engagement — an adopter reading the package surface sees the named
primitive, calls it, gets a structured ``NotImplementedError`` with
a citation pointer, and learns within thirty seconds that the
framework engages the problem and does not yet ship a runtime
answer.

**Ship-gate plan toward v1.2.**
    1. Annotated bibliography committed to
       ``docs/research/protected_class_proxy_detector_bibliography.md``.
    2. Method survey across mutual-information thresholds, SHAP
       attribution audits, conditional-demographic-disparity
       measures, and the published critiques of each.
    3. Benchmark selection — HMDA mortgage-application data (carries
       race / ethnicity / sex suitable for proxy benchmarking),
       GiveMeSomeCredit for non-mortgage credit, in-house synthetic
       data for sensitivities the public datasets do not cover.
    4. Method ships only when it carries an evaluated FPR and FNR
       against the benchmark plus a published failure-mode list.
       No method ships on theoretical appeal alone.
    5. Runtime API targets the Sovereign Veto gate (ADR-0002) and
       the audit-chain rationale field (ADR-0003) — a proxy-detector
       hit is a veto-relevant signal, not an automatic veto.

See ADR-0019 (``docs/adr/0019-protected-class-proxy-detector-
deferred.md``) for the full deferral rationale, the cross-references
to ADR-0002 / ADR-0003 / ADR-0010, and the reversibility framing.

> Patterns are software, not legal advice. Fair-lending
> characterizations are summaries; consult qualified counsel and
> qualified fair-lending statisticians.
"""

from __future__ import annotations

from dataclasses import dataclass

_ADR_REFERENCE = (
    "ADR-0019 (docs/adr/0019-protected-class-proxy-detector-deferred.md) "
    "defers the protected-class proxy detector to v1.2. A runtime answer "
    "ships only with an evaluated FPR/FNR against a defined benchmark "
    "(HMDA / GiveMeSomeCredit) per the method-selection criterion in ADR-0019."
)


@dataclass(frozen=True)
class ProxyDetectionResult:
    """Placeholder for the v1.2 detector's structured output.

    The v1.2 contract will carry the suspected proxy feature names,
    the mutual-information (or SHAP-attribution) signal magnitude,
    the protected attribute the proxy correlates with, and the
    evaluated false-positive / false-negative envelope from the
    benchmark suite. The dataclass is named here so the v1.2
    implementation can populate it without a breaking API change.
    """


class ProtectedClassProxyDetector:
    """Stub for the ECOA / FHA protected-class proxy detector (ADR-0019).

    The public surface is one method, ``detect``, which raises
    ``NotImplementedError`` with a citation pointer to ADR-0019. The
    stub's presence is the contract: silence in v1.1 would let
    adopters assume either that the framework had solved the problem
    (it has not) or had ignored it (it has not). The stub converts
    silence into documented engagement.
    """

    def detect(
        self,
        features: dict[str, object],
        decision_outcomes: list[object],
    ) -> ProxyDetectionResult:
        """Detect feature-level proxies for ECOA / FHA protected classes.

        **Not yet implemented.** See module docstring and ADR-0019
        for the ship-gate plan toward v1.2. Calling this method
        raises ``NotImplementedError`` with the ADR reference.

        Args:
            features: Mapping from feature name to feature value (or
                feature vector) for one decision input.
            decision_outcomes: The model's decision outcomes for a
                relevant population window, against which mutual-
                information or attribution signal will be evaluated
                in the v1.2 implementation.

        Raises:
            NotImplementedError: Always, in v1.1. The error message
                references ADR-0019 and the v1.2 ship gate.
        """
        raise NotImplementedError(_ADR_REFERENCE)


__all__ = [
    "ProtectedClassProxyDetector",
    "ProxyDetectionResult",
]
