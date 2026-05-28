# Vendor Clauses — Credit-Decision / ML-Underwriting Vendors for AI Governance under finserv-agent-audit v1.1

## Purpose

This document is a procurement companion intended for direct insertion into vendor contracts, MSAs, SOWs, and RFP responses with credit-decision and machine-learning-underwriting vendors (application risk scoring, line-assignment recommendation, pricing-tier assignment, second-look decisioning, and any ML-driven underwriting surface used in consumer or small-business lending). It aligns vendor obligations with the audit-chain and `VendorScoreGate` framework that finserv-agent-audit v1.1 adopters operate, and translates the Adopter's ECOA / Regulation B, FCRA, CFPB Circular 2022-03, and SR 11-7 exposure into vendor-side performance, disclosure, and cooperation duties.

The clause set assumes the Adopter is a US-regulated depository, lender, or fintech sponsor-bank arrangement consuming vendor scoring outputs in an automated or partially automated credit-decision surface that produces adverse-action-eligible outcomes.

## Scope

Covers vendor outputs used in:

- Application risk scoring for credit cards, personal loans, auto, small business, and mortgage-adjacent product lines
- Line-assignment and credit-limit recommendation
- Pricing-tier and APR-band assignment
- Second-look and decline-recovery decisioning
- Income-estimation and cash-flow-underwriting outputs
- Alternative-data-derived credit signals (bank-transaction-derived, employment-verified, education-derived where lawful)

Regulatory frameworks the vendor's outputs touch on the Adopter's side: ECOA / Regulation B (12 C.F.R. § 1002) including the prohibited-bases provisions and the adverse-action-notice rules; FCRA Section 615 (15 U.S.C. § 1681m) adverse-action notice; FCRA Section 607(b) on accuracy of consumer-report information when the vendor functions as or relies on a consumer-reporting agency; CFPB Circular 2022-03 on adverse-action explainability under complex models; the CFPB-DOJ-EEOC-FTC Joint Statement on AI Discrimination (April 2023); SR 11-7 / OCC Bulletin 2011-12 on model risk management; OCC Bulletin 2020-10 on third-party-relationship risk; and state UDAP / fair-lending statutes.

## Clause 1 — Audit-Chain Emit Requirements

Vendor SHALL emit, for every score, recommendation, or pricing-tier output returned to Adopter:

- Vendor identifier
- Input hash (SHA-256 over the canonical, ordered input feature set; canonicalization spec published)
- Output value (numeric risk score, normalized to [0.0, 1.0]) and the vendor-native scale endpoints
- Recommendation (approve / counter-offer / decline / refer-to-human / pend) in the `VendorRecommendation` vocabulary
- Reason codes (vendor-native, with an explicit FCRA-Section-615-compliant principal-reason mapping; per CFPB Circular 2022-03 the reasons must be specific and accurate, not generic)
- Model version identifier (semantic version or content-addressed SHA)
- Timestamp (ISO 8601 UTC)
- Vendor-side request ID for cross-reference during examination and dispute resolution
- Where the vendor used a consumer-report attribute as a material input, the consumer-reporting agency identifier and the date of the report

These fields are consumed by `VendorScoreGate.record_score()` and produce an `AuditEventType.VENDOR_SCORE_RECORDED` entry in the Adopter's audit chain. Vendor acknowledges that the Adopter relies on this emission set to satisfy ECOA Regulation B § 1002.9 (notification of action taken) and the FCRA Section 615 obligation, and that incompleteness is a contract-grade defect.

## Clause 2 — Model Version Pinning + Drift Disclosure

Vendor SHALL:

- Publish a stable model-version identifier for every scoring model, pricing model, and ensemble in production
- Provide model-card-grade documentation per Mitchell et al. (2019) for each version: training-data sources and provenance windows, model class (GBM, neural, ensemble), the input feature set with definitions, evaluation metrics (AUC, KS, Gini, calibration), known limitations, and the disparate-impact and equal-opportunity test results across the protected classes the Adopter is required to monitor under ECOA
- Notify Adopter no less than 10 business days before any production model-version change; 20 business days for any change that shifts the approval-rate or the mean priced APR at Adopter's calibrated thresholds beyond a contractually-set band
- Cooperate in version-change post-mortems when `VendorScoreGate.record_score()` raises `VendorScoreDriftDetected` on the `(vendor_id, input_hash, model_version)` key
- Provide a 60-day rollback option on the prior model version so Adopter can re-score a disputed adverse-action cohort under the prior model
- Disclose any retraining event that materially altered the model's feature-importance ranking and notify Adopter of the change in advance

## Clause 3 — Reproducibility on Request

For any score Adopter consumed in an adverse-action, counter-offer, or pricing decision, Adopter MAY request:

- The exact model version used
- The exact normalized input feature set
- The decision-path explanation: for tree-ensemble models, the leaf-path or the top-N SHAP / feature-attribution contributions; for neural models, the integrated-gradients or attention-attribution package; for ensemble combinations, the per-base-model attribution combined into a coherent customer-facing principal-reason statement
- The CFPB-Circular-2022-03-compliant principal-reason rationale in customer-readable language

Vendor SHALL provide the reproducibility package within 10 business days of an Adopter audit, regulatory examination, customer-complaint escalation, ECOA § 1002.9 request, or subpoena. Vendor SHALL provide it within 3 business days for any CFPB consumer-complaint inquiry routed through the Adopter.

