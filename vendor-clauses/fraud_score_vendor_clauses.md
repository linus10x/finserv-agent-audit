# Vendor Clauses — Fraud-Score / Device-Risk Vendors for AI Governance under finserv-agent-audit v1.1

## Purpose

This document is a procurement companion intended for direct insertion into vendor contracts, MSAs, SOWs, and RFP responses with fraud-score and device-risk vendors (real-time payment-fraud scoring, account-takeover risk, first-party-fraud risk, device-fingerprint risk, behavioral-biometric risk). It aligns vendor obligations with the audit-chain and `VendorScoreGate` framework that finserv-agent-audit v1.1 adopters operate, and translates the operator's UDAAP, Reg E, and dispute-resolution exposure on declined transactions into vendor-side performance, disclosure, and cooperation duties.

The clause set assumes the Adopter is a US-regulated financial institution or licensed money-services business consuming vendor fraud-score outputs in an automated or partially automated transaction-authorization, account-access, or onboarding-fraud surface.

## Scope

Covers vendor outputs used in:

- Real-time payment-fraud and authorization-fraud scoring (card-present, card-not-present, ACH, RTP, wires, P2P)
- Account-takeover and credential-stuffing risk scoring
- Session and behavioral-biometric risk
- Device-fingerprint and device-reputation risk
- First-party-fraud and synthetic-identity-fraud scoring at onboarding and at funding events
- Mule-account-detection scoring

Regulatory frameworks the vendor's outputs touch on the Adopter's side: Reg E (12 C.F.R. Part 1005) error-resolution timelines on consumer EFTs; Reg Z (12 C.F.R. Part 1026) on credit-card disputes; UDAAP exposure on false-positive declines (CFPB and prudential supervisors); Nacha Operating Rules on ACH return-window obligations; CARD Act provisions on rate and decline disclosures; state UDAP statutes; and CFPB Circular 2022-03 on adverse-action explainability where a fraud-score decline functionally substitutes for credit denial.

## Clause 1 — Audit-Chain Emit Requirements

Vendor SHALL emit, for every score or recommendation returned to Adopter:

- Vendor identifier
- Input hash (SHA-256 over the canonical, ordered input feature set; canonicalization spec published)
- Output value (numeric risk score, normalized to [0.0, 1.0]) and the vendor-native scale endpoints
- Recommendation (approve / step-up / decline / pend) in the `VendorRecommendation` vocabulary
- Reason codes (vendor-native + an explicit mapping to operator-side dispute and chargeback categories)
- Model version identifier (semantic version or content-addressed SHA)
- Timestamp (ISO 8601 UTC)
- Vendor-side request ID for cross-reference during dispute resolution and examination
- Latency-tier indicator (synchronous, near-real-time, batch) — required because Reg E timing obligations on the Adopter side compound with vendor latency

These fields are consumed by `VendorScoreGate.record_score()` and produce an `AuditEventType.VENDOR_SCORE_RECORDED` entry in the Adopter's audit chain. Vendor acknowledges that the emission set is the evidentiary backbone the Adopter relies on in a CFPB UDAAP examination, a Reg E dispute investigation, and any class-action fraud-decline allegation.

## Clause 2 — Model Version Pinning + Drift Disclosure

Vendor SHALL:

- Publish a stable model-version identifier for every scoring model in production (payment-fraud, ATO, device-risk, behavioral-biometric, first-party-fraud) and for any ensemble or meta-model that combines them
- Provide model-card-grade documentation per Mitchell et al. (2019) for each version: training-data sources and provenance windows, the specific fraud taxonomies covered, precision and recall by fraud-type bucket, the calibration curve, known limitations and out-of-distribution behavior
- Notify Adopter no less than 5 business days before any production model-version change in a synchronous-scoring path; 10 business days for any change that materially shifts the decline-rate at Adopter's calibrated thresholds
- Cooperate in version-change post-mortems when `VendorScoreGate.record_score()` raises `VendorScoreDriftDetected` on the `(vendor_id, input_hash, model_version)` key
- Provide a 30-day rollback option on the prior model version so Adopter can re-score a disputed decline cohort
- Disclose any training-data event that triggered a model retrain (large breach event, new fraud-typology emergence, vendor portfolio shift)

## Clause 3 — Reproducibility on Request

For any score Adopter consumed in a decline, step-up, or post-hoc review action, Adopter MAY request:

- The exact model version used
- The exact normalized input feature set Vendor scored
- The decision-path explanation (top-N contributing features by attribution, the device-reputation-graph context, the behavioral-biometric session evidence)
- The vendor-side analyst rationale where Vendor's workflow routed the case through human review

Vendor SHALL provide the reproducibility package within 10 business days of an Adopter audit, regulatory examination, customer-complaint escalation, Reg E dispute investigation, or subpoena. Vendor SHALL provide it within 3 business days for any single-case CFPB consumer-complaint inquiry routed through the Adopter.

