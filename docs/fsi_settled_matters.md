# FSI Settled Matters — Anchor Cases for the Autonomy Ladder Framework

**Status:** Reference doc · FSI parallel to the three-case anchor in `cre-agent-audit/docs/regulatory_matters.md`
**Date:** 2026-05-28
**Repo:** finserv-agent-audit

> **Reference document, not legal advice.** The matter summaries below are paraphrases of the public record at the retrieval date noted in the References section. No attorney-client relationship is formed by reading this document, and adopters must engage qualified counsel for any compliance determination. See repo-root [`DISCLAIMER.md`](../DISCLAIMER.md).

---

## Purpose

This doc anchors the `finserv-agent-audit` v1.1 framework to named, on-record AI- and algorithm-adjacent enforcement matters in U.S. financial services. The objective is concrete: when an adopter walks counsel or an internal audit committee through the framework, they need to be able to point at specific matters that establish the operator-side governance gap, not at abstract risk language. The four matters below establish, in combination, that the relevant regulators (NYDFS, CFPB, DOJ, SEC) treat opacity, missing model validation, missing reason-code decomposition, and undisclosed conflict-of-interest in algorithmic recommendations as supervisable and sanctionable conduct.

The framing rule for every matter section below: state the documented record, identify which v1.1 pattern would have engaged with the failure mode, and stop. The framework is governance scaffolding, not magic. Where the framework would have engaged, that engagement would have produced a defensible audit trail, an earlier escalation, or a sovereign-veto hold. It would not have substituted for fair-lending judgment, model validation, or counsel review.

---

## Matter 1 · Goldman Sachs / Apple Card — NYDFS Supervisory Inquiry (March 23, 2021)

**Agency:** New York State Department of Financial Services
**Respondents:** Goldman Sachs Bank USA (issuer), Apple Inc. (program partner)
**Date of report:** March 23, 2021
**Dollar amount:** No monetary penalty. Voluntary corrective measures implemented (transparency initiatives, credit-improvement assistance program, shortened appeal window).

### Factual summary

NYDFS opened the inquiry in November 2019 after public complaints alleging that the Apple Card credit-line allocation algorithm treated similarly-situated applicants in the same household unequally on the basis of gender. The Department reviewed thousands of pages of records, conducted witness interviews, and analyzed underwriting data for approximately 400,000 New York applicants. The March 2021 report concluded that the underwriting decisions reviewed were "explainable, lawful, and consistent with the Bank's credit policy" and identified no fair-lending-statute violation. The Department flagged deficiencies in customer service and perceived transparency as undermining consumer trust even where the underlying decisions were lawful.

### Regulatory significance

The matter is the clearest U.S. example to date of a fair-lending supervisor running a full algorithmic-credit-allocation investigation under the Equal Credit Opportunity Act (15 U.S.C. § 1691 et seq.) and Regulation B (12 C.F.R. § 1002) against a model-driven credit product. Two operator-side lessons sit in the record: (1) the investigation cost was real even though no violation was found, because the issuer could not initially produce a clean, decision-by-decision reason-code trail in a form the supervisor could read; (2) the appeal mechanism in place at the time of the initial complaints did not include an expedited reconsideration path for algorithmic-only denials, which the Department flagged as a transparency gap.

### What the framework would have engaged with

The decision surface in question is exactly the surface ADR-0009 (`AdverseActionGate`) and ADR-0010 (`ECOA / Reg B fair-lending pre-emit check`) address. An adverse credit-line allocation that materially deviates from a co-applicant in the same household would, under the v1.1 pattern, emit an `AuditEventType.ADVERSE_ACTION_TAKEN` event with a `ReasonCode` decomposition (institution code + plain-language wording + factor contribution + upstream feature IDs) recorded immutably on the hash-chain ledger before the notice is issued. ADR-0019 (`ProtectedClassProxyDetector`, deferred-but-specified) would have engaged with the household-level disparity signal. The framework would not have decided the fair-lending question; it would have produced the reason-code trail the supervisor asked for, on demand, in the form the supervisor reads.

---

## Matter 2 · CFPB Circular 2022-03 — Adverse Action Notification for Complex Algorithms (May 26, 2022)

