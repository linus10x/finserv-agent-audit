# Vendor Clauses — AML Transaction-Monitoring Vendors for AI Governance under finserv-agent-audit v1.1

## Purpose

This document is a procurement companion intended for direct insertion into vendor contracts, MSAs, SOWs, and RFP responses with AML transaction-monitoring vendors (suspicious-activity scoring, alert-generation, alert-prioritization, sanctions-screening match scoring, typology-detection model output, and machine-learning-driven SAR-decision-support). It aligns vendor obligations with the audit-chain and `VendorScoreGate` framework that finserv-agent-audit v1.1 adopters operate, and translates the Adopter's BSA / SAR-filing, OFAC, NYDFS Part 504, and FFIEC examination exposure into vendor-side performance, disclosure, and cooperation duties.

The clause set assumes the Adopter is a financial institution subject to BSA/AML examination by FinCEN and the Adopter's federal functional regulator (OCC, FRB, FDIC, NCUA), with NYDFS Part 504 applying to NY-supervised entities, and that the AML-TM vendor's scoring outputs feed an alert queue and SAR-decision workflow.

## Scope

Covers vendor outputs used in:

- Suspicious-activity scoring on transaction-stream events
- Alert generation and alert-prioritization (risk-tiering)
- Typology-detection model outputs (structuring, layering, smurfing, trade-based money laundering, human-trafficking patterns, terrorist-financing patterns)
- Sanctions-screening match scoring on transaction parties (OFAC, EU, UN, UK HMT lists)
- Customer-risk-rating refresh outputs
- Network-analytics outputs (entity-resolution, beneficial-ownership-link inference)
- Machine-learning false-positive-reduction outputs on legacy rule-based alerts

Regulatory frameworks the vendor's outputs touch on the Adopter's side: Bank Secrecy Act (31 U.S.C. § 5311 et seq.); SAR-filing rule (31 C.F.R. § 1020.320 for banks; analogous rules for non-bank institutions); BSA safe harbor (31 U.S.C. § 5318(g)(2)); CDD rule (31 C.F.R. § 1010.230); OFAC compliance (31 C.F.R. Part 501); NYDFS Part 504 transaction-monitoring program rule; FFIEC BSA/AML Examination Manual; FinCEN's 2023 Joint Statement on Innovative Approaches to AML/CFT Compliance; and the FinCEN-FRB-OCC-FDIC-NCUA Interagency Statement on Model Risk Management for BSA/AML Compliance (April 2021).

## Clause 1 — Audit-Chain Emit Requirements

Vendor SHALL emit, for every score, alert, or recommendation returned to Adopter:

- Vendor identifier
- Input hash (SHA-256 over the canonical, ordered input transaction-set and customer-attribute set; canonicalization spec published)
- Output value (numeric risk score, normalized to [0.0, 1.0]) and the vendor-native scale endpoints
- Alert classification (alert / no-alert / refer-to-Tier-2 / auto-disposition) in the `VendorRecommendation` vocabulary
- Typology classification (the named typology bucket the model assigns; e.g. structuring, layering, trade-based, human-trafficking) where applicable
- Reason codes (vendor-native, with explicit mapping to SAR-narrative-supporting categories)
- Model version identifier (semantic version or content-addressed SHA)
- Rule or scenario identifier where the alert was produced by a named rule or scenario in a hybrid rule-plus-model system
- Timestamp (ISO 8601 UTC)
- Vendor-side request ID for cross-reference during examination and FinCEN inquiry
- Sanctions-list version identifier where a screening output is produced

These fields are consumed by `VendorScoreGate.record_score()` and produce an `AuditEventType.VENDOR_SCORE_RECORDED` entry in the Adopter's audit chain. The emission set is the evidentiary backbone the Adopter relies on in FFIEC examination, NYDFS Part 504 certification, and any FinCEN inquiry.

## Clause 2 — Model Version Pinning + Drift Disclosure

Vendor SHALL:

