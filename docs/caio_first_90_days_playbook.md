# Chief AI Officer — First 90 Days Playbook

**Status:** v1.2.0-draft · Last reviewed: 2026-05-28.
**Audience:** Newly hired Chief AI Officer at a Tier-1 or large-regional US bank, wealth platform, insurance carrier, or FinTech with regulated-FSI surface. The framework's premise is that the CAIO is the buyer persona for v1.2 and v2.0.

> **Patterns are software, not legal advice.** Engage qualified counsel, your internal-audit function, and your primary federal regulator before any commitment. See repo-root [`DISCLAIMER.md`](../DISCLAIMER.md).

---

## Persona context

**76% of large firms now employ a Chief AI Officer**, up from 26% in 2025 [UNVERIFIED — verify against current Deloitte / IBM / Gartner CAIO-prevalence surveys]. The role is no longer experimental; it is governance, and the institution's board expects a 30 / 60 / 90 day plan within the first week.

**The talent market.** The CAIO market in 2026 is shallow — pricing has gone up, the field of qualified candidates is thin, and most institutions are pulling from adjacent roles (Chief Data Officer, Chief Risk Officer with technology background, VP of Engineering with quant / fair-lending tour-of-duty). The board's expectation is that the CAIO will build the governance framework, not staff it line-by-line; the line-staffing comes in months 2-6.

**What the board expects, by milestone:**

- **Day 30.** A written governance plan. Inventory of every AI use in the institution. Initial risk-tiering. Named partners in CRO, CIO, CISO, Internal Audit, Legal, Compliance.
- **Day 60.** Deployment of foundational controls. Pre-examination self-assessment completed. Top 2-3 risk surfaces identified with remediation plans.
- **Day 90.** Big-4 engagement scoped. Vendor-management starter pack in place. First quarterly board report drafted. Hire plan for months 2-6 approved.

The CAIO who arrives on Day 1 without a playbook spends the first 30 days inventorying — and discovers that the institution has more AI in production than anyone realized (shadow IT copilots, business-unit-procured vendor scorers, pilots that quietly converted to production). The CAIO who arrives with a playbook is shipping by Day 14.

This document is that playbook.

---

## Weeks 1-4 — Foundation

**Goal.** Get the foundational governance machinery in production. Map every existing AI use. Identify the 2-3 highest-risk surfaces. Brief the board on Day 30.

### Week 1 — Land the role
- Walk the org. Name your partners in CRO, CIO, CISO, Internal Audit, Legal, Compliance, Procurement, HR. Set weekly standing meetings with each.
- Read the institution's most-recent MRM policy, third-party-risk policy, IR procedure, and any AI-specific policy that exists.
- Read the most-recent regulator examination findings or MRA letters touching AI / model risk.
- Read the most-recent SOC 1, SOC 2, and Big-4 audit report.
- Deploy the **DEFCON state machine** (`finserv_agent_audit.governance.defcon.DEFCONMachine`) into your CAIO command-center dashboard. This is your daily ops view — risk states + hysteresis, not slideware.
- Deploy the **Sovereign Veto** (`finserv_agent_audit.governance.sovereign_veto.SovereignVeto`) into the institution's incident-response procedure. Test the path: confirm `VetoBlockedError` raises during a non-production drill.

### Week 2 — Inventory
- Deploy the **Audit Chain** (`finserv_agent_audit.governance.audit_chain.AuditChain`) wired to the institution's ledger backend (`JsonlLedgerStore`, `SqliteLedgerStore`, or `WORMLedgerStore` paired with S3 Object Lock COMPLIANCE for SEC 17a-4 in-scope retention).
- Deploy the **Autonomy Ladder** (`finserv_agent_audit.governance.autonomy_ladder.AutonomyTier`) classification across every known AI use case. A0 (advisory-only) to A4 (autonomous, audit-only). The default ceiling for any new use case is A2 (human on the loop).
- Stand up an institution-wide AI-inventory canvass. Survey every business unit; ask "do you use any AI / ML / LLM tool in customer-facing or decisioning processes?" Many will say no when the answer is yes. Cross-check with Procurement spend on AI / ML vendors; cross-check with CI/CD systems for ML-model artifacts.

