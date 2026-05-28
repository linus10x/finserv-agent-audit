# ADR-0022 · Effective Challenge Harness for Frontier-API Models

**Status:** Accepted · v1.3 · ships with v1.3.0
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit v1.3

> **Reference pattern, not legal advice.** Model-risk-management characterizations are summaries; readers must consult qualified counsel and qualified MRM practitioners. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

## Context

SR 11-7 (Federal Reserve, April 4, 2011) Section V.1 names "effective challenge" as a non-optional element of model risk management. The second-line MRM function is expected to mount a credible test of the primary model — typically a parallel implementation in a different toolchain, a competing methodology, or a published benchmark the primary's performance can be measured against. OCC Bulletin 2011-12 adopted SR 11-7 for OCC-regulated institutions; FFIEC examination handbooks treat effective challenge as evidence the institution operates the model-risk three-lines-of-defense as designed.

When the primary model is a frontier-API LLM the bank does not control (Anthropic Claude, OpenAI GPT, Google Gemini, equivalent), the standard parallel-implementation challenger is unavailable: the bank cannot reproduce the model's weights, cannot inspect its training data, cannot audit its inference path, cannot run statistical-bootstrap tests against a sealed binary. The traditional MRM challenge methodology assumed white-box or open-source primary models; the frontier-API regime breaks the assumption.

**OCC Bulletin 2026-13** (the operative buyer-conversation context for v1.2-onward of this framework) narrowed the scope of OCC 2011-12 to non-agentic AI; the model-risk governance principles continue to apply via SR 11-7 plus the interagency Statement of Principles, but the agencies acknowledged they have not yet scoped agentic AI. The operational gap is real: institutions deploying frontier-API LLMs in regulated decision surfaces need a documented effective-challenge artifact and the historical methodology does not produce one.

The 2026-05-28 council debate (MRM chamber, AI/Tech-positioning chamber, BigLaw chamber) named effective-challenge for frontier-API primaries as the discrimination-frontier control most likely to be required by the next OCC matter-requiring-attention or Federal Reserve MRA against an institution using a frontier-API LLM in a credit-decisioning surface.

## Decision

Ship `EffectiveChallengeHarness` in `src/finserv_agent_audit/governance/effective_challenge_harness.py`. The harness takes:

- `primary_model`: callable `(input: str) -> Any` — the production frontier-API call
- `challenger_model`: callable `(input: str) -> Any` — the deployer's chosen challenger
- `eval_set`: `list[tuple[input, expected_output]]` — MRM-curated
- `audit_chain`: optional. When supplied, every `run` emits one `AuditEventType.MODEL_VALIDATED` chain entry (the v1.1 enum member tied to ADR-0007 SR 11-7 model risk management)
- `accept_threshold` (default 0.05), `investigate_threshold` (default 0.30): recommendation-band thresholds

`run()` evaluates both models on the eval set; computes per-row agreement with the expected output, per-row agreement between the two models, aggregates accuracy and disagreement rate; emits a `ChallengeReport` with up to 20 sample disagreements (the first 20 in eval-set order — capped per the brief) and a recommendation in `{"accept_primary", "investigate", "escalate"}`. The eval-set SHA-256 hash binds the artifact to the evaluation set used.

### Why MODEL_VALIDATED, not COMPLIANCE_CHECK

The chain emission uses `AuditEventType.MODEL_VALIDATED` — the v1.1 enum member ADR-0007 introduced for the SR 11-7 model-risk three-lines-of-defense overlay. The effective-challenge artifact is exactly the kind of validation-lifecycle evidence that enum member exists to carry: it is consumed by the second-line MRM function as input to the validation file, and it is read by the third-line internal-audit function to attest the second line is operating as designed.

### Challenger choice is the deployer's responsibility

The framework does not prescribe the challenger. Reasonable choices:

- A smaller open-source LLM (Llama 3, Mistral, or equivalent) the bank runs in-house
- A different frontier-API vendor (Claude vs GPT vs Gemini)
- A rule-based heuristic the MRM function designed for the surface
- A domain-specific fine-tune the bank validated independently

The harness's contract is to score and report what the deployer supplies; the challenger-design discipline lives in the MRM playbook. A challenger that is the same vendor and same model family as the primary produces a rubber-stamp report; ADR-0022 names this in the docstring.

### Recommendation bands

The default thresholds:

- `disagreement_rate <= 0.05` → `accept_primary`
- `0.05 < disagreement_rate <= 0.30` → `investigate`
- `disagreement_rate > 0.30` → `escalate`

The thresholds are deployer-overridable on the constructor. The defaults are calibrated to the FAccT/MRM convention that small disagreement is within model-variance noise; large disagreement indicates either a misspecified eval set or a primary-vs-challenger semantic mismatch that the MRM function must understand before validating.

### Eval-set hashing

The eval-set hash (SHA-256 over the JSON-serialized eval set with sorted keys) is recorded on the chain entry. A regulator-facing investigation can attest the eval set used for the validation is the one named in the artifact — and a re-run of the harness on a different eval set produces a different hash, surfacing eval-set drift between validation cycles.

## Alternatives Considered

