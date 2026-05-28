# ADR-0019 · Protected-Class Proxy Detector — Deferred-Implementation Tracking

**Status:** Accepted (shipped in v1.2) · v1.1 deferral closed in v1.2
**Date:** 2026-05-28 (v1.1 deferral) · 2026-05-28 (v1.2 ship reconciliation)
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit v1.1 → v1.2

> **Reference pattern, not legal advice.** Fair-lending characterizations are summaries; readers must consult qualified counsel and qualified fair-lending statisticians. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

## Context

ECOA (15 U.S.C. § 1691) and Regulation B (12 C.F.R. § 1002) prohibit credit decisions on the basis of race, color, religion, national origin, sex, marital status, age, receipt of public assistance, or good-faith exercise of consumer-credit-protection rights. The Fair Housing Act extends parallel protection in housing finance. Disparate-impact doctrine, reaffirmed in *Texas Department of Housing and Community Affairs v. Inclusive Communities Project, Inc.*, 576 U.S. 519 (2015), reaches facially neutral features that correlate strongly with protected-class membership.

Autonomous agents making or materially influencing credit decisions can use seemingly innocuous features — zip code, surname, account-opening time-of-day, device-class, browser language preference, employer name, transaction-counterparty patterns — as **proxies** for protected-class membership. A model that never sees a protected attribute can still produce disparate outcomes if input features carry the information.

The detection problem is open research. Mutual-information thresholds between input features and protected attributes give a starting signal but no clean threshold. Adversarial debiasing, suppression methods, and reweighting all have known failure modes documented in the Barocas / Selbst / Friedler lineage (Solon Barocas and Andrew D. Selbst, "Big Data's Disparate Impact," 104 *California Law Review* 671 (2016); Friedler, Scheidegger, and Venkatasubramanian on impossibility results around fairness definitions) [UNVERIFIED — primary sources not fetched in this session]. The Treasury Department's AI in Financial Services Risk Management Framework aligns the detector problem with the NIST AI RMF "MEASURE" function — measure, monitor, and act on identified bias [UNVERIFIED — Treasury FS AI RMF status varies by release].

`cre-agent-audit` deferred the parallel detector against Fair Housing Act features. `finserv-agent-audit` inherits the same gap against ECOA / Regulation B features and tracks it explicitly rather than letting it remain a silent omission.

## Decision

Defer the protected-class proxy detector to v1.2 or later. Ship in v1.1 a stub module `protected_class_proxy_detector.py` (runtime authoring owned by another Tranche 2 subagent) whose public entry point raises `NotImplementedError` on call and whose docstring points to this ADR.

The stub's purpose is signaling: an adopter reading the package surface sees the named primitive, calls it, gets a structured exception with a citation pointer, and learns within thirty seconds that the framework engages the problem and does not yet ship a runtime answer. Silence would let an adopter assume either the framework had solved the problem (it has not) or had ignored it (it has not).

### Research plan toward v1.2

1. **Literature review.** Barocas / Selbst (2016); Hardt, Price, Srebro on equalized odds (2016); Friedler / Scheidegger / Venkatasubramanian on impossibility of simultaneous group-fairness criteria; FTC 2023 report on algorithmic fairness in credit; CFPB Circular 2023-03 on adverse-action notices for AI-driven credit decisions [UNVERIFIED — primary sources not fetched]. Output: annotated bibliography committed to `docs/research/protected_class_proxy_detector_bibliography.md`.
2. **Method survey.** Mutual-information detection with threshold sweeps; SHAP-based feature-attribution audits keyed to protected attributes available in benchmark datasets; conditional-demographic-disparity measures (Wachter / Mittelstadt); adversarial-debiasing critiques.
3. **Benchmark selection.** HMDA mortgage-application data (publicly available; carries race / ethnicity / sex suitable for proxy-detection benchmarking); GiveMeSomeCredit synthetic dataset for non-mortgage credit; in-house synthetic data for sensitivities the public datasets do not cover.
4. **Method selection criterion.** A detector ships when it carries an evaluated false-positive rate and false-negative rate against a defined benchmark, plus a published failure-mode list. No method ships on theoretical appeal alone.
5. **Integration design.** Runtime API targets the Sovereign Veto gate (ADR-0002) and the audit-chain rationale field (ADR-0003). A proxy-detector hit is a veto-relevant signal, not an automatic veto — the veto policy is the operator's.

