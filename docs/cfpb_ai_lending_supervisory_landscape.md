# CFPB AI-Lending Supervisory Landscape — Unified Mapping

This document unifies the four federal supervisory pronouncements that
now define the CFPB's posture on AI-driven credit decisioning, plus the
**May 2026 final rule** that recalibrated the federal enforcement
posture. It supersedes the single-circular framing in
[`docs/cfpb_circular_2022_03_mapping.md`](cfpb_circular_2022_03_mapping.md)
for buyer-conversation purposes, while that earlier mapping continues to
serve as the article-by-article reference for Circular 2022-03 itself.

The narrative across the four years (2022 → 2026) is the central buyer
fact: **federal CFPB enforcement scaled back under the new
administration; state attorneys general and private class actions are
now the primary forward enforcement path**, with the federal-circular
record preserved as supervisory expectation and the May 2026 final rule
narrowing the federal disparate-impact theory while leaving state
authority untouched.

> **Disclaimer:** Reference pattern, not legal advice. Regulatory
> characterizations are summaries; engage qualified counsel for your
> specific compliance determination. See repo-root
> [`DISCLAIMER.md`](../DISCLAIMER.md).

---

## The Supervisory Landscape (2022 → 2026)

| # | Date | Pronouncement | Posture |
|---|---|---|---|
| 1 | May 26, 2022 | **CFPB Circular 2022-03** — Adverse-action notification requirements for credit decisions based on complex algorithms | Federal floor: specific-reason adverse-action notice required even when the model is opaque |
| 2 | September 19, 2023 | **CFPB Circular 2023-03** — Adverse-action notification requirements and the proper use of the CFPB's sample forms in Regulation B (published in the September 2023 issue cycle; also referenced in some compliance literature as "2023-09" by month-issue convention) | Extension: a checkbox reason from Form C-1 through C-5 in Reg B Appendix C cannot be used if the actual principal reason is not listed; sample forms cannot disguise the real reason |
| 3 | August 2024 | **U.S. Treasury request for information on AI in the financial services sector** with public comment record | Treasury-level acknowledgement that AI underwriting has fair-lending exposure; CFPB / FFIEC / FRB / OCC all cited the comment record going forward |
| 4 | December 2025 | **CFPB Fair Lending Annual Report to Congress (2025)** | Names AI / algorithmic underwriting as an active supervisory priority; cites coordination with state AGs |
| 5 | May 2026 | **CFPB final rule "Recalibrating Fair Lending Enforcement"** | Narrows federal disparate-impact theory under ECOA; requires "more concrete and demonstrable evidence" for discouragement liability; explicitly **does not alter state-law enforcement authority** |

The first three rows establish the federal supervisory record. The
fourth row is the most recent federal articulation of an active AI
enforcement priority. The fifth row is the May 2026 federal recalibration
that shifts the enforcement centre of gravity to state AGs and to
residential lending (where FHA disparate-impact liability survives the
federal recalibration unaffected).

---

## Primary-Source Citations

| Source | Retrieved | Status |
|---|---|---|
| CFPB Circular 2022-03 | Prior verification recorded in [`docs/cfpb_circular_2022_03_mapping.md`](cfpb_circular_2022_03_mapping.md) | Verified |
| CFPB Circular 2023-03 (publication page) | 2026-05-28, https://www.consumerfinance.gov/compliance/circulars/circular-2023-03-adverse-action-notification-requirements-and-the-proper-use-of-the-cfpbs-sample-forms-provided-in-regulation-b/ | Verified — title, date (September 19, 2023), and archived-content notice confirmed |
| CFPB Circular 2023-03 (PDF) | 2026-05-28, https://files.consumerfinance.gov/f/documents/cfpb_adverse_action_notice_circular_2023-09.pdf | Verified — PDF metadata confirms CFPB authorship, title, and September 19, 2023 creation date. PDF binary stream not text-extractable in this pass; standalone mapping in [`docs/cfpb_circular_2023_09_mapping.md`](cfpb_circular_2023_09_mapping.md) cites the publication-page text and the press-release summary |
| U.S. Treasury — Request for Information on AI in the Financial Services Sector (August 2024) | `[UNVERIFIED — primary-source PDF not fetched this pass]` | Cited as supervisory-record context; engage counsel for any examination defence |
| CFPB Fair Lending Annual Report to Congress (December 2025) | 2026-05-28, https://files.consumerfinance.gov/f/documents/cfpb_fair-lending-annual-report_2025-12.pdf | `[UNVERIFIED — PDF binary stream returned; text not extractable in this pass]` |
| Consumer Finance Monitor — "CFPB's Final Rule Recalibrates Fair Lending Enforcement" (May 4, 2026) | 2026-05-28, https://www.consumerfinancemonitor.com/2026/05/04/cfpbs-final-rule-recalibrates-fair-lending-enforcement-a-return-to-clarity-and-core-statutory-principles/ | Verified — recalibration scope (narrowed disparate-impact theory, retained FHA exposure, retained state authority) confirmed |