- Publish a stable model-version identifier for every scoring model, typology-detection model, alert-prioritization model, and ML-false-positive-reduction model in production
- Publish a stable scenario or rule-set version identifier for every rule-based or scenario-based component
- Provide model-card-grade documentation per Mitchell et al. (2019) for each version: training-data sources (synthetic, redacted SAR narratives, vendor-consortium data), the typology coverage, the precision and recall by typology bucket on a held-out test set, the false-positive-rate at the deployed threshold, the alert-volume implications at the deployed threshold, known limitations, and the interagency-statement-required pre-implementation testing artifacts
- Notify Adopter no less than 10 business days before any production model-version or scenario-set change; 20 business days for any change that materially shifts the alert-volume distribution at Adopter's deployed thresholds
- Cooperate in version-change post-mortems when `VendorScoreGate.record_score()` raises `VendorScoreDriftDetected` on the `(vendor_id, input_hash, model_version)` key
- Provide a 60-day rollback option so Adopter can re-score a contested SAR-decision cohort
- Disclose any retraining event materially altering the typology mix or feature-importance ranking

## Clause 3 — Reproducibility on Request

For any alert Adopter received and disposed of (alerted-and-cleared, escalated-Tier-2, SAR-filed, no-SAR-filed), Adopter MAY request:

- The exact model version, scenario version, and sanctions-list version used
- The exact normalized input transaction and customer-attribute snapshot
- The decision-path explanation: the typology-evidence chain, the contributing transactions, the entity-resolution graph context, the rule or scenario that fired (in a hybrid system), and the model's feature attributions
- The narrative-supporting evidence package sufficient for a SAR filing under 31 C.F.R. § 1020.320 (the "five Ws" of the SAR narrative: who, what, when, where, why)

Vendor SHALL provide the reproducibility package within 10 business days of an Adopter audit, FFIEC examination, NYDFS Part 504 certification cycle, or subpoena. Vendor SHALL provide it within 3 business days for any FinCEN 314(a), grand-jury subpoena, or 314(b)-related inquiry routed through the Adopter, and within 1 business day for any OFAC blocking-action inquiry.

## Clause 4 — SR 11-7 / Interagency-Statement Model Validation Pass-Through

Vendor's AML-TM models constitute "models" under SR 11-7 / OCC Bulletin 2011-12 and within the scope of the April 2021 Interagency Statement on Model Risk Management for BSA/AML Compliance when consumed by SR 11-7-supervised Adopters. Vendor SHALL:

- Maintain SR 11-7-compliant model-development documentation (theoretical construction, intended use, conceptual soundness, data lineage, typology coverage analysis)
- Subject every production model to independent validation by Vendor's second line of defense at least annually; conduct above-the-line and below-the-line testing on threshold-tuning recommendations
- Conduct the Interagency-Statement-recommended pre-implementation testing and document the results
- Provide `ModelInventory`-compatible metadata: `model_id`, `version`, `owner`, `validator`, `implementation_status`, `validation_date`, `next_validation_due`, `material_change_log`
- Make Vendor's model-validation reports available under NDA for Adopter's third-line internal audit
- Furnish, on examiner request, the validation report or a counsel-mediated summary sufficient to satisfy SR 11-7 and FFIEC examination
- Support the NYDFS Part 504 annual certification process by providing the artifacts required for the Senior Officer of the institution to certify the transaction-monitoring program

## Clause 5 — AML-Transaction-Monitoring-Specific Obligations

Vendor SHALL:

- Refresh OFAC SDN list ingestion no less than every 4 hours during US business hours and within 12 hours otherwise; refresh other consolidated sanctions lists within 24 hours of publication
- Maintain typology coverage aligned with FinCEN advisories and the most recent FATF typology reports; disclose typology coverage gaps in the SOC 2 Type 2 report
- Support the BSA § 5318(g)(2) safe-harbor metadata requirement by emitting the fields needed to evidence good-faith filing: alert-generation timestamp, investigator-assignment chain, narrative-supporting evidence package, and the model and scenario versions in force
- Maintain a documented above-the-line / below-the-line threshold-tuning methodology aligned with FFIEC expectations; provide the most recent threshold-tuning study and the supporting statistical analysis
- Provide a documented procedure for SAR-narrative support that does not put vendor employees in possession of SAR-confidential information beyond what is necessary for the support function; Vendor employees with SAR exposure SHALL be bound by SAR-confidentiality controls equivalent to 31 C.F.R. § 1020.320(e)
- Provide an alert-disposition audit trail capable of supporting a regulator's request to reconstruct the full Tier-1 / Tier-2 / Tier-3 review path
- Disclose any model accuracy disparities relevant to fair-treatment considerations (e.g. typology-detection performance variation across geographic correspondent-banking corridors)
- Honor a 4-hour suppress-and-rescore SLA when Adopter contests a sanctions-screening match disposition, and a 24-hour SLA for alert-disposition disputes
- Cooperate in Adopter's NYDFS Part 504 annual certification, providing artifacts within 20 business days of Adopter request