## Clause 4 — SR 11-7 Model Validation Pass-Through

Vendor's credit-decision models constitute "models" under SR 11-7 / OCC Bulletin 2011-12 when consumed by SR 11-7-supervised Adopters. Vendor SHALL:

- Maintain SR 11-7-compliant model-development documentation (theoretical construction, intended use, conceptual soundness, data lineage, segmentation analysis)
- Subject every production scoring model to independent validation by Vendor's second line of defense at least annually, and on any material change
- Provide `ModelInventory`-compatible metadata: `model_id`, `version`, `owner`, `validator`, `implementation_status`, `validation_date`, `next_validation_due`, `material_change_log`
- Make Vendor's model-validation reports, including conceptual-soundness reviews and outcomes-analysis testing, available under NDA for Adopter's third-line internal audit
- Furnish, on examiner request, the validation report or a counsel-mediated summary sufficient to satisfy SR 11-7 governance review
- Maintain ongoing benchmarking against an independent challenger model and disclose the comparison results quarterly

## Clause 5 — Credit-Decision-Specific Obligations

Vendor SHALL:

- Map every vendor-native reason code to an FCRA-Section-615-compliant principal-reason in language drafted to satisfy CFPB Circular 2022-03 (specific and accurate, not generic boilerplate); maintain the mapping table under version control and notify Adopter of any change
- For any model change that alters the principal-reason population for similarly-situated applicants, provide a side-by-side comparison so Adopter can re-validate adverse-action notice content
- Conduct disparate-impact and adverse-impact testing on each model version across the protected classes the Adopter is required to monitor under ECOA / Reg B and HMDA where applicable; provide the report under NDA pre-deployment
- Conduct less-discriminatory-alternative search and document the methodology, the search space, and the rationale for not adopting any alternative tested; CFPB and prudential supervisors increasingly expect this artifact
- Where Vendor uses alternative data (bank-transaction-derived, education-attribute-derived, or any data not traditionally on the consumer report), document lawful basis for use under ECOA's prohibited-bases provisions and the CFPB's stated guidance on alternative-data underwriting (Request for Information, 82 Fed. Reg. 11183)
- Where Vendor's outputs function as or rely on consumer-reporting-agency activity, comply with FCRA Section 607(b) accuracy obligations and provide Adopter with the dispute-resolution channel applicants will be directed to
- Disclose income-estimation methodology where income-estimate inputs are used; the CFPB has indicated heightened scrutiny on this in 2024-2026 supervisory cycles
- Refresh disparate-impact testing on a quarterly basis and on every model-version deployment

## Clause 6 — Audit and Right to Examine

Adopter MAY, on 30 days' written notice (reduced to 5 days for regulator-driven audits), audit Vendor's:

- Model-validation procedures and the most recent independent validation reports
- Disparate-impact and less-discriminatory-alternative reports
- Principal-reason-code mapping tables and any change history
- Drift-detection cadence and historical drift events on Adopter's portfolio
- Reproducibility infrastructure
- Audit-chain emission completeness against a sampled set of Adopter decisions
- SOC 2 Type 2 and ISO 27001 control evidence

Vendor SHALL cooperate at Vendor's reasonable expense.

## Clause 7 — Disclosure to Regulators

Vendor acknowledges that Adopter is subject to examination by federal functional regulators (OCC, FRB, FDIC, NCUA, CFPB) and state regulators (NYDFS, CDFPI, DBO, state attorneys-general), and that Adopter MAY disclose Vendor's outputs, model documentation, disparate-impact reports, less-discriminatory-alternative analyses, and drift-detection logs to:

- Federal and state regulatory examiners (including HMDA examiners where applicable)
- External auditors (Big-4 firms acting on Adopter's behalf)
- Outside counsel (for privileged review preceding any required disclosure)
- The DOJ Civil Rights Division and the CFPB Office of Fair Lending Enforcement under fair-lending inquiry

Such disclosure does not constitute waiver of Vendor's trade secrets in jurisdictions recognizing the regulatory-disclosure privilege.

## Clause 8 — Termination and Data Continuity

On termination for any reason, Vendor SHALL:

- Continue serving scores for in-flight applications and pending second-look workflows for 30 business days
- Provide a final dump of all audit-chain emissions (Clause 1 fields) and disparate-impact testing reports for the Adopter's compliance retention period — default 25 months under Reg B § 1002.12 for adverse-action records, 7 years for HMDA-reportable LARs where applicable, and 7 years where SEC Rule 17a-4 applies
- Provide all principal-reason mapping tables in force during the relationship
- Cooperate, at commercial reasonable rates, in any pending or subsequently-noticed regulatory examination, fair-lending inquiry, or civil litigation related to Vendor's outputs for a period of 5 years post-termination
- Surrender or destroy applicant-attribute data per the data-retention schedule and provide a certificate of destruction

## References

- ADR-0014 (persistence-witness-timestamp pattern)
- ADR-0016 (vendor-score-gate)
- ADR-0009 (FCRA / Reg V adverse-action)
- ADR-0010 (ECOA / Reg B fair-lending)
- ADR-0007 (SR 11-7 overlay)
- `docs/fcra_reg_v_mapping.md`
- `docs/ecoa_reg_b_mapping.md`
- `docs/cfpb_circular_2022_03_mapping.md`
- `docs/sr11_7_mapping.md`
- v1.1 module: `finserv_agent_audit.governance.vendor_score_gate`
