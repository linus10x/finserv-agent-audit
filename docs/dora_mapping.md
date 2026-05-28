# EU Digital Operational Resilience Act (DORA) — Control Mapping

**Status:** v2.0.0-draft · Last reviewed: 2026-05-28.
**Audience:** Chief AI Officer, Chief Risk Officer, or Chief Operational Resilience Officer at a US-headquartered financial entity with EU subsidiaries or EU customers; LLM-provider counsel preparing for ICT third-party-service-provider (ICT TPSP) designation; Big-4 advisory partner supporting DORA examination readiness.

This document maps the governance patterns in this repository to the
**Digital Operational Resilience Act (Regulation (EU) 2022/2554)** with
emphasis on **Articles 28-30** governing ICT third-party risk
management — the article cluster where AI vendors squarely sit.

DORA entered into force on **January 16, 2023** and became applicable
on **January 17, 2025**. The Register of Information first submission
to the European Supervisory Authorities (ESAs) was due **April 30,
2025**. Critical ICT third-party-service-provider (CTPP) designations
began in 2025 and are ongoing. Penalties under Article 50 reach
**up to 1% of average daily worldwide turnover per day** for ICT TPSPs
subject to ESA oversight, applied continuously until compliance.

> **Disclaimer:** This mapping is provided for reference only and does
> not constitute legal advice. Engage qualified EU financial-services
> counsel for your specific compliance determination. See repo-root
> [`DISCLAIMER.md`](../DISCLAIMER.md).

---

## Framework Overview

DORA harmonises ICT risk management across **21 categories of EU
financial entities** — credit institutions, payment institutions,
electronic-money institutions, investment firms, crypto-asset service
providers, central securities depositories, central counterparties,
trading venues, trade repositories, managers of alternative investment
funds, management companies, data reporting service providers,
insurance and reinsurance undertakings, insurance intermediaries,
institutions for occupational retirement provision, credit-rating
agencies, administrators of critical benchmarks, crowdfunding service
providers, securitisation repositories, account information service
providers, and (in respect of certain provisions) ICT third-party
service providers.

The substantive obligation set spans five pillars: (1) ICT risk
management (Chapter II); (2) ICT-related incident management,
classification, and reporting (Chapter III); (3) digital operational
resilience testing (Chapter IV); (4) managing ICT third-party risk
(Chapter V); (5) information-sharing arrangements (Chapter VI).

**AI vendors are ICT third-party service providers** under DORA's
definitional scope (Article 3, Definition 19): "an undertaking
providing ICT services." LLM API providers, retrieval-augmented-
generation platform vendors, agentic-orchestration platforms, vector
database vendors, model-evaluation platforms, and fine-tuning
platforms all fall within this definition when supplying services to
an EU financial entity. The Chapter V obligation cluster (Articles
28-30 in particular) applies to those vendor relationships.

For a US-headquartered financial entity with an EU subsidiary (a
common posture for JPMorgan SE, Citi Europe, Bank of New York Mellon
SA/NV based in Brussels, Goldman Sachs Bank Europe SE, Morgan Stanley
Europe SE, and similar EU-incorporated subsidiaries of US parents),
DORA applies at the EU-subsidiary level. The US parent is not directly
subject but inherits group-level operational consequences. For a US
LLM provider serving EU financial entities (OpenAI, Anthropic, Amazon
Web Services Bedrock, Microsoft Azure OpenAI, Google Cloud Vertex AI),
the vendor is squarely in scope as an ICT TPSP and may be designated a
CTPP if the ESAs determine it meets the criticality criteria.

---

## Primary-Source Citations