### Week 3 — Self-assessment
- Complete the [`pre-examination AI self-assessment`](pre_examination_ai_self_assessment.md). Walk through all 50 questions with the relevant stakeholders. Score YES / NO / PARTIAL / N/A.
- For every NO and PARTIAL, name an owner and a date. Enter the gap list on the remediation tracker.
- Identify the 2-3 highest-risk surfaces based on (a) decision class consequentiality, (b) volume, (c) autonomy band, (d) vendor opacity, (e) fair-lending exposure.

### Week 4 — Board brief
- Draft the Day 30 board brief: governance framework deployed (DEFCON + Sovereign Veto + Audit Chain + Autonomy Ladder); AI inventory complete; pre-examination self-assessment in progress; top 2-3 risk surfaces identified; 60-day plan named.
- Schedule the Day 30 board meeting; deliver the brief in 15 minutes; reserve 30 minutes for questions.
- Run a Sovereign-Veto tabletop with the CRO. Walk the IR procedure end-to-end. Confirm the named-authorized-actor list is current.

---

## Weeks 5-8 — FSI overlay

**Goal.** Deploy the FSI-specific gates the institution's regulator will examine. Establish the vendor-management starter pack. Ship the first VendorScoreGate. Brief the Risk Committee.

### Week 5 — SR 11-7 overlay
- Deploy **ModelInventory** (`finserv_agent_audit.governance.model_inventory.ModelInventory`) into the institution's MRM system of record. Migrate the existing model inventory; reconcile to source-of-truth systems.
- Confirm every model has owner + validator + validation date + next revalidation due. Anything missing is a Day-90 closure item.
- Run `ModelInventory.query_overdue()`. Schedule remediation for every overdue model with the Model Risk Committee.

### Week 6 — Adverse-action + fair-lending
- Deploy **AdverseActionGate** (`finserv_agent_audit.governance.adverse_action_gate.AdverseActionGate`) into the credit-decisioning path. Wire to the institution's reason-code dictionary; enforce specificity against CFPB Circular 2022-03 (May 26, 2022) [UNVERIFIED]. Test the path: confirm `AdverseActionViolation` raises on a deliberately-generic reason code in a non-production drill.
- Deploy **EquityAudit** (`finserv_agent_audit.governance.equity_audit.EquityAudit`) into the pre-promotion gate for credit, lending, and insurance underwriting models. Confirm the ProtectedClass enum (9 classes per ECOA / Reg B) is fully populated for the institution's testing posture.
- For models that exclude direct protected-class fields, identify the compensating control for protected-class proxy review. The framework's `ProtectedClassProxyDetector` ships the mutual-information arm in v1.2 (per ADR-0019 § "v1.2 ship reconciliation"); SHAP and conditional-demographic-disparity arms remain on the v1.3 roadmap, so deployers wire a third-party tool or qualified analytics resource for the arms not yet shipped.

### Week 7 — BSA / AML + Reg-BI
- Where applicable: deploy **SARWorkflowAudit** (`finserv_agent_audit.governance.sar_workflow_audit.SARWorkflowAudit`) into the institution's BSA / AML system. Wire the 30-day (and 60-day extension) deadline tracker; capture § 5318(g)(2) safe-harbor metadata at filing time.
- Where applicable (broker-dealer, RIA): deploy **BestInterestCheck** (`finserv_agent_audit.governance.best_interest_check.BestInterestCheck`) into the recommendation path.

### Week 8 — Vendor-management starter
- Pick your top 5 vendor relationships by spend or by risk concentration. For each, identify the appropriate `vendor-clauses/` template (KYC, fraud, credit, robo-advisor, AML).
- For each top-5 vendor, schedule a contract amendment / addendum conversation with Procurement + Legal + the vendor's relationship owner. Use the template as the negotiation starting point.
- Ship the first **VendorScoreGate** (`finserv_agent_audit.governance.vendor_score_gate.InMemoryVendorScoreGate`) into the highest-volume vendor scoring path. Confirm `VENDOR_SCORE_RECORDED` chain entries appear; confirm a deliberate drift in a non-production drill emits `VENDOR_SCORE_DRIFT_DETECTED` and raises `VendorScoreDriftDetected`.
- Brief the Risk Committee on the 60-day status: FSI overlay deployed, vendor-management starter pack live, top-5 vendor amendments in negotiation, model-inventory reconciliation complete.

