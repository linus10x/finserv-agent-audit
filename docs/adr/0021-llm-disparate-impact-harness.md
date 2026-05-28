# ADR-0021 · LLM Disparate-Impact Harness

**Status:** Accepted · v1.3 · ships with v1.3.0
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit v1.3

> **Reference pattern, not legal advice.** Disparate-impact characterizations are summaries; readers must consult qualified counsel and qualified fair-lending / employment-discrimination statisticians. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

## Context

The disparate-impact framework — codified in EEOC's "four-fifths rule" (29 C.F.R. § 1607.4(D)) and applied across fair-lending (ECOA / Reg B), fair-housing (FHA), and employment (Title VII, ADEA) — is a selection-rate-ratio test: when the rate of favorable outcomes for a protected group divided by the rate for the most-favored group is less than 0.8, the institution is on notice of an adverse impact and the burden shifts to business-justification.

Scorecard models produce numeric scores and one selection cut; the 4/5ths rule applies cleanly. LLM agents produce free-text or categorical outputs against a prompt; the unit of analysis is the *output of a canary prompt*, not a row of a feature matrix. The scorecard methodology does not transfer cleanly:

1. **No single selection cut.** The LLM agent's output is an action (approve / deny / refer / clarify) or a paragraph that a downstream rubric scores. The selection-rate computation requires the rubric.
2. **Stochastic outputs.** Same prompt yields different outputs across runs (temperature > 0). The methodology must account for run-to-run variance.
3. **Canary design.** Scorecards run against real applications; LLM canaries are crafted to vary the protected dimension while holding everything else constant. Canary design is its own discipline.

Two 2025 enforcement / litigation facts make this a v1.3 priority:

- **Mobley v. Workday, May 16, 2025** [UNVERIFIED — confirm exact docket and certification language]: the Northern District of California conditionally certified an ADEA class against an AI-mediated employment-screening system. The case is the template plaintiff counsel will cite for AI-mediated decision systems across regulated industries.
- **ACM-FAccT 2024 LDA paper** (Black, Gillis, Hall, Schrag, Singh, Yadav): names a tractable methodology for searching for less-discriminatory alternatives and frames the dominance criterion this harness's adverse-impact-ratio computation feeds.