| Source | Retrieved | Status |
|---|---|---|
| ESMA — Digital Operational Resilience Act (DORA) topic page | 2026-05-28, https://www.esma.europa.eu/esmas-activities/digital-finance-and-innovation/digital-operational-resilience-act-dora | Verified — scope (21 categories of financial entities, 12 under ESMA remit), applicable date (Jan 17, 2025), Register of Information (Art. 28.9 via Implementing Regulation (EU) 2024/2956), CTPP designation (Art. 31.8 via Delegated Regulation (EU) 2024/1502 with first designations 2025), contractual provisions (Art. 28.10 via Delegated Regulation (EU) 2024/1773), subcontracting assessment (Art. 30.5 via Delegated Regulation (EU) 2025/532) |
| EIOPA — Digital Operational Resilience Act (DORA) topic page | 2026-05-28, https://www.eiopa.europa.eu/digital-operational-resilience-act-dora_en | Verified — six obligation pillars (ICT risk management, third-party risk, resilience testing, incident reporting, threat-intelligence sharing, critical-provider oversight); insurance-sector applicability confirmed |
| Regulation (EU) 2022/2554 (DORA) | Referenced; consult EUR-Lex for operative article text | `[UNVERIFIED — full regulation text not fetched this pass; consult eur-lex.europa.eu/eli/reg/2022/2554/oj]` |
| Commission Delegated Regulation (EU) 2024/1773 (RTS on ICT contractual arrangements) | Referenced via ESMA topic page | `[UNVERIFIED — RTS text not fetched this pass]` |
| Commission Implementing Regulation (EU) 2024/2956 (Register of Information template) | Referenced via ESMA topic page | `[UNVERIFIED — implementing regulation text not fetched this pass]` |

---

## Article-by-Article Mapping — Articles 28-30 (ICT Third-Party Risk)

DORA's Chapter V is the article cluster where AI-vendor exposure
concentrates. The mapping below is the operative AI-vendor surface.

### Article 28 — General principles for ICT third-party risk

| Article 28 Element | Requirement | Pattern in This Repo | File |
|---|---|---|---|
| Art. 28(1) — Sound, comprehensive, well-documented ICT-third-party-risk management as integral part of ICT risk-management framework | Documented framework; integrated to ICT risk | Maturity model self-score harness drives the framework-state evidence pack | `docs/agentic_ai_governance_maturity_model.md`, `scripts/maturity_self_score.py` |
| Art. 28(2) — Strategy on ICT third-party risk, including policy on use of ICT services supporting critical or important functions | Documented strategy; explicit critical-or-important-function inventory | Autonomy Ladder published A0→A4 classification identifies critical decision classes | `docs/autonomy_ladder.md` |
| Art. 28(3) — Maintain a Register of Information on all contractual arrangements with ICT TPSPs | Register entry per arrangement; populated to the Implementing Regulation (EU) 2024/2956 template; submitted to competent authority annually | Vendor attestation ledger records WHO attested WHAT version on WHAT date with cadence; output is the substrate for the Register | `src/finserv_agent_audit/governance/vendor_attestation_ledger.py` |
| Art. 28(4) — Pre-contractual due diligence on prospective ICT TPSPs | Documented due-diligence prior to contracting | Vendor score gate blocks promotion of any third-party model lacking documented evidence | `src/finserv_agent_audit/governance/vendor_score_gate.py` |
| Art. 28(5) — Periodic risk assessment of ICT third-party risk concentration | Concentration analysis; multi-vendor diversification posture | Vendor attestation ledger query API supports concentration-risk analysis across vendor classes | `src/finserv_agent_audit/governance/vendor_attestation_ledger.py` |
| Art. 28(7)(c) — Contractual termination rights for critical-or-important-function arrangements | Termination triggers documented; exit-strategy enabled | Deprecation watch surfaces sunset windows; vendor-clauses companion ships transition-notice contract language | `src/finserv_agent_audit/governance/deprecation_watch.py`, `vendor-clauses/foundation_model_api_vendor_clauses.md` |
| Art. 28(8) — Exit strategies for ICT services supporting critical or important functions | Documented exit strategy; ability to substitute without disruption | Deprecation watch + shadow-mode pre-validation of substitutes; vendor-clauses transition-notice + transition-assistance covenants | `src/finserv_agent_audit/governance/deprecation_watch.py`, `src/finserv_agent_audit/governance/shadow_mode.py`, `vendor-clauses/` |
| Art. 28(9) — Register of Information per Implementing Regulation (EU) 2024/2956 | Submit register to competent authority annually | `[UNVERIFIED] — the framework produces vendor-by-vendor evidence; the Register submission is the operator's reporting workflow, not a framework artifact` | n/a |

### Article 29 — Preliminary assessment of ICT concentration risk at entity level

