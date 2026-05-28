# ADR-0009 · FCRA § 615 / Reg V — AdverseActionGate

**Status:** Accepted · FSI-native
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel. No attorney-client relationship is formed by use of this ADR. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

## Context

Two regulatory artifacts in the last 30 months frame the operator-side AI-governance gap this pattern addresses:

- **CFPB Circular 2022-03 (May 26, 2022)** — "Adverse action notification requirements in connection with credit decisions based on complex algorithms." The Circular's operative holding: a creditor's use of a complex model does not relieve the obligation under ECOA / Reg B and FCRA / Reg V to provide **specific principal reasons** for an adverse action. "The model is too complex to explain" is not a defense.
- **TransUnion FTC/CFPB consent orders, October 2023** — $15M aggregate civil penalty for systemic accuracy failures in consumer reports under FCRA § 607(b). The underlying failure pattern — reports generated and used in adverse decisions without the operator having a defensible audit of the inputs — is the same failure pattern an AI-driven credit-decision stack creates by default.

FCRA § 615 (15 U.S.C. § 1681m) and Reg V (12 C.F.R. § 1022.74) require that when a consumer-report-based adverse action is taken, the notice must (i) state the adverse action, (ii) provide the name, address, and toll-free number of the consumer reporting agency, (iii) state that the agency did not make the decision, and (iv) disclose the consumer's right to a free file disclosure and to dispute. Reg B § 1002.9 (the ECOA arm) layers in the requirement of **specific principal reasons** — generic statements such as "credit score too low" without the underlying factor decomposition do not satisfy the rule.

An autonomous-agent stack that issues, recommends, or materially influences an adverse credit decision must therefore (a) produce a reason-code decomposition for every such decision before the decision is emitted, and (b) record the decomposition immutably so the resulting notice is defensible if challenged.

## Decision

Every agent action that produces or materially influences an adverse credit decision routes through the **AdverseActionGate** before emission. The gate **fails closed**: if a reason-code mapping is not present, defensible, and recorded on the audit chain, the decision is vetoed under the sovereign-veto pattern (ADR-0002), and the workflow either escalates to a human-in-the-loop reviewer or is dropped, depending on configured policy.

### The data model

```python
class AdverseActionKind(Enum):
    CREDIT_DENIED = "credit_denied"
    CREDIT_TERMINATED = "credit_terminated"
    UNFAVORABLE_CHANGE = "unfavorable_change"
    COUNTEROFFER_LESS_FAVORABLE = "counteroffer_less_favorable"
    INSURANCE_DENIED_OR_PRICED_UP = "insurance_decline_or_priced_up"

@dataclass(frozen=True)
class ReasonCode:
    code: str                        # institution's reason-code taxonomy entry
    plain_language: str              # consumer-facing wording
    factor_contribution: float       # >= 0 · normalized within the decision
    upstream_feature_ids: tuple[str, ...]  # traceable to input features

@dataclass(frozen=True)
class AdverseActionPacket:
    decision_id: str
    consumer_id: str
    action_kind: AdverseActionKind
    primary_reasons: tuple[ReasonCode, ...]   # 1–4 per Reg B convention
    model_id: str
    model_version: str
    model_validation_id: str                  # SR 11-7 model-risk artifact reference
    cra_used: str | None                      # consumer reporting agency identifier
    decision_timestamp: datetime
```

### The fail-closed veto

Vetoes fire on any of:

1. **`FCRA-REASONS-MISSING`** — `primary_reasons` is empty or contains generic placeholders ("model decision", "score below threshold" without factor decomposition).
2. **`FCRA-REASONS-OVERLOAD`** — more than four reason codes provided; Reg B expects the four principal reasons. Over-provision suggests the model did not actually rank factors.
3. **`FCRA-CRA-UNNAMED`** — `cra_used` is null on an action that meets the FCRA trigger (consumer report was a factor in the decision).
4. **`FCRA-VALIDATION-MISSING`** — `model_validation_id` does not resolve to an active model-validation artifact (SR 11-7 / OCC 2011-12 model-risk-management artifact).
5. **`FCRA-FACTOR-TRACE-MISSING`** — `upstream_feature_ids` does not resolve to features visible to the explainability harness.
6. **`FCRA-TIMING-STALE`** — `decision_timestamp` precedes the most recent challenger-model promotion gate (the decision was rendered on a model that has since been retired without back-fill of pending notices).

### The decision-notice obligation

For every `AdverseActionPacket` that clears the gate, the audit chain entry contains the full reason-code decomposition. The downstream notice-generation system reads the decomposition; the gate does not generate the notice itself but guarantees the input is well-formed.