**Agency:** Consumer Financial Protection Bureau
**Instrument:** Consumer Financial Protection Circular 2022-03
**Date issued:** May 26, 2022
**Dollar amount:** Not an enforcement action; a binding interpretive guidance issued to all CFPB-supervised institutions and parallel-jurisdiction supervisors.

### Factual summary

The Circular answers a single question: must a creditor using a complex algorithm (including machine-learning models whose internal decision logic is not readily interpretable) still comply with the adverse-action notification requirements of ECOA and Regulation B when it denies, terminates, or counteroffers credit? The CFPB's answer is yes, without exception. The interpretive text rejects the "we don't know why the model said no" defense in explicit terms: "a creditor's lack of understanding of its own methods is therefore not a cognizable defense." The reasons disclosed in the notice must be specific, must indicate the principal reasons, and must accurately describe the factors actually considered or scored. Post-hoc model-explanation outputs (SHAP values, LIME approximations, surrogate-model reasons) are permissible only if validated for accuracy against the underlying decision.

### Regulatory significance

The Circular is the federal anchor for the operator-side proposition that an autonomous-agent stack which issues or materially influences a credit decision inherits the full ECOA / Reg B adverse-action burden. It elevates explainability from a model-quality concern to a notice-content compliance concern, and it places the burden of validating any post-hoc explanation on the creditor, not the model vendor. CFPB Circulars are interpretive guidance, not regulations, but supervised institutions treat them as the supervisor's stated examination posture, and several subsequent enforcement actions against credit-decision software have cited Circular 2022-03 as the operative interpretation.

### What the framework would have engaged with

The Circular is the regulatory anchor for ADR-0009. The `AdverseActionGate` fails closed: if a reason-code mapping is not present, defensible, and recorded on the hash-chain before emission, the decision is vetoed under the sovereign-veto pattern (ADR-0002) and either escalates to a human-in-the-loop reviewer at Autonomy Ladder A0 or A1, or is dropped. The recorded `AuditEventType.ADVERSE_ACTION_TAKEN` event carries the `ReasonCode` decomposition with `upstream_feature_ids` so the post-hoc-explanation accuracy claim required by the Circular is reproducible from the ledger, not from a vendor dashboard that could be modified or lost.

---

## Matter 3 · CFPB v. Wells Fargo Bank, N.A. — $3.7B Consent Order (December 20, 2022)

**Agency:** Consumer Financial Protection Bureau
**Respondent:** Wells Fargo Bank, N.A.
**Date:** December 20, 2022
**Dollar amount:** $3.7 billion aggregate ($2.0 billion consumer redress + $1.7 billion civil money penalty)

### Factual summary

The consent order found systemic failures across three product lines: auto loans, residential mortgages, and consumer deposit accounts. Documented findings included improper denial of mortgage loan modifications the bank's own systems should have approved, misapplied auto-loan payments that produced wrongful repossessions, and unauthorized fees on deposit accounts. The order is the largest CFPB civil money penalty at the time of issuance. It does not characterize the underlying systems as "AI," but the mortgage-modification denial findings describe a workflow in which automated scoring and rule engines produced denials the bank could not reconstruct or defend on a per-decision basis when challenged. The order requires compliance management systems including model-validation and decision-traceability controls, in addition to the monetary components.

### Regulatory significance

The Wells Fargo matter is the proof, on the largest scale in CFPB history, that the operator-side liability for an automated adverse decision does not depend on whether the system is labeled "AI." It depends on whether the operator can, on demand, produce a defensible per-decision audit trail showing what inputs were used, what the system computed, what reason codes were attached, and how a human reviewer (or a documented automated escalation) approved or vetoed the action. The order's requirement of remediation-as-controls — not just remediation-as-checks — is the regulatory template that any autonomous-agent stack should treat as the operator-side bar.

### What the framework would have engaged with

