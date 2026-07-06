# EU AI Act — August 2, 2026 High-Risk Compliance Pack for US FSI

**Status:** v2.0.0-draft · Last reviewed: 2026-05-28.
**Audience:** Chief AI Officer, Chief Compliance Officer, or General Counsel at a US-headquartered financial-services institution serving EU customers (including consumers, retail-banking customers, life or health policyholders, and asset-management clients with EU domicile); Big-4 advisory partner advising on EU AI Act readiness.

This compliance pack is the operative companion to
[`docs/eu_ai_act_mapping.md`](eu_ai_act_mapping.md). The mapping
document covers the article-by-article control surface; this pack
covers the **August 2, 2026** application-date forcing function and
the specific Annex III FSI high-risk categories that pull a US
financial-services institution into scope when it serves EU customers.

> **Disclaimer:** This compliance pack is provided for reference only
> and does not constitute legal advice. Engage qualified EU AI Act
> counsel for your specific compliance determination. See repo-root
> [`DISCLAIMER.md`](../DISCLAIMER.md).

---

## Framework Overview — The Phased Application Calendar

| Date | Application |
|---|---|
| **February 2, 2025** | Prohibited-practice provisions (Title II) and AI-literacy provisions entered into force |
| **August 2, 2025** | Governance rules and General-Purpose AI (GPAI) obligations became applicable |
| **August 2, 2026** | **Full applicability** — high-risk system obligations (Chapter III) including Articles 8-15 substantive requirements, conformity-assessment obligations (Art. 43), registration in the EU AI database (Art. 49), and post-market monitoring (Art. 72) become applicable to Annex III high-risk systems |
| **August 2, 2027** | Extended application for high-risk systems integrated into products subject to Union harmonisation legislation listed in Annex I, and certain GPAI-model obligations for models placed on the market before August 2, 2025 |
| **December 2, 2027** | Specific high-risk systems in named domains (biometrics, critical infrastructure, education, employment, migration, asylum, border control) |
| **August 2, 2028** | Rules for high-risk systems embedded into products covered by Annex I Section B |

The **August 2, 2026** date is the operative forcing function for the
FSI Annex III categories. A US-headquartered financial-services
institution placing an in-scope high-risk AI system on the EU market —
or putting one into service for an EU customer or for an EU-based
controller — must meet the Chapter III obligation set by that date.

> Application-date sourcing: European Commission, *Regulatory framework
> for AI*, <https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai>
> (retrieved 2026-05-28). The Commission's topic page states "February
> 2, 2025: Prohibited practices entered into force", "August 2, 2025:
> Governance rules and GPAI obligations became applicable", "August 2,
> 2026: Full applicability", "December 2, 2027: Rules for high-risk
> systems in specific domains", and "August 2, 2028: Rules for
> high-risk systems embedded into products". The Aug 2, 2027 date for
> certain GPAI-model legacy obligations is cited in the EU AI Act
> implementation literature but was not surfaced verbatim on the
> Commission topic page during this mapping refresh —
> `[UNVERIFIED — re-check against the live AI Office implementation
> tracker before relying on this column for an operative date]`.

---

## Primary-Source Citations

| Source | Retrieved | Status |
|---|---|---|
| European Commission — Regulatory framework for AI | 2026-05-28, https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai | Verified — application calendar, high-risk obligation summary (risk assessment, dataset quality, logging, technical documentation, human oversight, accuracy / cybersecurity) |
| EU AI Act — Annex III | 2026-05-28, https://artificialintelligenceact.eu/annex/3/ | Verified — Annex III Category 5(b) creditworthiness / credit scoring; Category 5(c) life and health insurance risk assessment and pricing; both fall under Section 5 (Access to and enjoyment of essential private services and essential public services and benefits) |
| Regulation (EU) 2024/1689 (the AI Act) | Referenced; consult EUR-Lex for operative article text | `[UNVERIFIED — full regulation text not fetched this pass; consult eur-lex.europa.eu/eli/reg/2024/1689/oj]` |

---

## Annex III FSI High-Risk Scope — Three Categories That Pull a US FSI Into Scope