## Alternatives Considered

- **Post-hoc explainability via SHAP / LIME applied to a black-box score at notice-generation time.** Rejected: produces explanations that are statistical artifacts of the explainer rather than the principal reasons the model actually weighted. CFPB Circular 2022-03 anticipates and rejects exactly this evasion.
- **Generic reason codes from a fixed taxonomy regardless of decision.** Rejected: violates Reg B § 1002.9(a)(2)(i).
- **Open-loop emission with after-the-fact review.** Rejected: a notice goes to the consumer in 30 days under Reg B § 1002.9(a)(1); the operator does not have time for after-the-fact reconstruction at scale.

## Consequences

**Positive.** Adverse credit decisions are emission-blocked unless they carry a defensible, traceable, time-anchored reason-code decomposition tied to a model-validated model version. Notice generation becomes a deterministic transform of audit-chain data rather than a reconstruction exercise. A CFPB examination request for the basis of a sampled adverse decision can be answered from the chain.

**Negative.** Engineering effort to surface upstream-feature traceability through the modeling pipeline is non-trivial. Mitigation: the model-risk function already owns this artifact for SR 11-7 model validation; the gate consumes the existing artifact rather than creating parallel infrastructure.

**Latency.** Each adverse decision pays a millisecond-scale gate cost. The cost of a $15M consent order is several orders of magnitude greater.

## Regulatory Mapping

- **FCRA § 615, 15 U.S.C. § 1681m.** Operative adverse-action notification obligation when a consumer report is a factor in the decision. The gate enforces `cra_used` presence on FCRA-trigger actions.
- **FCRA § 607(b), 15 U.S.C. § 1681e(b).** Accuracy and integrity of reports — the TransUnion 2023 matter's basis. The gate's traceability of upstream features supports the accuracy obligation on the consumer-of-report side.
- **Reg V, 12 C.F.R. § 1022.74.** FCRA implementing regulation for risk-based-pricing notices; gate enforces packet completeness.
- **Reg B (ECOA), 12 C.F.R. § 1002.9(a)(2)(i).** Specific principal reasons requirement; `FCRA-REASONS-MISSING` and `FCRA-REASONS-OVERLOAD` vetoes operationalize this. § 1002.9(a)(1) sets the 30-day timing window the gate's input-completeness guarantees protect.
- **CFPB Circular 2022-03 (May 26, 2022).** Algorithmic complexity is not a defense. The gate's failure mode is closed, by design, against this evasion.
- **SR 11-7 / OCC 2011-12 (model risk management).** The `model_validation_id` field is the bridge to the institution's existing model-risk artifact set.
- **TransUnion FTC/CFPB consent orders (October 2023).** Aggregate $15M civil penalty under FCRA § 607(b) accuracy obligations on rental-screening reports; the consumer-of-report failure pattern the gate is designed to make defensible on a credit-decision stack.

## Pre-mortem

The gate fails if the reason-code taxonomy itself is too coarse — engineers provide one of four allowed codes that does not actually correspond to the model's primary driver. Mitigation: taxonomy granularity is reviewed annually with the Fair-Lending function; the audit chain logs reason-code frequency, and a code that appears on >25% of decisions is treated as evidence the taxonomy needs refinement.

The other failure mode is **model swap without notice back-fill**: a challenger model is promoted, decisions are re-rendered on the new model, but in-flight notices still reference the old model version. Mitigation: the `FCRA-TIMING-STALE` veto fires until pending notices are reconciled to the latest model.

## Reversibility

Moderate. The gate is a wrapper; disabling it requires removing the AdverseActionGate from the agent compose order and is itself an audit-chain entry that drops the program to DEFCON-3 (ADR-0001).

## Cross-references

- ADR-0001 (DEFCON State Machine) — gate-disable drops to DEFCON-3
- ADR-0002 (Sovereign Veto) — the enforcement layer
- ADR-0003 (Hash-chain Audit) — every reason-code packet recorded
- ADR-0008 (GLBA Safeguards) — the consumer NPI used in the reason-code packet is GLBA-gated
- ADR-0010 (ECOA/Reg B Fair Lending) — the protected-class side of the same decision surface
- ADR-0019 (Protected-Class Proxy Detector) — deferred-implementation, layers proxy detection on the feature set the reason codes reference

## Implementation status

**Deferred to Tranche 2C.** The reference implementation lands at `src/finserv_agent_audit/governance/adverse_action_gate.py`. This ADR is the design contract; the module is not yet committed.
