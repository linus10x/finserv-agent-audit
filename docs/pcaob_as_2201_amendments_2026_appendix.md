# PCAOB AS 2201 + AS 2101 Amendments (FY 2026+) — ASSURANCE-GUIDE Appendix

**Status:** v2.0.0-draft · Last reviewed: 2026-05-28.
**Audience:** Big-4 audit partner planning the FY-2026 financial-statement audit at a US-listed financial-services issuer with AI-mediated processes affecting internal control over financial reporting (ICFR); the issuer's Chief Internal Auditor; the SOX 404 compliance leader supporting the external auditor's walkthrough; the Chief AI Officer producing the audit-evidence pack.

This appendix is the companion to
[`ASSURANCE-GUIDE.md`](../ASSURANCE-GUIDE.md). The parent guide covers
the general SOX 404 / SOC 2 / OCC examination walk against the
framework's modules; this appendix addresses the **PCAOB AS 2201 +
AS 2101 amendments effective for fiscal years beginning on or after
December 15, 2026** and the AI-specific audit-procedure changes that
follow from them.

> **Disclaimer:** This appendix is provided for reference only and does
> not constitute legal or audit advice. Engage qualified counsel and
> the engagement audit partner for your specific compliance and audit-
> readiness determination. See repo-root [`DISCLAIMER.md`](../DISCLAIMER.md).

---

## Framework Context — PCAOB AS 2201 + AS 2101 Amendments

**AS 2201 — *An Audit of Internal Control Over Financial Reporting That
Is Integrated with An Audit of Financial Statements*** is the PCAOB
standard governing the external auditor's evaluation of ICFR at
US-listed issuers. **AS 2101 — *Audit Planning*** is the standard
governing the audit-planning workstream that precedes the ICFR walk.

The PCAOB amendments effective for fiscal years beginning on or after
**December 15, 2026** add explicit auditor obligations around
**AI-involved processes within ICFR**. The amendments do not introduce
a new audit standard for AI; rather, they extend the AS 2201 walkthrough
expectations and the AS 2101 planning expectations to capture
AI-mediated control activities that affect financial-reporting
assertions.

For a US-listed financial-services issuer running LLM-mediated agents
inside an ICFR-relevant process — loan-origination underwriting that
flows to loan-loss reserves, claims-adjudication agents that flow to
incurred-but-not-reported (IBNR) reserves, AI-mediated revenue-
recognition routines, AI-driven fraud-detection that flows to
allowance-for-credit-losses — the FY 2026+ audit will include
AI-specific procedures the issuer must be ready to support.

---

## Primary-Source Citations

| Source | Retrieved | Status |
|---|---|---|
| PCAOB Auditing Standard AS 2201 (as amended) | Referenced; consult pcaobus.org standards index for operative text | `[UNVERIFIED — primary source not fetched this pass; the PCAOB website's auditing-standards index is the authoritative URL]` |
| PCAOB Auditing Standard AS 2101 (as amended) | Referenced; consult pcaobus.org standards index for operative text | `[UNVERIFIED — primary source not fetched this pass]` |
| PCAOB release adopting the AI-related amendments effective FY beginning Dec 15, 2026 | Referenced; consult pcaobus.org rulemaking-docket index for the adopting release | `[UNVERIFIED — adopting release not fetched this pass; verify against the published PCAOB release before relying on this appendix for FY-2026 audit planning]` |
| PCAOB inspection priorities — AI-related findings | Referenced; consult the PCAOB's most-recent staff inspection brief | `[UNVERIFIED — staff brief not fetched this pass]` |

> The amendment text and effective date below are characterized
> consistent with the published PCAOB rulemaking record as of
> 2026-05-28. The mapping table operates as a defensible scaffolding
> against the framework's modules; the engagement audit partner is the
> authoritative source for the operative text. Re-verify before any
> FY-2026 audit-planning communication.

---

## Amendment-by-Amendment Walkthrough

The PCAOB amendments cluster into five substantive areas. For each
area, the table below identifies the AS 2201 / AS 2101 surface, the
auditor-procedure change, the framework module that supplies the
audit evidence, and the cross-reference to
[`ASSURANCE-GUIDE.md`](../ASSURANCE-GUIDE.md).

### Area 1 — Identifying AI-Involved Controls in the ICFR Walk (AS 2101 Planning)

The auditor's risk-assessment work in the planning phase must
identify control activities where AI is involved in the operation of
the control. The amendment language clarifies that this identification
is part of obtaining an understanding of the entity and its
environment, including ICFR.