| Article 29 Element | Requirement | Pattern in This Repo | File |
|---|---|---|---|
| Art. 29(1) — Assess whether contracting an ICT TPSP for critical-or-important functions would create concentration risk | Pre-contracting concentration analysis | Vendor attestation ledger + vendor-clauses cross-cutting concentration covenants | `src/finserv_agent_audit/governance/vendor_attestation_ledger.py`, `vendor-clauses/` |
| Art. 29(2) — Assess the difficulty of substituting the ICT TPSP | Substitutability analysis prior to contracting | Shadow-mode parallel-evaluation harness supports substitute-vs-incumbent comparison | `src/finserv_agent_audit/governance/shadow_mode.py` |
| Art. 29 — CTPP designation criteria (Art. 31 cross-reference) | The ESAs designate CTPPs based on systemic importance and substitutability; the entity must track which of its vendors are CTPPs | Vendor attestation ledger stores designation status as part of vendor metadata | `src/finserv_agent_audit/governance/vendor_attestation_ledger.py` |

### Article 30 — Key contractual provisions

| Article 30 Element | Requirement | Pattern in This Repo | File |
|---|---|---|---|
| Art. 30(2)(a) — Clear and complete description of ICT services | Service description in writing | Vendor-clauses companion ships service-description templates per vendor class | `vendor-clauses/` |
| Art. 30(2)(b) — Locations of service performance and data processing | Location disclosure; right to require change | Vendor-clauses foundation-model API clauses include data-residency and processing-location language | `vendor-clauses/foundation_model_api_vendor_clauses.md` |
| Art. 30(2)(c) — Confidentiality, data protection, access to recovery | Data-handling covenants | Vendor-clauses companion across all six vendor classes | `vendor-clauses/` |
| Art. 30(2)(e) — Service-level descriptions including updates and revisions | SLA with revision discipline | Vendor-clauses companion ships SLA-and-change-notice language | `vendor-clauses/foundation_model_api_vendor_clauses.md` |
| Art. 30(2)(g) — Notice periods and reporting obligations on TPSP, including notification of any developments that may materially affect the TPSP's capacity to provide the ICT service | Change-notification and material-development reporting | Deprecation watch monitors vendor changelogs; vendor-clauses transition-notice covenants | `src/finserv_agent_audit/governance/deprecation_watch.py`, `vendor-clauses/foundation_model_api_vendor_clauses.md` |
| Art. 30(3)(a) — Audit, inspection, and access rights | Right of audit (and right for competent authority to audit) | Vendor-clauses examination-access language; vendor-attestation-ledger evidence trail supports audit walk | `vendor-clauses/`, `src/finserv_agent_audit/governance/vendor_attestation_ledger.py` |
| Art. 30(3)(c) — ICT-security training and digital-operational-resilience-awareness obligations | Training obligations on TPSP | Vendor-clauses templates include training-attestation language | `vendor-clauses/foundation_model_api_vendor_clauses.md` |
| Art. 30(3)(d) — Participation in TLPT (threat-led penetration testing) where applicable | Cooperation with TLPT exercises | Vendor-clauses TLPT-cooperation covenants | `vendor-clauses/foundation_model_api_vendor_clauses.md` |
| Art. 30(3)(e) — Exit strategies + transition periods | Transition-period covenants + assistance | Vendor-clauses transition-assistance + minimum-notice language; deprecation watch surfaces sunset windows in time to invoke | `vendor-clauses/foundation_model_api_vendor_clauses.md`, `src/finserv_agent_audit/governance/deprecation_watch.py` |
| Art. 30(5) — Subcontracting / fourth-party disclosure per Commission Delegated Regulation (EU) 2025/532 | Material subcontractors enumerated; financial entity's right to object | Vendor-clauses fourth-party-disclosure covenants; vendor-attestation-ledger sub-tier tracking | `vendor-clauses/foundation_model_api_vendor_clauses.md`, `src/finserv_agent_audit/governance/vendor_attestation_ledger.py` |

---

## ICT Incident Reporting (Article 19) — AI-Vector Coverage

DORA Article 19 requires classification and reporting of
"major ICT-related incidents" to competent authorities. AI-vector
events count when they meet the major-incident classification
thresholds.

| Incident class | Pattern in this repo |
|---|---|
| Major ICT incident notification (Art. 19(1)) | Audit-chain walk-back replay produces the incident-reconstruction evidence pack; `ai_incident_retrospective_template.md` covers the postmortem |
| Significant cyber-threat reporting (Art. 19(2)) | DEFCON state transitions are board-visible signals; the May 2026 NYDFS frontier-AI letter pattern (see `docs/nydfs_part500_ai_mapping.md`) is the closest US analog |
| Recurrence root-cause analysis | `docs/ai_incident_retrospective_template.md` provides the Google-SRE-style postmortem |

