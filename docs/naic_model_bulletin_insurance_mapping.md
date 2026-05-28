# NAIC Model Bulletin on Use of AI Systems by Insurers — Control Mapping

**Status:** v2.0.0-draft · Last reviewed: 2026-05-28.
**Audience:** Chief AI Officer or Chief Risk Officer at a US insurance carrier (life, health, P&C, supplemental); Big-4 advisory partner supporting an insurance client through NAIC Model Bulletin examination readiness.

This document maps the governance patterns in this repository to the
**NAIC Model Bulletin on the Use of Artificial Intelligence Systems by
Insurers** adopted by the NAIC membership on **December 4, 2023**, and
to the **AI Systems Evaluation Tool (AISET)** pilot launched by the
NAIC Big Data and Artificial Intelligence (H) Working Group in
**January 2026**.

The Model Bulletin is not a model law — adopting jurisdictions issue it
as a bulletin under existing market-conduct authority, which means
adoption produces immediate examination consequences without requiring
new legislation. As of the May 2026 mapping refresh, **23 to 24 states
plus the District of Columbia** have adopted the bulletin substantively
verbatim or with limited material deviations.

> **Disclaimer:** This mapping is provided for reference only and does
> not constitute legal advice. Engage qualified insurance regulatory
> counsel for your specific compliance determination. See repo-root
> [`DISCLAIMER.md`](../DISCLAIMER.md).

---

## Framework Overview

The Model Bulletin asserts that decisions or actions impacting
consumers — adverse underwriting decisions, claims denials, rating
factors, fraud-flag investigations, marketing audience selection — that
are made or supported by AI Systems must be subject to a documented
**AI Systems (AIS) program** that aligns with the four governance
principles the bulletin codifies as **FACT**: **Fair and Ethical**,
**Accountable**, **Compliant**, and **Transparent and Secure**.

The bulletin organizes carrier obligations across four sections:

1. **Governance** — Board-level or senior-executive accountability for
   AI use; written governance framework; risk-tiered review of AI
   systems by use case.
2. **Risk Management and Internal Controls** — Pre-deployment testing,
   ongoing monitoring, validation against bias and discrimination,
   data-quality controls, change management.
3. **Third-Party AI Systems and Data** — Due diligence on vendors and
   data providers; written contractual provisions covering
   examination access; ongoing oversight.
4. **Regulatory Oversight and Market Conduct Examinations** — The
   carrier must produce documentation and evidence on examination
   request; the bulletin previews specific document categories.

The **AI Systems Evaluation Tool (AISET)** is the NAIC working group's
2026 examination instrument, piloted in **January 2026** with a
volunteer cohort of state insurance departments. AISET is the
structured interview + document-request workflow an examiner will use
to evaluate a carrier's AIS program for substantive Model Bulletin
alignment.

For a US insurance carrier deploying autonomous AI agents — claims
triage, underwriting recommendation, fraud-score adjudication, customer
service routing, marketing audience selection — every element of the
AIS program is in scope for any examination conducted by an adopting
state.

---

## Primary-Source Citations

| Source | Retrieved | Status |
|---|---|---|
| NAIC Model Bulletin on the Use of Artificial Intelligence Systems by Insurers (adopted December 4, 2023) | 2026-05-28, https://content.naic.org/sites/default/files/cmte-h-big-data-artificial-intelligence-wg-ai-model-bulletin.pdf | `[UNVERIFIED — HTTP 404 on the canonical content.naic.org path during this mapping refresh; consult the current NAIC publication index for the live URL]` |
| NAIC Model Bulletin Adoption Map | 2026-05-28, https://content.naic.org/sites/default/files/cmte-h-big-data-artificial-intelligence-wg-map-ai-model-bulletin.pdf | `[UNVERIFIED — HTTP 404 on the canonical content.naic.org path during this mapping refresh; consult the NAIC Big Data and Artificial Intelligence (H) Working Group landing page for the current adoption tracker]` |
| AI Systems Evaluation Tool (AISET) pilot announcement (January 2026) | Referenced; consult NAIC Big Data and Artificial Intelligence (H) Working Group meeting minutes for primary text | `[UNVERIFIED — primary source not fetched this pass]` |