---

## Weeks 9-12 — Assurance and scale

**Goal.** Deploy the four Protocol seams to harden the audit-chain integrity layer. Engage the Big-4 firm with the engagement-letter exhibit. Complete the maturity self-score. Brief the board on Q+1 roadmap on Day 90.

### Week 9 — Protocol seams
- Deploy **LedgerStore** Protocol with the substrate that matches the institution's posture (`WORMLedgerStore` + S3 Object Lock COMPLIANCE for SEC 17a-4 in-scope; `SqliteLedgerStore` for lower-criticality; `JsonlLedgerStore` for development).
- Deploy **TimestampSource** Protocol. For high-integrity surfaces, choose `RFC3161Source` with a named TSA and an explicit `fallback_to_local_on_failure` policy.
- Deploy **WitnessRegister** Protocol. Pick one or both of `RekorWitness` (Sigstore public good) and `OpenTimestampsWitness`. Set the anchor cadence (default: every 6 hours). Wire alerting on anchor failure.
- Deploy **MIProxy** Protocol with `LocalMIProxy` HMAC-SHA256 as the default. For high-integrity surfaces, plan the move to a substrate-pluggable backend (SLSA / in-toto) on the Q+1 roadmap.

### Week 10 — Big-4 engagement
- Pick the Big-4 (or comparable assurance) firm. Schedule the engagement-letter conversation with the engagement partner.
- Attach [`docs/big4_engagement_letter_exhibit.md`](big4_engagement_letter_exhibit.md) to the Statement of Work. Walk through Section 1 (client framework declaration) with the audit team.
- Schedule the audit-team walk-through of the institution's `finserv-agent-audit` deployment. Provide read-only access to the audit chain, the model inventory, the vendor-score log, and the failure-modes matrix snapshot.

### Week 11 — Maturity self-score
- Run the **maturity self-score CLI** (`scripts/maturity_self_score.py`). Score the institution against the 5-level CMMI-style maturity model in [`docs/agentic_ai_governance_maturity_model.md`](agentic_ai_governance_maturity_model.md).
- Identify the level the institution is at (most institutions land at Level 2 or Level 3 on Day 90; Level 4 by Day 180 is a stretch goal; Level 5 is a 12-18 month commitment).
- Draft the gap-closure plan for the next level.

### Week 12 — Day 90 board brief
- Draft the Day 90 board brief: foundational controls deployed (DEFCON + Sovereign Veto + Audit Chain + Autonomy Ladder); FSI overlay deployed (ModelInventory + AdverseActionGate + SARWorkflowAudit + EquityAudit + BestInterestCheck); Protocol seams deployed (LedgerStore + TimestampSource + WitnessRegister + MIProxy); Big-4 engaged; pre-examination self-assessment complete; current maturity level + next-level gap; Q+1 roadmap.
- Deliver the brief in 15 minutes. Reserve 30 minutes for questions. Document board feedback in the IR / governance log.

---

## Reporting cadence

| Cadence | Audience | Format | Owner |
|---|---|---|---|
| Weekly | CAIO direct staff | Tactical stand-up; ops dashboard review (DEFCON state, vendor-drift count, overdue-model count, audit-chain verify status) | CAIO |
| Monthly | CRO + CIO + CISO | One-page status memo + ops dashboard PDF export | CAIO chief of staff |
| Quarterly | Risk Committee | 8-page package: incident summary, control changes, vendor-disposition log, model-inventory delta, maturity trajectory | CAIO + CRO joint |
| Quarterly | Audit Committee | 4-page package: audit-chain verify history, MIProxy attestation history, Big-4 engagement status, regulator interactions | CAIO + Chief Internal Auditor joint |
| Quarterly | Board | 15-minute readout; 1-page summary template (see Day 90 below); roadmap update | CAIO |

---

