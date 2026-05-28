# Vendor Clauses — KYC / Identity-Verification Vendors for AI Governance under finserv-agent-audit v1.1

## Purpose

This document is a procurement companion intended for direct insertion into vendor contracts, MSAs, SOWs, and RFP responses with KYC and identity-verification vendors (identity-verification + document-validity scoring + PEP / sanctions-watchlist screening vendor classes). It aligns vendor obligations with the audit-chain and `VendorScoreGate` framework that finserv-agent-audit v1.1 adopters operate, and translates the operator's regulatory exposure into vendor-side performance, disclosure, and cooperation duties.

The clause set assumes the Adopter is a US-regulated financial institution subject to BSA/AML examination by a federal functional regulator (OCC, FRB, FDIC, NCUA), state regulator (NYDFS, CDFPI), and/or FinCEN, and that the KYC vendor's scoring outputs are consumed by an automated or partially automated customer-onboarding decision surface.

## Scope

Covers vendor outputs used in:

- Customer Identification Program (CIP) document verification and identity-attribute matching
- Customer Due Diligence (CDD) risk-rating contributions
- PEP (Politically Exposed Person) screening
- OFAC sanctions screening (SDN, sectoral, and consolidated lists)
- Adverse-media screening
- Watchlist-match-confidence scoring

Regulatory frameworks the vendor's outputs touch on the Adopter's side: BSA (31 U.S.C. § 5311 et seq.), CIP rule (31 C.F.R. § 1020.220), CDD rule (31 C.F.R. § 1010.230), beneficial-ownership rule (FinCEN Reporting Rule, 87 Fed. Reg. 59498), OFAC compliance (31 C.F.R. Part 501), GLBA Safeguards Rule (16 C.F.R. Part 314), FCRA Section 615 (where identity scoring informs adverse-action notices on credit-adjacent products), state UDAP statutes (NYDFS Part 504 for NY-supervised institutions), and FFIEC BSA/AML Examination Manual expectations.

## Clause 1 — Audit-Chain Emit Requirements

Vendor SHALL emit, for every score, recommendation, or watchlist hit returned to Adopter:

- Vendor identifier (stable across requests)
- Input hash (SHA-256 of the canonical, ordered input attribute set; vendor publishes the canonicalization spec)
- Output value (numeric risk score, normalized to [0.0, 1.0]) and the vendor-native scale endpoints
- Recommendation (approve / review / decline / pend) in the `VendorRecommendation` vocabulary
- Reason codes (vendor-native + an explicit mapping to BSA/AML CIP-failure categories and OFAC list-classification codes where applicable)
- Watchlist hits with list identifier, match strength, and the list version (date-stamped)
- Model version identifier (semantic version or content-addressed SHA)
- Timestamp (ISO 8601 UTC)
- Vendor-side request ID for cross-reference during examination

These fields are consumed by `VendorScoreGate.record_score()` and produce an `AuditEventType.VENDOR_SCORE_RECORDED` entry in the Adopter's audit chain. Vendor acknowledges that incomplete emissions degrade the Adopter's BSA/AML examination posture and that completeness is a contract-grade obligation, not a best-effort target.

## Clause 2 — Model Version Pinning + Drift Disclosure

Vendor SHALL:

- Publish a stable model-version identifier for every scoring model, document-verification model, biometric-matcher model, and screening-engine version in production
- Provide model-card-grade documentation per Mitchell et al. (2019) for each version: training-data sources and provenance, evaluation metrics (precision, recall, F1, false-accept rate, false-reject rate by document type and issuing country), known limitations (low-resource issuing-country accuracy floors, demographic accuracy spreads), and out-of-distribution behavior
- Notify Adopter no less than 5 business days before any production model-version change
- Disclose watchlist-source refresh cadence (OFAC SDN list typically intraday; consolidated EU and UK lists daily; PEP list weekly minimum) and the actual cadence Vendor operates
- Cooperate in version-change post-mortems when `VendorScoreGate.record_score()` raises `VendorScoreDriftDetected` on the `(vendor_id, input_hash, model_version)` key
- Provide a 30-day rollback option on the prior model version so Adopter can re-score a disputed onboarding cohort under the prior model

## Clause 3 — Reproducibility on Request

For any KYC decision Adopter made in reliance on Vendor output, Adopter MAY request:

- The exact model version and watchlist version used at decision time
- The exact normalized input attribute set
- The decision-path explanation (document-region confidence by zone, attribute-match scores by field, biometric-match quality)
- The watchlist-match analyst rationale where Vendor's screening engine routed the hit through human review

Vendor SHALL provide the package within 10 business days of an Adopter audit, regulatory examination, FFIEC field-visit, or subpoena. Vendor SHALL provide it within 3 business days when the requesting authority is FinCEN under a 314(a) request or OFAC under a blocking-action inquiry.