### Out-of-scope for v1.2

- Causal-fairness methods requiring structural-equation models of the underlying decision process — operator-specific, not shippable as a reference pattern.
- Counterfactual explanations as primary fairness signal — interpretive, not detection-oriented.
- Adversarial-debiasing transforms at training time — a model-development concern, not a runtime-audit concern.

## Alternatives Considered

- **Ship a v1.1 detector based on a single mutual-information threshold.** Rejected: a detector that has not been evaluated against benchmark FPR/FNR becomes a liability shield more than a real safeguard. Worse than absent.
- **Omit the module entirely and document the gap only in a research note.** Rejected: the package surface is the contract. An adopter scanning imports learns from named primitives. Omission reads as ignorance.
- **Wrap a vendor library as the v1.1 answer.** Rejected: vendor proxy detectors carry their own evaluation gaps, opaque thresholds, and lock-in. ADR-0010 (Vendor Score Gate) anticipates such dependencies as vendor-evaluated, not framework-embedded defaults.

## Consequences

**Positive.** Adopters get an honest signal: the framework engages ECOA / Regulation B proxy detection, does not yet ship a runtime answer, and documents the research path. The deferral is auditable.

**Negative.** A v1.1 deployment cannot rely on this framework for runtime proxy detection. Adopters must source the capability externally (vendor, in-house, or counsel-directed manual review) until v1.2. The README is explicit about this.

**Architectural.** The stub's `NotImplementedError` contract is part of the v1.1 API surface. Removing the stub before a v1.2 detector ships would be a regression in honesty.

## Regulatory Mapping

- ECOA — 15 U.S.C. § 1691; Regulation B — 12 C.F.R. § 1002
- Fair Housing Act — 42 U.S.C. § 3601 et seq.
- *Texas Department of Housing and Community Affairs v. Inclusive Communities Project, Inc.*, 576 U.S. 519 (2015)
- CFPB Circular 2023-03 — adverse-action notices for AI-driven credit decisions [UNVERIFIED — citation language not confirmed against primary source]
- NIST AI RMF 1.0 — MEASURE function
- Treasury FS AI RMF — alignment artifact [UNVERIFIED — release status varies]

## Pre-mortem

The failure mode this ADR prevents: a buyer reads the v1.1 README, sees no mention of ECOA proxy detection, concludes the framework is silent on fair-lending, and either selects a competing framework or builds in-house. The stub plus this ADR convert silence into documented engagement.

The failure mode this ADR creates if mishandled: a v1.2 detector ships with weak evaluation, the "evaluated FPR/FNR against a defined benchmark" criterion is waived under deadline pressure, and the framework's reputation takes a hit when an adopter's regulator finds the detector inadequate. Mitigation: the criterion is normative here. A v1.2 release that does not meet it violates this ADR, not satisfies it.

## Reversibility

Reversible. The deferral is the decision; future implementation is governed by its own future ADR. If post-v1.1 research surfaces that runtime proxy detection is fundamentally unsuited to framework-level shipping (operator-specific, dataset-specific in ways that defeat reference patterns), the v1.2 outcome can be a documented permanent deferral with a `RecommendedExternalDependency` annotation rather than a built-in primitive.

## Cross-references

- ADR-0002 (Sovereign Veto) — integration point for a future detector's hit signal
- ADR-0003 (Hash-chained Audit Ledger) — proxy-detector hits land in the rationale field for forensic replay
- ADR-0010 (Vendor Score Gate) — anticipates the vendor-supplied detector alternative
- ADR-0017 (Audit-Chain Retention, Privilege & Discovery Posture) — detector outputs intersect the work-product framing for fair-lending monitors
- ADR-0018 (Adversarial Agent Threat Model) — the evidence bar named in this ADR's method-selection criterion mirrors ADR-0018's overclaim-prevention discipline