## Clause 4 — SR 11-7 Model Validation Pass-Through

Vendor's fraud-scoring models constitute "models" under SR 11-7 / OCC Bulletin 2011-12 when consumed by SR 11-7-supervised Adopters. Vendor SHALL:

- Maintain SR 11-7-compliant model-development documentation (theoretical construction, intended use, conceptual soundness, data lineage)
- Subject every production scoring model and ensemble to independent validation by Vendor's second line of defense at least annually
- Provide `ModelInventory`-compatible metadata: `model_id`, `version`, `owner`, `validator`, `implementation_status`, `validation_date`, `next_validation_due`, `material_change_log`
- Make Vendor's model-validation reports available under NDA for Adopter's third-line internal audit
- Furnish, on examiner request, the validation report or a counsel-mediated summary sufficient to satisfy SR 11-7 governance review

## Clause 5 — Fraud-Score-Specific Obligations

Vendor SHALL:

- Commit to a published precision floor at Adopter's contractually-set decline threshold; report monthly against that floor
- Commit to a published recall floor by fraud-type bucket (card-not-present, ATO, first-party, mule, synthetic-identity); report monthly against that floor
- Disclose the false-positive rate (good transactions declined) by transaction-amount band; the operator's UDAAP exposure rises sharply at the tails of that distribution
- Publish a service-level objective for synchronous-scoring latency (commonly p99 < 250 ms for card authorization paths) and report monthly against it
- Disclose any model accuracy disparities across cohorts the Adopter is required to monitor under fair-treatment expectations (CFPB Bulletin 2014-01 on disparate fraud-decline rates), to the extent Vendor's evaluation data permits; provide the underlying test report under NDA
- Honor a 4-hour suppress-and-rescore SLA when Adopter contests a decline disposition that has triggered a Reg E error-resolution clock
- Provide an event-stream feed of model behavior changes — score-distribution shifts, decline-rate shifts, reason-code-mix shifts — at hourly granularity for the rolling 30 days
- Cooperate in periodic challenger-model and champion-challenger framework testing where Adopter operates an in-house or alternate-vendor challenger model

## Clause 6 — Audit and Right to Examine

Adopter MAY, on 30 days' written notice (reduced to 5 days for regulator-driven audits), audit Vendor's:

- Model-validation procedures and the most recent independent validation reports
- Precision-recall and false-positive-rate reporting against Clause 5 commitments
- Drift-detection cadence and historical drift events on Adopter's portfolio
- Reproducibility infrastructure (the ability to re-emit a prior-version score on a prior-version feature snapshot)
- Audit-chain emission completeness against a sampled set of Adopter decisions
- SOC 2 Type 2 and ISO 27001 control evidence pertinent to payment-data handling and PCI-DSS-equivalent scope

Vendor SHALL cooperate at Vendor's reasonable expense.

## Clause 7 — Disclosure to Regulators

Vendor acknowledges that Adopter is subject to examination by federal functional regulators (OCC, FRB, FDIC, NCUA, CFPB), state regulators (NYDFS, CDFPI, DBO), and card-network compliance bodies, and that Adopter MAY disclose Vendor's outputs, model documentation, performance reports, and drift-detection logs to:

- Federal and state regulatory examiners
- External auditors (Big-4 firms acting on Adopter's behalf)
- Outside counsel (for privileged review preceding any required disclosure)
- Card-network compliance functions where the Adopter's network agreement so requires

Such disclosure does not constitute waiver of Vendor's trade secrets in jurisdictions recognizing the regulatory-disclosure privilege.

## Clause 8 — Termination and Data Continuity

On termination for any reason, Vendor SHALL:

- Continue serving scores for in-flight transactions and pending dispute investigations for 30 business days
- Provide a final dump of all audit-chain emissions (Clause 1 fields) for the Adopter's compliance retention period — default 5 years (BSA/AML retention) and 7 years where SEC Rule 17a-4 applies
- Provide the analyst rationale package on every case Vendor's workflow touched in the prior 12 months
- Cooperate, at commercial reasonable rates, in any pending or subsequently-noticed regulatory examination, civil litigation, or class-action discovery related to Vendor's outputs for a period of 3 years post-termination
- Surrender or destroy transaction and device-attribute data per the data-retention schedule in the MSA and provide a certificate of destruction

## References

- ADR-0014 (persistence-witness-timestamp pattern)
- ADR-0016 (vendor-score-gate)
- ADR-0007 (SR 11-7 overlay)
- ADR-0008 (GLBA Safeguards)
- `docs/sr11_7_mapping.md`
- `docs/cfpb_circular_2022_03_mapping.md`
- v1.1 module: `finserv_agent_audit.governance.vendor_score_gate`