The Annex III categories below capture the bulk of US-FSI AI use
serving EU customers. Each category triggers the full Chapter III
obligation set (Articles 8-15, plus conformity assessment, registration,
and post-market monitoring).

### Category 5(b) — Creditworthiness Evaluation and Credit Scoring

**Verbatim Annex III text:** "AI systems intended to be used to
evaluate the creditworthiness of natural persons or establish their
credit score, with the exception of AI systems used for the purpose of
detecting financial fraud."

**Scope.** Any AI system that produces a creditworthiness assessment
or a credit score on a natural person. Includes:

- Personal-loan underwriting models
- Credit-card line-assignment models
- Mortgage prequalification + underwriting models
- Buy-now-pay-later approval models
- Small-business owner-personal-guarantee creditworthiness models
- LLM-mediated credit-decision agents (the agent is the AI system; the
  underlying LLM is a component of the system)
- Agentic-orchestration platforms that wrap a credit-decision LLM with
  retrieval and policy-application steps

**Out of scope (by exception).** Pure fraud-detection systems. The
exception is narrow — a system that produces a creditworthiness
output AND a fraud signal is in scope for the creditworthiness output.

**US-FSI population in scope.** US banks (JPMorgan Chase, Capital One,
Citi, Bank of America, US Bancorp, Wells Fargo) serving EU customers;
US fintechs (Affirm, Klarna US operations, Upstart, SoFi, Block,
PayPal) with EU consumer touch; US-domiciled cards networks
(American Express, Discover, Synchrony) with EU cardholder issuance.

### Category 5(c) — Life and Health Insurance Risk Assessment and Pricing

**Verbatim Annex III text:** "AI systems intended to be used for risk
assessment and pricing in relation to natural persons in the case of
life and health insurance."

**Scope.** Any AI system used in life-insurance or health-insurance
underwriting or pricing on a natural person. Includes:

- Life-insurance underwriting models (mortality risk)
- Health-insurance underwriting models (morbidity risk; medical-
  expense risk)
- Annuity pricing models touching life-contingent components
- Supplemental-health pricing models
- LLM-mediated insurance-underwriting agents

**Out of scope (by category).** Property-and-casualty insurance,
auto insurance, and commercial-lines underwriting (the Annex III text
is explicit about "life and health"). Property-and-casualty AI may
still be high-risk under other Annex III sections, but not 5(c).

**US-FSI population in scope.** US life insurers (Prudential
Financial, MetLife, New York Life, MassMutual, Northwestern Mutual,
TIAA, Guardian Life) with EU policyholders; US health insurers
with EU expatriate-coverage products; US reinsurers (Berkshire
Hathaway Re, RGA) on EU-ceded business.

### Category 5(a) — Access to Essential Services More Broadly

While not specifically credit or insurance, Section 5(a) covers
"AI systems intended to be used by public authorities or on behalf of
public authorities to evaluate the eligibility of natural persons for
essential public assistance benefits and services," which can extend
to AI tools FSIs supply to government for benefits-disbursement
adjudication.

---

## Article-by-Article Compliance Walkthrough

The table below maps each substantive Chapter III article to the
framework's coverage. The mapping pulls forward and amplifies the
table in [`docs/eu_ai_act_mapping.md`](eu_ai_act_mapping.md).