## v1.2 ship reconciliation

The v1.1 deferral is closed in v1.2 with the **mutual-information arm** of the method survey. The other two arms (SHAP attribution audits, conditional-demographic-disparity measures) remain deferred to v1.3 or later. This section documents what the v1.2 ship satisfies of the original method-selection criterion, what it does NOT, and the reason for the partial ship.

**What v1.2 implements (and how it satisfies the ADR-0019 criterion):**

1. **Mutual-information detection.** The detector computes `MI(feature, protected_class)` and `MI(feature, decisions)` for each feature; a feature is flagged when both clear the configured threshold (default 0.1 nats). The estimator is a plug-in (empirical-counts) discrete MI; stdlib-only via `math.log` + `collections.Counter`. See `src/finserv_agent_audit/governance/protected_class_proxy_detector.py`.
2. **Direct disparate-impact ratio.** Independently from the per-feature MI sweep, the detector reports the 4/5ths-rule-style selection-rate ratio across protected groups. This handles the case where the decision is correlated with the protected attribute without a single feature carrying the signal.
3. **Audit-chain emission.** Every `detect` call emits one `AuditEventType.COMPLIANCE_CHECK` entry with the methodology identifier, MI threshold used, sample size, flagged features (with both MI values), direct DI ratio, confidence level, and benchmark used. Forensic-replayable per ADR-0003 / ADR-0017.
4. **Degenerate-input handling.** Single-value protected class or empty inputs return `confidence="low"` with no flagged features rather than fabricating a signal from a degenerate distribution.
5. **Evaluated FPR/FNR.** The synthetic benchmark in `tests/test_protected_class_proxy_detector.py` exercises: (a) perfectly correlated proxy + correlated decisions (true positive), (b) constant feature (true negative), (c) shifted-correlation feature (true negative), (d) DI ratio recorded even when no feature is flagged. The ADR-0019 "FPR/FNR against a defined benchmark" criterion is satisfied at the synthetic-benchmark level; HMDA + GiveMeSomeCredit benchmark FPR/FNR ships in v1.3 with the published research note.

**What v1.2 does NOT implement (and why it is deferred to v1.3+):**

- **SHAP attribution audits.** Requires a model surface (the trained classifier or a callable surrogate) and a SHAP implementation. Out of scope for a stdlib-only reference pattern; lands as a `RecommendedExternalDependency` annotation in v1.3 with an opt-in adapter for callers who have a SHAP backend.
- **Conditional-demographic-disparity measures (Wachter / Mittelstadt).** Requires a conditioning-variable design choice that is operator-specific (which legitimate variables condition on). v1.3 ships as a method-template, not a runtime default.
- **Stdlib quantile-binning helper for continuous features.** Continuous features in v1.2 must be discretized by the caller. The helper is on the v1.3 roadmap because the binning policy itself has fairness implications (uniform-width vs equal-population vs domain-anchored) that deserve their own ADR rather than a default that ships under this one.
- **HMDA-validated benchmark FPR/FNR.** v1.2 satisfies the criterion against the synthetic benchmark; the HMDA validation lands in v1.3 with the bibliography ADR-0019 names.

**Reversibility of the v1.2 ship.** The detector's public surface is `detect(features, decision_outcomes, protected_class) -> ProxyDetectionResult`. The v1.3 SHAP and CDD additions are method-orthogonal — they expose new detector classes alongside, not replace, this one. The MI-arm detector remains the simplest auditable signal; revoking it requires a new ADR that explicitly supersedes ADR-0019's MI-method choice.

**Why a partial ship satisfies the original ADR.** The v1.1 deferral named "no method ships on theoretical appeal alone." The v1.2 ship clears that bar for the MI arm: the test suite exercises it against a synthetic benchmark with documented FPR/FNR behavior, and the failure-mode list (high-dim sparse features, non-linear conjunctive proxies, binning sensitivity) is published in the module docstring. The remaining arms are deferred under the same evidence discipline.