---

## Module Coverage by Pronouncement

### CFPB Circular 2022-03 (May 26, 2022)

The 2022 circular is the federal floor: a creditor cannot defend
non-compliance with ECOA's specific-reason adverse-action requirement
on the basis that the underlying model is too complex. Every AI agent
that produces or materially influences an adverse credit decision must
emit a specific principal-reason rationale per decision, before the
notice is issued.

**Module coverage:** `adverse_action_gate` (the v1.1 gate that blocks
the decline if rationale is missing or generic), `explainability_stub`
(top-K input contributions to the model output), `audit_chain`
(hash-chain decision ledger with retention window).

**Reference mapping:** [`docs/cfpb_circular_2022_03_mapping.md`](cfpb_circular_2022_03_mapping.md).

### CFPB Circular 2023-03 (September 19, 2023)

The 2023 circular extends the 2022 floor by addressing the model-form
checkbox problem. The Bureau makes explicit that selecting a Form C-1
through C-5 reason because it is the nearest pre-printed option does
not satisfy § 1002.9(b)(2) if the actual principal reason is not listed
on the form. A creditor using AI-generated decline reasons must either
expand the form or supply free-text reasons that accurately describe
the factors considered.

**Module coverage:** `adverse_action_gate` (gate rejects rationale that
maps only to a generic checkbox when the actual reason is novel),
`explainability_stub` (top-K contribution capture is the evidence the
gate inspects), `equity_audit` (fairness signals that can corroborate
or contradict the rationale at population level).

**Standalone mapping:** [`docs/cfpb_circular_2023_09_mapping.md`](cfpb_circular_2023_09_mapping.md).

### U.S. Treasury RFI on AI in Financial Services (August 2024)

The Treasury RFI established the federal-policy floor that AI use in
financial services creates fair-lending exposure, and the comment
record from major banks, civil-rights organisations, and academic
researchers has been cited by every subsequent federal supervisor.
While Treasury did not issue a rule, the RFI is the supervisory-record
anchor that lets examiners ask AI-specific questions during 2025-2026
examinations without waiting on a fresh rule.

**Module coverage:** `model_inventory` (AI-system inventory),
`equity_audit` (population-level fairness audit), `vendor_score_gate`
(third-party model gate), `audit_chain` (record of every decision).

### CFPB Fair Lending Annual Report to Congress (December 2025)

The 2025 fair-lending annual report cites AI / algorithmic underwriting
as an active supervisory priority and references coordination with
state attorneys general — the explicit textual anchor for the
post-recalibration state-AG enforcement narrative. Banks reading the
report should treat the state-AG channel as the forward enforcement
risk, not just a backstop.

**Module coverage:** `equity_audit` (population-level disparate-impact
testing), `protected_class_proxy_detector` (the v1.2 detector for
features that proxy a protected class), `lda_search` (the v1.3
linear-decision-analysis search surface for fair-lending audit),
`audit_chain` (every decision, every rationale, every override).

### CFPB Final Rule "Recalibrating Fair Lending Enforcement" (May 2026)

The May 2026 final rule narrowed the federal disparate-impact theory
under ECOA, requiring "more concrete and demonstrable evidence" for
discouragement liability and emphasising statutory text, evidentiary
rigor, and demonstrable causation. The rule **does not alter state law
enforcement**, and FHA disparate-impact liability for residential
lending persists. The article on which this row is based names New
Jersey, Massachusetts, California, New York, and Illinois as
disparate-impact-active states for multi-state creditors.

**Module coverage:** Same modules as the December 2025 report, with
heightened weight on `equity_audit` evidence preservation (state-AG
case posture requires a strong evidentiary record at the disparate-
impact and discouragement-evidence layers) and `audit_chain` retention
under the privilege / discovery posture documented in
[`adr/0017-audit-chain-retention-privilege-discovery.md`](../adr/0017-audit-chain-retention-privilege-discovery.md).

---

## Unified Coverage Table

| Pronouncement | adverse_action_gate | explainability_stub | equity_audit | protected_class_proxy_detector | lda_search | model_inventory | vendor_score_gate | audit_chain |
|---|---|---|---|---|---|---|---|---|
| Circular 2022-03 | Primary | Primary | Secondary | Secondary | — | — | — | Primary |
| Circular 2023-03 | Primary | Primary | Secondary | — | — | — | — | Primary |
| Treasury RFI (Aug 2024) | — | — | Primary | Primary | — | Primary | Primary | Primary |
| CFPB Fair Lending Report (Dec 2025) | Secondary | Secondary | Primary | Primary | Primary | Primary | Secondary | Primary |
| CFPB Final Rule (May 2026) | Secondary | Secondary | Primary | Primary | Primary | Secondary | Secondary | Primary |