## Clause 6 — Audit and Right to Examine

Adopter MAY, on 30 days' written notice (reduced to 5 days for regulator-driven audits), audit Vendor's:

- Model-validation procedures and the most recent independent validation reports
- Above-the-line / below-the-line threshold-tuning studies
- Typology coverage documentation and FATF-typology-alignment evidence
- Sanctions-list refresh logs
- Drift-detection cadence and historical drift events on Adopter's portfolio
- Reproducibility infrastructure
- Audit-chain emission completeness against a sampled set of Adopter dispositions
- SOC 2 Type 2 and ISO 27001 control evidence pertinent to transaction-data handling and SAR-confidentiality controls

Vendor SHALL cooperate at Vendor's reasonable expense.

## Clause 7 — Disclosure to Regulators

Vendor acknowledges that Adopter is subject to BSA/AML examination by FinCEN and the Adopter's federal functional regulator, by NYDFS for NY-supervised entities, and by state regulators where applicable, and that Adopter MAY disclose Vendor's outputs, model documentation, threshold-tuning studies, typology-coverage analyses, and drift-detection logs to:

- FinCEN, federal functional regulators, and state regulators (including NYDFS)
- External auditors (Big-4 firms acting on Adopter's behalf in BSA/AML-program audits)
- Outside counsel (for privileged review preceding any required disclosure)
- Law-enforcement agencies acting under 314(a), grand-jury subpoena, or 314(b)-related inquiry
- OFAC under blocking-action inquiry

Such disclosure does not constitute waiver of Vendor's trade secrets in jurisdictions recognizing the regulatory-disclosure privilege, and does not constitute a SAR-confidentiality violation when made under the safe-harbor provisions of 31 U.S.C. § 5318(g)(2).

## Clause 8 — Termination and Data Continuity

On termination for any reason, Vendor SHALL:

- Continue serving scores and alert outputs for in-flight transaction-monitoring runs and pending SAR-decision workflows for 30 business days
- Provide a final dump of all audit-chain emissions (Clause 1 fields), threshold-tuning studies, and typology-coverage documentation for the Adopter's compliance retention period — default 5 years from the date of the SAR filing or transaction record per 31 C.F.R. § 1010.430, and 7 years where SEC Rule 17a-4 applies to the Adopter
- Provide all alert-disposition audit trails and sanctions-list versions in force during the relationship
- Cooperate, at commercial reasonable rates, in any pending or subsequently-noticed FinCEN inquiry, FFIEC examination, NYDFS Part 504 certification, OFAC enforcement, or grand-jury subpoena related to Vendor's outputs for a period of 7 years post-termination
- Surrender or destroy transaction and customer-attribute data per the data-retention schedule and provide a certificate of destruction; SAR-related data SHALL be retained per BSA recordkeeping rules until the statutory retention window expires

## References

- ADR-0014 (persistence-witness-timestamp pattern)
- ADR-0016 (vendor-score-gate)
- ADR-0011 (BSA / AML SAR-workflow mapping)
- ADR-0007 (SR 11-7 overlay)
- ADR-0013 (SEC 17a-4 WORM retention)
- `docs/bsa_aml_mapping.md`
- `docs/sr11_7_mapping.md`
- `docs/sec_17a_4_mapping.md`
- v1.1 module: `finserv_agent_audit.governance.vendor_score_gate`
