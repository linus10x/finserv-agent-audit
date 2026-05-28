# Vendor Clauses — Foundation-Model API Vendors for AI Governance under finserv-agent-audit v1.3

## Purpose

This document is a procurement companion intended for direct insertion into vendor contracts, MSAs, SOWs, and RFP responses with foundation-model API providers (Anthropic, OpenAI, Google, Mistral, Cohere, AWS Bedrock, Azure OpenAI, and equivalent providers). It aligns vendor obligations with the audit-chain, `VendorAttestationLedger`, `RetrainingCadenceMonitor`, and `DeprecationWatch` framework that finserv-agent-audit v1.3 adopters operate, and translates the Adopter's regulatory exposure across SR 11-7 / OCC Bulletin 2026-13, BSA / AML, FCRA / ECOA, SEC Reg-BI, DORA, and the Treasury FS AI RMF into vendor-side performance, disclosure, and cooperation duties.

The clause set assumes the Adopter is a US-regulated financial institution consuming foundation-model APIs across multiple decision surfaces (customer-facing chatbots, internal copilots, document-processing pipelines, narrative-generation supporting BSA/AML SAR-filing flows, decision-support augmenting Reg-BI recommendations, KYC document-verification augmentation). It is the sixth FSI vendor-clauses document and the first that covers a vendor class whose primary product is the model itself, not a scoring output. This is the v1.3 close on the OCC 2026-13 scope-exclusion gap from the procurement side; the runtime companions are `vendor_attestation_ledger.py`, `retraining_cadence_monitor.py`, and `deprecation_watch.py`.

## Scope

Covers vendor outputs used in:

- Generative-text completion (chat, structured output, tool-use chains)
- Embedding-vector generation for retrieval-augmented workflows
- Document understanding (vision-text fusion on KYC documents, statements, contracts)
- Narrative generation supporting regulated-decision documentation (SAR narratives, adverse-action explanations, Reg-BI recommendation rationales)
- Internal employee copilots accessing customer data
- Fine-tuned adapter pipelines on the Adopter's data
- Agentic workflows where the model executes tools on the Adopter's behalf