| Article | Requirement | Pattern in This Repo | File |
|---|---|---|---|
| Art. 8 — Compliance with the requirements | Establish and maintain compliance with Arts. 9-15 across the system's lifecycle | Maturity model self-score harness drives the lifecycle-state evidence pack | `docs/agentic_ai_governance_maturity_model.md`, `scripts/maturity_self_score.py` |
| Art. 9 — Risk management system | Documented risk-management system applied across the lifecycle | DEFCON state machine — continuous risk evaluation with hysteresis-controlled transitions | `examples/defcon_state_machine.py`, `src/finserv_agent_audit/governance/defcon.py` |
| Art. 10 — Data and data governance | Training, validation, and test datasets meet quality criteria; bias-mitigation measures; data governance | Equity audit + LDA-search harness + LLM disparate-impact harness; protected-class proxy detector (MI / LDA arms shipped; SHAP / CDD arms on v1.4 roadmap) | `src/finserv_agent_audit/governance/equity_audit.py`, `src/finserv_agent_audit/governance/lda_search.py`, `src/finserv_agent_audit/governance/llm_disparate_impact_harness.py`, `src/finserv_agent_audit/governance/protected_class_proxy_detector.py` |
| Art. 11 — Technical documentation (and Annex IV detail) | Detailed technical documentation including intended purpose, system design, training methodology, post-market monitoring plan, **AI bill of materials (AIBOM) components** | Every audit-chain entry carries the model_version, prompt_version, policy_version, and rationale; AIBOM generator (v2.0.B work product) consolidates the per-component evidence; vendor attestation ledger supplies the third-party-component evidence | `src/finserv_agent_audit/schemas/audit_event.py`, `src/finserv_agent_audit/governance/vendor_attestation_ledger.py` |
| Art. 12 — Record-keeping (logging) | Automatic logging of events over the system's lifecycle | SHA-256 hash-chained audit ledger with WORM-eligible storage; RFC 3161 trusted-timestamp source; external-witness anchor (OpenTimestamps / Sigstore Rekor) | `src/finserv_agent_audit/governance/audit_chain.py`, `src/finserv_agent_audit/governance/ledger_store_worm.py`, `src/finserv_agent_audit/governance/timestamp_source.py`, `src/finserv_agent_audit/governance/witness_anchor.py` |
| Art. 13 — Transparency and provision of information to deployers | Instructions for use; intended purpose; characteristics, capabilities, and limitations | Autonomy Ladder published A0→A4 classification per decision class; customer-facing chatbot guardrail covers the consumer-facing disclosure | `docs/autonomy_ladder.md`, `src/finserv_agent_audit/governance/customer_facing_chatbot_guardrail.py` |
| Art. 14 — Human oversight | Effective human oversight by natural persons during the use of the system; ability to intervene or interrupt | Sovereign veto hard-stop with documented human clearance; adverse-action gate (FCRA Reg V analog) for credit-decision contexts | `src/finserv_agent_audit/governance/sovereign_veto.py`, `src/finserv_agent_audit/governance/adverse_action_gate.py` |
| Art. 15 — Accuracy, robustness, cybersecurity | Appropriate level of accuracy, robustness, and cybersecurity; consistent performance throughout lifecycle | DEFCON hysteresis prevents oscillation under adversarial conditions; MI proxy attests verifier integrity; effective-challenge harness produces second-line challenge evidence | `src/finserv_agent_audit/governance/defcon.py`, `src/finserv_agent_audit/governance/mi_proxy.py`, `src/finserv_agent_audit/governance/effective_challenge_harness.py` |
| Art. 16 — Obligations of providers | Quality management system; technical documentation; record-keeping; conformity assessment; corrective actions | Maturity model self-score + per-regime mapping docs; corrective-action workflow tied to `ai_incident_retrospective_template.md` | `docs/agentic_ai_governance_maturity_model.md`, `docs/ai_incident_retrospective_template.md` |
| Art. 17 — Quality management system | Documented QMS spanning compliance strategy, design control, change management, test, validation, and post-market | Model inventory PROPOSED → IN_VALIDATION → APPROVED_FOR_PRODUCTION → RETIRED state machine; retraining cadence monitor; shadow-mode evaluation | `src/finserv_agent_audit/governance/model_inventory.py`, `src/finserv_agent_audit/governance/retraining_cadence_monitor.py`, `src/finserv_agent_audit/governance/shadow_mode.py` |
| Art. 26 — Obligations of deployers | Use the system per instructions; assign human oversight; monitor operation; retain logs | Audit-chain retention per the deployer-side LedgerStore configuration; sovereign-veto records the human-clearance assignment | `src/finserv_agent_audit/governance/audit_chain.py`, `src/finserv_agent_audit/governance/ledger_store.py`, `src/finserv_agent_audit/governance/sovereign_veto.py` |
| Art. 27 — Fundamental Rights Impact Assessment (FRIA) | Deployers in specified categories must complete a FRIA before deploying a high-risk system | `[UNVERIFIED — the framework supplies the inputs (audit-chain history, bias-testing results, protected-class analysis) but does not ship a FRIA template; consult the AI Office FRIA template]` | n/a |
| Art. 43 — Conformity assessment | Internal control conformity assessment (Annex VI) for most Annex III high-risk systems; third-party conformity assessment for biometrics under Annex VII | Maturity model + audit-chain + per-regime mapping docs supply the substantive evidence; engage an accredited conformity-assessment body for Annex VII paths | `docs/agentic_ai_governance_maturity_model.md`, `docs/pre_examination_ai_self_assessment.md` |
| Art. 49 — Registration in EU AI database | Register high-risk systems before placing on market or putting into service | `[UNVERIFIED — registration is an administrative workflow against the EU AI Office portal; framework does not ship the registration submission]` | n/a |
| Art. 72 — Post-market monitoring | Documented post-market-monitoring system; data collection, documentation, analysis | Retraining cadence monitor + deprecation watch + MI proxy + DEFCON state-machine telemetry | `src/finserv_agent_audit/governance/retraining_cadence_monitor.py`, `src/finserv_agent_audit/governance/deprecation_watch.py`, `src/finserv_agent_audit/governance/mi_proxy.py`, `src/finserv_agent_audit/governance/defcon.py` |
| Art. 73 — Reporting of serious incidents | Provider report of serious incident to market surveillance authority within 15 days (sometimes sooner) | Audit-chain walk-back replay produces the incident reconstruction; `ai_incident_retrospective_template.md` covers the postmortem | `src/finserv_agent_audit/governance/audit_chain.py`, `docs/ai_incident_retrospective_template.md` |

