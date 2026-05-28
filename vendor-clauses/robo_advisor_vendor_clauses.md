# Vendor Clauses — Robo-Advisor / Signal-Generation Vendors for AI Governance under finserv-agent-audit v1.1

## Purpose

This document is a procurement companion intended for direct insertion into vendor contracts, MSAs, SOWs, and RFP responses with robo-advisor and signal-generation vendors (algorithmic allocation recommendation, rebalancing-trigger generation, risk-tolerance scoring, model-portfolio assignment, retirement-glide-path generation, and ML-driven research-signal feeds used in recommendation surfaces). It aligns vendor obligations with the audit-chain and `VendorScoreGate` framework that finserv-agent-audit v1.1 adopters operate, and translates the Adopter's Investment Advisers Act fiduciary, FINRA Rule 2111 suitability, SEC Regulation Best Interest, and Reg S-P / Reg S-ID exposure into vendor-side performance, disclosure, and cooperation duties.

The clause set assumes the Adopter is an SEC- or state-registered investment adviser, an SEC-registered broker-dealer subject to Reg BI, or a dual-registrant operating a recommendation surface that consumes vendor signals, allocation outputs, or model-portfolio recommendations.

## Scope

Covers vendor outputs used in:

- Algorithmic asset-allocation recommendation
- Model-portfolio assignment and risk-tolerance scoring
- Rebalancing-trigger signal generation
- Tax-loss-harvesting opportunity signals
- Retirement-glide-path and decumulation-path generation
- Manager-selection and fund-selection signals
- Research-driven security-selection signals consumed in an automated recommendation path
- Concentration, ESG-screen, and restricted-list overlay signals

Regulatory frameworks the vendor's outputs touch on the Adopter's side: Investment Advisers Act of 1940 fiduciary duty as articulated in the SEC's 2019 Standard of Conduct release; SEC Regulation Best Interest (17 C.F.R. § 240.15l-1) including Care, Disclosure, Conflict, and Compliance obligations; FINRA Rule 2111 (suitability); FINRA Rule 3110 (supervision); SEC Marketing Rule (17 C.F.R. § 275.206(4)-1); Form CRS (17 C.F.R. § 275.204-5); Reg S-P (17 C.F.R. Part 248) on customer-information safeguards; Reg S-ID on identity-theft red flags; the SEC's Risk Alert on Robo-Advisers (Feb 2021); and applicable state fiduciary-rule extensions.

## Clause 1 — Audit-Chain Emit Requirements

Vendor SHALL emit, for every signal, allocation recommendation, rebalancing trigger, or risk-tolerance score returned to Adopter:

- Vendor identifier
- Input hash (SHA-256 over the canonical, ordered input set, which for this class typically includes the client's risk-tolerance profile, time-horizon, current allocation, restriction set, and tax context)
- Output value (signal score normalized to [0.0, 1.0] or the allocation-vector hash)
- Recommendation (the allocation, the rebalancing-trigger flag, the model-portfolio identifier) in a vendor-published vocabulary
- Reason codes (the vendor's documented rationale set; for Reg BI Care-obligation review the Adopter must be able to reconstruct why this recommendation was suitable for this client)
- Model version identifier (semantic version or content-addressed SHA) and the assumption-set version (capital-market-assumption release date, Monte-Carlo seed if applicable)
- Timestamp (ISO 8601 UTC)
- Vendor-side request ID for cross-reference during examination

These fields are consumed by `VendorScoreGate.record_score()` and produce an `AuditEventType.VENDOR_SCORE_RECORDED` entry in the Adopter's audit chain. Vendor acknowledges that the Adopter relies on this emission set to evidence Care and Compliance obligations under Reg BI, suitability under Rule 2111, and the Adviser's documentation duty under the Investment Advisers Act.

## Clause 2 — Model Version Pinning + Drift Disclosure

Vendor SHALL:

- Publish a stable model-version identifier for every signal-generation model, allocation-engine version, optimizer build, and capital-market-assumption release in production
- Provide model-card-grade documentation per Mitchell et al. (2019) for each version: the model class, the capital-market assumptions in use (returns, volatilities, correlations) with publication date, the optimization objective, the constraint set, the rebalancing-trigger thresholds, known limitations, and backtest-performance disclosures consistent with the SEC Marketing Rule
- Notify Adopter no less than 10 business days before any production model-version or assumption-set change; 20 business days for any change that shifts the recommended-allocation distribution across the Adopter's book beyond a contractually-set band
- Cooperate in version-change post-mortems when `VendorScoreGate.record_score()` raises `VendorScoreDriftDetected` on the `(vendor_id, input_hash, model_version)` key
- Provide a 60-day rollback option so Adopter can re-score a contested recommendation cohort
- Disclose any retraining, re-optimization, or assumption-refresh event

## Clause 3 — Reproducibility on Request

For any recommendation or rebalancing trigger Adopter consumed in a client-facing action, Adopter MAY request:

- The exact model version, assumption-set version, and optimizer build used
- The exact client-profile input set and the constraint set in force
- The decision-path explanation: the optimizer's objective value, the binding constraints, the marginal contribution of each input dimension, and the alternative-allocation comparison the vendor evaluated
- The Reg-BI-Care-obligation-grade rationale in language suitable for inclusion in the Adopter's Care-obligation documentation

Vendor SHALL provide the reproducibility package within 10 business days of an Adopter audit, SEC or FINRA examination, client complaint, or subpoena. Vendor SHALL provide it within 3 business days for any examiner-driven single-account inquiry.

## Clause 4 — SR 11-7-Adjacent Model Governance

Robo-advisor signal-generation models are not always within the literal scope of SR 11-7 (which applies to banking organizations), but functionally-equivalent model-risk-management discipline is the expectation in SEC and FINRA examinations of automated advice surfaces. Vendor SHALL:

- Maintain model-development documentation comparable in rigor to SR 11-7 standards (theoretical construction, intended use, conceptual soundness, data lineage)
- Subject every production model and optimizer to independent validation by Vendor's second line of defense at least annually
- Provide `ModelInventory`-compatible metadata: `model_id`, `version`, `owner`, `validator`, `implementation_status`, `validation_date`, `next_validation_due`, `material_change_log`
- Make Vendor's validation reports available under NDA for Adopter's compliance and internal-audit review
- Furnish, on examiner request, validation documentation sufficient to support SEC or FINRA examination response under the Adviser's or broker-dealer's compliance program
- Where Adopter is a banking organization or affiliate operating under SR 11-7, all SR 11-7 obligations in Clause 4 of the credit-decision and fraud-score companion documents apply

## Clause 5 — Robo-Advisor-Specific Obligations

Vendor SHALL:

- Document the suitability framework — the mapping from client risk-tolerance, time-horizon, liquidity needs, and stated objectives to the recommended allocation — in a form the Adopter can attach to its Care-obligation file under Reg BI and its suitability file under Rule 2111
- Document the capital-market assumption source, publication cadence, and historical assumption history; assumption changes that produce material allocation shifts SHALL be disclosed in advance per Clause 2
- Maintain conflict-of-interest disclosures aligned with Reg BI's Conflict obligation, including any vendor-side compensation arrangement with fund sponsors, model-portfolio originators, or research providers whose products appear in vendor recommendations
- Disclose any vendor-side affiliations that bias signal generation toward a particular fund family, model-portfolio sponsor, or asset class
- Provide a documented rebalancing-trigger logic and an audit trail of every trigger fired
- Maintain backtest, hypothetical-performance, and predecessor-performance disclosures consistent with the SEC Marketing Rule (17 C.F.R. § 275.206(4)-1) when these are presented to Adopter or the Adopter's clients
- Provide a Form CRS-compatible summary of the vendor relationship that Adopter can incorporate by reference in its Form CRS where appropriate
- Comply with Reg S-ID identity-theft red-flag obligations where vendor-mediated client-onboarding flows are in scope
- Where vendor outputs power a fiduciary advice surface, acknowledge the Adopter's fiduciary duty does not delegate to vendor and that vendor performance failures may give rise to Adopter recourse without limitation of liability beyond customary contract caps

## Clause 6 — Audit and Right to Examine

Adopter MAY, on 30 days' written notice (reduced to 5 days for regulator-driven audits), audit Vendor's:

- Model-validation procedures and the most recent independent validation reports
- Capital-market-assumption release history and methodology
- Conflict-of-interest disclosures and vendor-affiliate compensation arrangements
- Drift-detection cadence and historical drift events on Adopter's book
- Reproducibility infrastructure
- Audit-chain emission completeness against a sampled set of Adopter recommendations
- SOC 2 Type 2 and ISO 27001 control evidence pertinent to client-information safeguards under Reg S-P

Vendor SHALL cooperate at Vendor's reasonable expense.

## Clause 7 — Disclosure to Regulators

Vendor acknowledges that Adopter is subject to examination by the SEC, FINRA, state securities regulators, and where applicable a federal functional banking regulator on a bank-affiliated investment surface, and that Adopter MAY disclose Vendor's outputs, model documentation, capital-market-assumption history, conflict disclosures, and drift-detection logs to:

- The SEC Division of Examinations and Division of Enforcement
- FINRA examiners and Enforcement
- State securities regulators
- External auditors (Big-4 firms acting on Adopter's behalf)
- Outside counsel (for privileged review preceding any required disclosure)

Such disclosure does not constitute waiver of Vendor's trade secrets in jurisdictions recognizing the regulatory-disclosure privilege.

## Clause 8 — Termination and Data Continuity

On termination for any reason, Vendor SHALL:

- Continue serving signals for in-flight recommendation paths and pending rebalancing windows for 30 business days
- Provide a final dump of all audit-chain emissions (Clause 1 fields), suitability-framework documentation, and capital-market-assumption history for the Adopter's compliance retention period — default 5 years under SEC Rule 204-2 (Adviser's books and records), 6 years under FINRA Rule 4511 for broker-dealer records, and 7 years where SEC Rule 17a-4 applies
- Provide all conflict-of-interest disclosures and vendor-affiliate compensation reports in force during the relationship
- Cooperate, at commercial reasonable rates, in any pending or subsequently-noticed SEC, FINRA, or state-securities-regulator examination, or client litigation related to Vendor's outputs for a period of 5 years post-termination
- Surrender or destroy client-profile and recommendation data per the data-retention schedule and provide a certificate of destruction

## References

- ADR-0014 (persistence-witness-timestamp pattern)
- ADR-0016 (vendor-score-gate)
- ADR-0007 (SR 11-7 overlay, where banking-organization Adopter)
- ADR-0013 (SEC 17a-4 WORM retention)
- `docs/sec_reg_bi_mapping.md`
- `docs/sec_17a_4_mapping.md`
- `docs/sr11_7_mapping.md`
- v1.1 module: `finserv_agent_audit.governance.vendor_score_gate`