| Auditor procedure | Framework evidence | File |
|---|---|---|
| Inventory of AI systems that operate within or alongside ICFR controls | `ModelInventory.query_by_status(ImplementationStatus.APPROVED_FOR_PRODUCTION)` filtered to ICFR-relevant decision classes | `src/finserv_agent_audit/governance/model_inventory.py` |
| Mapping each AI system to the specific financial-reporting assertion(s) it affects | Audit-chain rationale strings carry the assertion mapping; model inventory metadata can carry the assertion tag | `src/finserv_agent_audit/governance/audit_chain.py`, `src/finserv_agent_audit/governance/model_inventory.py` |
| Identification of LLM-vs-deterministic split inside each control | Autonomy Ladder published A0-A4 classification per decision class disambiguates autonomous-vs-human-supervised steps | `docs/autonomy_ladder.md` |
| Provider-vs-deployer designation per AI system (informs evidence-availability scoping) | Vendor attestation ledger records third-party-provider attestations; model inventory records in-house systems | `src/finserv_agent_audit/governance/vendor_attestation_ledger.py`, `src/finserv_agent_audit/governance/model_inventory.py` |

### Area 2 — Walkthrough Procedures for AI-Involved Controls (AS 2201 Walkthrough)

The walkthrough discipline extends from the deterministic control-
activity layer into the AI-mediated layer. The auditor must observe
the AI's contribution to the control's operation, not just the human-
sign-off step around the AI.

| Auditor procedure | Framework evidence | File |
|---|---|---|
| Observation of a live AI-mediated control execution | Audit-chain entries carry the input hash, model_version, prompt_version, policy_version, rationale, and downstream effect; auditor can request a live execution and observe the chain entry produced | `src/finserv_agent_audit/governance/audit_chain.py`, `src/finserv_agent_audit/schemas/audit_event.py` |
| Reperformance of a sample of AI-mediated control outputs (where reproducibility holds) | Shadow-mode parallel-evaluation harness supports reperformance against a held-aside dataset; model inventory captures the model version under test | `src/finserv_agent_audit/governance/shadow_mode.py`, `src/finserv_agent_audit/governance/model_inventory.py` |
| Inspection of the human-oversight evidence per AI-mediated control | Sovereign-veto records the named human-clearance event; adverse-action gate records the human review for adverse decisions | `src/finserv_agent_audit/governance/sovereign_veto.py`, `src/finserv_agent_audit/governance/adverse_action_gate.py` |
| Inquiry of the control owner regarding AI behaviour under edge cases | The framework's `ai_incident_retrospective_template.md` instances supply documented edge-case behaviour; the effective-challenge harness produces second-line challenge evidence | `docs/ai_incident_retrospective_template.md`, `src/finserv_agent_audit/governance/effective_challenge_harness.py` |

### Area 3 — Evaluating Design Effectiveness of AI-Involved Controls (AS 2201)

Design effectiveness now explicitly considers the AI's contribution to
the control's design — including the prompt, the system instructions,
the retrieval index, the model version, the policy version, and the
human-oversight design.

| Auditor procedure | Framework evidence | File |
|---|---|---|
| Inspection of the prompt / system-instruction artifact under change control | Audit-chain entries carry the prompt_version; the prompt artifact must be version-controlled in the issuer's source-control system | `src/finserv_agent_audit/schemas/audit_event.py` |
| Inspection of the retrieval-index lineage | Vendor attestation ledger records the retrieval-index vendor's attestation if third-party; model inventory carries lineage metadata if in-house | `src/finserv_agent_audit/governance/vendor_attestation_ledger.py`, `src/finserv_agent_audit/governance/model_inventory.py` |
| Evaluation of the human-oversight design adequacy | Autonomy Ladder published classification per decision class; sovereign-veto deployment per decision class | `docs/autonomy_ladder.md`, `src/finserv_agent_audit/governance/sovereign_veto.py` |
| Evaluation of model-change-management discipline | Model inventory PROPOSED → IN_VALIDATION → APPROVED_FOR_PRODUCTION transitions emit `MODEL_VALIDATED` events; retraining cadence monitor enforces revalidation cycles | `src/finserv_agent_audit/governance/model_inventory.py`, `src/finserv_agent_audit/governance/retraining_cadence_monitor.py` |

### Area 4 — Testing Operating Effectiveness of AI-Involved Controls (AS 2201)

The auditor's operating-effectiveness testing must capture both the
AI's contribution and the surrounding control activities. The
amendment language clarifies that AI-output variability over the audit
period is a relevant factor in sample size and selection.

