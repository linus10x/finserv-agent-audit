# ADR-0010 · ECOA / Reg B — EquityAudit Pre-Flight Gate

**Status:** Accepted · FSI-native
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel. No attorney-client relationship is formed by use of this ADR. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

## Context

The Equal Credit Opportunity Act (ECOA, 15 U.S.C. § 1691) and its implementing regulation Reg B (12 C.F.R. Part 1002) prohibit discrimination in any aspect of a credit transaction on the basis of race, color, religion, national origin, sex, marital status, age (with capacity exceptions), receipt of public assistance, or the good-faith exercise of any right under the Consumer Credit Protection Act. ECOA covers more than the threshold yes/no decision: it covers application processing, pricing, limit setting, account maintenance, and adverse-action handling.

Three regulatory artifacts frame the operator-side AI-governance gap this pattern addresses:

- **CFPB / DOJ / OCC joint statement on AI and discrimination in credit underwriting (April 25, 2023).** Five-agency statement (CFPB, DOJ, EEOC, FTC, OCC) affirming that existing civil-rights authorities including ECOA apply to AI systems and that the agencies will enforce. `[UNVERIFIED — confirm full agency list before publication; April 25, 2023 joint statement is on the record per CFPB press release of the same date.]`
- **CFPB Circular 2022-03 (May 26, 2022).** Algorithmic complexity is not a defense for failing to provide specific reasons under ECOA / Reg B (see ADR-0009 for the adverse-action arm).
- **SR 11-7 (Federal Reserve, April 4, 2011) / OCC 2011-12.** Supervisory guidance on model risk management. Models that drive credit decisions are model-risk artifacts; AI models that drive credit decisions are model-risk artifacts. Pre-deployment validation, ongoing monitoring, and challenger testing are expectations, not options.

The CRE-side analog is the Fair-Housing Pre-Flight Gate (cre-agent-audit ADR-0008); the FSI-side problem differs in three ways: (i) the protected-class set under ECOA is broader than under the FHA, (ii) the decision surfaces extend through pricing and limit-setting rather than threshold admit/deny, and (iii) the model-risk regime (SR 11-7) layers a pre-deployment validation obligation that has no direct FHA analog.

The pattern that works at scale is **a fail-closed pre-flight gate at the agent boundary that refuses to execute a lending-decision action on a protected-class-adjacent surface unless a documented model-validation artifact is present and current.**

## Decision

Every agent action that touches a **lending decision surface** routes through the EquityAudit Pre-Flight Gate before execution. The gate **fails closed**: if a current model-validation artifact is not present, the action is vetoed under the sovereign-veto pattern (ADR-0002), and an entry is recorded on the hash-chain audit ledger (ADR-0003).

### Protected lending surfaces

```python
PROTECTED_LENDING_SURFACES = {
    "credit_underwriting_decision",
    "credit_limit_assignment",
    "risk_based_pricing",
    "renewal_repricing",
    "line_increase_decision",
    "line_decrease_decision",
    "account_termination_credit",
    "marketing_audience_pre_screen",
    "loss_mitigation_offer_assignment",
}
```

A surface is protected if a decision on it falls within ECOA's "any aspect of a credit transaction" or is an ECOA-adjacent pre-decision step (e.g., pre-screened marketing). The list is in `config/compliance_rules.yaml` and is updated by PR with regulatory citation.

### The check sequence

The gate runs five ordered checks. Each is implemented as a separate function for testability and selective enable/disable per jurisdiction.

**1. Model-validation currency — `ECOA-VALIDATION-MISSING`**

The decision input names a `model_id` + `model_version`. The gate resolves these against the institution's model-risk inventory and confirms the artifact carries (i) a pre-deployment validation date, (ii) an ongoing-monitoring report dated within the configured window (default 12 months), and (iii) a fair-lending-monitoring report dated within the configured window (default quarterly). Any missing element fails closed.

**2. Protected-class proxy detection — `ECOA-PROXY`**

The decision input is screened against a configurable lexical blocklist for features that are known named proxies for ECOA-protected class (e.g., census-tract-only granularity proxies for race; surname-only granularity is a Bayesian proxy for race / ethnicity per the BISG literature; salutation can proxy for sex; first-name-only can proxy for sex and ethnicity). Lexical-named-feature detection only; learned and embedding-space proxies are out of scope for v1 — see ADR-0019 (deferred-implementation MI-threshold proxy detector).

**3. Disparate-treatment fenceposts — `ECOA-FENCEPOST`**

Reg B § 1002.4(b) prohibits any discouragement of an application based on a prohibited basis. The gate refuses to emit a discouragement-shaped action (e.g., an offer assignment of "no offer" routed only to applicants on a protected dimension) without a documented business-necessity record. § 1002.6(b) limits the use of age in scoring to demonstrably and statistically sound systems; the gate enforces an age-use flag that requires a model-validation pointer to the demonstrably-sound documentation.

**4. Disparate-impact monitor on outputs — `ECOA-DISPARATE`**