The 2026-05-28 council debate (BigLaw chamber, Plaintiff's chamber, AI/Tech-positioning chamber) named LLM DI testing as the discrimination-frontier control most likely to be missing from an institution's existing MRM playbook when an LLM-mediated decision surface is the subject of an enforcement action.

## Decision

Ship `LLMDisparateImpactHarness` in `src/finserv_agent_audit/governance/llm_disparate_impact_harness.py`. The harness takes:

- `llm_agent`: callable `(prompt: str) -> Any`
- `rubric_scorer`: callable `(output: Any) -> bool | float`. Booleans pass through; floats above 0.5 count as success per the methodology default
- `canary_populations`: `{protected_class_value: [(prompt_id, prompt_text), ...]}`
- `audit_chain`: optional. When supplied, every `run` emits one `COMPLIANCE_CHECK` entry
- `adverse_impact_threshold`: float; 0.8 default per EEOC 4/5ths rule

`run(n_iterations)` runs each canary `n_iterations` times to handle stochastic outputs, scores each output through the rubric, aggregates per-class success rates, computes the adverse-impact ratio as `min(rate) / max(rate)` across protected classes, and flags `significant = True` when the ratio falls below the threshold. The result is returned in `LLMDisparateImpactResult` and recorded on the chain.

### Why not bundle a chi-square or proportions z-test

The harness ships a 4/5ths-rule ratio + a threshold-based significance verdict. It explicitly does NOT bundle a chi-square or proportions z-test as the default. Reasoning:

- The choice of test is jurisdiction- and case-law-specific. Some courts apply a strict 4/5ths rule; others apply binomial significance with the 4/5ths rule as a secondary screen.
- The sample-size discipline that makes a chi-square meaningful (sufficient cell counts, non-degenerate marginals) is the operator's MRM-playbook concern, not the framework's.
- An institution that wants a significance test wraps the harness's result with `statistics` module calls and records the additional finding on the audit chain. The framework does not pretend the choice of test is settled.

### Rubric design is the operator's responsibility

The rubric scorer is the load-bearing component. A rubric that rubber-stamps "approved" outputs without inspecting their substance produces a rubber-stamp DI result; a rubric that itself encodes protected-class bias produces a bias-amplifying DI result. ADR-0021 names this in the docstring; the MRM playbook is where rubric-design discipline lives.

### Canary-population design

The harness does not enforce canary-design rigor. A canary set that varies only on the protected dimension under test — surnames, neighborhood references, language register — is the methodology; a canary set that confounds the protected dimension with unrelated content produces a null or confounded result. The framework records the per-class canary count + per-class success count in the chain payload so a regulator-facing reviewer can inspect the canary-set discipline.

## Alternatives Considered

- **Apply the scorecard `ProtectedClassProxyDetector` (ADR-0019) to LLM outputs.** Rejected: that detector consumes feature dataframes against decision outcomes against protected attributes; LLM outputs are not feature dataframes. The MI-arm methodology does not transfer.
- **Wrap a vendor LLM-safety eval framework.** Rejected: vendor frameworks embed canary sets and rubric choices the deployer cannot inspect or modify. The 4/5ths-rule discipline requires the deployer to own the canary set.
- **Defer LLM DI testing to v1.4.** Rejected: the Mobley v. Workday conditional certification is May 2025 fact pattern; deferring leaves adopters exposed during the v1.3 window.
- **Bundle a significance test by default.** Rejected (see "Why not bundle..." above). The framework ships the 4/5ths-rule ratio and threshold-based verdict; the significance-test choice is operator-side.

## Consequences

**Positive.** Adopters get a framework-level DI test for LLM-mediated decision surfaces with a hash-chained receipt per `run` call. The receipt records the per-class canary counts, the success rates, the adverse-impact ratio, and the threshold the verdict applied. Regulator-facing investigations and plaintiff-side discovery have a forensic trail.

**Negative.** A naive caller can produce misleading results: a small canary set, a permissive rubric, a single iteration on a stochastic agent. ADR-0021 documents these failure modes; the MRM playbook is where the discipline lives. The chain payload records `n_iterations` and per-class counts so misuse is at least visible.

**Architectural.** The harness consumes the same `AuditChain` Protocol as the rest of the v1.1+ governance modules. Stdlib-only (no `statistics` module dependency in the default path; significance tests are operator-side). No new runtime dependencies.

## Regulatory Mapping

- **EEOC Uniform Guidelines on Employee Selection Procedures, 29 C.F.R. § 1607.4(D)** — the "four-fifths rule" (selection-rate ratio less than 0.8 is the adverse-impact benchmark)
- **ECOA, 15 U.S.C. § 1691 / Regulation B, 12 C.F.R. § 1002** — protected-class enumeration for credit
- **Fair Housing Act, 42 U.S.C. § 3601 et seq.** — protected-class enumeration for housing
- **Title VII, 42 U.S.C. § 2000e** — employment discrimination framework
- **Age Discrimination in Employment Act (ADEA), 29 U.S.C. § 621** — protected-class basis in *Mobley v. Workday*
- **Mobley v. Workday, N.D. Cal., conditional class certification May 16, 2025** — AI-mediated employment-screening liability template [UNVERIFIED — confirm exact docket and certification scope]
- **ACM-FAccT 2024 paper** — Black, Gillis, Hall, Schrag, Singh, Yadav, "Operationalizing the Search for Less Discriminatory Alternatives in Fair Lending"
- **SR 11-7 (Federal Reserve, 2011) / OCC 2011-12** — model risk management; LLM DI testing as the validation-time control for LLM-mediated decision surfaces

## Pre-mortem

The way this harness fails is **rubric capture**: an adopter builds a rubric that scores any agent output favorably as long as it contains a polite refusal, and the chain payload records a clean 1.0 adverse-impact ratio across protected classes. The harness is silent because the rubric never said no. Mitigation: ADR-0021 names this in the docstring; the MRM playbook owns rubric review (and a second-line MRM reviewer should run the rubric against a held-out adversarial canary set before the rubric is approved for production DI testing).

The other failure mode is **canary-set tokenism**: an adopter ships a canary set with three prompts per class, gets a noisy but clean adverse-impact ratio, and treats the chain entry as a regulator-facing shield. Mitigation: the chain payload records per-class counts; a regulator-facing reviewer can see the canary-set thinness directly.

## Reversibility

Reversible. The harness is a wrapper over caller-supplied callables; removing it from the governance package surface is a one-line `__all__` edit. The 4/5ths-rule threshold and the float-rubric cutoff are constructor knobs; a v1.4 may add additional verdict-band thresholds without breaking the v1.3 contract.

## Cross-references

- ADR-0003 (Hash-chain Audit) — LLM DI receipts land on the chain
- ADR-0010 (ECOA / Reg B EquityAudit) — the protected-lending-surface gate that triggers when an LLM mediates the decision
- ADR-0019 (ProtectedClassProxyDetector) — the scorecard analog; this ADR is the LLM-output complement
- ADR-0020 (LDA Search) — the dominance criterion; an LDA candidate is a remediation for a significant DI finding
- ADR-0022 (Effective Challenge Harness) — frontier-API model challenge; pairs with this harness for LLM-mediated decision surfaces

## Implementation status

**Shipped in v1.3.** Module: `src/finserv_agent_audit/governance/llm_disparate_impact_harness.py`. Tests: `tests/test_llm_disparate_impact_harness.py`. Exports: `LLMDisparateImpactHarness`, `LLMDisparateImpactResult`, `RubricScorer`.