## Clause 4 — SR 11-7 Model Validation Pass-Through

Vendor's identity-scoring, document-verification, biometric-matching, and watchlist-screening models constitute "models" under SR 11-7 / OCC Bulletin 2011-12 when consumed by SR 11-7-supervised Adopters. Vendor SHALL:

- Maintain SR 11-7-compliant model-development documentation (theoretical construction, intended use, data lineage)
- Subject every production model to independent validation by Vendor's second line of defense at least annually
- Provide `ModelInventory`-compatible metadata: `model_id`, `version`, `owner`, `validator`, `implementation_status`, `validation_date`, `next_validation_due`, `material_change_log`
- Make Vendor's model-validation reports available under NDA for Adopter's third-line internal audit
- Furnish, on examiner request, the validation report or a counsel-mediated summary sufficient to satisfy SR 11-7 governance review

## Clause 5 — KYC-Specific Obligations

Vendor SHALL:

- Maintain CIP-rule alignment: the four CIP minimum elements (name, date of birth, address, identification number) and the verification methods Vendor uses for each, documented and refreshed on regulatory change
- Refresh OFAC SDN list ingestion no less than every 4 hours during US business hours and within 12 hours otherwise; document any miss in the next monthly service report
- Refresh consolidated sanctions lists (UN, EU, UK HMT, Canadian Consolidated, Australian DFAT) within 24 hours of publication
- Refresh PEP and adverse-media corpora on a published cadence and disclose the cadence in the SOC 2 Type 2 report
- Apply fuzzy-match thresholds in the OFAC-recommended band and publish the false-positive-rate and false-negative-rate test results from the most recent independent test
- Disclose any known model accuracy disparities by issuing-country, document type, age cohort, or skin-tone bin in line with NIST FRVT methodology; provide the underlying test report under NDA
- Honor a 24-hour suppress-and-rescore SLA when Adopter contests a watchlist-match disposition
- Provide a watchlist-match resolution narrative sufficient to support a Suspicious Activity Report (SAR) when the Adopter elects to file
- Maintain a documented procedure for the FinCEN beneficial-ownership reporting rule data the Adopter is required to collect and report under 31 C.F.R. § 1010.380

## Clause 6 — Audit and Right to Examine

Adopter MAY, on 30 days' written notice (reduced to 5 days for regulator-driven audits), audit Vendor's:

- Model-validation procedures and the most recent independent validation reports
- Watchlist-source refresh logs, including evidence of OFAC SDN ingestion timing
- Drift-detection cadence and historical drift events
- Reproducibility infrastructure (the ability to re-emit a prior-version score on a prior-version watchlist)
- Audit-chain emission completeness against a sampled set of Adopter decisions
- SOC 2 Type 2 and ISO 27001 control evidence pertinent to identity-data handling

Vendor SHALL cooperate at Vendor's reasonable expense; Adopter bears travel and out-of-pocket only.

## Clause 7 — Disclosure to Regulators

Vendor acknowledges that Adopter is subject to BSA/AML examination by FinCEN, the Adopter's federal functional regulator, and any applicable state regulator (including NYDFS Part 504 for NY-supervised entities), and that Adopter MAY disclose Vendor's outputs, model documentation, watchlist-version history, and drift-detection logs to:

- Federal and state regulatory examiners
- External auditors (Big-4 firms acting on Adopter's behalf in financial-statement, SOX, or BSA/AML-program audit capacities)
- Outside counsel (for privileged review preceding any required disclosure)
- FinCEN under 31 U.S.C. § 5318(g)(2) and OFAC under blocking-action inquiry

Such disclosure does not constitute waiver of Vendor's trade secrets in jurisdictions recognizing the regulatory-disclosure privilege.

## Clause 8 — Termination and Data Continuity

On termination for any reason, Vendor SHALL:

- Continue serving scores for in-flight onboarding decisions for 30 business days
- Provide a final dump of all audit-chain emissions (Clause 1 fields) for the Adopter's compliance retention period — default 5 years post-customer-closure for BSA/AML records (31 C.F.R. § 1010.430) and 7 years where SEC Rule 17a-4 applies to the Adopter
- Provide all watchlist-match resolution narratives and the watchlist versions in force at the relevant times
- Cooperate, at commercial reasonable rates, in any pending or subsequently-noticed regulatory examination of Vendor's outputs for a period of 3 years post-termination
- Surrender or destroy customer-attribute data per the data-retention schedule in the MSA and provide a certificate of destruction

## References

- ADR-0014 (persistence-witness-timestamp pattern)
- ADR-0016 (vendor-score-gate)
- ADR-0011 (BSA / AML SAR-workflow mapping)
- ADR-0008 (GLBA Safeguards)
- `docs/bsa_aml_mapping.md`
- `docs/glba_safeguards_mapping.md`
- v1.1 module: `finserv_agent_audit.governance.vendor_score_gate`