A running statistical monitor across all decisions in a configurable window (default 90 days). For each protected cohort with reportable demographics (where the institution uses BISG, HMDA-equivalent, or other lawful proxy), the monitor computes the approval rate, the average price, and the average limit relative to the highest-rate cohort. A ratio outside the institution's calibrated band on any active surface triggers the veto on every subsequent decision in that surface until the rate recovers or a logged exception with model-risk-function sign-off is filed.

**5. Notice timing — `ECOA-NOTICE-TIMING`**

Every action with a `denial` outcome on a covered surface must carry a downstream notice-generation handle that satisfies Reg B § 1002.9(a)(1) — 30 calendar days from completed application for credit. The handle is verified at gate time; absence is a hard veto.

### Human bypass path

A human can override any single veto. The bypass writes a logged exception structurally identical to the cre-agent-audit `FairHousingException` pattern, with `bypass_authority` of MANAGER, DIRECTOR, or GC depending on the reason code. Three bypasses by the same owner in a 90-day window auto-escalate to the Chief Compliance Officer; five bypasses on the same reason code in a 90-day window force the program to DEFCON-4 (ADR-0001).

## Alternatives Considered

- **Post-deployment fair-lending monitoring only.** Necessary but insufficient — the model has already produced decisions on which liability has attached.
- **Human review on every lending decision.** Theatre at portfolio scale; produces a bottleneck or a stamp.
- **Disparate-impact monitoring as a pure dashboard.** Visibility without enforcement; the institution sees the problem and is on notice of it without a control surface.

## Consequences

**Positive.** Lending decisions on ECOA-protected surfaces are emission-blocked unless a model-validation artifact under SR 11-7 / OCC 2011-12 is current and a downstream notice handle is in place. The exception log becomes a board-level governance artifact and a Fair-Lending-Committee artifact. A regulator inquiring about a sampled adverse decision can reconstruct gate verdicts on every decision in the audit chain.

**Negative.** Throughput is bounded by the gate's compute cost. Checks 1–3 are O(features); check 4 is O(decisions in window) with caching; check 5 is O(1). The cost is measured in milliseconds per decision; the cost of a Fair-Lending consent order is measured in tens of millions.

**Calibration risk.** An over-tight gate produces exceptions that overwhelm the Fair-Lending function. An under-tight gate produces settled liability. The gate ships with reasonable defaults and a calibration playbook in `docs/`.

## Regulatory Mapping

- **ECOA, 15 U.S.C. § 1691.** Prohibition on discrimination in any aspect of a credit transaction on prohibited bases.
- **Reg B, 12 C.F.R. Part 1002.** § 1002.4(a) general rule against discrimination; § 1002.4(b) prohibition on discouragement; § 1002.6(b) limits on the use of certain information including age; § 1002.9(a)(1) 30-day notice timing; § 1002.9(a)(2)(i) specific principal reasons for adverse action (operationalized in ADR-0009).
- **SR 11-7 (Federal Reserve, 2011) / OCC 2011-12.** Model risk management — pre-deployment validation, ongoing monitoring, challenger testing. The `ECOA-VALIDATION-MISSING` veto enforces these at decision time.
- **CFPB / DOJ / OCC / FTC / EEOC joint statement on AI and discrimination (April 25, 2023).** Existing civil-rights authorities apply to AI systems. `[UNVERIFIED — confirm full agency list before publication.]`
- **CFPB Circular 2022-03 (May 26, 2022).** Algorithmic complexity is not a defense (see ADR-0009).
- **HMDA, 12 C.F.R. Part 1003.** Reporting regime that supplies the demographic backbone the disparate-impact monitor uses where applicable.

## Pre-mortem

The way this gate fails is **proxy-class drift**: lexical proxies the blocklist catches today are replaced over time by feature-engineering choices that recreate the proxy in the latent space. Mitigation: ADR-0019 (deferred-implementation MI-threshold proxy detector) is the structural backstop; until it ships, the disparate-impact monitor on outputs is the safety net.

The other failure mode is **validation-artifact rot**: a model passes validation, runs for 18 months, drifts, and the 12-month re-validation review lapses under operational pressure. Mitigation: the `ECOA-VALIDATION-MISSING` veto fires the day the artifact ages out; the program drops to DEFCON-3 on that surface until re-validated.

## Reversibility

Moderate. The gate is a wrapper; disabling it requires removing EquityAudit from the agent compose order and is itself an audit-chain entry that drops the program to DEFCON-3 (ADR-0001) on every protected lending surface.

## Cross-references

- ADR-0001 (DEFCON State Machine) — gate-disable drops to DEFCON-3
- ADR-0002 (Sovereign Veto) — the enforcement layer
- ADR-0003 (Hash-chain Audit) — every veto and every exception is recorded
- ADR-0008 (GLBA Safeguards) — the customer NPI used in the lending decision is GLBA-gated
- ADR-0009 (FCRA / Reg V Adverse Action) — the adverse-action notice arm of the same decision surface
- ADR-0019 (Protected-Class Proxy Detector) — deferred-implementation MI-threshold proxy detector layered on the same feature set

## Implementation status

**Deferred to Tranche 2C.** The reference implementation lands at `src/finserv_agent_audit/governance/equity_audit.py`. This ADR is the design contract; the module is not yet committed.