The mortgage-modification denial findings sit in the same surface as ADR-0009 (`AdverseActionGate`) and ADR-0010 (`ECOA / Reg B fair-lending pre-emit check`); a denial of a loan modification is an "unfavorable change" under FCRA § 615 and an adverse action under ECOA. The hash-chain ledger (ADR-0003) plus WORM persistence (ADR-0013, SEC Rule 17a-4-style retention adapted for consumer-finance discovery) would have produced the per-decision reconstruction the consent order's remediation requirements demand. ADR-0007 (`SR 11-7 model-validation overlay`) would have engaged with the missing model-validation discipline behind the auto-loan and mortgage scoring engines: every model used in a decision surface emits `AuditEventType.MODEL_VALIDATED` with the validation lineage, and a stale or missing validation triggers the sovereign-veto path.

---

## Matter 4 · SEC v. Charles Schwab & Co., et al. — Schwab Intelligent Portfolios ($187M, June 13, 2022)

**Agency:** U.S. Securities and Exchange Commission
**Respondents:** Charles Schwab & Co., Charles Schwab Investment Advisory, Schwab Wealth Investment Advisory
**Date:** June 13, 2022
**Dollar amount:** $187 million ($52 million civil penalty + $135 million disgorgement and prejudgment interest)

### Factual summary

The SEC found that from March 2015 to November 2018, Schwab's robo-advisor product, Schwab Intelligent Portfolios, marketed itself as having no advisory fees, no commissions, and no account-service fees, while in fact the program's allocation logic systematically held a higher cash allocation than a competing investment of an equivalent risk profile would have held, with the cash swept to a Schwab affiliate bank that earned a spread on the funds. The economic effect, per the SEC's order, was that clients earned less than they would have in a comparable non-cash-heavy portfolio, while Schwab earned undisclosed revenue on the cash spread. The matter was settled on an Investment Advisers Act of 1940 § 206(2) basis (negligent breach of fiduciary duty) and § 206(4) basis (anti-fraud rule for advisers). The order required Schwab to retain an independent compliance consultant in addition to the monetary components.

### Regulatory significance

The Schwab Intelligent Portfolios matter is the canonical operator-side enforcement against an algorithmically-driven recommendation surface in U.S. asset management. It establishes three things directly relevant to autonomous-agent governance in wealth and capital markets: (1) the recommendation surface itself is the regulated artifact, not the disclaimer language wrapped around it; (2) a conflict of interest baked into the allocation logic is treated identically to a conflict of interest in a human adviser's recommendation; (3) the SEC will and does compute disgorgement on the spread the operator earned, not just the customer harm. The matter is the closest existing analogue under U.S. securities law to the operator-side bar that Regulation Best Interest (Reg BI, effective June 30, 2020) and the related Form CRS rule impose on broker-dealer recommendations to retail customers.

### What the framework would have engaged with

The recommendation-surface decision is exactly the surface ADR-0013-equivalent (`BestInterestGate`) addresses. Every recommendation emitted by an autonomous-agent stack to a retail customer or to an internal portfolio-allocation engine routes through a pre-emit gate that records `AuditEventType.BEST_INTEREST_CHECKED` with the customer-profile inputs, the universe considered, the chosen recommendation, and the conflict-of-interest declarations attached to each option. Where the allocation logic carries a conflict (cash sweep spread, payment-for-order-flow, affiliated-fund preference, payment-of-revenue-share), the conflict is a first-class field on the audit event, not a footnote in a prospectus. ADR-0007 (`SR 11-7 model-validation overlay`) would have engaged with the allocation-model validation gap: an allocation model whose validation file does not document the cash-spread conflict as a tested-and-disclosed feature would not have cleared the pre-emit gate. The hash-chain ledger would have made the four-year spread economically reconstructable on demand from a regulator request, not from internal product-team memory.

---

## Cross-Vertical Reference · TransUnion FTC/CFPB Consent Orders (October 2023)

The `cre-agent-audit` reference doc cites the October 2023 TransUnion FTC/CFPB consent orders ($15 million aggregate civil penalty for systemic accuracy failures in consumer reports under FCRA § 607(b)) as the anchor for the CRA-side accuracy obligation. The matter is equally on-point for FSI adopters: any autonomous-agent stack that consumes a consumer report in a credit-decision surface inherits the same accuracy-and-defensibility chain. ADR-0009 cites the matter in its Context section. Adopters should not re-litigate the cross-vertical question; the consumer-report accuracy obligation runs in both directions, and the framework's hash-chain treatment of `upstream_feature_ids` is identical for housing-decision and credit-decision adverse-action workflows.