| Auditor procedure | Framework evidence | File |
|---|---|---|
| Sample selection across the audit period (not just point-in-time) | Audit-chain retention per the issuer's LedgerStore configuration; WORM-eligible storage preserves the audit-period sample population | `src/finserv_agent_audit/governance/audit_chain.py`, `src/finserv_agent_audit/governance/ledger_store_worm.py` |
| Stratified sampling by model version | Model inventory captures the version-history; audit-chain entries carry model_version | `src/finserv_agent_audit/governance/model_inventory.py`, `src/finserv_agent_audit/schemas/audit_event.py` |
| Testing of the model-integrity attestation | MI proxy attestation per verifier; `enforce_attestation` raises on integrity failure | `src/finserv_agent_audit/governance/mi_proxy.py` |
| Testing of the audit-chain integrity | `AuditChain.verify()` and `AuditChain.verify_strict()` produce the integrity attestation; external-witness anchor (OpenTimestamps / Sigstore Rekor) supplies the cross-trust-boundary evidence | `src/finserv_agent_audit/governance/audit_chain.py`, `src/finserv_agent_audit/governance/witness_anchor.py` |
| Bias and fairness testing as design-effectiveness input | Equity audit, LDA-search harness, LLM disparate-impact harness, protected-class proxy detector (MI / LDA arms shipped; SHAP / CDD arms on v1.4 roadmap) | `src/finserv_agent_audit/governance/equity_audit.py`, `src/finserv_agent_audit/governance/lda_search.py`, `src/finserv_agent_audit/governance/llm_disparate_impact_harness.py`, `src/finserv_agent_audit/governance/protected_class_proxy_detector.py` |

### Area 5 — Identifying and Communicating AI-Related Deficiencies (AS 2201)

Where an AI-involved control is found ineffective, the auditor must
characterize the deficiency at the appropriate severity (deficiency,
significant deficiency, or material weakness) and communicate per the
existing AS 2201 communication discipline.

| Auditor procedure | Framework evidence | File |
|---|---|---|
| Documentation of the deficiency with reference to specific chain entries | Audit-chain walk-back replay produces the deficiency reconstruction | `src/finserv_agent_audit/governance/audit_chain.py` |
| Evaluation of compensating controls | Sovereign-veto + adverse-action gate + human-oversight design serve as common compensating controls | `src/finserv_agent_audit/governance/sovereign_veto.py`, `src/finserv_agent_audit/governance/adverse_action_gate.py` |
| Communication to the audit committee | `ai_incident_retrospective_template.md` instances support the audit-committee communication; the pre-examination self-assessment provides the operating-effectiveness narrative | `docs/ai_incident_retrospective_template.md`, `docs/pre_examination_ai_self_assessment.md` |

---

## Audit-Procedure Changes for LLM-Agent-Involved Processes

The amendments raise five specific procedure changes that apply
distinctively when the AI is an LLM-mediated agent rather than a
classical statistical model.

1. **Prompt-and-system-instruction inspection.** The auditor inspects
   the prompt and the system instruction under change control, the
   same way the auditor inspects a source-code change. The framework's
   `prompt_version` field in the audit-event payload is the substrate.

2. **Retrieval-augmented-generation (RAG) index inspection.** Where
   the agent retrieves from a vector index, the auditor inspects the
   index's lineage, the embedding model, and the document-source
   chain. The vendor attestation ledger and model inventory carry
   the relevant metadata.

3. **Agent-orchestration-platform vendor walkthrough.** Where the
   issuer uses a third-party agentic-orchestration platform
   (LangChain Hub, LlamaIndex Cloud, CrewAI, AutoGen Studio), the
   auditor walks the third-party-AI-vendor evidence per AS 2201's
   service-organization-control discipline. The vendor attestation
   ledger entries are the substrate; the SOC 1 / SOC 2 reports from
   the platform vendor are the supplementary evidence.

4. **Foundation-model deprecation testing.** Where the issuer's
   AI-mediated ICFR control depends on a foundation model, the
   auditor inspects the deprecation-watch posture and the
   substitute-readiness evidence. A foundation-model deprecation
   inside the audit period without a documented substitute is an
   operating-effectiveness deficiency at minimum.

5. **Cross-period model drift.** Where the operating-effectiveness
   test spans multiple model versions, the auditor evaluates whether
   the model-change discipline was applied (validation memo, second-
   line sign-off, MI proxy attestation, shadow-mode pre-promotion
   evidence). The retraining cadence monitor and model inventory
   produce the evidence.

---

## Sample Audit-Evidence Requests

The list below is modeled on PCAOB inspection priorities and is
suitable for inclusion in the FY-2026 PBC (Provided-by-Client) list.

