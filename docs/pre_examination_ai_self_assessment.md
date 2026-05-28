# Pre-Examination AI Self-Assessment

**Status:** v1.2.0-draft · Last reviewed: 2026-05-28.
**Audience:** Bank CTO / CISO / Chief Risk Officer / Chief AI Officer preparing for an OCC, FDIC, FRB, NYDFS, or state-banking-department examination that will touch the institution's AI / agentic-AI surface.

> **Patterns are software, not legal advice.** Use this self-assessment as a worksheet, not as a regulatory submission. Engage qualified counsel + your model-risk + compliance functions before any examination response. See repo-root [`DISCLAIMER.md`](../DISCLAIMER.md).

---

## Purpose

The FFIEC Cybersecurity Assessment Tool (CAT) was sunset effective August 31, 2025; the FFIEC's announced direction is for institutions to rely on **NIST Cybersecurity Framework 2.0** (Feb 26, 2024) and the **NIST AI Risk Management Framework 1.0 + Generative AI Profile (NIST AI 600-1, July 2024)** as the self-assessment baselines [UNVERIFIED — verify against your primary federal regulator's most-recent guidance bulletin]. The April 17, 2026 interagency revision to the model-risk-management guidance (the agencies' joint update to SR 11-7 / OCC 2011-12 / FDIC FIL-22-2017 to add an explicit agentic-AI carve-out) closes the gap for AI agents that materially shape regulated decisions [UNVERIFIED — confirm exact issue date and citation].

This self-assessment fills the operational gap between those frameworks and the questions an examiner actually asks during a walk-through. It is calibrated so that an institution that answers YES to every question can produce hash-chain-mechanism audit-trail evidence for each answer using the v1.1 module set in `finserv_agent_audit.governance`.

**How to use it.** Walk top-to-bottom in one sitting; do not let any question sit at PARTIAL longer than one revalidation cycle without an attached remediation memo. Submit the completed sheet to your CRO + Internal Audit before an examination window opens; attach the evidence pack (see appendix).

**Scoring legend.**

- **YES** — control is in place, documented, and the named evidence artifact exists and is retrievable in under 15 minutes.
- **NO** — control is absent; this is a gap entered on the remediation tracker with an owner and a date.
- **PARTIAL** — control is partially in place; the gap is named and a closure plan exists.
- **N/A** — not in scope for this institution. Document why; examiners ask.

---

## Section 1 — AI Use Inventory

Anchored on the NYDFS Industry Letter "Cybersecurity Risks Arising from Artificial Intelligence" (Oct 16, 2024) [UNVERIFIED — verify exact citation against NYDFS publication archive] and the GAO report on banking-regulator AI oversight (GAO-25-107197) [UNVERIFIED]. The premise: you cannot govern what you have not enumerated.

| # | Question | YES / NO / PARTIAL / N/A | Evidence required | v1.1 module mapping |
|---|---|---|---|---|
| 1.1 | Every AI / ML model in production is registered in a single inventory of record, with owner, version, and lifecycle status. |   | `ModelInventory` CSV export filtered to all non-`RETIRED` rows | `finserv_agent_audit.governance.model_inventory.ModelInventory` |
| 1.2 | Every third-party AI scorer in production is registered with vendor name, vendor class, contract reference, and most-recent due-diligence date. |   | Vendor-scoring log + procurement file cross-reference | `finserv_agent_audit.governance.vendor_score_gate.VendorClass` |
| 1.3 | Every internally developed LLM-based agent or copilot is registered (including pilots and "shadow IT" copilots discovered by the security team). |   | Model inventory + shadow-IT discovery scan report | `finserv_agent_audit.governance.model_inventory.ModelInventory` |
| 1.4 | Each registered model has a documented intended-use statement (decision class, customer / employee / both, autonomy band A0-A4). |   | Intended-use memo per model; autonomy-band classification | `finserv_agent_audit.governance.autonomy_ladder.AutonomyTier` |
| 1.5 | Each model carries a current validation date and a next-revalidation-due date. |   | `ModelInventory.query_overdue()` returns an empty set | `finserv_agent_audit.governance.model_inventory.ModelInventory.query_overdue` |
| 1.6 | Each model has a named first-line owner and a named second-line validator. |   | RACI matrix; model-risk-committee minutes | `finserv_agent_audit.governance.model_inventory.Model` |
| 1.7 | The institution can produce the implementation-status counts (PROPOSED / IN_VALIDATION / APPROVED_FOR_LIMITED_USE / APPROVED_FOR_PRODUCTION / RETIRED) on demand. |   | `ModelInventory.query_by_status()` output | `finserv_agent_audit.governance.model_inventory.ImplementationStatus` |
| 1.8 | Generative-AI use cases (copilots, summarization, drafting) are inventoried separately and tiered against the NIST GAI Profile (NIST AI 600-1) [UNVERIFIED]. |   | GAI inventory; per-use-case GAI-profile alignment memo | `finserv_agent_audit.governance.model_inventory.ModelInventory` |
| 1.9 | Every agent that takes consequential action (commits state, sends a message externally, files a regulatory artifact) has a documented A-band ceiling approved by the board or risk committee. |   | Board / risk-committee approval entry; ceiling-per-agent table | `finserv_agent_audit.governance.autonomy_ladder.AutonomyTier` |
| 1.10 | The inventory is reconciled to source-of-truth systems (CI/CD, model registry, vendor procurement) on at least a quarterly cadence. |   | Quarterly reconciliation memo; gap-closure ledger | `finserv_agent_audit.governance.model_inventory.ModelInventory` |

---

## Section 2 — Model Risk Management

Anchored on SR 11-7 (April 4, 2011) + OCC Bulletin 2011-12 + FDIC FIL-22-2017, as updated by the April 17, 2026 interagency revision adding the agentic-AI carve-out [UNVERIFIED — confirm exact issue date and citation]. The premise: the agent is the model.

| # | Question | YES / NO / PARTIAL / N/A | Evidence required | v1.1 module mapping |
|---|---|---|---|---|
| 2.1 | The institution has a written MRM policy that names agentic-AI systems as in-scope models. |   | MRM policy with agentic-AI section; effective-date stamp | `docs/sr11_7_mapping.md` |
| 2.2 | Each in-scope model has documented development evidence: stated purpose, data sources, assumptions, limitations. |   | Per-model development memo; data-source attestations | `finserv_agent_audit.governance.model_inventory.ModelInventory` |
| 2.3 | Each in-scope model has documented validation evidence: conceptual soundness, ongoing monitoring, outcomes analysis. |   | Per-model validation memo signed by second line | `finserv_agent_audit.governance.model_inventory.ModelInventory.transition_status` (MODEL_VALIDATED emission) |
| 2.4 | The shadow-mode parallel-run pattern is used before any model moves from `IN_VALIDATION` to `APPROVED_FOR_PRODUCTION`. |   | Shadow-mode outcome report per promotion; promotion-gate verdict | `finserv_agent_audit.governance.shadow_mode.ShadowRouter` |
| 2.5 | The A2-to-A3 autonomy-band promotion gate is evaluated programmatically (not via slide deck). |   | `check_a2_to_a3_promotion()` report per promotion | `finserv_agent_audit.governance.autonomy_ladder.check_a2_to_a3_promotion` |
| 2.6 | Every model in production has an effective-challenge record from a named, organizationally-independent second-line reviewer. |   | Effective-challenge memo per model | `finserv_agent_audit.governance.sovereign_veto.SovereignVeto` (challenge enforcement mechanism) |
| 2.7 | Every model implementation change (code, prompt, weights, fine-tune) flows through documented change-management with second-line approval. |   | Change-record per change; second-line approval signature | `finserv_agent_audit.governance.audit_chain.AuditChain` |
| 2.8 | Override patterns (human reverses an agent decision) are logged with reason and reviewed by second line at a defined cadence. |   | Override log; second-line review cadence + minutes | `finserv_agent_audit.governance.sovereign_veto.VetoRecord` |
| 2.9 | The institution can attest the integrity of the verifier binary that produces "audit chain intact" results (verifier compromise is in-scope). |   | `MIProxy.verify_integrity()` attestation receipt; backend documented | `finserv_agent_audit.governance.mi_proxy.LocalMIProxy.verify_integrity` |
| 2.10 | The institution has a documented model-retirement procedure that closes the audit-chain artifacts and updates dependent systems. |   | Retirement runbook; per-retirement closure memo | `finserv_agent_audit.governance.model_inventory.ImplementationStatus.RETIRED` |

---

## Section 3 — Third-Party AI Risk Management

Anchored on DORA Articles 28-30 (Reg (EU) 2022/2554, in force January 17, 2025) [UNVERIFIED — DORA does not bind US institutions directly but applies to EU operations + US-EU service flows; verify scope with counsel], Treasury's FS AI RMF guidance to the financial-services sector, and OCC Bulletin 2024-26 ("Risk Management: Third-Party Relationships") [UNVERIFIED]. The premise: most FSI AI is consumed, not built; opacity is the norm.

| # | Question | YES / NO / PARTIAL / N/A | Evidence required | v1.1 module mapping |
|---|---|---|---|---|
| 3.1 | Every third-party AI scorer is captured into the audit chain on each call (vendor_id, input_hash, model_version, score). |   | `VendorScoreGate` emission rate; chain entries per day | `finserv_agent_audit.governance.vendor_score_gate.InMemoryVendorScoreGate.emit` |
| 3.2 | Score drift on the (vendor_id, input_hash, model_version) key is detected and routed to a vendor-review queue. |   | `VENDOR_SCORE_DRIFT_DETECTED` count per quarter; disposition per entry | `finserv_agent_audit.governance.vendor_score_gate.VendorScoreDriftDetected` |
| 3.3 | Each vendor contract includes the procurement clauses for the vendor's class (KYC, fraud, credit, robo-advisor, AML). |   | Signed contract addenda or amendments per vendor | `vendor-clauses/` per `VendorClass` |
| 3.4 | Each vendor has a documented exit / portability plan in case of vendor failure, vendor sale, or vendor model deprecation. |   | Per-vendor exit plan + last review date | DORA Articles 28-30 [UNVERIFIED] |
| 3.5 | Each vendor's incident-response obligations are documented and tested at least annually. |   | Incident-response runbook per vendor; last tabletop date | `docs/fsi_settled_matters.md` (incident pattern catalog) |
| 3.6 | The institution conducts independent validation of vendor model outputs (not just vendor-supplied accuracy claims). |   | Independent-validation memo per vendor; sample-size + method | `finserv_agent_audit.governance.shadow_mode.ShadowRouter` |
| 3.7 | Sub-processors and the vendor's own model-supply chain (training data, fine-tuning data, third-party APIs) are documented. |   | Sub-processor map per vendor; supply-chain attestation | `vendor-clauses/` (supply-chain clauses per class) |
| 3.8 | Concentration risk across vendors (single-vendor dependency, single-region dependency) is tracked and reported to the risk committee. |   | Concentration-risk report; committee minutes | OCC Bulletin 2024-26 [UNVERIFIED] |
| 3.9 | Vendor's reuse of customer data for training is contractually prohibited or explicitly permitted with notice + consent. |   | Contract clauses; customer-notice records | `vendor-clauses/kyc_vendor_clauses.md` (data-use clauses) |
| 3.10 | Vendor's AI/ML provenance (model card, training-data lineage, evaluation methodology) is on file and reviewed annually. |   | Vendor model card + provenance pack per vendor | EU AI Act 2024/1689 Annex IV § 1(g) (component records) [UNVERIFIED] |

---

## Section 4 — Fair Lending and Algorithmic Discrimination

Anchored on ECOA / Reg B (12 CFR Part 1002), FCRA § 615 + Reg V, CFPB Circular 2022-03 (May 26, 2022) on "Adverse action notification requirements in connection with credit decisions based on complex algorithms" [UNVERIFIED], CFPB Circular 2023-09 (Sep 19, 2023) on "Adverse action notices when using artificial intelligence or complex credit models" [UNVERIFIED], and state-AG enforcement patterns (TX, CA, NY, MA). The premise: the algorithm is no defense to a fair-lending violation.

| # | Question | YES / NO / PARTIAL / N/A | Evidence required | v1.1 module mapping |
|---|---|---|---|---|
| 4.1 | Every adverse action driven by an AI / agentic-AI system produces specific, accurate, traceable reason codes. |   | Sample notices; reason-code dictionary; per-decision code-list | `finserv_agent_audit.governance.adverse_action_gate.AdverseActionGate` |
| 4.2 | Reason codes are validated against the institution's reference vocabulary before the notice is sent (no "credit decision" boilerplate). |   | `AdverseActionViolation` rate per quarter; remediation log | `finserv_agent_audit.governance.adverse_action_gate.AdverseActionViolation` |
| 4.3 | The fair-lending second-line conducts pre-deployment review of every model that touches credit, lending, or insurance underwriting. |   | Pre-deployment review memo per model | `finserv_agent_audit.governance.equity_audit.EquityAudit` |
| 4.4 | Disparate-impact testing on protected classes (race, color, religion, national origin, sex, marital status, age, public-assistance income, ECOA-exercised rights) runs on a documented cadence. |   | Disparate-impact test reports; cadence policy | `finserv_agent_audit.governance.equity_audit.ProtectedClass` (9-class enum) |
| 4.5 | Protected-class proxy detection (geography, education, occupation, name pattern, device pattern, behavioral patterns) is in place for models that exclude direct protected-class fields. |   | Proxy-detection report per model; method documented | `finserv_agent_audit.governance.protected_class_proxy_detector.ProtectedClassProxyDetector` (v1.2 ships the mutual-information arm per ADR-0019; SHAP / CDD arms on the v1.3 roadmap) |
| 4.6 | Model explanations meet the CFPB Circular 2022-03 specificity standard (no boilerplate; identify the actual factors) [UNVERIFIED]. |   | Sample notices; specificity review per model | `finserv_agent_audit.governance.adverse_action_gate.AdverseActionGate` |
| 4.7 | The institution has a documented procedure for handling consumer disputes of AI-driven adverse actions. |   | Dispute-handling runbook; dispute volume + resolution metrics | `docs/fcra_reg_v_mapping.md` |
| 4.8 | The fair-lending function reports to the board (or risk committee) on AI-driven adverse-action patterns at least quarterly. |   | Quarterly fair-lending board package | `docs/ecoa_reg_b_mapping.md` |
| 4.9 | The institution has reviewed Apple-Card-class precedents (NYDFS Mar 2021 letter; CFPB enforcement actions; state-AG matters) and documented the lessons applied. |   | Lessons-learned memo; control changes traceable | `docs/fsi_settled_matters.md` |
| 4.10 | The institution has reviewed CFPB Circular 2023-09 on AI-specific adverse-action obligations and documented the alignment [UNVERIFIED]. |   | Circular alignment memo; gap-closure plan | `docs/cfpb_circular_2022_03_mapping.md` |

---

## Section 5 — Incident Response and Audit Trail

Anchored on 23 NYCRR Part 500 (NYDFS Cybersecurity Regulation, amended Nov 1, 2023) and the FFIEC IT Examination Handbook Architecture, Infrastructure, and Operations booklet (AIO, June 2021) [UNVERIFIED — confirm against the AIO booklet's most-recent revision]. The premise: detection without recovery is failure; an audit trail you cannot read is no audit trail.

| # | Question | YES / NO / PARTIAL / N/A | Evidence required | v1.1 module mapping |
|---|---|---|---|---|
| 5.1 | The agent's audit chain runs in production with verify-on-read enabled. |   | Recent `AuditChain.verify_strict()` log + alerting destination | `finserv_agent_audit.governance.audit_chain.AuditChain.verify_strict` |
| 5.2 | The ledger backend is paired with substrate-layer write-once posture (S3 Object Lock COMPLIANCE, equivalent). |   | Bucket-policy export; substrate configuration doc | `finserv_agent_audit.governance.ledger_store_worm.WORMLedgerStore` |
| 5.3 | Witness-anchor cron runs at a documented cadence to an external register (Sigstore Rekor, OpenTimestamps, equivalent). |   | Cron schedule; recent `WITNESS_ANCHOR` chain entry; failure alerting | `finserv_agent_audit.governance.witness_anchor.anchor_to_witness` |
| 5.4 | The verifier binary is itself attested (MI Proxy backend wired). |   | `MIProxy.verify_integrity()` attestation + key-management doc | `finserv_agent_audit.governance.mi_proxy.LocalMIProxy` |
| 5.5 | A documented incident-response procedure covers AI / agentic-AI-specific incidents (autonomy escalation, vendor drift, prompt injection, model-output tampering). |   | IR runbook with AI-specific sections; tabletop date | `docs/fsi_settled_matters.md` (pattern catalog) |
| 5.6 | The 72-hour NYDFS cyber-event reporting clock is wired to the AI-incident playbook for institutions subject to 23 NYCRR Part 500 § 500.17 [UNVERIFIED]. |   | Notification template; 72-hour timer + escalation tree | `docs/glba_safeguards_mapping.md` |
| 5.7 | The audit chain's retention period is set against the most-binding applicable rule (SEC Rule 17a-4 for broker-dealer records; CFPB 25-month record-retention; institution policy). |   | Retention-policy memo; per-data-class retention table | `docs/sec_17a_4_mapping.md` |
| 5.8 | The institution has a documented procedure for producing audit-chain segments to regulators and counsel under a litigation hold or examination request. |   | Hold-procedure runbook; sample production package | `docs/adr/0017-audit-chain-retention-privilege-discovery.md` |
| 5.9 | The SAR-filing workflow (BSA / AML) is captured in the audit chain with timestamp evidence of the 30-day (or 60-day extension) deadline. |   | `SAR_FILED` chain entries; deadline-compliance metric | `finserv_agent_audit.governance.sar_workflow_audit.SARWorkflowAudit` |
| 5.10 | The institution has tested its ability to reconstruct an operational day from the audit chain alone (no other system available). |   | Tabletop reconstruction memo; gap list + closure plan | `finserv_agent_audit.governance.audit_chain.AuditChain` |

---

## Appendix — Submit-ready Evidence Pack

For each examination engagement, assemble the following pack and stage it on a read-only share for the examination team. The folder structure below mirrors the section structure above.

### `01_ai_use_inventory/`
- `model_inventory_export.csv` — full `ModelInventory.query_by_status()` dump
- `vendor_inventory.csv` — every registered vendor with `VendorClass`, contract reference, due-diligence date
- `shadow_ai_discovery_scan.pdf` — last quarterly scan + remediation status
- `intended_use_memos/` — one memo per registered model
- `autonomy_band_classification.md` — per-agent A0-A4 ceiling + board-approval reference

### `02_model_risk_management/`
- `mrm_policy.pdf` — board-approved MRM policy with agentic-AI section
- `validation_memos/` — per-model second-line validation memos
- `shadow_mode_outcome_reports/` — per-promotion shadow-mode comparison reports
- `a2_to_a3_promotion_gate_reports/` — per-promotion `check_a2_to_a3_promotion()` outputs
- `verifier_attestation.json` — most-recent `MIProxy.verify_integrity()` attestation

### `03_third_party_risk/`
- `vendor_scores_log.csv` — `VendorScoreGate` emission log for the examination period
- `vendor_drift_dispositions.md` — every `VENDOR_SCORE_DRIFT_DETECTED` entry + disposition
- `vendor_contracts/` — signed addenda per vendor referencing the appropriate `vendor-clauses/` template
- `vendor_exit_plans/` — per-vendor exit + portability plan
- `concentration_risk_report.pdf` — current snapshot + trend

### `04_fair_lending/`
- `adverse_action_notices_sample.zip` — randomly selected sample (≥ 30 notices) with reason-code traceability
- `disparate_impact_tests/` — per-model test reports + cadence policy
- `proxy_detection_reports/` — per-model proxy-detection output + method documentation
- `fair_lending_board_package_yearly.pdf` — annual board package + quarterly updates

### `05_incident_response/`
- `audit_chain_verify_log.txt` — most-recent `AuditChain.verify_strict()` runs
- `witness_anchor_cron_log.txt` — anchor cron success / failure log
- `ir_runbook_ai_sections.pdf` — AI / agentic-AI-specific IR procedures
- `nydfs_72hour_notification_template.docx` — wired template if 23 NYCRR Part 500 applies
- `tabletop_reconstruction_memo.pdf` — last tabletop that reconstructed an operational day from the chain

### Top-level
- `assessment_completion_certificate.md` — signed by CRO, CIO / CTO, and Chief Compliance Officer (or CAIO if hired)
- `gap_remediation_tracker.csv` — every PARTIAL / NO answer with owner + date

---

## Related

- [`ASSURANCE-GUIDE.md`](../ASSURANCE-GUIDE.md) — Big-4 audit-evidence walkthrough
- [`FAILURE-MODES.md`](../FAILURE-MODES.md) — adversarial matrix
- [`DEPLOY-CHECKLIST.md`](../DEPLOY-CHECKLIST.md) — go-live walkthrough
- [`docs/sr11_7_mapping.md`](sr11_7_mapping.md) — SR 11-7 overlay
- [`docs/nist_ai_rmf_mapping.md`](nist_ai_rmf_mapping.md) — NIST AI RMF 1.0 mapping
- [`docs/glba_safeguards_mapping.md`](glba_safeguards_mapping.md) — GLBA Safeguards Rule mapping
- [`docs/fcra_reg_v_mapping.md`](fcra_reg_v_mapping.md) — FCRA + Reg V mapping
- [`docs/ecoa_reg_b_mapping.md`](ecoa_reg_b_mapping.md) — ECOA + Reg B mapping
- [`docs/bsa_aml_mapping.md`](bsa_aml_mapping.md) — BSA / AML SAR workflow mapping
- [`docs/cfpb_circular_2022_03_mapping.md`](cfpb_circular_2022_03_mapping.md) — CFPB Circular 2022-03 mapping

---

*Patterns are software, not legal advice. Regulatory citations are reference mappings; consult counsel for applicability to your control environment. Citations flagged [UNVERIFIED] require primary-source confirmation before use in any regulatory submission.*