---

## How to Use This Doc

For an adopter's first internal audit-committee briefing: open with Matter 2 (CFPB Circular 2022-03 — the cleanest articulation of the operator-side rule), move to Matter 3 (Wells Fargo $3.7B — the dollar-amount anchor and the controls-as-remediation template), move to Matter 4 (Schwab $187M — the recommendation surface as regulated artifact), and close with Matter 1 (Apple Card / NYDFS — the counter-example: a full supervisory inquiry that ended without a violation finding, and the audit-and-explainability cost the institution still incurred). For first counsel review, walk the ADRs cited in each matter section (ADR-0007 / 0009 / 0010 / 0013 / 0019) against the institution's existing reason-code taxonomy and model-validation file format using the hash-chain ledger schema in `schemas/audit_event.py`.

---

## References

All URLs retrieved 2026-05-28. Where a primary-source URL was not directly fetchable, the citation notes the alternative source consulted and the verification limitation.

- **Matter 1 — Apple Card / NYDFS report.** Primary source: NYDFS Press Release (March 23, 2021), `https://www.dfs.ny.gov/reports_and_publications/press_releases/pr202103231`. Retrieved and verified 2026-05-28. The full report (`rpt_202103_apple_card_investigation.pdf`) is linked from the press release.
- **Matter 2 — CFPB Circular 2022-03.** Primary source: Consumer Financial Protection Bureau, Consumer Financial Protection Circular 2022-03, "Adverse action notification requirements in connection with credit decisions based on complex algorithms" (May 26, 2022), `https://www.consumerfinance.gov/compliance/circulars/circular-2022-03-adverse-action-notification-requirements-in-connection-with-credit-decisions-based-on-complex-algorithms/`. Retrieved and verified 2026-05-28.
- **Matter 3 — CFPB v. Wells Fargo Bank, N.A. consent order.** Primary source URL `https://files.consumerfinance.gov/f/documents/cfpb_wells-fargo-na_consent-order_2022-12.pdf` returned HTTP 404 on retrieval 2026-05-28. Substantive details (date December 20, 2022; aggregate $3.7B; $2.0B consumer redress / $1.7B civil penalty; product scope auto / mortgage / deposit) cross-verified against the Wells Fargo Wikipedia entry, retrieved 2026-05-28. [VERIFICATION LIMITATION — primary CFPB consent-order PDF not fetched at retrieval time; adopters should retrieve the consent order directly from `consumerfinance.gov/enforcement/actions/` and confirm citation before relying on this summary in counsel-facing material.]
- **Matter 4 — SEC v. Charles Schwab / Schwab Intelligent Portfolios.** Primary-source SEC press release URL `https://www.sec.gov/news/press-release/2022-104` returned HTTP 403 on retrieval 2026-05-28. Substantive details (date June 13, 2022; aggregate $187M; $52M penalty / $135M disgorgement and prejudgment interest; respondents Charles Schwab & Co., Charles Schwab Investment Advisory, Schwab Wealth Investment Advisory; statutory basis Investment Advisers Act § 206(2) and § 206(4); violation period March 2015 to November 2018) cross-verified against the Charles Schwab Corporation Wikipedia entry, retrieved 2026-05-28. [VERIFICATION LIMITATION — primary SEC press release and administrative order not fetched at retrieval time; adopters should retrieve the SEC order from `sec.gov/litigation/admin/` and confirm citation before relying on this summary in counsel-facing material.]
- **Cross-vertical — TransUnion FTC/CFPB consent orders.** Cited by reference from `cre-agent-audit/docs/regulatory_matters.md` and from `adr/0009-fcra-reg-v-adverse-action.md` in this repo. October 2023; $15M aggregate; FCRA § 607(b).

---

## Out of Scope

This doc does not editorialize on whether any matter above was correctly decided. It does not recommend any specific compliance program. It does not represent that the framework would have prevented any matter; the framework is governance scaffolding that produces defensible audit artifacts. Adopters retain full responsibility for fair-lending judgment, model validation, and counsel review.
