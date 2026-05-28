# CFPB Circular 2023-03 — Standalone Control Mapping

This document maps the governance patterns in this repository to **CFPB
Circular 2023-03**, *Adverse Action Notification Requirements and the
Proper Use of the CFPB's Sample Forms Provided in Regulation B*
(September 19, 2023). It is a companion to the earlier mapping for
Circular 2022-03 ([`docs/cfpb_circular_2022_03_mapping.md`](cfpb_circular_2022_03_mapping.md))
and rolls up into the unified supervisory landscape document
([`docs/cfpb_ai_lending_supervisory_landscape.md`](cfpb_ai_lending_supervisory_landscape.md)).

> **Filename note.** Some compliance literature references this circular
> as "2023-09" (the September 2023 issue month). The official Bureau
> designation is **Circular 2023-03**. This document uses the official
> designation in the body and preserves the month-suffix filename for
> compatibility with internal cross-references that already cite that
> pattern.

> **Disclaimer:** Reference pattern, not legal advice. Regulatory
> characterizations are summaries; engage qualified counsel for your
> specific compliance determination. See repo-root
> [`DISCLAIMER.md`](../DISCLAIMER.md).

---

## Framework Overview

The Bureau issued Circular 2023-03 on **September 19, 2023**. The
circular answers a single question with a single answer:

> **Question.** When using the model-form adverse-action notices that
> the CFPB publishes in Appendix C of Regulation B (Form C-1, C-2, C-3,
> C-4, C-5), may a creditor satisfy ECOA's specific-reasons requirement
> by selecting the closest pre-printed checkbox reason when the actual
> principal reason for the adverse action is not listed on the form?
>
> **Answer.** No. The Bureau's sample forms are illustrative and do
> not relieve a creditor of the obligation to provide specific reasons
> that accurately describe the principal factors the creditor actually
> considered. If the principal reason is not on the pre-printed list,
> the creditor must add it or supply a free-text reason.

The circular extends Circular 2022-03 (May 26, 2022). Where the 2022
circular held that the complexity or opacity of the underlying model
is not a defence to the specific-reasons requirement, the 2023 circular
closes the adjacent gap: creditors using AI-generated rationale cannot
defeat the specific-reasons requirement by mapping a novel principal
reason to whichever checkbox is least wrong.

**Primary source citations:** CFPB Circular 2023-03 (September 19, 2023);
ECOA 15 U.S.C. § 1691(d); 12 C.F.R. § 1002.9(b)(2); 12 C.F.R. Part 1002
Appendix C, Forms C-1 through C-5.

| Source | Retrieved | Status |
|---|---|---|
| CFPB Circular 2023-03 publication page | 2026-05-28, https://www.consumerfinance.gov/compliance/circulars/circular-2023-03-adverse-action-notification-requirements-and-the-proper-use-of-the-cfpbs-sample-forms-provided-in-regulation-b/ | Verified — title, date (September 19, 2023), archived-content notice confirmed |
| CFPB Circular 2023-03 PDF | 2026-05-28, https://files.consumerfinance.gov/f/documents/cfpb_adverse_action_notice_circular_2023-09.pdf | Verified — PDF metadata confirms CFPB authorship, title, September 19, 2023 creation date. PDF binary stream not text-extractable in this WebFetch pass; Q&A summary above reflects the publication page and the CFPB's own September 2023 press release on the circular |

---

## Why This Circular Reaches Every AI Adverse-Action Surface

Circular 2022-03 established that an opaque model is not a defence to
the specific-reasons requirement. Circular 2023-03 addresses a related
defence that creditors had started to assert post-2022:

1. **The "nearest checkbox" defence.** Some creditors had taken the
   position that the Appendix C model forms exhaust ECOA's
   specific-reasons set, and that selecting the nearest pre-printed
   reason from C-1 through C-5 was sufficient even when the actual
   principal reason was not on the form. The 2023 circular rejects
   this position.
