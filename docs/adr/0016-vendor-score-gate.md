# ADR-0016: Vendor Score Gate for FSI Third-Party Model Adapters

**Status:** Accepted — Design + Reference Implementation (v1.1)
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit v1.1

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel and the firm's model-risk-management function. No attorney-client relationship is formed by use of this ADR. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

---

## Context

The Sovereign Veto (ADR-0002), the Fair-Lending Pre-Flight Gate (analog of CRE's ADR-0008, scoped for FSI in the credit-decision and KYC patterns), and the per-decision Audit Ledger (ADR-0003) all assume the operator controls the feature vector and the model. That assumption is incorrect for the majority of FSI agent surface.

**Most FSI operators do not run in-house AI models for the high-risk decision classes.** They consume vendor outputs across five named vendor categories:

| Vendor class | Decision surface | Operator's regulatory exposure |
|---|---|---|
| KYC / identity verification | Customer onboarding accept/reject; document-validity score; PEP/sanctions match score | BSA/AML CIP rule (31 C.F.R. § 1020.220); CDD rule (31 C.F.R. § 1010.230); OFAC screening obligations |
| Fraud-score / device-risk | Real-time payment-fraud score; account-takeover risk; first-party-fraud risk | UDAAP exposure on declined transactions; Reg E error-resolution timelines on false-positive declines |
| Credit-decision / underwriting | Application risk score; line-assignment recommendation; pricing-tier assignment | ECOA / Regulation B (12 C.F.R. § 1002); FCRA adverse-action notice (15 U.S.C. § 1681m); CFPB UDAAP |
| Robo-advisor / signal-generation | Allocation recommendation; rebalancing trigger; risk-tolerance scoring | Investment Advisers Act fiduciary; FINRA Rule 2111 suitability; SEC Reg BI |
| AML transaction monitoring | Suspicious-activity scoring; alert-prioritization; sanctions-screening match scoring | BSA SAR filing (31 C.F.R. § 1020.320); OFAC compliance; NYDFS Part 504 transaction-monitoring program |

The operator's AI-governance surface for these vendor-mediated workflows is the **vendor output** (score, recommendation, reason codes, optional vendor-side fairness metric), **not the feature vector**. A Fair-Lending Pre-Flight Gate cannot run feature-level proxy checks because the operator does not see the features.

The operator still carries the regulatory exposure on the *use* of the vendor's output. The pattern that works is an adapter that operates on the vendor-output tuple and produces the same engineering rails (Sovereign Veto, Audit Ledger, disparate-impact monitor on accept/decline outcomes) without requiring feature-level access.

The 2026-05-28 internal audit named the absence of this pattern as a Critical finding (companion to D9.1). This ADR closes it.

## Decision

Define a `VendorScoreGate` Protocol that operates on vendor outputs without access to the feature vector. The adapter:

1. Receives `VendorOutput` (score, recommendation, reason codes, optional vendor-supplied fairness metric, vendor model version, vendor request ID).
2. Runs operator-side fair-treatment monitoring on accept/decline outcomes at the operator's decision boundary — the four-fifths-rule analog and equivalent disparity-ratio tests are computable from vendor-output records alone; feature access is not required.
3. Logs every operator decision (accept / decline / refer-to-human / pend) with full vendor-output context to the Audit Ledger (ADR-0003).
4. Generates adverse-action notice content (FCRA / ECOA / SAR-filing-narrative as applicable) preserving vendor-supplied reason codes.
5. Fires Sovereign Veto (ADR-0002) on operator-side decisions that fail fair-treatment monitoring even when the underlying vendor score is "approved."
6. Detects vendor-score drift via the `VendorScoreDriftDetected` event — when the rolling distribution of vendor scores or vendor recommendations shifts beyond a calibrated band, the gate emits a drift event into the audit chain and (configurably) escalates DEFCON for that vendor surface.

### Protocol surface

```python
from typing import Protocol
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class VendorRecommendation(Enum):
    APPROVE = "approve"
    REVIEW = "review"
    DECLINE = "decline"
    PEND = "pend"

class VendorClass(Enum):
    KYC = "kyc"
    FRAUD_SCORE = "fraud_score"
    CREDIT_DECISION = "credit_decision"
    ROBO_ADVISOR_SIGNAL = "robo_advisor_signal"
    AML_TRANSACTION_MONITORING = "aml_transaction_monitoring"

@dataclass(frozen=True)
class VendorOutput:
    """What an operator receives from a third-party FSI AI vendor.

    Deliberately does NOT include the feature vector — that is what the
    operator does not have access to in vendor-mediated workflows. Vendor-side
    feature engineering is contractually-disclosed signal only; the runtime
    cannot synthesize it.
    """
    vendor_class: VendorClass
    vendor_name: str                          # operator-side handle; never client-side PII
    vendor_model_version: str | None          # if disclosed in contract
    request_id: str                           # vendor-side correlation ID
    score: float | None                       # vendor's score on its native scale
    score_scale_min: float | None
    score_scale_max: float | None
    recommendation: VendorRecommendation
    reason_codes: tuple[str, ...]             # vendor-provided; FCRA/ECOA-style if applicable
    vendor_fairness_output: dict[str, float] | None = None
    received_at: datetime = ...

@dataclass(frozen=True)
class CustomerContext:
    """What the operator knows about the customer (the protected-class
    reportable-demographics fields are tightly controlled — only what the
    operator has lawful basis to record and report under ECOA / HMDA / fair-
    lending data-collection rules)."""
    customer_id: str                          # operator-side ID; never vendor-side PII
    cohort_signal: str | None                 # only if lawfully reportable
    surface: VendorClass                      # which vendor surface

@dataclass(frozen=True)
class OperatorDecision:
    """The operator's decision on the vendor output."""
    customer_id: str
    operator_decision: VendorRecommendation
    reason_codes: tuple[str, ...]             # operator-side + vendor-side, preserved
    sovereign_veto_fired: bool = False
    sovereign_veto_reason: str | None = None
    bypass_owner: str | None = None
    timestamp: datetime = ...

class VendorScoreGate(Protocol):
    """Adapter for vendor-mediated FSI AI surfaces."""

    def evaluate(
        self,
        vendor_output: VendorOutput,
        customer: CustomerContext,
    ) -> OperatorDecision: ...

    def disparity_window(
        self,
        surface: VendorClass,
        days: int = 90,
    ) -> dict[str, float]: ...

    def detect_score_drift(
        self,
        surface: VendorClass,
        window_days: int = 30,
    ) -> "VendorScoreDriftDetected | None": ...

    def emit_audit_entry(self, decision: OperatorDecision) -> "AuditEntry": ...
```

Reference implementation `InMemoryVendorScoreGate` ships in `src/finserv_agent_audit/governance/vendor_score_gate.py` (Tranche 2A). Drift detection uses a Kolmogorov-Smirnov test against the calibrated baseline window with a configurable p-value floor; the default fail-closed posture means a detected drift requires either operator acknowledgment or DEFCON escalation before vendor decisions continue.

### Pairs with procurement clauses

The adapter only works if the vendor exposes the data it needs. The contractual companion is per-vendor-class clause language under `docs/vendor-clauses/` (Tranche 3 deliverable):

| Vendor class | Clause file |
|---|---|
| KYC | `docs/vendor-clauses/kyc.md` |
| Fraud-score | `docs/vendor-clauses/fraud-score.md` |
| Credit-decision | `docs/vendor-clauses/credit-decision.md` |
| Robo-advisor signal | `docs/vendor-clauses/robo-advisor.md` |
| AML transaction monitoring | `docs/vendor-clauses/aml-tm.md` |

Each clause file covers: DPA terms · model-risk addendum (SR 11-7 alignment, vendor commits to provide model-validation evidence) · fairness-reporting SLA (vendor commits to disclose vendor-side disparity metrics) · breach-notification timing · termination-for-cause for material model drift · cooperation-with-regulator-examination clauses.

Operators that cannot negotiate the disclosure SLA into the next vendor contract renewal are running uncovered exposure regardless of the adapter's existence.

## Alternatives Considered

1. **Require feature-level access from every vendor.** Rejected — most KYC, fraud-score, and credit-decision vendors will not contractually expose features (proprietary signal). Refusing to deploy without feature access means the operator builds in-house at multiples of the vendor cost; not a realistic posture for the median FSI deployer.
2. **Operator-side shadow model that approximates the vendor's signal.** Rejected — adds an in-house model to the operator's MRM scope, recreates the proxy-feature problem inside the firm, and does not bind the vendor's actual signal. The shadow signal is decision-theater.
3. **Treat vendor outputs as oracles and skip the gate.** Rejected — leaves the operator carrying the regulatory exposure with no architectural artifact. ECOA, FCRA, BSA/AML, and Reg BI all attach to the *use* of the score, not to the vendor's production of it.
4. **A single generic VendorGate without per-class enumeration.** Rejected — the five FSI vendor classes have meaningfully different reason-code vocabularies, regulator routing (CFPB for credit-decision, FinCEN for AML, FINRA/SEC for robo-advisor, OFAC for sanctions), and adverse-action posture (FCRA for credit; UDAAP for fraud-score false positives; SAR-filing for AML). The enumeration is load-bearing; downstream report generation routes off it.

## Consequences

**Positive.** Operators get the Sovereign-Veto + Audit-Ledger + disparity-monitoring rails on the >80% of FSI AI surface they do not control directly. The adapter is a clean seam: vendor-side opacity stops at the adapter; the operator's downstream stack keeps working as designed. The procurement-clause companion converts the pattern into a procurement-side requirement that a Chief Procurement Officer can circulate without engineering involvement. The drift-detection event closes the model-monitoring loop that SR 11-7 expects for third-party models.

**Negative.** The adapter cannot detect proxy features the operator does not see. The fair-treatment monitor on the operator-side decision is necessary-but-insufficient — if the vendor's model has a learned proxy bias, the operator-side accept/decline disparity ratio may pass while the vendor-side scoring is the actual discriminatory signal. The mitigation is on the contracting side (vendor-side fairness-reporting SLA) plus regulatory-discovery insistence on vendor-side model documentation. The CFPB's *Wisdom Project* and recent enforcement posture on vendor-mediated credit decisions make this an active regulatory area. [UNVERIFIED — specific CFPB action not re-fetched]

**Architectural.** The adapter is the seam between the operator's stack and the vendor's stack. In a production FSI deployment it is the highest-impact governance boundary because it converts opaque third-party signals into operator-side, audit-chain-recorded decisions. The seam should be loud (heavily logged) and explicit (configured per vendor class, not implicit).

## What this ADR does NOT cover

- **Vendor-side training-time controls.** Out of operator control by definition; recourse is contractual (model-risk addendum) and regulatory-discovery (vendor-due-diligence on the model lifecycle, per OCC Bulletin 2013-29 and SR 11-7).
- **Vendor-internal proxy-feature usage.** The operator cannot inspect the vendor's feature engineering; the operator requires the fairness-metric output as contractually-disclosed signal.
- **Vendor SLA enforcement at runtime.** If the vendor fails to provide the fairness report the contract obligates, the operator's runtime cannot synthesize the missing data — the failure becomes a contract-breach issue, surfaced via the drift-detection alert and routed to procurement.
- **PCI DSS / HIPAA / other vertical-specific vendor frameworks.** This pattern is FSI-specific; analogous patterns exist for CRE in the sibling `cre-agent-audit` repo (ADR-0011 there).
- **Per-vendor integration code.** The Protocol is the contract; adapter implementations per vendor (Persona / Alloy / Socure-class for KYC; Sift / Sardine / Feedzai-class for fraud; Zest-class / Upstart-class for credit; specific robo-signal vendors; NICE Actimize / SAS-class for AML) are deployer-side. The repo does not ship vendor-named integrations.

## Regulatory Mapping

- **ECOA / Regulation B** (15 U.S.C. § 1691; 12 C.F.R. § 1002) — adverse-action notice requirements apply to operator use of vendor scores; reason-code preservation is the technical control. [UNVERIFIED — primary source not fetched]
- **FCRA** (15 U.S.C. § 1681) — accuracy and dispute rights apply to consumer reports purchased from vendors. [UNVERIFIED — primary source not fetched]
- **BSA / CIP rule** (31 C.F.R. § 1020.220) — customer identification program; KYC vendor outputs feed the program record. [UNVERIFIED — primary source not fetched]
- **BSA / SAR filing** (31 C.F.R. § 1020.320) — Suspicious Activity Report obligations on AML vendor outputs; reason-code preservation feeds the narrative. [UNVERIFIED — primary source not fetched]
- **OFAC sanctions-screening obligations** — strict-liability framework on operator's use of sanctions-screening vendor output.
- **SR 11-7** (Federal Reserve Guidance on Model Risk Management, 2011) — third-party model risk; the drift-detection event is the model-monitoring control behind the policy. [UNVERIFIED — primary source not fetched]
- **OCC Bulletin 2013-29** — third-party risk management; the procurement-clause companion is the contractual instrument behind this guidance. [UNVERIFIED — primary source not fetched]
- **NYDFS 23 NYCRR Part 504** — transaction-monitoring program governance; the AML vendor class is the surface. [UNVERIFIED — primary source not fetched]
- **SEC Regulation Best Interest (Reg BI)** — robo-advisor signal use carries broker-dealer best-interest obligation; reason-code preservation supports the disclosure record. [UNVERIFIED — primary source not fetched]
- **FINRA Rule 2111** — suitability obligation on robo-advisor allocation recommendations. [UNVERIFIED — primary source not fetched]
- **CFPB UDAAP** — unfair, deceptive, or abusive acts/practices; vendor-mediated declines without adequate adverse-action posture create UDAAP exposure.
- **EU AI Act Annex III §5(b) and §5(c)** (Regulation (EU) 2024/1689) — credit-worthiness and insurance-risk pricing are high-risk use cases under the Act; vendor-mediated decisions inherit the obligations. [UNVERIFIED — primary OJ text not fetched]

## Pre-mortem

What fails:

1. **Vendor returns a recommendation but withholds reason codes.** Mitigation — the Protocol requires `reason_codes` (typed as `tuple[str, ...]`, non-optional); a vendor-side empty tuple is preserved and surfaces as a contract-compliance issue at the adverse-action-notice generation step.
2. **Vendor model version is undisclosed.** Mitigation — `vendor_model_version` is optional; the gate accepts None but emits an audit entry tagged `vendor_version_undisclosed=true` so the operator's MRM team can track the disclosure-gap and surface it at vendor review.
3. **Drift detection fires repeatedly during a normal seasonal shift (tax-season fraud-score recalibration, year-end KYC volume spike).** Mitigation — the drift detector accepts per-class baseline windows that can be set to year-over-year rather than 30-day; deployers calibrate per surface. The detector does not auto-DEFCON without operator-configured escalation policy.
4. **Operator decisions never deviate from vendor recommendations.** Mitigation — the gate emits a `vendor_decision_concurrence_rate` metric; concurrence above a calibrated ceiling (e.g., 99%) is itself an audit signal — the operator may be rubber-stamping the vendor, which is a Reg-BI / Reg-B exposure on its own.
5. **Disparity-ratio test on a low-volume surface produces noisy results.** Mitigation — the gate carries a `min_sample_size` parameter; below the threshold, the gate reports "insufficient sample" rather than a misleading ratio. The threshold is set per surface in the calibration file.

## Reversibility

High. Switching gate implementations (e.g., from the in-memory reference to a Postgres-backed production gate) preserves the audit chain — every gate emits the same `AuditEntry` shape. Removing the gate entirely is a configuration change that reverts the operator's stack to direct vendor-output consumption; the consequence is loss of the audit-chain entries and the disparity-monitoring rail, but no chain corruption.

## Cross-references

- **Implementation:** `src/finserv_agent_audit/governance/vendor_score_gate.py` (Tranche 2A) — `VendorScoreGate` Protocol + `InMemoryVendorScoreGate` reference + `VendorScoreDriftDetected` event
- **Tests:** `tests/test_vendor_score_gate.py` — round-trip per vendor class, disparity window, drift detection on synthetic distribution shift, sovereign-veto fire on operator-side disparity, reason-code preservation
- **Related ADRs:** ADR-0002 (Sovereign Veto — adapter generates decisions the veto can fire on) · ADR-0003 (Hash-chained audit ledger — adapter emits entries here) · ADR-0012 (SOX 404 ITGC — third-party vendor onboarding falls under program-development category) · ADR-0014 (Persistence/Witness/Timestamp seams — gate decisions persist through the same backend) · ADR-0015 (MI Proxy — the gate's verifier is in the verifier-integrity scope)
- **Companion artifacts:** `docs/vendor-clauses/*.md` (Tranche 3) — per-class contract addenda
- **Sibling repo:** `cre-agent-audit` ADR-0011 (Vendor-Output Adapter Pattern) — analog for CRE vendor classes