---

## The Enforcement-Shift Narrative

Three buyer-relevant facts follow from the unified landscape:

1. **Federal supervisory record is preserved.** The 2022 / 2023 circulars,
   the August 2024 Treasury RFI, and the December 2025 annual report
   remain on the record as supervisory expectation. The May 2026 final
   rule narrowed the federal disparate-impact theory but did not
   rescind the circular series.
2. **State AGs are the forward enforcement risk.** The
   Consumer Finance Monitor summary names New Jersey, Massachusetts,
   California, New York, and Illinois as disparate-impact-active
   states whose authority the federal recalibration explicitly does
   not affect. See [`docs/state_ag_ai_fair_lending_matrix.md`](state_ag_ai_fair_lending_matrix.md)
   for the 50-state matrix.
3. **FHA residential-lending exposure survives.** The federal
   recalibration leaves FHA disparate-impact liability for residential
   lending intact. CRE-related repositories already cover that surface;
   for unsecured-consumer-credit agents, this means the residential-
   lending channel remains the most enforcement-active federal sub-
   surface.

---

## Gap Analysis — What the Unified Landscape Still Does Not Cover

| Requirement | Gap | Guidance |
|---|---|---|
| State UDAAP overlays | Federal landscape only | Engage state-by-state counsel; see state AG matrix |
| Private-class-action litigation posture | Not a supervisory surface | Engage litigation counsel; the audit-chain privilege / discovery posture is the central technical question |
| Specific fairness metric thresholds | The CFPB has not published threshold values | The Bureau's posture is principles-based; use industry-standard thresholds (e.g., four-fifths rule for adverse-impact ratio) and document the choice |
| Reg B § 1002.5(b) demographic-data segregation | Lawful collection and segregation of monitoring information | Handle in the data-architecture layer; not in agent code |
| FCRA / Reg V adverse-action overlay for credit-report-based decisions | Different statutory regime | See [`docs/fcra_reg_v_mapping.md`](fcra_reg_v_mapping.md) |
| ECOA § 1002.9(a)(1)(ii) account-management adverse actions | Same statute, different sub-surface | The same modules apply; the trigger is account-management actions (line reductions, closures) rather than origination |

---

## References

- CFPB Circular 2022-03, *Adverse Action Notification Requirements in
  Connection with Credit Decisions Based on Complex Algorithms*
  (May 26, 2022).
- CFPB Circular 2023-03, *Adverse Action Notification Requirements and
  the Proper Use of the CFPB's Sample Forms Provided in Regulation B*
  (September 19, 2023).
  <https://www.consumerfinance.gov/compliance/circulars/circular-2023-03-adverse-action-notification-requirements-and-the-proper-use-of-the-cfpbs-sample-forms-provided-in-regulation-b/>
- U.S. Treasury, *Request for Information on Uses, Opportunities, and
  Risks of Artificial Intelligence in the Financial Services Sector*
  (August 2024; public comment record).
- Consumer Financial Protection Bureau, *Fair Lending Annual Report
  to Congress 2025* (December 2025).
- Allon Kedem & Joseph Schuster, *CFPB's Final Rule Recalibrates Fair
  Lending Enforcement: A Return to Clarity and Core Statutory
  Principles*, Consumer Finance Monitor (May 4, 2026).
  <https://www.consumerfinancemonitor.com/2026/05/04/cfpbs-final-rule-recalibrates-fair-lending-enforcement-a-return-to-clarity-and-core-statutory-principles/>
- 15 U.S.C. § 1691 et seq. — Equal Credit Opportunity Act.
- 12 C.F.R. Part 1002 — Regulation B; Appendix C model forms.
- Patterns in this repo:
  `src/finserv_agent_audit/governance/adverse_action_gate.py`,
  `src/finserv_agent_audit/governance/equity_audit.py`,
  `src/finserv_agent_audit/governance/protected_class_proxy_detector.py`,
  `src/finserv_agent_audit/governance/model_inventory.py`,
  `src/finserv_agent_audit/governance/vendor_score_gate.py`,
  `src/finserv_agent_audit/governance/audit_chain.py`.
- Related mappings:
  [`docs/cfpb_circular_2022_03_mapping.md`](cfpb_circular_2022_03_mapping.md),
  [`docs/cfpb_circular_2023_09_mapping.md`](cfpb_circular_2023_09_mapping.md),
  [`docs/ecoa_reg_b_mapping.md`](ecoa_reg_b_mapping.md),
  [`docs/fcra_reg_v_mapping.md`](fcra_reg_v_mapping.md),
  [`docs/state_ag_ai_fair_lending_matrix.md`](state_ag_ai_fair_lending_matrix.md).