---

## Penalty Matrix

| Breach Class | Penalty Ceiling |
|---|---|
| Prohibited-practice violation (Title II — Art. 5) | Up to €35,000,000 or 7% of total worldwide annual turnover, whichever is higher |
| High-risk obligation violation (Chapter III — Arts. 8-15, 16, 17, 26-29) | Up to €15,000,000 or 3% of total worldwide annual turnover, whichever is higher |
| Provision of incorrect / incomplete / misleading information to notified bodies or authorities | Up to €7,500,000 or 1% of total worldwide annual turnover, whichever is higher |

For SMEs and start-ups, the lower of the absolute and percentage
amounts applies; for other undertakings, the higher applies.

> Penalty-figure sourcing: cited per the EU AI Act published text;
> `[UNVERIFIED — re-confirm against the published Article 99 figures in
> Regulation (EU) 2024/1689 before any pre-submission financial-exposure
> calculation]`.

---

## Compliance-Pack Checklist — 35 Action Items a US FSI Must Complete by August 2, 2026

The checklist below is the operative pre-Aug-2-2026 plan. Items are
grouped by article cluster.

### Scoping (Items 1-5)

- [ ] **1. Inventory every AI system in production touching EU customers.** Run `ModelInventory.query_by_status(ImplementationStatus.APPROVED_FOR_PRODUCTION)`. Filter by EU-customer exposure.
- [ ] **2. Classify each inventoried system against Annex III Categories 5(b) and 5(c).** For each in-scope system, document the Annex III citation.
- [ ] **3. Confirm provider-vs-deployer posture per system.** US FSI placing a system on the EU market is a provider; US FSI using a third-party system on EU customers is a deployer.
- [ ] **4. Document the fraud-detection exception applicability per credit system.** Mixed creditworthiness-plus-fraud outputs remain in scope.
- [ ] **5. Reconcile the AI inventory against the SR 11-7 inventory of record and the procurement spend record.** Drift here is the most common Aug 2026 finding.

### Article 9 — Risk Management (Items 6-9)

- [ ] **6. Deploy DEFCON state machine.** Calibrate thresholds to the system's risk tolerance.
- [ ] **7. Document the risk-management policy** as a written program covering the full system lifecycle.
- [ ] **8. Establish hysteresis-controlled transitions.** De-escalation must require more confirmations than escalation.
- [ ] **9. Tie DEFCON transitions to the audit chain.** Every transition is a chain event.

### Article 10 — Data Governance (Items 10-14)

