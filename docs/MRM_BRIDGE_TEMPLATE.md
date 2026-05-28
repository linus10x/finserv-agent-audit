# MRM Bridge Whitepaper — Agentic-AI Governance Pre-RFI

**A forkable internal whitepaper template for second-line model-risk-management teams.**

This template is designed to be filled in by a bank's second-line MRM function and submitted to the firm's Model Risk Committee, Chief Risk Officer, Audit Committee chair, and (where applicable) the prudential examiner of record as **the documented rationale for adopting `finserv-agent-audit` v1.x as the operational reference for agentic-AI workloads during the period between OCC Bulletin 2026-13 (April 17, 2026) and the finalization of the joint OCC / FRB / FDIC RFI on agentic-AI model risk management.**

Frame: _what you can hand to validation while waiting for the joint RFI._

> **License.** This template is published under the MIT License of the parent framework. Banks are free to fork, adapt, and submit internally without attribution back to the framework.

---

## Title block

| Field | Value |
|---|---|
| **Institution** | _[Bank legal entity name]_ |
| **Whitepaper title** | Adoption of `finserv-agent-audit` v_[X.Y]_ as Operational Reference for Agentic-AI Workloads, Pre-RFI |
| **Document version** | _[v1.0]_ |
| **Date of issue** | _[YYYY-MM-DD]_ |
| **Effective period** | From _[issuance date]_ until the joint OCC / FRB / FDIC RFI on agentic-AI MRM is finalized and adopted by the institution (see Section 6, Sunset Clause). |
| **Author (second-line MRM lead)** | _[Name, title, signature]_ |
| **Approver — Chief Risk Officer** | _[Name, signature]_ |
| **Approver — Chair, Audit Committee** | _[Name, signature]_ |
| **Approver — Head of Model Validation** | _[Name, signature]_ |
| **Examiner of record (if applicable)** | _[Name, agency, exam cycle]_ |
| **Confidentiality classification** | _[e.g. Internal — Privileged Examination Material]_ |

---

## 1. Executive summary

_[Two-paragraph summary, written by the second-line MRM lead. Recommended structure:]_

Paragraph 1: **The supervisory landscape changed on April 17, 2026.** The OCC, Federal Reserve, and FDIC jointly issued revised model-risk-management guidance (OCC Bulletin 2026-13) that rescinded the previous binding instruments and explicitly excluded generative and agentic AI from scope, deferring to a forthcoming joint RFI. Our agentic-AI workloads — _[list workload categories: customer-service triage, fraud-detection orchestration, treasury-operations co-pilot, etc.]_ — are accordingly operating without a binding supervisory model-risk-management framework as of _[date]_.

Paragraph 2: **This whitepaper documents the institution's adoption of `finserv-agent-audit` v_[X.Y]_** (MIT-licensed, public reference, primary-source-mapped) as the operational governance reference for these workloads during the pre-RFI interval. The framework is selected because (a) its design is purpose-fit for agentic AI rather than retrofitted from a credit-scorecard frame; (b) its mapping documentation cross-references the non-MRM regimes (GLBA, SOX § 404 ITGC, SEC 17a-4, OCC Heightened Standards, interagency TPRM final guidance, Treasury FS AI RMF, NIST AI 600-1) that remain in force; and (c) its evidence stack (hash-chain audit log, external witness anchor, WORM ledger) survives any plausible RFI outcome. This adoption sunsets on RFI finalization; the framework's binding-citation references will update accordingly within one minor release.

---

## 2. Regulatory landscape as of _[date]_

### 2.1 What changed on April 17, 2026

On April 17, 2026 the OCC, Federal Reserve Board, and FDIC jointly issued revised model-risk-management guidance. The OCC's instrument is **OCC Bulletin 2026-13, _Model Risk Management: Revised Guidance_**, signed by Senior Deputy Comptroller James M. Gallagher. The bulletin rescinds:

- OCC Bulletin 2011-12 (Sound Practices for Model Risk Management)
- OCC Bulletin 1997-24 (Credit Scoring Models)
- OCC Bulletin 2021-19 (BSA/AML Model Risk Management)
- The Model Risk Management booklet of the Comptroller's Handbook

For Federal Reserve-supervised institutions, the parallel SR letter supersedes SR 11-7. For FDIC-supervised institutions, the parallel FIL supersedes FIL-22-2017's adoption of the 2011 attachment.

### 2.2 The agentic-AI carve-out

OCC Bulletin 2026-13 contains verbatim language (appearing twice):

> "Generative AI and agentic AI models are novel and rapidly evolving. As such, they are not within the scope of this guidance."

The agencies further committed to issuing "a request for information that addresses model risk management generally and considers, in particular, banks' use of AI, including generative AI and agentic AI and AI-based models" in the near future.

### 2.3 Frameworks that remain operational

Despite the MRM rescission, the following remain in force and apply to the institution's agentic-AI workloads:

- **GLBA Safeguards Rule** (16 CFR § 314) — information-security program obligations.
- **SOX § 404 ITGC** — financial-reporting integrity controls where agentic AI touches the general ledger or affects financial-statement assertions.
- **SEC 17a-4(f)** — record-keeping in WORM-equivalent format for broker-dealer workloads.
- **OCC Heightened Standards** (12 CFR Part 30, Appendix D) — governance and risk-appetite framework for large banks.
- **Interagency Third-Party Risk Management Final Guidance** (June 6, 2023) — vendor / external-model governance.
- **Treasury Financial Services Sector AI Risk Management Framework** (February 12, 2026, Cyber Risk Institute / FSSCC; 230 control objectives; 100+ contributing institutions) — the most-mature operational framework for AI in financial services available as of this writing.
- **NIST AI 600-1, Generative AI Profile** (July 26, 2024) — the 12 generative-AI risk categories and the Govern / Map / Measure / Manage action matrix.
- **State-level AI statutes** where applicable to the institution's footprint.

The 2026-13 rescission shifts the binding MRM citation; it does not unwind the control surface.

---

## 3. Framework selection rationale

### 3.1 Selection criteria

The second-line MRM function evaluated candidate references against the following criteria:

1. **Design fit for agentic AI** — the reference must be designed at the shape of agentic AI (state, action, trust-boundary motion), not retrofitted from statistical-model frames.
2. **Primary-source citation discipline** — every regulatory claim in the reference must trace to a verifiable primary source.
3. **License posture** — the reference must permit internal adoption without contractual encumbrance.
4. **Evidence-stack defensibility** — the reference's audit, witness, and record-keeping pattern must survive the most plausible RFI outcomes.
5. **Maintenance posture** — the reference must have a documented plan to update citation lineage when the joint RFI finalizes.

### 3.2 Why `finserv-agent-audit` v_[X.Y]_

| Criterion | `finserv-agent-audit` v1.2 | Alternative reference _[name]_ |
|---|---|---|
| Design fit for agentic AI | Six v1.0 patterns + nine v1.1 hardening modules designed at the shape of agentic AI | _[fill in]_ |
| Primary-source citation discipline | Per-mapping verification; `[UNVERIFIED — primary source not fetched]` hedges where applicable | _[fill in]_ |
| License | MIT | _[fill in]_ |
| Evidence stack | SHA-256 hash-chain audit log + external witness anchor + WORM ledger (jsonl / sqlite / WORM variants) | _[fill in]_ |
| Maintenance posture | Sunset clause documented; citation refresh committed within one minor release of RFI finalization | _[fill in]_ |

### 3.3 Alternative references considered and rejected

_[Fill in. Common alternatives: vendor-proprietary AI governance toolkits with closed licensing; internal-only frameworks that lack public peer review; the legacy 2011 attachment that no longer carries binding citation.]_

---

## 4. Control mapping — framework modules to institution risk taxonomy

This section maps each `finserv-agent-audit` v_[X.Y]_ module to the institution's internal risk taxonomy. Banks should fork this table and replace generic categories with their specific taxonomy (e.g. RCSA categories, ORX taxonomy, internal risk-and-control framework).

| Framework module | Canonical path | Institution risk taxonomy entry | Owning second-line function |
|---|---|---|---|
| `defcon` | `finserv_agent_audit.governance.defcon` | _[e.g. Model-Risk: Autonomy-Degradation]_ | _[MRM]_ |
| `sovereign_veto` | `finserv_agent_audit.governance.sovereign_veto` | _[e.g. Operational-Risk: Human-in-the-Loop Effective Challenge]_ | _[MRM + Operational Risk]_ |
| `autonomy_ladder` | `finserv_agent_audit.governance.autonomy_ladder` | _[e.g. Model-Risk: Scope of Agentic Action]_ | _[MRM]_ |
| `audit_chain` | `finserv_agent_audit.governance.audit_chain` | _[e.g. Operational-Risk: Evidence Pipeline]_ | _[Internal Audit + MRM]_ |
| `shadow_mode` | `finserv_agent_audit.governance.shadow_mode` | _[e.g. Model-Risk: Conceptual-Soundness Validation]_ | _[Model Validation]_ |
| `ledger_store` (jsonl / sqlite / WORM) | `finserv_agent_audit.governance.ledger_store_*` | _[e.g. Records-Management: Audit Retention]_ | _[Records Mgmt + Compliance]_ |
| `timestamp_source` | `finserv_agent_audit.governance.timestamp_source` | _[e.g. Information-Security: Trusted Time]_ | _[InfoSec]_ |
| `witness_anchor` | `finserv_agent_audit.governance.witness_anchor` | _[e.g. Internal-Audit: Cross-Verification]_ | _[Internal Audit]_ |
| `mi_proxy` | `finserv_agent_audit.governance.mi_proxy` | _[e.g. Model-Risk: Implementation-Integrity Control]_ | _[MRM]_ |
| `vendor_score_gate` | `finserv_agent_audit.governance.vendor_score_gate` | _[e.g. Third-Party-Risk: Model-Vendor Governance]_ | _[TPRM]_ |
| `model_inventory` | `finserv_agent_audit.governance.model_inventory` | _[e.g. Model-Risk: Inventory and Lifecycle]_ | _[MRM]_ |
| `adverse_action_gate` | `finserv_agent_audit.governance.adverse_action_gate` | _[e.g. Compliance: FCRA/ECOA Adverse Action]_ | _[Compliance]_ |
| `sar_workflow_audit` | `finserv_agent_audit.governance.sar_workflow_audit` | _[e.g. Financial-Crimes: BSA/AML SAR Workflow]_ | _[BSA/AML]_ |
| `equity_audit` | `finserv_agent_audit.governance.equity_audit` | _[e.g. Fair-Lending: ECOA/HMDA Equity]_ | _[Fair Lending]_ |
| `best_interest_check` | `finserv_agent_audit.governance.best_interest_check` | _[e.g. Compliance: Reg BI]_ | _[Compliance]_ |