---

## US-FSI Relevance — Who Cares About DORA from a US Perspective

DORA is an EU regulation, but the US-FSI population with substantive
DORA exposure is broad:

**US banks with EU subsidiaries** (DORA applies to the EU subsidiary
directly; the US parent inherits operational consequences):
- JPMorgan SE (Frankfurt)
- Citigroup Global Markets Europe AG and Citibank Europe plc
- Bank of New York Mellon SA/NV (Brussels)
- Goldman Sachs Bank Europe SE (Frankfurt)
- Morgan Stanley Europe SE (Frankfurt)
- State Street Bank International GmbH
- Wells Fargo Bank International Unlimited Company (Ireland)
- Bank of America Europe Designated Activity Company (Ireland)

**US insurers and reinsurers with EU operations.** DORA applies to
EU-incorporated insurance undertakings and intermediaries; US groups
operating through EU subsidiaries inherit the obligation set.

**US LLM and AI-infrastructure vendors serving EU financial entities**
(directly in scope as ICT TPSPs and at risk of CTPP designation):
- OpenAI (API + Enterprise)
- Anthropic (Claude API + Enterprise)
- Amazon Web Services (Bedrock + foundation-model hosting)
- Microsoft (Azure OpenAI Service)
- Google Cloud (Vertex AI)
- Databricks, Snowflake, NVIDIA NIM, Cohere, Mistral AI (EU-domiciled
  but EU-financial-entity-facing services are covered)

**US RAG / agentic-orchestration platforms.** LangChain Hub, LlamaIndex
Cloud, CrewAI, AutoGen Studio, and similar platforms supplying
agentic-orchestration capability to EU financial entities are ICT TPSPs
under the definition.

For each of these populations, the framework's modules supply the
substantive evidence the DORA contractual + audit-trail + register
obligations require.

---

## Module Coverage Detail

### Vendor Score Gate (`vendor_score_gate`)

Pre-promotion gate that blocks any third-party model promotion lacking
documented evidence: license attestation, red-team artifacts,
SOC 2 / ISO 27001 / ISO 42001 evidence, and per-vendor-class
substantive testing. Maps to DORA Art. 28(4) pre-contractual due
diligence.

### Vendor Attestation Ledger (`vendor_attestation_ledger`)

Records WHO attested WHAT version on WHAT date with cadence. The
ledger is the substrate for the DORA Art. 28(3) Register of
Information. Designed to support re-attestation on a regulatory cadence
and to produce chain-of-custody evidence the third-line auditor can
replay. Cross-references SOC 2, ISO 27001, ISO 42001, FedRAMP, PCI
DSS, HITRUST, and SR 11-7 validation pass-through tokens.

### Deprecation Watch (`deprecation_watch`)

Polling harness for vendor changelogs; computes days-until-sunset;
emits an audit-chain `DEPRECATION_ALERT` while there is still time to
swap the upstream. Maps to DORA Art. 30(2)(g) material-development
notification and Art. 30(3)(e) exit-strategy invocation timing.
Calibrated against the 14-day notice precedent (Novita, January 2026).

### Foundation-model API vendor clauses (`vendor-clauses/foundation_model_api_vendor_clauses.md`)

Reusable contract language for foundation-model-API arrangements with
EU financial entities. Covers DORA Art. 30(2) and (3) substantive
provisions: service description, location, data protection,
service-level, change notice, audit / inspection / access,
ICT-security training, TLPT cooperation, exit strategy + transition,
and subcontracting disclosure.

---

## Gap Analysis — What This Repo Does NOT Cover for DORA