## Hire plan — Months 2-6

The CAIO is a leader, not an army. Hire the following roles in approximate order across months 2-6:

| Role | Month | Reports to | First-90-day mandate |
|---|---|---|---|
| **Model Risk Lead** (SR 11-7 + agentic-AI carve-out, second-line) | Month 2 | CAIO or CRO (institution preference) | Take over ModelInventory operation; chair Model Risk Committee for AI surfaces; lead second-line validation cadence |
| **AI Audit Lead** (third-line) | Month 3 | Chief Internal Auditor | Take over audit-chain verification cadence; lead Big-4 fieldwork interface; own the assurance walk-through |
| **Fair-Lending Counsel Liaison** | Month 3 | General Counsel; matrixed to CAIO | Own AdverseActionGate operation; lead disparate-impact testing cadence; CFPB Circular 2022-03 + 2023-09 alignment |
| **Vendor AI Risk Lead** | Month 4 | CAIO or Chief Procurement (institution preference) | Own VendorScoreGate operation; lead vendor-disposition queue; vendor-amendment program |
| **AI Incident Response Coordinator** | Month 4 | CISO; matrixed to CAIO | Wire AI-specific IR sections; lead tabletops; own 72-hour reporting clock where applicable |
| **GenAI / LLM Governance Specialist** | Month 5 | CAIO | Own copilot inventory; NIST AI 600-1 GAI Profile alignment; LLM-specific evaluation harness |
| **AI Governance Engineer** (platform) | Month 5 | CAIO or CIO (institution preference) | Maintain `finserv-agent-audit` deployment; CI/CD wiring; backend / substrate upgrades |
| **Chief AI Officer Chief of Staff** | Month 6 | CAIO | Reporting cadence operation; board package authoring; cross-functional coordination |

The exact titles vary by institution; the role coverage is what matters. The CAIO who fills these eight roles in the first six months has a sustainable governance organization. The CAIO who tries to do it alone hits a wall in months 4-6.

---

## Vendor-management starter pack

Within the first 90 days, firm up the contractual posture for the institution's top 3-5 vendor relationships. Use the per-class clause templates in `vendor-clauses/`:

| Vendor type | Clause template | Priority signal |
|---|---|---|
| Credit-decision scorer (e.g. bureau enrichment) | [`vendor-clauses/credit_decision_vendor_clauses.md`](../vendor-clauses/credit_decision_vendor_clauses.md) | High — FCRA + CFPB exposure |
| Fraud-score / device-risk provider | [`vendor-clauses/fraud_score_vendor_clauses.md`](../vendor-clauses/fraud_score_vendor_clauses.md) | High — adverse-action exposure |
| KYC / identity verification | [`vendor-clauses/kyc_vendor_clauses.md`](../vendor-clauses/kyc_vendor_clauses.md) | High — BSA / OFAC exposure |
| AML transaction monitoring | [`vendor-clauses/aml_transaction_monitoring_vendor_clauses.md`](../vendor-clauses/aml_transaction_monitoring_vendor_clauses.md) | High — BSA SAR exposure |
| Robo-advisor / wealth signal | [`vendor-clauses/robo_advisor_vendor_clauses.md`](../vendor-clauses/robo_advisor_vendor_clauses.md) | High — SEC Reg-BI + fiduciary exposure |

For each top vendor, the addendum conversation covers: model-change notification, training-data lineage attestation, sub-processor disclosure, exit / portability plan, incident-response obligations, audit rights, and (critically) the institution's right to surface vendor scores into the audit chain via `VendorScoreGate`.

---

## Quick-wins

Five demonstrable items that show the CAIO's governance is real, not theoretical. Aim to land all five inside the first 90 days.

1. **Ship a verifiable audit chain to the CRO.** Run `AuditChain.verify_strict()` against the production chain in the CRO's presence. Mutate one byte on a non-production copy; demonstrate the `AuditChainTamperError` raise. The CRO's takeaway: this is a working control, not a slide.

2. **Submit a model-inventory export to the Big-4 firm.** Stage the CSV produced by `ModelInventory.query_by_status()` for the audit team's pre-fieldwork review. The audit-firm partner's takeaway: the client is fieldwork-ready, not fieldwork-anxious.