- [ ] **10. Run `equity_audit` per in-scope system.** Document the population, the test, the result.
- [ ] **11. Run `protected_class_proxy_detector` MI and LDA arms** for each credit and insurance system.
- [ ] **12. Run `llm_disparate_impact_harness`** for any LLM-mediated credit or insurance decision.
- [ ] **13. Document data-quality controls and dataset lineage.** Audit-chain entries should carry dataset_hash where applicable.
- [ ] **14. Establish bias-mitigation measures** appropriate to the system's risk class.

### Article 11 — Technical Documentation including AIBOM (Items 15-17)

- [ ] **15. Generate the AI Bill of Materials (AIBOM) per in-scope system** using the v2.0.B AIBOM generator. The AIBOM enumerates LLM components, fine-tuning datasets, retrieval indices, agentic-orchestration platforms, and material third-party tools.
- [ ] **16. Compile the Annex IV technical-documentation package** including intended purpose, system architecture, training methodology, validation plan, monitoring plan, and AIBOM.
- [ ] **17. Map each vendor-attestation-ledger entry to the AIBOM component.** Third-party-component evidence ties into the AIBOM via the vendor attestation ledger.

### Article 12 — Logging (Items 18-20)

- [ ] **18. Deploy `AuditChain` per in-scope system** with a WORM-eligible LedgerStore backend.
- [ ] **19. Pair the chain with an RFC 3161 trusted-timestamp source** for chain-of-custody time anchoring.
- [ ] **20. Anchor the chain head to an external witness register** (OpenTimestamps, Sigstore Rekor, or a regulator-side append-only log) on a documented cadence.

### Article 13 — Transparency (Items 21-22)

- [ ] **21. Publish Autonomy Ladder A0-A4 classification per decision class.** The classification IS the transparency artifact to the deployer when the system is offered to other deployers.
- [ ] **22. Wire `customer_facing_chatbot_guardrail`** to any consumer-facing surface; document disclosure language and escalation paths.

### Article 14 — Human Oversight (Items 23-25)

- [ ] **23. Deploy `sovereign_veto`** per in-scope system. Document the named human clearance role.
- [ ] **24. For credit-decision systems, deploy `adverse_action_gate`.** Aligns with both EU AI Act Art. 14 and US FCRA Reg V analog.
- [ ] **25. Document the human-oversight assignment** in writing per Art. 14(4); ensure assigned natural persons have the competence, training, and authority.

### Article 15 — Accuracy, Robustness, Cybersecurity (Items 26-28)

- [ ] **26. Deploy `mi_proxy`** to attest the verifier itself; document the backend (LocalMIProxy vs substrate-pluggable).
- [ ] **27. Run `effective_challenge_harness`** to produce second-line challenge evidence.
- [ ] **28. Establish cybersecurity controls** appropriate to the system's risk class; cross-reference NYDFS Part 500 mapping for the AI-specific cybersecurity overlay.

### Articles 16-17 — Provider QMS (Items 29-30)

- [ ] **29. Document the Quality Management System (QMS)** per Art. 17 elements; the maturity model + per-regime mapping docs supply the substrate.
- [ ] **30. Wire the corrective-action workflow** to `ai_incident_retrospective_template.md`.

### Articles 26-27 — Deployer Obligations (Items 31-32)

- [ ] **31. For systems used as a deployer, retain logs for at least 6 months** per Art. 26(6); the framework's audit-chain retention supports longer windows.
- [ ] **32. For deployers in scope, complete a Fundamental Rights Impact Assessment (FRIA)** per Art. 27; consult the AI Office FRIA template.

### Articles 43, 49, 72-73 — Conformity, Registration, Monitoring (Items 33-35)

- [ ] **33. Complete the Annex VI internal-control conformity assessment** per in-scope provider system.
- [ ] **34. Register the system in the EU AI database** per Art. 49 before placing on the EU market.
- [ ] **35. Establish the post-market monitoring program** per Art. 72; tie to `retraining_cadence_monitor`, `deprecation_watch`, `mi_proxy`, and DEFCON telemetry.

---

## Gap Analysis — Beyond the Framework's Coverage