Regulatory frameworks the vendor's outputs touch on the Adopter's side: SR 11-7 / OCC Bulletin 2026-13 (model risk management; generative + agentic AI scope-excluded pending joint RFI but the operator's exposure persists); BSA (31 U.S.C. § 5311 et seq.) and SAR-filing rule (31 C.F.R. § 1020.320) when the model contributes to narrative or alert disposition; FCRA Section 615 (15 U.S.C. § 1681m) when the model contributes to adverse-action narrative; ECOA / Regulation B (15 U.S.C. § 1691; 12 C.F.R. § 1002) for any credit-decision-adjacent use; SEC Regulation Best Interest and FINRA Rule 2111 for any investment-recommendation-adjacent use; GLBA Safeguards Rule (16 C.F.R. Part 314) for customer NPI handling; DORA (Regulation (EU) 2022/2554) Article 28 and Commission Delegated Regulation 2024/1773 RTS on subcontracting for EU-supervised Adopters; Treasury FS AI RMF (February 2026) and the Cyber Risk Institute FS AI RMF (February 2026, 108 contributing institutions) for third-party + fourth-party AI oversight; NIST AI 600-1 § "Value Chain and Component Integration" as the cross-cutting US-side reference; EU AI Act (Regulation (EU) 2024/1689) Annex III obligations for high-risk use cases the foundation model serves.

## Clause 1 — Audit-Chain Emit Requirements

Vendor SHALL emit, for every API call returned to Adopter:

- Vendor identifier (stable across requests)
- Request identifier (vendor-side correlation ID)
- Model identifier (vendor-side stable model name and version pin)
- Input-content hash (SHA-256 of the canonical, ordered input payload; vendor publishes the canonicalization spec)
- Output-content hash (SHA-256 of the canonical, ordered output payload)
- Endpoint identifier (Zero Data Retention endpoint or standard endpoint; see Clause 5.i)
- Sub-processor route (if the call was served by a deployment partner — Anthropic-on-Bedrock, Anthropic-on-Vertex, OpenAI-on-Azure)
- Timestamp (ISO 8601 UTC)
- Token counts (input, output, cached, and reasoning tokens where applicable)

These fields are consumed by Adopter's audit-chain pipeline and stored alongside any operator-side `VendorScoreGate` entries (ADR-0016) that wrap the call. Vendor acknowledges that incomplete emissions degrade the Adopter's FFIEC examination posture, the Adopter's SR 11-7 / OCC 2026-13 evidence trail, and any regulator-driven discovery request, and that completeness is a contract-grade obligation, not a best-effort target.

## Clause 2 — Model Version Pinning + Drift Disclosure

Vendor SHALL:

- Publish a stable semantic-version identifier for every production model surface; the version identifier MUST change on any change that alters the model's outputs in a manner observable on Adopter's evaluation suite
- Maintain a vendor-side `material_change_log` exposed to Adopter on request and updated within 5 business days of any production model-version change
- Provide model-card-grade documentation per Mitchell et al. (2019) for each version: training-data sources and provenance to the extent legally and commercially disclosable, evaluation metrics on standard safety and capability benchmarks, known limitations, and out-of-distribution behavior summaries
- Notify Adopter no less than 30 calendar days before any production model-version change that materially shifts capability or safety behavior; 90 calendar days when the change affects models used in FCRA-, ECOA-, BSA-, or Reg-BI-touched decision surfaces (the decision surfaces governed by Adopter's `ModelInventory` entry)
- Cooperate in version-change post-mortems when Adopter's `RetrainingCadenceMonitor` (ADR-0024) or `VendorScoreGate` (ADR-0016) surfaces drift attributable to the version change
- Provide a 30-day rollback option on the prior model version so Adopter can re-process a contested cohort under the prior model

## Clause 3 — Reproducibility on Request

For any model output Adopter relied upon in a regulated decision, Adopter MAY request:

- The exact model identifier and version active at the time of the call
- The exact input payload (subject to Adopter-side tokenization if the input contains NPI Adopter is contractually obligated to mask before vendor receipt)
- The exact output payload
- The endpoint variant served (Zero Data Retention or standard)
- The sub-processor route
- A reproducibility statement: under what conditions running the same input on the same version returns the same output (deterministic-mode flag where the vendor surface supports one; otherwise the documented variance band)

Vendor SHALL provide the reproducibility package within 10 business days of an Adopter audit, regulatory examination, or subpoena. Vendor SHALL provide it within 3 business days when the requesting authority is FinCEN under a 314(a) request, OFAC under a blocking-action inquiry, the SEC under a Reg-BI examination, or the CFPB under an adverse-action-notice review.

## Clause 4 — SR 11-7 / OCC Bulletin 2026-13 Pass-Through

Vendor's foundation models constitute "models" under SR 11-7 / OCC Bulletin 2011-12, and the operator's SR 11-7 / OCC 2026-13 obligations persist notwithstanding the OCC 2026-13 scope-exclusion of generative + agentic AI pending the joint RFI. Vendor SHALL:

- Maintain SR 11-7-grade model-development documentation (theoretical construction, intended use, conceptual soundness, training-data provenance to the extent disclosable, evaluation methodology)
- Subject every production model to independent second-line model-safety review at least annually; conduct red-team evaluation cycles on safety-critical capabilities (jailbreak resistance, prompt-injection defense, NPI-extraction resistance, generation of disallowed content, agentic-misuse pathways)
- Provide `VendorAttestationLedger`-compatible metadata for each independent attestation: `attesting_entity`, `version`, `attestation_hash`, `valid_from`, `valid_until`, `evidence_url` — sufficient for Adopter to record into the ledger (ADR-0023) without operator-side curation
- Make Vendor's most recent independent safety-evaluation report available under NDA for Adopter's second-line model-risk-management function and third-line internal audit
- Furnish, on examiner request, the validation report or a counsel-mediated summary sufficient to satisfy SR 11-7 / OCC 2026-13 governance review
- Cooperate with Adopter's `EffectiveChallengeHarness` (ADR-0022 in v1.3) when Adopter exercises the SR 11-7 effective-challenge requirement against a frontier-model primary surface

## Clause 5 — Foundation-Model API Specific Obligations

Vendor SHALL:

### (i) Zero Data Retention (ZDR) endpoint mandate

Provide a Zero Data Retention endpoint variant for any API call routed by Adopter for Reg-BI, BSA / AML, FCRA, ECOA / Reg B, or GLBA-touched workflows. The ZDR variant SHALL guarantee that input and output payloads are not retained beyond the operational window required to return the response; in no event longer than 30 days for diagnostic purposes, and only when the diagnostic-retention path is contractually disclosed and Adopter has opted in. Default for the regulated surfaces above is opt-out of all diagnostic retention.

### (ii) Model version pinning — stable identifiers, semver-style

Publish stable semantic-version identifiers (or content-addressed SHA pins where the deployment surface supports them) for every production model. Adopter selects the pin in the API call; Vendor SHALL honor the pin for the duration of the pin's published support window. A pin that has been deprecated MUST continue to return responses (with a deprecation header on each response) for the remainder of the contractually-disclosed support window per Clause 5.iii.

### (iii) Deprecation-notice minimum: 180 days; tiered election

Set the contractual deprecation-notice floor at 180 calendar days. Adopter MAY elect a notice tier — 90 days, 120 days, or 180 days — at contract execution and at each annual renewal; the 180-day tier is the default for any model used in FCRA-, ECOA-, BSA-, or Reg-BI-touched surfaces. The notice tier SHALL be enforced regardless of any general "models may be deprecated at any time" terms-of-service clause. The Adopter's `DeprecationWatch` harness (ADR-0025) consumes Vendor's changelog as the operational verification of the contractual notice.

### (iv) Audit-report cadence: annual SOC 2 Type II; independent safety audit at tier-up

Maintain SOC 2 Type II on an annual cycle and make the report available to Adopter under NDA within 30 days of issuance. At Adopter's election (and at Adopter's expense for any tier-up beyond the standard offering), Vendor SHALL commission an independent third-party model-safety audit and provide the resulting report to Adopter under NDA within 30 days of issuance.

### (v) Sub-processor disclosure: full list including fine-tuning vendors and data-processing locales

Disclose the full list of sub-processors at contract execution and update within 30 days of any change. The disclosure SHALL include: deployment partners (AWS Bedrock, Azure, Vertex), any fine-tuning sub-processors, any human-feedback labeling vendors, any safety-evaluation contractors, and the data-processing locales (country and US state where applicable) for each sub-processor. The fourth-party disclosure cadence aligns with DORA RTS on subcontracting (Commission Delegated Regulation 2024/1773).

### (vi) Fine-tuning data segregation

Guarantee contractually that Adopter's fine-tuning data, any prompts containing Adopter-side NPI, and any data submitted to the vendor under a fine-tuning or knowledge-base ingestion path is NOT used for general model training, evaluation, benchmarking, or product improvement without Adopter's prior express written consent. Default posture is full segregation; any opt-in path is a contract amendment, not a default.

### (vii) Vendor cooperation with Adopter's SR 11-7 second-line model validation team

Cooperate with Adopter's second-line model-risk-management function in providing model-card-grade documentation, safety-evaluation results, and a vendor-side point of contact qualified to answer second-line technical questions. Vendor's cooperation SHALL extend to written responses to second-line questionnaires within 15 business days, and to live working sessions with Adopter's second line at a cadence not less than annually.

### (viii) Termination + data continuity

On termination for any reason, Vendor SHALL:

- Continue serving inference requests on then-pinned model versions for in-flight Reg-BI cases, BSA / AML investigations, FCRA-touched adverse-action workflows, and any litigation-hold workflows for 365 days post-termination
- Provide a final dump of all audit-chain emissions (Clause 1 fields) for Adopter's compliance retention period — default 5 years post-customer-closure for BSA/AML records (31 C.F.R. § 1010.430) and 7 years where SEC Rule 17a-4 applies to Adopter
- Provide all vendor-side independent safety-evaluation reports issued during the contract term, as a final attestation drop into the Adopter's `VendorAttestationLedger`
- Surrender or destroy Adopter's fine-tuning data, any retained input payloads from non-ZDR endpoints, and any vendor-side derived data per the data-retention schedule in the MSA and provide a certificate of destruction

## Clause 6 — Audit and Right to Examine

Adopter MAY, on 30 days' written notice (reduced to 5 days for regulator-driven audits), audit Vendor's:

- Model-safety evaluation procedures and the most recent independent safety-audit reports
- Sub-processor list and the contractual safeguards in place with each sub-processor
- ZDR endpoint enforcement (technical attestation that calls routed to ZDR endpoints leave no residual payload data)
- Fine-tuning data segregation controls
- Deprecation-notice cadence against the contractually-elected tier
- Audit-chain emission completeness against a sampled set of Adopter calls
- SOC 2 Type II, ISO 27001, ISO 42001 (where Vendor has obtained it), FedRAMP (where Vendor serves federal-aligned surfaces), HITRUST (where Vendor serves health-finance crossover surfaces), and any SR 11-7-aligned independent model-validation attestation
- Incident-response procedures, including the procedure for notifying Adopter of any safety incident, jailbreak-publication event, or capability change that materially shifts risk profile

Vendor SHALL cooperate at Vendor's reasonable expense; Adopter bears travel and out-of-pocket only.

## Clause 7 — Disclosure to Regulators

Vendor acknowledges that Adopter is subject to examination by Adopter's federal functional regulator (OCC, FRB, FDIC, NCUA), state regulators (including NYDFS), the SEC and FINRA where applicable, FinCEN, OFAC, the CFPB, and (for EU-supervised entities) the European supervisory authorities under DORA, and that Adopter MAY disclose Vendor's outputs, model documentation, safety-evaluation reports, sub-processor disclosures, deprecation-notice records, fine-tuning data segregation attestations, and audit-chain emissions to:

- Federal, state, and EU supervisory examiners
- External auditors (Big-4 firms acting on Adopter's behalf in financial-statement, SOX, BSA/AML-program, or DORA-compliance audit capacities)
- Outside counsel (for privileged review preceding any required disclosure)
- FinCEN under 31 U.S.C. § 5318(g)(2), OFAC under blocking-action inquiry, the SEC under Reg-BI examination, and the CFPB under adverse-action-notice review

Such disclosure does not constitute waiver of Vendor's trade secrets in jurisdictions recognizing the regulatory-disclosure privilege.

## Clause 8 — Termination and Data Continuity

See Clause 5.viii for the full termination + data-continuity obligations; the 365-day continued-service window for in-flight regulated workflows is the foundation-model-API class's distinctive provision relative to the other five vendor-clauses documents in this set.

## References

- ADR-0014 (persistence-witness-timestamp pattern)
- ADR-0016 (vendor-score-gate — the runtime-output adapter; this document is the model-itself adapter)
- ADR-0022 (effective challenge harness — Adopter exercises SR 11-7 effective challenge against frontier-API primaries)
- ADR-0023 (vendor attestation ledger — the chain-of-custody record for the receipts this document obligates the vendor to provide)
- ADR-0024 (retraining cadence monitor — the temporal companion that translates Clause 2 disclosures into validation-cadence enforcement)
- ADR-0025 (deprecation watch — the lifecycle companion that translates Clause 5.iii contractual floor into operational early-warning)
- ADR-0026 (customer-facing chatbot guardrail — one of the runtime surfaces this vendor class powers)
- Treasury FS AI RMF (February 2026) — third-party + fourth-party AI oversight control objectives
- Cyber Risk Institute FS AI RMF (February 2026, 108 contributing institutions) — vendor-attestation control objectives
- NIST AI 600-1 § "Value Chain and Component Integration" — generative-AI third-party component control objective
- DORA Article 28 and Commission Delegated Regulation 2024/1773 RTS on subcontracting — EU ICT third-party risk management
- v1.3 modules: `finserv_agent_audit.governance.vendor_attestation_ledger`, `finserv_agent_audit.governance.retraining_cadence_monitor`, `finserv_agent_audit.governance.deprecation_watch`