2. **The "AI-generated rationale doesn't fit the form" pattern.** ML
   underwriting models routinely produce principal-reason rationales
   that are not on the pre-printed list (e.g., "high transaction-velocity
   anomaly on linked deposit accounts," "device-fingerprint mismatch with
   stated address geography"). The 2023 circular requires the creditor
   to expand the form or supply free text — generic checkboxes do not
   discharge the obligation.
3. **The "principal reason" standard.** The Bureau reinforced that the
   notice must describe **the principal factors actually considered**,
   not the factors that happen to map to the form. This is the
   accuracy standard, not just the specificity standard.

The combined effect of the 2022 and 2023 circulars is a two-prong test
that every AI adverse-action pipeline must meet:

- **Specificity prong (2022).** The notice must name specific principal
  reasons; "internal standards" or "model output" does not satisfy.
- **Accuracy prong (2023).** The named reasons must reflect the factors
  the model actually considered; nearest-checkbox mapping does not
  satisfy.

---

## Control Mapping Table

| Circular 2023-03 / ECOA Requirement | Citation | Pattern in This Repo | File |
|---|---|---|---|
| Specific principal reasons must accurately reflect factors actually considered | Circular 2023-03; 12 C.F.R. § 1002.9(b)(2) | `adverse_action_gate` blocks the decline when rationale relies on a generic checkbox while the explainability payload names a different principal factor | `src/finserv_agent_audit/governance/adverse_action_gate.py` (v1.1) |
| Top-K factor capture from the model | Circular 2023-03 § II (factors actually considered) | `explainability_stub` records the top-K input contributions to the model output, with directional weights | `patterns/explainability_stub.py` (v1.1) |
| Free-text rationale support when no checkbox fits | Circular 2023-03 (sample forms are not exhaustive) | `adverse_action_gate` accepts free-text rationale; gate verifies non-empty and non-generic | `src/finserv_agent_audit/governance/adverse_action_gate.py` |
| Population-level corroboration of rationale accuracy | Circular 2023-03 (fair-lending corollary) | `equity_audit` evaluates whether the declared rationale class explains observed disparate-impact patterns; `protected_class_proxy_detector` flags features that proxy a protected class | `src/finserv_agent_audit/governance/equity_audit.py`, `src/finserv_agent_audit/governance/protected_class_proxy_detector.py` |
| Decision auditability for fair-lending examination | ECOA § 706; 12 C.F.R. § 1002.12 | `audit_chain` — hash-chain decision ledger; rationale, explainability payload, and checkbox / free-text choice all recorded | `src/finserv_agent_audit/governance/audit_chain.py` |
| Human override on novel-principal-reason cases | Circular 2023-03 (implicit in accuracy standard) | `sovereign_veto` halts the automated pipeline when the explainability payload diverges from the available checkbox set | `src/finserv_agent_audit/governance/sovereign_veto.py` |
| Governance posture under explanation-quality drift | ECOA fair-lending supervisory expectations | `defcon` state machine — halts new adverse-action issuance when rationale-quality metrics breach threshold | `src/finserv_agent_audit/governance/defcon.py` |
| Autonomy classification for adverse-action surface | Supervisory expectation under fair lending | `autonomy_ladder` — A1 (human in the loop) or A2 (human on the loop) default for adverse-action surfaces; A3 / A4 not appropriate | `docs/autonomy_ladder.md` |

---

## Differences from Circular 2022-03

| Dimension | Circular 2022-03 (May 2022) | Circular 2023-03 (September 2023) |
|---|---|---|
| Question answered | Does model complexity excuse the specific-reasons requirement? | Does selecting the nearest checkbox from Reg B Appendix C satisfy the specific-reasons requirement when the actual principal reason isn't on the form? |
| Defence rejected | "Our model is too complex to explain" | "We picked the closest pre-printed reason" |
| Test prong added | Specificity | Accuracy |
| Sample-forms posture | Did not address | Sample forms are illustrative; do not exhaust ECOA's specific-reasons set |
| Repo module weight | `adverse_action_gate` blocks generic rationale | `adverse_action_gate` + `explainability_stub` together verify that checkbox / free-text rationale reflects actual top-K factors |

---

## Walkthrough — Adverse-Action Lifecycle with the 2023 Accuracy Prong

A consumer-lending agent scores an unsecured-personal-loan application.

1. **Model scoring.** The underlying ML model produces a score and a
   decision (decline).
2. **Explainability capture.** `explainability_stub` captures the top
   contributing features and directional contributions
   (e.g., revolving utilisation +0.42, recent inquiries +0.31,
   device-fingerprint geographical mismatch +0.27).
3. **Checkbox mapping attempt.** The pipeline attempts to map the top
   factors to Form C-1 through C-5 reasons. Revolving utilisation maps
   cleanly (C-1: credit history). Device-fingerprint geographical
   mismatch does not map to any pre-printed reason.
4. **`adverse_action_gate` — accuracy prong.** The gate verifies that
   either (a) the top-K factors map cleanly to checkboxes, or (b) a
   free-text rationale is supplied that names the unmapped factor.
   Generic checkbox substitution is blocked.
5. **30-day clock.** A timer fires on decision entry; if the notice
   has not issued within 30 days, the event is flagged.
6. **`audit_chain` record.** Every input, the model output, the
   explainability payload, the checkbox / free-text choice, and the
   final rationale are hash-chained into the ledger.
7. **`equity_audit` corroboration.** Population-level fairness
   monitoring evaluates whether the declared rationale class explains
   any observed disparate-impact patterns; divergence triggers
   `protected_class_proxy_detector` review of the underlying feature.
8. **`sovereign_veto` escalation.** A compliance officer can halt the
   automated pipeline if novel-principal-reason cases exceed a
   reviewable rate.

---

## Gap Analysis — What This Repo Does NOT Cover

| Requirement | Gap | Guidance |
|---|---|---|
| Generation of the customer-facing notice document | Out-of-scope for agent code | Generate via consumer-communications system using the rationale payload as input |
| Form C-1 through C-5 PDF template management | Customer-comms layer | Maintain authoritative templates; rationale payload feeds the template |
| Demographic-data segregation under Reg B § 1002.5(b) | Out-of-scope for agent code | Handle in data-architecture layer |
| Multi-jurisdictional notice variation (state UDAAP overlays) | Out-of-scope for federal mapping | Engage state-by-state counsel; see [`docs/state_ag_ai_fair_lending_matrix.md`](state_ag_ai_fair_lending_matrix.md) |
| FCRA / Reg V adverse-action overlay for credit-report-based decisions | Different statute | See [`docs/fcra_reg_v_mapping.md`](fcra_reg_v_mapping.md) |
| Real-property-secured credit (right to receive appraisal) | Out-of-scope | Separate ECOA sub-surface |

---

## References

- CFPB Circular 2023-03, *Adverse Action Notification Requirements and
  the Proper Use of the CFPB's Sample Forms Provided in Regulation B*
  (September 19, 2023).
  <https://www.consumerfinance.gov/compliance/circulars/circular-2023-03-adverse-action-notification-requirements-and-the-proper-use-of-the-cfpbs-sample-forms-provided-in-regulation-b/>
- CFPB Circular 2022-03, *Adverse Action Notification Requirements in
  Connection with Credit Decisions Based on Complex Algorithms*
  (May 26, 2022).
- 15 U.S.C. § 1691 et seq. — Equal Credit Opportunity Act.
- 12 C.F.R. Part 1002 — Regulation B; Appendix C model forms (C-1
  through C-5).
- Patterns in this repo:
  `src/finserv_agent_audit/governance/adverse_action_gate.py`,
  `src/finserv_agent_audit/governance/equity_audit.py`,
  `src/finserv_agent_audit/governance/protected_class_proxy_detector.py`,
  `src/finserv_agent_audit/governance/audit_chain.py`,
  `src/finserv_agent_audit/governance/defcon.py`,
  `src/finserv_agent_audit/governance/sovereign_veto.py`,
  `patterns/explainability_stub.py` (v1.1),
  `docs/autonomy_ladder.md`.
- Related mappings:
  [`docs/cfpb_circular_2022_03_mapping.md`](cfpb_circular_2022_03_mapping.md),
  [`docs/cfpb_ai_lending_supervisory_landscape.md`](cfpb_ai_lending_supervisory_landscape.md),
  [`docs/ecoa_reg_b_mapping.md`](ecoa_reg_b_mapping.md),
  [`docs/fcra_reg_v_mapping.md`](fcra_reg_v_mapping.md).