| Requirement | Gap | Guidance |
|---|---|---|
| Conformity assessment (Art. 43) third-party-body path | Out-of-scope for framework code | Engage an accredited conformity-assessment body for any system requiring Annex VII paths |
| Registration in EU AI database (Art. 49) | Administrative workflow against the EU AI Office portal | Operator workflow; framework supplies inputs |
| Fundamental Rights Impact Assessment (Art. 27) | Structured assessment process, not framework code | Use the AI Office FRIA template (forthcoming as of 2026-05-28) |
| Notified-body interactions | Out-of-scope for framework code | Engage qualified counsel for notified-body management |
| EU representative (Art. 22 for non-EU providers) | Legal-entity workflow | US-headquartered providers must appoint an EU-established authorised representative |
| EU AI Office direct examination posture | Examination-process discipline, not framework code | The framework's pre-examination self-assessment supplies the substrate |

---

## References

- European Commission. *Regulatory framework for artificial
  intelligence.*
  <https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai>
  (retrieved 2026-05-28).
- EU Artificial Intelligence Act — Annex III.
  <https://artificialintelligenceact.eu/annex/3/> (retrieved 2026-05-28).
- Regulation (EU) 2024/1689 of the European Parliament and of the
  Council laying down harmonised rules on artificial intelligence
  (Artificial Intelligence Act).
- Companion mapping:
  [`docs/eu_ai_act_mapping.md`](eu_ai_act_mapping.md) —
  article-by-article control mapping (parent doc).
- Companion mapping:
  [`docs/dora_mapping.md`](dora_mapping.md) — DORA + AI Act stack
  for US-FSI operators with EU operations.
- Patterns in this repo:
  `src/finserv_agent_audit/governance/audit_chain.py`,
  `src/finserv_agent_audit/governance/defcon.py`,
  `src/finserv_agent_audit/governance/sovereign_veto.py`,
  `src/finserv_agent_audit/governance/adverse_action_gate.py`,
  `src/finserv_agent_audit/governance/equity_audit.py`,
  `src/finserv_agent_audit/governance/lda_search.py`,
  `src/finserv_agent_audit/governance/llm_disparate_impact_harness.py`,
  `src/finserv_agent_audit/governance/protected_class_proxy_detector.py`,
  `src/finserv_agent_audit/governance/effective_challenge_harness.py`,
  `src/finserv_agent_audit/governance/mi_proxy.py`,
  `src/finserv_agent_audit/governance/model_inventory.py`,
  `src/finserv_agent_audit/governance/shadow_mode.py`,
  `src/finserv_agent_audit/governance/vendor_attestation_ledger.py`,
  `src/finserv_agent_audit/governance/vendor_score_gate.py`,
  `src/finserv_agent_audit/governance/deprecation_watch.py`,
  `src/finserv_agent_audit/governance/retraining_cadence_monitor.py`,
  `src/finserv_agent_audit/governance/customer_facing_chatbot_guardrail.py`,
  `src/finserv_agent_audit/governance/witness_anchor.py`,
  `src/finserv_agent_audit/governance/timestamp_source.py`,
  `src/finserv_agent_audit/governance/ledger_store_worm.py`,
  `docs/autonomy_ladder.md`,
  `docs/agentic_ai_governance_maturity_model.md`,
  `docs/ai_incident_retrospective_template.md`,
  `docs/pre_examination_ai_self_assessment.md`.
- ADR cross-references: ADR-0001 (DEFCON), ADR-0002 (Sovereign Veto),
  ADR-0003 (Hash-chain audit), ADR-0004 (Autonomy Ladder A0-A4),
  ADR-0005 (EU AI Act mapping), ADR-0014 (Persistence / Witness /
  Timestamp), ADR-0015 (MI Proxy), ADR-0016 (Vendor Score Gate),
  ADR-0019 (Protected-Class Proxy Detector), ADR-0020 (LDA Search),
  ADR-0021 (LLM Disparate-Impact Harness), ADR-0022 (Effective
  Challenge), ADR-0023 (Vendor Attestation Ledger), ADR-0024
  (Retraining Cadence Monitor), ADR-0025 (Deprecation Watch),
  ADR-0026 (Customer-Facing Chatbot Guardrail).