> Where the NAIC primary URLs returned HTTP 404 during the mapping
> refresh on 2026-05-28, the section text below relies on the public
> Model Bulletin language as widely cited in carrier compliance
> publications. Adopters should re-verify against the live NAIC source
> before relying on this mapping for examination preparation.

---

## Control Mapping Table — NAIC Model Bulletin (with AISET)

| Model Bulletin Section | Requirement | Pattern in This Repo | File |
|---|---|---|---|
| § 2 Governance — board / senior-executive accountability | Documented governance framework with named accountable executive | Autonomy Ladder published A0→A4 classification, accountable-executive sign-off per decision class; Chief AI Officer first-90-days playbook | `docs/autonomy_ladder.md`, `docs/caio_first_90_days_playbook.md` |
| § 2 Governance — written AIS program | Written program covering FACT principles across all AI use | Maturity model self-score harness produces the program-state evidence pack | `docs/agentic_ai_governance_maturity_model.md`, `scripts/maturity_self_score.py` |
| § 3 Risk Management — pre-deployment testing | Documented test plan covering bias, discrimination, accuracy, robustness | Equity audit + LLM disparate-impact harness + LDA-search harness + effective-challenge harness | `src/finserv_agent_audit/governance/equity_audit.py`, `src/finserv_agent_audit/governance/llm_disparate_impact_harness.py`, `src/finserv_agent_audit/governance/lda_search.py`, `src/finserv_agent_audit/governance/effective_challenge_harness.py` |
| § 3 Risk Management — ongoing monitoring | Continuous monitoring for drift, model integrity, scheduled re-validation | MI proxy + retraining cadence monitor + DEFCON state machine | `src/finserv_agent_audit/governance/mi_proxy.py`, `src/finserv_agent_audit/governance/retraining_cadence_monitor.py`, `src/finserv_agent_audit/governance/defcon.py` |
| § 3 Risk Management — model inventory | Current inventory of every AI System in production with lifecycle state | Model inventory primitive with PROPOSED → IN_VALIDATION → APPROVED_FOR_PRODUCTION → RETIRED states | `src/finserv_agent_audit/governance/model_inventory.py` |
| § 3 Risk Management — change management | Documented change process; shadow evaluation of candidate changes | Shadow-mode parallel evaluation prior to binding effect | `src/finserv_agent_audit/governance/shadow_mode.py` |
| § 3 Risk Management — adverse-decision human oversight | Human review gate for adverse consumer decisions | Sovereign veto hard-stop + adverse-action gate (FCRA Reg V analog applies to insurance adverse underwriting actions in many states) | `src/finserv_agent_audit/governance/sovereign_veto.py`, `src/finserv_agent_audit/governance/adverse_action_gate.py` |
| § 3 Risk Management — record-keeping | Audit log sufficient to reconstruct a consumer-affecting decision | SHA-256 hash-chained audit ledger with WORM-eligible storage; RFC 3161 trusted-timestamp source; external-witness anchor | `src/finserv_agent_audit/governance/audit_chain.py`, `src/finserv_agent_audit/governance/ledger_store_worm.py`, `src/finserv_agent_audit/governance/timestamp_source.py`, `src/finserv_agent_audit/governance/witness_anchor.py` |
| § 4 Third-Party AI Systems and Data — due diligence | Pre-promotion due diligence on every third-party model and data provider | Vendor score gate blocks promotion without documented evidence; vendor attestation ledger records who attested what version when | `src/finserv_agent_audit/governance/vendor_score_gate.py`, `src/finserv_agent_audit/governance/vendor_attestation_ledger.py` |
| § 4 Third-Party AI Systems and Data — contractual provisions | Written agreement with examination-access, breach-notification, change-notification provisions | Vendor-clauses companion ships reusable contract language across the five vendor classes plus foundation-model API | `vendor-clauses/kyc_vendor_clauses.md`, `vendor-clauses/fraud_score_vendor_clauses.md`, `vendor-clauses/credit_decision_vendor_clauses.md`, `vendor-clauses/robo_advisor_vendor_clauses.md`, `vendor-clauses/aml_transaction_monitoring_vendor_clauses.md`, `vendor-clauses/foundation_model_api_vendor_clauses.md` |
| § 4 Third-Party AI Systems and Data — change / deprecation tracking | Notification when a third-party model is deprecated or sunset | Deprecation watch harness emits an alert ahead of sunset windows; pairs with vendor-clauses transition-notice covenants | `src/finserv_agent_audit/governance/deprecation_watch.py` |
| § 5 Regulatory Oversight — examination response | Produce documentation on examination request | Pre-examination AI self-assessment template + audit-chain evidence pack | `docs/pre_examination_ai_self_assessment.md`, `examples/evidence_pack_sample/` |
| § 5 Regulatory Oversight — customer-facing chatbots | Disclosure that the consumer is interacting with AI; escalation to a human; transcript retention | Customer-facing chatbot guardrail with disclosure, off-ramp, and full audit-chain transcript capture | `src/finserv_agent_audit/governance/customer_facing_chatbot_guardrail.py` |
| FACT — Fair and Ethical | Bias testing across protected classes | Protected-class proxy detector (MI + LDA arms shipped; SHAP + CDD arms on the v1.4 roadmap) | `src/finserv_agent_audit/governance/protected_class_proxy_detector.py` |
| FACT — Accountable | Named accountable executive + audit trail tied to a person | Audit-chain records `actor_id` on every event; sovereign-veto records the named human clearance | `src/finserv_agent_audit/schemas/audit_event.py`, `src/finserv_agent_audit/governance/sovereign_veto.py` |
| FACT — Compliant | Mapping to applicable regulatory regimes; documentary evidence | Per-regime mapping docs in `docs/`; pre-examination self-assessment | `docs/*_mapping.md`, `docs/pre_examination_ai_self_assessment.md` |
| FACT — Transparent and Secure | Disclosure obligations; cybersecurity controls integrated with AI governance | Customer-facing chatbot guardrail (disclosure); cross-reference to NYDFS Part 500 mapping for cybersecurity overlay | `src/finserv_agent_audit/governance/customer_facing_chatbot_guardrail.py`, `docs/nydfs_part500_ai_mapping.md` |