3. **Complete the pre-examination self-assessment.** Walk all 50 questions; produce the assessment-completion certificate signed by CRO, CIO, and CAIO. The regulator's takeaway (during the next examination): the institution is self-aware about its AI risk posture.

4. **Ship the first VendorScoreGate.** Pick the highest-volume vendor scorer; ship the gate; demonstrate drift detection in a non-production drill. The Procurement chief's takeaway: the institution can now hold vendors accountable for silent model changes.

5. **Run a Sovereign-Veto tabletop with the IR team.** Walk the kill-switch path end-to-end; document the runbook update; capture the IR team's feedback. The CISO's takeaway: the AI program has a defensible IR posture, not just a controls list.

---

## Day 90 — What to put in front of the board

A single-page summary template the CAIO walks the board through in five minutes, plus the supporting deck for the 10-minute Q&A.

```
=== North River Bank — CAIO Day 90 Board Summary ===
=== Date: [Day 90 date]            Author: [CAIO name] ===

1. Governance machinery deployed
   - DEFCON state machine: live (with hysteresis)
   - Sovereign Veto: live (tabletop-tested with IR team)
   - Audit Chain: live (verify-on-read enabled; witness-anchor cron every 6h)
   - Autonomy Ladder: A0-A4 classification across [N] use cases

2. FSI overlay deployed
   - ModelInventory: [N] models registered; [X] approved_for_production; [Y] in_validation; [Z] overdue (remediation plans filed)
   - AdverseActionGate: live in credit-decisioning path
   - EquityAudit: live in pre-promotion gate (lending models)
   - SARWorkflowAudit: live in BSA/AML path
   - BestInterestCheck: live in wealth-platform recommendation path

3. Assurance posture
   - Four Protocol seams (LedgerStore, TimestampSource, WitnessRegister, MIProxy): deployed
   - Big-4 firm engaged: [firm name]; engagement-letter exhibit signed; fieldwork begins [date]
   - Pre-examination self-assessment: completed; [X] gaps remain with named owners
   - Agentic-AI governance maturity: Level [N] of 5 ([target level] by Day 180)

4. Hire plan
   - [N] of 8 governance roles filled in months 2-6; remaining roles in active search
   - Talent-market context: [brief on pipeline]

5. Q+1 roadmap (top 3)
   - [Surface 1]: [stated objective + month]
   - [Surface 2]: [stated objective + month]
   - [Surface 3]: [stated objective + month]

6. Top risks (top 3)
   - [Risk 1]: [mitigation + owner + date]
   - [Risk 2]: [mitigation + owner + date]
   - [Risk 3]: [mitigation + owner + date]

7. Asks of the board
   - [Ask 1: budget / hiring / committee charter / etc.]
   - [Ask 2: ...]
```

The board's takeaway from the Day 90 readout should be: governance is operational, not aspirational; risks are named with owners and dates; the next quarter has a defined plan; the CAIO is in command of the function.

---

## Related

- [`docs/pre_examination_ai_self_assessment.md`](pre_examination_ai_self_assessment.md) — 50-question worksheet
- [`docs/big4_engagement_letter_exhibit.md`](big4_engagement_letter_exhibit.md) — SOW exhibit
- [`docs/agentic_ai_governance_maturity_model.md`](agentic_ai_governance_maturity_model.md) — 5-level maturity model
- [`ASSURANCE-GUIDE.md`](../ASSURANCE-GUIDE.md) — Big-4 walk-through guide
- [`docs/sr11_7_mapping.md`](sr11_7_mapping.md) — SR 11-7 overlay
- [`docs/nist_ai_rmf_mapping.md`](nist_ai_rmf_mapping.md) — NIST AI RMF mapping
- [`vendor-clauses/`](../vendor-clauses/) — per-class procurement templates

---

*Patterns are software, not legal advice. This playbook is a starting framework; calibrate each step to your institution's regulator, scale, business mix, and existing posture. Citations flagged [UNVERIFIED] require primary-source confirmation before use in regulatory or board-facing documents.*