| Requirement | Gap | Guidance |
|---|---|---|
| Register of Information annual submission to competent authority (Art. 28.3) | Reporting workflow, not framework code | The framework produces vendor-by-vendor evidence; the financial entity must wire the submission workflow to its competent authority |
| Threat-led penetration testing (TLPT) coordination (Arts. 26-27) | TLPT is a coordinated examination exercise, not a framework artifact | Engage a TIBER-EU-accredited threat-intelligence and red-team provider |
| Major-incident-reporting workflow to ESA (Art. 19) | Reporting-channel integration, not framework code | The framework produces the incident reconstruction; the reporting submission must be wired to the financial entity's competent authority |
| CTPP designation tracking (Art. 31) | Designation is an ESA action, not a framework artifact | The vendor-attestation-ledger metadata supports tracking; the operator must monitor ESA publications for designation actions |
| Concentration-risk quantitative modeling (Art. 29) | Quantitative-modeling workstream beyond framework scope | Engage the operational-risk team for concentration-risk quantification |
| Information-sharing arrangement participation (Art. 45) | Industry-association participation, not framework code | Participate via the relevant industry-association ICT-threat-intelligence forum |
| Digital operational resilience testing program (Chapter IV) | Program-level, not framework code | The framework supplies the audit-chain substrate for test-result capture; the test program itself is broader |

---

## DORA + US Regulatory Cross-References

For US-FSI operators with both US and EU obligations, the framework's
mappings stack:

- **DORA + NYDFS Part 500** — US bank with EU subsidiary and New York
  office; the DORA ICT-third-party-risk obligations parallel the NYDFS
  Part 500 § 500.11 third-party obligations. See
  [`docs/nydfs_part500_ai_mapping.md`](nydfs_part500_ai_mapping.md).
- **DORA + Interagency MRM 2026 Overlay** — DORA's ICT-third-party
  cluster substitutes for the SR 11-7 third-party-validation
  pass-through in EU-touching deployments. See
  [`docs/interagency_mrm_2026_overlay.md`](interagency_mrm_2026_overlay.md).
- **DORA + EU AI Act** — DORA covers operational resilience; the EU
  AI Act covers AI-specific high-risk obligations. The two regimes
  apply concurrently. See
  [`docs/eu_ai_act_mapping.md`](eu_ai_act_mapping.md) and
  [`docs/eu_ai_act_aug_2026_compliance_pack.md`](eu_ai_act_aug_2026_compliance_pack.md).

---

## References

- European Securities and Markets Authority. *Digital Operational
  Resilience Act (DORA).*
  <https://www.esma.europa.eu/esmas-activities/digital-finance-and-innovation/digital-operational-resilience-act-dora>
  (retrieved 2026-05-28).
- European Insurance and Occupational Pensions Authority. *Digital
  Operational Resilience Act (DORA).*
  <https://www.eiopa.europa.eu/digital-operational-resilience-act-dora_en>
  (retrieved 2026-05-28).
- Regulation (EU) 2022/2554 of the European Parliament and of the
  Council of 14 December 2022 on digital operational resilience for
  the financial sector.
- Commission Delegated Regulation (EU) 2024/1773 (RTS on ICT
  contractual arrangements).
- Commission Implementing Regulation (EU) 2024/2956 (Register of
  Information template).
- Commission Delegated Regulation (EU) 2024/1502 (RTS on CTPP
  designation criteria).
- Commission Delegated Regulation (EU) 2025/532 (RTS on
  subcontracting assessment).
- Patterns in this repo:
  `src/finserv_agent_audit/governance/vendor_score_gate.py`,
  `src/finserv_agent_audit/governance/vendor_attestation_ledger.py`,
  `src/finserv_agent_audit/governance/deprecation_watch.py`,
  `src/finserv_agent_audit/governance/shadow_mode.py`,
  `src/finserv_agent_audit/governance/audit_chain.py`,
  `src/finserv_agent_audit/governance/witness_anchor.py`,
  `vendor-clauses/foundation_model_api_vendor_clauses.md`,
  `vendor-clauses/`,
  `docs/autonomy_ladder.md`,
  `docs/agentic_ai_governance_maturity_model.md`,
  `docs/ai_incident_retrospective_template.md`.
- Related mappings:
  [`docs/eu_ai_act_mapping.md`](eu_ai_act_mapping.md),
  [`docs/eu_ai_act_aug_2026_compliance_pack.md`](eu_ai_act_aug_2026_compliance_pack.md),
  [`docs/nydfs_part500_ai_mapping.md`](nydfs_part500_ai_mapping.md),
  [`docs/interagency_mrm_2026_overlay.md`](interagency_mrm_2026_overlay.md).
- ADR cross-references: ADR-0014 (Persistence / Witness / Timestamp),
  ADR-0016 (Vendor Score Gate), ADR-0023 (Vendor Attestation Ledger),
  ADR-0025 (Deprecation Watch).