---

## State Adoption Matrix

The following table summarizes adoption posture as of the **2026-05-28**
mapping refresh. Adoption is a moving target — verify against the
current NAIC adoption tracker before relying on this matrix for
examination prep.

| State | Adoption Status | Effective | Notable Deviations from Model Bulletin |
|---|---|---|---|
| Alaska | Adopted | 2024 | Substantively verbatim |
| Arkansas | Adopted | 2024 | Substantively verbatim |
| Connecticut | Adopted | 2024 | Connecticut had a pre-existing 2022 bulletin; the 2024 NAIC adoption reconciles to the pre-existing framework |
| District of Columbia | Adopted | 2024 | Substantively verbatim |
| Illinois | Adopted | 2024 | Substantively verbatim |
| Iowa | Adopted | 2024 | Substantively verbatim |
| Kentucky | Adopted | 2024 | Substantively verbatim |
| Maryland | Adopted | 2024 | Substantively verbatim |
| Michigan | Adopted | 2024 | Substantively verbatim |
| Nebraska | Adopted | 2024 | Substantively verbatim |
| Nevada | Adopted | 2024 | Substantively verbatim |
| New Hampshire | Adopted | 2024 | Substantively verbatim |
| Oklahoma | Adopted | 2024 | Substantively verbatim |
| Oregon | Adopted | 2024 | Substantively verbatim |
| Pennsylvania | Adopted | 2024 | Substantively verbatim |
| Rhode Island | Adopted | 2024 | Substantively verbatim |
| Vermont | Adopted | 2024 | Substantively verbatim |
| Washington | Adopted | 2024 | Substantively verbatim |
| West Virginia | Adopted | 2024 | Substantively verbatim |
| Virginia | Adopted | 2024 | Substantively verbatim |
| Texas | Adopted | 2025 | Substantively verbatim |
| New York | Pre-existing | 2024-2025 | New York issued the January 2025 Circular Letter on AI in insurance underwriting and pricing; substantively aligns to the bulletin and adds explicit fair-lending overlay tied to NYDFS authority |
| California | Pre-existing | 2024 | California Department of Insurance has separate notices preceding the NAIC bulletin; substantive overlap |
| Colorado | Separate regime | 2023+ | Colorado Reg 10-1-1 governs life-insurer use of external consumer data and algorithms; the bulletin is supplementary, not primary, in Colorado |