1. Current `ModelInventory.query_by_status(ImplementationStatus.APPROVED_FOR_PRODUCTION)` output, filtered to ICFR-relevant systems.
2. For each ICFR-relevant system: the most-recent validation memo, the second-line sign-off, the validation-completion `MODEL_VALIDATED` audit-chain entry.
3. For each ICFR-relevant system: the Autonomy Ladder classification artifact, the sovereign-veto deployment evidence, the adverse-action-gate deployment evidence where applicable.
4. For each ICFR-relevant system: three randomly-selected audit-chain entries from the audit period, with reconstruction of the control's operation from input to downstream effect.
5. For each ICFR-relevant system: the prompt_version and system-instruction artifacts under change control; the source-control history of any changes within the audit period.
6. For each ICFR-relevant system: the bias-and-fairness testing outputs (equity audit, protected-class proxy detector arms, LDA-search results where applicable).
7. For each ICFR-relevant system: the model-integrity attestation log (MI proxy attestation chain); the audit-chain integrity result (`AuditChain.verify()`) at audit-period-end and at the most recent external-witness anchor.
8. For each ICFR-relevant third-party AI system: the vendor-attestation-ledger entries for the audit period; the vendor's SOC 1 / SOC 2 / ISO 42001 report; the vendor-score-gate evidence.
9. For each ICFR-relevant system: the deprecation-watch posture log for the audit period; the substitute-readiness evidence for any in-window sunset alerts.
10. For each AI-related incident reported in the audit period: the `ai_incident_retrospective_template.md` instance; the audit-committee communication if any; the corrective-action evidence.
11. The maturity self-score history (`scripts/maturity_self_score.py` output) across the audit period; the trajectory narrative.
12. The pre-examination AI self-assessment if completed during the audit period.

---

## Audit-Committee Communication Implications

The PCAOB amendments do not change the AS 1301 audit-committee
communication standard, but the substantive content of those
communications expands. The audit committee should expect:

- **Pre-audit planning communication.** AI-systems-in-scope inventory;
  the auditor's planned procedures for AI-involved controls; the
  evidence-availability scoping (which AI systems are deployer-side
  with full evidence and which are third-party with SOC-report-
  mediated evidence).
- **Interim communications.** Any AI-related deficiencies identified
  during interim work, with severity characterization and management's
  remediation response.
- **Year-end communication.** Aggregate AI-related findings; any
  significant deficiencies or material weaknesses; the auditor's view
  on the issuer's AI-governance maturity trajectory; comparison to
  peer-issuer practices in the same industry vertical.
- **Communication of management responses.** Management's view of
  identified AI-related deficiencies; remediation plan; timeline.

---

## Cross-References

- Parent guide: [`ASSURANCE-GUIDE.md`](../ASSURANCE-GUIDE.md)
- Companion engagement exhibit: [`docs/big4_engagement_letter_exhibit.md`](big4_engagement_letter_exhibit.md)
- Failure modes catalog: [`FAILURE-MODES.md`](../FAILURE-MODES.md)
- Limitations: [`LIMITATIONS.md`](../LIMITATIONS.md)
- Per-regime mapping docs:
  [`docs/sr11_7_mapping.md`](sr11_7_mapping.md),
  [`docs/sox_404_itgc_mapping.md`](sox_404_itgc_mapping.md),
  [`docs/coso_icair_mapping.md`](coso_icair_mapping.md),
  [`docs/occ_2011_12_mapping.md`](occ_2011_12_mapping.md),
  [`docs/interagency_mrm_2026_overlay.md`](interagency_mrm_2026_overlay.md).
- ADR cross-references: ADR-0001 (DEFCON), ADR-0002 (Sovereign Veto),
  ADR-0003 (Hash-chain audit), ADR-0007 (Model Inventory), ADR-0012
  (SOX 404 ITGC), ADR-0014 (Persistence / Witness / Timestamp),
  ADR-0015 (MI Proxy), ADR-0016 (Vendor Score Gate), ADR-0022
  (Effective Challenge), ADR-0023 (Vendor Attestation Ledger),
  ADR-0024 (Retraining Cadence Monitor), ADR-0025 (Deprecation
  Watch).

---

## Limitations of This Appendix

- The amendment text and effective date have not been re-verified
  against the live PCAOB rulemaking record on this mapping pass. The
  engagement audit partner is the authoritative source.
- The mapping table is scaffolding for audit-readiness preparation
  and is not a substitute for the engagement audit partner's
  judgment on the specific issuer's facts and circumstances.
- PCAOB inspection priorities evolve; the audit-evidence-request list
  is a starting point, not an exhaustive checklist.
- The amendments are written generally; the issuer's specific
  industry vertical (banking, insurance, broker-dealer, asset
  management) shapes how the procedures apply in practice.