- **Defer to "operator wraps two API calls in their own MRM harness."** Rejected: every institution would build the same harness with subtle differences; the regulator-facing artifact would not be consistent across institutions; the framework would carry the discrimination-frontier banner without the MRM control.
- **Bundle a benchmark suite (HELM, BIG-bench, equivalent).** Rejected: published benchmarks measure general capabilities, not the institution-specific decision surface. The MRM function curates the eval set against the deployment surface; the framework scores it.
- **Encode an agreement-significance test in the recommendation logic.** Rejected for v1.3: agreement-rate significance (paired-bootstrap, McNemar's test, sample-size correction) is the same operator-side discipline as in ADR-0021. The framework records the eval-set size; the operator's MRM playbook applies the significance discipline.
- **Use `AuditEventType.COMPLIANCE_CHECK` instead of `MODEL_VALIDATED`.** Rejected: COMPLIANCE_CHECK is the catch-all for fair-lending / DI / proxy-detection signals; MODEL_VALIDATED is the named member for validation-lifecycle artifacts under ADR-0007. The effective-challenge artifact is a validation-lifecycle artifact.

## Consequences

**Positive.** Adopters using frontier-API LLMs in regulated decision surfaces get a documented effective-challenge artifact with a hash-chained receipt. The receipt is the artifact the second-line MRM function attaches to the validation file; the eval-set hash + recommendation band + disagreement examples are the substance the third-line internal-audit function reviews. The OCC 2026-13 scope-exclusion gap is closed at the framework level.

**Negative.** A naive deployer can produce a misleading artifact: a same-vendor challenger that agrees with the primary by construction, a thin eval set with no adversarial cases, a recommendation-threshold override that makes "accept_primary" too easy. ADR-0022 documents the failure modes; the MRM playbook owns the discipline. The chain payload records the eval-set hash + recommendation band + thresholds so misuse is at least visible.

**Architectural.** The harness consumes the same `AuditChain` Protocol as the rest of the v1.1+ governance modules. Stdlib-only — `hashlib.sha256` for the eval-set hash, `json.dumps` for serialization, `zip` / `sum` for aggregates. No new runtime dependencies.

## Regulatory Mapping

- **SR 11-7 (Federal Reserve, April 4, 2011) § V.1** — effective challenge as a non-optional element of model risk management
- **OCC Bulletin 2011-12** — adopting SR 11-7 for OCC-regulated institutions (historical reference; supersession context in `docs/occ_2026_13_overlay.md`)
- **OCC Bulletin 2026-13** — narrowed scope of OCC 2011-12 to non-agentic AI; this harness fills the scope-exclusion gap [UNVERIFIED — confirm citation language against primary source]
- **Interagency Statement of Principles on Model Risk Management** — continues to apply for agentic AI per the OCC 2026-13 rescission
- **FFIEC IT Examination Handbook, Management Booklet** — effective-challenge as evidence the institution operates the three-lines-of-defense as designed
- **NIST AI RMF 1.0 — MAP-3.5** — third-party model risk
- **NIST AI 600-1 GenAI Profile** — frontier-API-specific risk considerations

## Pre-mortem

The way this harness fails is **same-vendor challenger malpractice**: an adopter picks GPT-4 as primary and GPT-4o as challenger, the two models agree by construction, the chain payload records a clean `accept_primary` recommendation, and the institution treats the artifact as effective-challenge evidence. The harness is silent because the challenger never disagreed. Mitigation: ADR-0022 names this in the docstring; the MRM playbook owns challenger-design review. A second-line MRM reviewer should review the challenger choice against the primary before the harness is approved for production use; "different model family from the primary" is a hard MRM-playbook requirement.

The other failure mode is **eval-set tokenism**: an adopter ships an eval set with twenty rows curated to be the primary's known-strong cases, gets a clean accuracy + low disagreement, and treats the artifact as comprehensive. Mitigation: the chain payload records the eval-set hash + size; a regulator-facing reviewer can compare the hash across validation cycles and inspect the size directly. The MRM playbook owns eval-set-design review.

## Reversibility

Reversible. The harness is a wrapper over caller-supplied callables; removing it from the governance package surface is a one-line `__all__` edit. The recommendation-band thresholds are constructor knobs; the disagreement-example cap is a module-level constant. A v1.4 may add a `significance_test` constructor knob without breaking the v1.3 contract.

## Cross-references

- ADR-0003 (Hash-chain Audit) — effective-challenge receipts land on the chain
- ADR-0006 (Shadow Mode Rollout) — the runtime parallel-running pattern; this harness is its validation-time counterpart for frontier-API primaries
- ADR-0007 (SR 11-7 Overlay) — the model-risk three-lines-of-defense overlay; the `MODEL_VALIDATED` enum member is this ADR's chain-emission target
- ADR-0020 (LDA Search) — fair-lending dominance verdict on alternatives
- ADR-0021 (LLM Disparate Impact Harness) — the DI complement; pairs with this harness for fair-lending-sensitive LLM-mediated decision surfaces

## Implementation status

**Shipped in v1.3.** Module: `src/finserv_agent_audit/governance/effective_challenge_harness.py`. Tests: `tests/test_effective_challenge_harness.py`. Exports: `EffectiveChallengeHarness`, `ChallengeReport`.