> Source posture for the table above: `[UNVERIFIED — synthesized from public carrier compliance publications and NAIC working-group meeting minutes available as of 2026-05-28; consult the live NAIC adoption tracker for the operative list before any examination response]`

The pattern that emerges: most adopting states took the bulletin
substantively verbatim, and the deviations cluster in three categories:
(1) states with pre-existing AI guidance reconciled the bulletin to
the older framework, (2) states with a specific algorithmic-bias
regime (Colorado) treat the bulletin as supplementary, and (3) New
York layered the bulletin into the NYDFS / DFS supervisory program.

---

## AISET Pilot Integration — Demonstrating Examination Readiness

The AISET pilot launched by the NAIC working group in **January 2026**
is the operative examination instrument. The bulletin is the standard;
AISET is the workflow an examiner will execute against the carrier's
AIS program. The framework's modules supply the substantive evidence
AISET expects.

A pre-AISET readiness walk for a carrier should produce:

1. **AIS program inventory.** `ModelInventory.query_by_status(ImplementationStatus.APPROVED_FOR_PRODUCTION)` produces the current production-AI inventory with lifecycle state. Spot-check the inventory against the carrier's model-risk inventory of record.
2. **Bias-testing evidence.** Most-recent `equity_audit` run results per AI System touching adverse consumer decisions; `protected_class_proxy_detector` MI / LDA arm results.
3. **Third-party-vendor inventory.** `vendor_attestation_ledger` history per vendor; `vendor_score_gate` artifacts; current `deprecation_watch` posture.
4. **Audit-chain integrity.** `AuditChain.verify()` on the production chain; most-recent `witness_anchor` external anchor; RFC 3161 trusted-timestamp evidence.
5. **Adverse-decision audit trail.** Pull three consumer-affecting decisions from the audit chain at random; produce the rationale string, the model version, the input hash, the human-clearance record if `sovereign_veto` was invoked.
6. **Maturity self-score.** `scripts/maturity_self_score.py` output; the maturity level the carrier asserts in its AIS program documentation.
7. **Customer-facing-chatbot disclosure log.** `customer_facing_chatbot_guardrail` transcript retention; disclosure verification.
8. **Incident posture.** `docs/ai_incident_retrospective_template.md` instances for any AI-system incident in the examination period.

---

## Gap Analysis — What This Repo Does NOT Cover for Insurance Carriers

| Requirement | Gap | Guidance |
|---|---|---|
| State-specific algorithmic-discrimination regimes (e.g. Colorado Reg 10-1-1 quantitative-testing requirements; New York DFS-Circular-Letter overlay) | Statutory regime, not agent code | Engage state-specific insurance regulatory counsel; pair the bulletin mapping with the state regulation |
| Rate-filing implications of AI rating factors | Actuarial / rate-filing function | Coordinate with the carrier's actuarial team; the bulletin does not displace rate-filing requirements |
| Unfair Trade Practices Act / Unfair Claim Settlement Practices Act application | Statutory regime, not agent code | Engage counsel; the bulletin notes existing UTPA and UCSPA application to AI-mediated practices |
| Claims-handling fairness across protected classes specifically in claims context (not underwriting) | Coverage gap — bias-testing harnesses target underwriting; claims-fairness testing requires extension | Extension on the v1.4 roadmap; consult `docs/agentic_ai_governance_maturity_model.md` Level 5 expectations |
| HIPAA + state genetic-information non-discrimination regimes (life and health insurance specifically) | Out-of-scope for agent-governance code | Engage HIPAA privacy counsel; cross-reference enterprise data governance |
| Producer / agent oversight of AI tools used in distribution | Distribution-channel governance | Carrier-specific distribution-channel program; bulletin notes producer oversight obligation |

---

## What Insurance Adopters Need That Banking Adopters Do Not

The bulletin's insurance-specific surface beyond a bank's existing AI
program:

- **Rating-factor explainability** at a granularity rate filings can
  accommodate; the framework's audit-chain rationale string is the
  substrate, not the rate-filing artifact itself.
- **Claims-handling AI fairness** treated independently from
  underwriting fairness — same harnesses, different population
  selections.
- **Producer-channel disclosure** when AI is used in the sales /
  distribution funnel; the customer-facing chatbot guardrail covers
  the consumer-facing surface but the producer-channel surface is
  carrier-program territory.
- **State-by-state rate-filing alignment** — the bulletin does not
  pre-empt the state rate-filing process; AI use in pricing must
  reconcile to the filing.

---

## References

- NAIC Big Data and Artificial Intelligence (H) Working Group. *Model
  Bulletin on the Use of Artificial Intelligence Systems by Insurers.*
  Adopted December 4, 2023.
- NAIC Big Data and Artificial Intelligence (H) Working Group.
  *AI Systems Evaluation Tool (AISET) pilot.* Launched January 2026.
- Patterns in this repo:
  `src/finserv_agent_audit/governance/audit_chain.py`,
  `src/finserv_agent_audit/governance/model_inventory.py`,
  `src/finserv_agent_audit/governance/sovereign_veto.py`,
  `src/finserv_agent_audit/governance/adverse_action_gate.py`,
  `src/finserv_agent_audit/governance/equity_audit.py`,
  `src/finserv_agent_audit/governance/llm_disparate_impact_harness.py`,
  `src/finserv_agent_audit/governance/lda_search.py`,
  `src/finserv_agent_audit/governance/effective_challenge_harness.py`,
  `src/finserv_agent_audit/governance/protected_class_proxy_detector.py`,
  `src/finserv_agent_audit/governance/customer_facing_chatbot_guardrail.py`,
  `src/finserv_agent_audit/governance/vendor_score_gate.py`,
  `src/finserv_agent_audit/governance/vendor_attestation_ledger.py`,
  `src/finserv_agent_audit/governance/deprecation_watch.py`,
  `src/finserv_agent_audit/governance/retraining_cadence_monitor.py`,
  `src/finserv_agent_audit/governance/mi_proxy.py`,
  `src/finserv_agent_audit/governance/shadow_mode.py`,
  `src/finserv_agent_audit/governance/witness_anchor.py`,
  `src/finserv_agent_audit/governance/timestamp_source.py`,
  `src/finserv_agent_audit/governance/ledger_store_worm.py`,
  `docs/autonomy_ladder.md`,
  `docs/agentic_ai_governance_maturity_model.md`,
  `docs/pre_examination_ai_self_assessment.md`,
  `docs/caio_first_90_days_playbook.md`,
  `docs/ai_incident_retrospective_template.md`,
  `vendor-clauses/`.
- Related mappings:
  [`docs/ecoa_reg_b_mapping.md`](ecoa_reg_b_mapping.md),
  [`docs/fcra_reg_v_mapping.md`](fcra_reg_v_mapping.md),
  [`docs/nydfs_part500_ai_mapping.md`](nydfs_part500_ai_mapping.md),
  [`docs/state_ag_ai_fair_lending_matrix.md`](state_ag_ai_fair_lending_matrix.md),
  [`docs/cfpb_ai_lending_supervisory_landscape.md`](cfpb_ai_lending_supervisory_landscape.md).
- ADR cross-references: ADR-0001 (DEFCON), ADR-0002 (Sovereign Veto),
  ADR-0003 (Hash-chain audit), ADR-0004 (Autonomy Ladder A0-A4),
  ADR-0009 (FCRA Reg V), ADR-0010 (ECOA Reg B), ADR-0014 (Persistence
  / Witness / Timestamp), ADR-0016 (Vendor Score Gate), ADR-0019
  (Protected-Class Proxy Detector), ADR-0020 (LDA Search), ADR-0021
  (LLM Disparate-Impact Harness), ADR-0022 (Effective Challenge),
  ADR-0023 (Vendor Attestation Ledger), ADR-0024 (Retraining Cadence
  Monitor), ADR-0025 (Deprecation Watch), ADR-0026 (Customer-Facing
  Chatbot Guardrail).