---

## 5. Pre-deployment and ongoing-monitoring evidence

The institution will maintain the following evidence artefacts for every agentic-AI workload governed under this whitepaper:

1. **Model-inventory entry** — populated via `finserv_agent_audit.governance.model_inventory`, including lifecycle state, last validation date, owning business line, and second-line MRM reviewer.
2. **Audit-chain ledger** — per-workload SHA-256 hash-chain ledger via `finserv_agent_audit.governance.audit_chain` and the chosen `ledger_store_*` backend, with retention per the institution's records-management policy (minimum: seven years from model retirement; the framework's `0017-audit-chain-retention-privilege-discovery` ADR documents the analysis).
3. **Witness-anchor receipts** — per-period external anchor receipts via `finserv_agent_audit.governance.witness_anchor` and `finserv_agent_audit.governance.rfc3161_codec` (RFC 3161 TSA backend).
4. **MI-proxy attestation log** — per-deployment verifier-integrity attestation via `finserv_agent_audit.governance.mi_proxy`, with asymmetric attestation (SLSA or Sigstore) where the verifier is consumed by an external auditor or regulator.
5. **Shadow-mode promotion record** — for every workload that transitioned from A0 / A1 to a higher autonomy level via shadow-mode evaluation per `finserv_agent_audit.governance.shadow_mode`.
6. **DEFCON state log** — per-workload autonomy-degradation state-machine log via `finserv_agent_audit.governance.defcon`, with hysteresis evidence per ADR-0001.
7. **Vendor-score-gate record** — for every third-party / pre-trained model component, vendor governance evidence per `finserv_agent_audit.governance.vendor_score_gate` consistent with the interagency TPRM final guidance.

---

## 6. Governance and sign-off

This whitepaper is approved by:

| Role | Name | Signature | Date |
|---|---|---|---|
| Second-line Model-Risk-Management Lead | | | |
| Head of Model Validation | | | |
| Chief Risk Officer | | | |
| Chair, Audit Committee | | | |
| Chief Compliance Officer (concur) | | | |
| Chief Information Security Officer (concur) | | | |
| General Counsel (legal-sufficiency review) | | | |

The whitepaper will be reviewed annually on its anniversary date and on any of the following triggers: (a) issuance of the joint OCC / FRB / FDIC RFI; (b) finalization of new guidance superseding OCC Bulletin 2026-13; (c) material change to the framework version adopted; (d) material change to the institution's agentic-AI workload portfolio; (e) examiner direction.

---

## 7. Sunset clause

**This whitepaper sunsets when the joint OCC / FRB / FDIC RFI on agentic AI MRM is finalized; the framework references update accordingly.**

On RFI finalization, the second-line MRM function will:

1. Receive the upstream framework citation refresh (committed within one minor release of RFI finalization).
2. Re-map the institution's risk taxonomy table (Section 4) against the finalized guidance.
3. Re-issue this whitepaper with updated binding-citation references.
4. Notify the Model Risk Committee, the Audit Committee, and the examiner of record of the re-issuance.
5. Retire this version of the whitepaper to the institution's records-management archive per the standard records-retention schedule.

---

## 8. References

- Office of the Comptroller of the Currency. _OCC Bulletin 2026-13: Model Risk Management — Revised Guidance._ April 17, 2026.
- Cyber Risk Institute. _Financial Services AI Risk Management Framework._ February 12, 2026.
- NIST. _NIST AI 600-1: AI Risk Management Framework — Generative AI Profile._ July 26, 2024.
- `finserv-agent-audit` v_[X.Y]_ — `docs/interagency_mrm_2026_overlay.md`, `docs/treasury_fs_ai_rmf_mapping.md`, `docs/nist_ai_600_1_genai_profile_mapping.md`, `ASSURANCE-GUIDE.md`, `DEPLOY-CHECKLIST.md`, and the per-regime mapping documents under `docs/`.
- Institution-internal: _[risk-appetite framework, model-risk policy, records-management policy, third-party-risk-management policy]_.
