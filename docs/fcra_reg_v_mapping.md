# FCRA § 615 / Regulation V — Control Mapping for Autonomous AI Agents

This document maps the governance patterns in this repository to the
adverse-action notification obligations under the Fair Credit Reporting Act
§ 615 (15 U.S.C. § 1681m), Regulation V (12 C.F.R. § 1022.74 for risk-based
pricing), and CFPB Circular 2022-03 on algorithmic adverse-action notices.
The pattern that anchors this mapping is the **AdverseActionGate**
(ADR-0009, reference module landing in Tranche 2C).

> **Disclaimer:** Reference pattern, not legal advice. Regulatory characterizations
> are summaries; engage qualified counsel for your specific compliance
> determination. See repo-root [`DISCLAIMER.md`](../DISCLAIMER.md).

---

## Framework Overview

When a creditor takes adverse action based in whole or in part on information
contained in a consumer report, FCRA § 615 requires notice to the consumer
identifying the consumer reporting agency (CRA), clarifying that the CRA did
not make the decision, and disclosing the consumer's right to a free file copy
and to dispute. Regulation V's risk-based-pricing arm (12 C.F.R. § 1022.74)
attaches a parallel obligation when the credit terms offered are materially
less favorable than those offered to a substantial proportion of consumers.
CFPB Circular 2022-03 (May 26, 2022) closes the loop on the AI side: a
creditor's use of a complex algorithm or "black-box" model does not relieve
the obligation under ECOA / Reg B and FCRA / Reg V to provide **specific
principal reasons** for the adverse action. The CFPB stated that "a creditor's
lack of understanding of its own methods is . . . not a cognizable defense."

An autonomous agent that issues, recommends, or materially influences an
adverse credit decision must therefore produce a defensible reason-code
decomposition **before emission** and record it immutably for the downstream
notice-generation system to read.

---

## Primary-Source Citations

| Source | Retrieved | Status |
|---|---|---|
| 15 U.S.C. § 1681m (FCRA § 615) | 2026-05-28, https://www.govinfo.gov/content/pkg/USCODE-2010-title15/html/USCODE-2010-title15-chap41-subchapIII-sec1681m.htm | Verified — adverse-action notice elements, CRA disclosure, free-report and dispute-right disclosures, third-party-information disclosure timing confirmed |
| CFPB Circular 2022-03 (May 26, 2022) | 2026-05-28, https://www.consumerfinance.gov/compliance/circulars/circular-2022-03-adverse-action-notification-requirements-in-connection-with-credit-decisions-based-on-complex-algorithms/ | Verified — central holding, rejection of complexity defense, specific-principal-reasons requirement, explicit ML/AI applicability confirmed verbatim |
| 12 C.F.R. § 1022.74 (Reg V risk-based pricing) | Referenced via CFPB eRegulations; verbatim section text not fetched in this pass |
| 15 U.S.C. § 1681e(b) (FCRA accuracy obligation) | Statutory foundation for the TransUnion 2023 enforcement matter; consult govinfo for the operative text |

---

## Control Mapping Table

| FCRA / Reg V / Circular Requirement | Citation | Pattern in This Repo | File |
|---|---|---|---|
| Notice of adverse action when consumer report is a factor | 15 U.S.C. § 1681m(a) | `AdverseActionGate` — emission-blocked unless `AdverseActionPacket` is well-formed | `src/finserv_agent_audit/governance/adverse_action_gate.py` (ADR-0009, Tranche 2C) |
| Name, address, toll-free number of CRA; statement that CRA did not make the decision | 15 U.S.C. § 1681m(a)(2) | `FCRA-CRA-UNNAMED` veto — packet `cra_used` field must be populated on FCRA-trigger actions | ADR-0009 |
| Free file disclosure (60-day window) and dispute-rights disclosure | 15 U.S.C. § 1681m(a)(3); cross-ref § 1681j, § 1681i | Audit-chain entry carries the disclosure-language template version; notice-generation system reads the version pinned at decision time | `src/finserv_agent_audit/schemas/audit_event.py` |
| Disclosure of non-CRA third-party information on consumer request | 15 U.S.C. § 1681m(b) | Hash-chain audit ledger — every upstream feature ID recorded; consumer-specific extract by query | `src/finserv_agent_audit/governance/ledger_store_sqlite.py` |
| Reasonable procedures safe harbor | 15 U.S.C. § 1681m(c) | `AdverseActionGate` fails closed; the gate-disable path is itself an audit-chain entry and drops the program to DEFCON-3 | `src/finserv_agent_audit/governance/defcon.py` |
| Specific principal reasons (1–4 per Reg B convention) | Reg B § 1002.9(a)(2)(i); CFPB Circular 2022-03 | `FCRA-REASONS-MISSING` and `FCRA-REASONS-OVERLOAD` vetoes — empty, generic, or over-provisioned reason sets fail closed | ADR-0009 |
| Algorithmic complexity is not a defense | CFPB Circular 2022-03 | `FCRA-FACTOR-TRACE-MISSING` veto — upstream feature IDs must resolve to features visible to the explainability harness; SHAP/LIME-only explanations on a black-box score are rejected by design | ADR-0009 |
| Specific reasons must relate to and accurately describe factors actually considered or scored | CFPB Circular 2022-03 | `ReasonCode.upstream_feature_ids` tuple — each reason traceable to the input features the model actually scored | ADR-0009 |
| Model version pinning at decision time | SR 11-7 / OCC 2011-12 (model risk); operationalized for FCRA defensibility | `FCRA-VALIDATION-MISSING` veto — `model_validation_id` must resolve to an active model-validation artifact; `FCRA-TIMING-STALE` veto on un-reconciled model swaps | ADR-0009 |
| Risk-based-pricing notice when terms materially less favorable | 12 C.F.R. § 1022.74 | `AdverseActionKind.COUNTEROFFER_LESS_FAVORABLE` — packet construction enforced at the same gate as outright denial | ADR-0009 |
| Consumer-report accuracy obligation (upstream) | 15 U.S.C. § 1681e(b); TransUnion FTC/CFPB consent orders, October 2023 ($15M aggregate, FCRA § 607(b)) | Upstream-feature traceability supports the consumer-of-report accuracy defense — every feature read for the decision is identified, time-anchored, and reproducible from the chain | ADR-0009 |
| Tamper-evident decision record (regulator-inquiry response) | Implementation discipline | Hash-chain audit ledger with RFC 3161 timestamp anchor on each batch | `src/finserv_agent_audit/governance/witness_anchor.py`, `src/finserv_agent_audit/governance/rfc3161_codec.py` |

---

## Reason-Code Walkthrough — What the Gate Demands on Every Adverse Decision

The `AdverseActionPacket` data model encodes the regulatory minimum on every
adverse decision the agent stack emits. Each field maps to a specific operative
obligation:

| Packet field | Obligation served | Veto on failure |
|---|---|---|
| `decision_id` | Audit-chain identifier; supports regulator-inquiry reproduction | Cannot pass — packet is rejected at validation |
| `consumer_id` | Identifies the data subject for the consumer-side notice | Cannot pass |
| `action_kind` | Distinguishes denial, termination, unfavorable change, counteroffer, insurance decline — each carries a distinct notice template | Cannot pass |
| `primary_reasons` (1–4 `ReasonCode` entries) | Reg B § 1002.9(a)(2)(i) specific-principal-reasons; CFPB Circular 2022-03 anti-genericness | `FCRA-REASONS-MISSING`, `FCRA-REASONS-OVERLOAD` |
| `ReasonCode.factor_contribution` (≥ 0, normalized) | Evidences that the reasons are ranked by the model's actual weighting, not arbitrarily ordered | `FCRA-REASONS-MISSING` |
| `ReasonCode.upstream_feature_ids` | Traceability to features the model actually scored — defeats post-hoc SHAP/LIME evasion | `FCRA-FACTOR-TRACE-MISSING` |
| `model_id`, `model_version` | Pins the model the decision was rendered on; defends against silent model swap | `FCRA-TIMING-STALE` |
| `model_validation_id` | Bridge to SR 11-7 / OCC 2011-12 model-risk artifact | `FCRA-VALIDATION-MISSING` |
| `cra_used` | CRA disclosure obligation per § 1681m(a)(2) | `FCRA-CRA-UNNAMED` |
| `decision_timestamp` | 30-day notice clock under Reg B § 1002.9(a)(1); chain-anchored | Cannot pass without timestamp |

---

## Gap Analysis — What This Repo Does NOT Cover

| Requirement | Gap | Guidance |
|---|---|---|
| Notice template language and formatting | The gate guarantees the input is well-formed; notice-generation rendering is a separate system | Use the institution's existing notice-generation system; consume the audit-chain decomposition as input |
| Risk-based-pricing exception notices (12 C.F.R. § 1022.74) | Packet supports the pricing-action kind; the exception-notice variants are out of scope | Notice-generation system handles the variant selection |
| Notice delivery and retention | Gate records the decision; delivery channels (mail, secure inbox) are out of scope | Institution's customer-communication system |
| Consumer-report procurement compliance (FCRA § 604 permissible-purpose) | The gate is a consumer-of-report defense, not a procurement-side control | Map separately; permissible-purpose tagging belongs at the data-acquisition layer |
| FCRA furnisher obligations (§ 1681s-2) | Out of scope — this repo is consumer-of-report side | Furnisher controls require their own pattern set |
| State-law adverse-action overlays (e.g., California Civil Code § 1785.20) | Substantively similar but distinct triggers | Map separately; the audit chain is the common evidentiary substrate |
| ECOA / Reg B protected-class screening on the same decision | Out of scope for this mapping; routed to `EquityAudit` pattern | See `docs/ecoa_reg_b_mapping.md` |

---

## References

- 15 U.S.C. § 1681m (FCRA § 615 — Requirements on users of consumer reports).
  Retrieved 2026-05-28, govinfo.
- 15 U.S.C. § 1681e(b) (FCRA § 607(b) — Accuracy of report). Statutory basis
  of the TransUnion FTC/CFPB consent orders, October 2023, $15M aggregate.
- 12 C.F.R. § 1022.74 (Regulation V — risk-based-pricing notices).
- CFPB Circular 2022-03 (May 26, 2022). "Adverse action notification
  requirements in connection with credit decisions based on complex algorithms."
  Retrieved 2026-05-28, consumerfinance.gov.
- SR 11-7 / OCC 2011-12 — Supervisory guidance on model risk management.
- ADR-0009 · FCRA § 615 / Reg V — AdverseActionGate
  (`docs/adr/0009-fcra-reg-v-adverse-action.md`).
- ADR-0002 · Sovereign Veto (`docs/adr/0002-sovereign-veto.md`).
- ADR-0001 · DEFCON State Machine (`docs/adr/0001-defcon-state-machine.md`).
- Cross-references: ADR-0008 (GLBA Safeguards), ADR-0010 (ECOA / Reg B),
  ADR-0019 (Protected-Class Proxy Detector, deferred).
