# finserv-agent-audit

**Governance patterns for autonomous AI agents in regulated financial services.**

Extracted from a multi-year build of a 6-agent autonomous trading system — hundreds of engineering sessions, architectural decision records, and documented failure-mode analyses. The source system operates in paper-trading Phase 0; no live capital has been deployed.

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/linus10x/finserv-agent-audit/actions/workflows/ci.yml/badge.svg)](https://github.com/linus10x/finserv-agent-audit/actions)
[![codecov](https://codecov.io/gh/linus10x/finserv-agent-audit/branch/main/graph/badge.svg)](https://codecov.io/gh/linus10x/finserv-agent-audit)
[![mypy](https://img.shields.io/badge/mypy-strict-blue)](https://mypy.readthedocs.io/)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Discussions](https://img.shields.io/github/discussions/linus10x/finserv-agent-audit)](https://github.com/linus10x/finserv-agent-audit/discussions)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen)](pyproject.toml)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20434570.svg)](https://doi.org/10.5281/zenodo.20434570)

---

## Table of Contents

- [Why this exists](#why-this-exists)
- [Quick Start](#quick-start)
- [Architecture Overview](#architecture-overview)
- [Patterns Included](#patterns-included)
- [Real-World Use Cases](#real-world-use-cases)
- [How It Compares](#how-it-compares)
- [Who This Is For](#who-this-is-for)
- [Roadmap](#roadmap)
- [Deployment](#deployment)
- [Commercial Services](#commercial-services)
- [Community](#community)
- [Contributing](#contributing)
- [Author](#author)
- [Citation](#citation)
- [License](#license)

---

## Why this exists

Every team building autonomous AI agents in a regulated environment eventually hits the same wall: the agent does something unexpected, and there is no audit trail, no kill switch, and no governance framework that satisfies a compliance review.

Existing AI safety research focuses on alignment. Existing compliance frameworks focus on humans. Neither addresses the operational reality of an agent that executes hundreds of decisions per day inside a risk-managed financial system.

This repository fills that gap. These are battle-tested patterns — not academic proposals — for teams building agents that must survive a regulatory audit, a risk committee, and a 3am incident.

---

## Quick Start

```bash
# Clone and install
git clone https://github.com/linus10x/finserv-agent-audit.git
cd finserv-agent-audit
pip install -e ".[dev]"

# Run the DEFCON state machine demo
python examples/defcon_state_machine.py

# Run tests
pytest tests/ -v
```

**Under 60 seconds from clone to running demo.** The state machine simulates 10 evaluation cycles, prints the DEFCON level at each step, and writes a JSON audit trail to `output/demo_audit.jsonl`:

```
Scenario                     DEFCON Level
------------------------------------------
Normal conditions            NORMAL
Light drawdown               CAUTION
Moderate drawdown            ALERT
Stress — DANGER              DANGER
Recovery eval 1/3            DANGER      ← hysteresis holding
Recovery eval 2/3            DANGER      ← hysteresis holding
Recovery eval 3/3            ALERT       ← confirmed de-escalation
Continued recovery 1/3       ALERT       ← hysteresis holding
Continued recovery 2/3       ALERT       ← hysteresis holding
Continued recovery 3/3       CAUTION     ← confirmed de-escalation

Audit trail written to: output/demo_audit.jsonl
State persisted to:     output/demo_state.json
```

---

## Architecture Overview

### DEFCON Risk-State Machine

Every agent in a regulated system needs a risk-state machine that degrades gracefully, escalates conservatively, and de-escalates only after sustained confirmation.

```mermaid
stateDiagram-v2
    direction LR
    [*] --> NORMAL

    NORMAL --> CAUTION : drawdown > caution threshold
    CAUTION --> NORMAL : 3 consecutive evals below caution [hysteresis]
    CAUTION --> ALERT : drawdown > alert threshold
    ALERT --> CAUTION : 3 consecutive evals below alert [hysteresis]
    ALERT --> DANGER : drawdown > danger threshold
    DANGER --> ALERT : 3 consecutive evals below danger [hysteresis]
    DANGER --> HALT : drawdown > halt threshold
    HALT --> DANGER : manual override + 3 confirmations only

    NORMAL : NORMAL\nFull execution\nAll strategies active
    CAUTION : CAUTION\nReduced position sizing\nHeightened monitoring
    ALERT : ALERT\nHalf position sizing\nSovereign veto armed
    DANGER : DANGER\nEmergency sizing only\nNew entries blocked
    HALT : HALT\nAll execution suspended\nHuman-in-the-loop required
```

### Sovereign Veto Architecture

```mermaid
flowchart TD
    A[Agent Decision] --> B{Autonomy Level}
    B -->|A0 — Human decides| C[Human Approval Required]
    B -->|A1 — Human in loop| D[Propose → Human Confirms]
    B -->|A2 — Human on loop| E[Execute → Human Can Override]
    B -->|A3 — Human notified| F[Execute → Log → Alert]
    B -->|A4 — Autonomous| G[Execute → Audit Trail Only]

    E --> H{Sovereign Veto?}
    F --> H
    G --> H
    H -->|VETO| I[Immediate Halt + Escalate]
    H -->|PASS| J[Execution Proceeds]

    style I fill:#d73027,color:#fff
    style C fill:#4575b4,color:#fff
    style J fill:#1a9850,color:#fff
```

### Audit Chain (Tamper-Detecting Hash Chain)

```mermaid
flowchart LR
    E1[Event N] -->|SHA-256 hash| H1[Hash N]
    H1 --> E2[Event N+1]
    E2 -->|SHA-256 hash of\nevent + prev hash| H2[Hash N+1]
    H2 --> E3[Event N+2]
    E3 --> H3[Hash N+2]
    H3 --> V[Verifier\nDetects any\ntampering]

    style V fill:#4575b4,color:#fff
```

---

## Patterns Included (v2.0)

**Core governance** (`src/finserv_agent_audit/governance/`)

| Pattern | Module | Covers | Regulation |
|---|---|---|---|
| DEFCON State Machine | `defcon.py` | Risk-state degradation with hysteresis | EU AI Act Art. 9, 15 |
| Sovereign Veto | `sovereign_veto.py` | Human-only kill switch | EU AI Act Art. 14 · MiFID II Art. 17 |
| Audit Chain | `audit_chain.py` | Tamper-detecting hash-chain logging (within-trust-boundary) | EU AI Act Art. 12 · SEC 17a-4 |
| Autonomy Ladder A0→A4 | `autonomy_ladder.py` | A2→A3 promotion-gate runtime helper | EU AI Act Art. 14 · SR 11-7 |
| Shadow Mode Rollout | `shadow_mode.py` | SR 11-7 pre-promotion parallel runs | SR 11-7 |
| LDA Search Harness | `lda_search.py` | Equally-accurate-less-discriminatory alternative search | ECOA · CFPB Circular 2023-09 |
| LLM Disparate-Impact Harness | `llm_disparate_impact_harness.py` | EEOC 4/5ths-rule DI testing for LLM-agent outputs | ECOA · *Mobley v. Workday* |
| Effective Challenge Harness | `effective_challenge_harness.py` | Frontier-API model validation per SR 11-7 | SR 11-7 · OCC 2026-13 |
| Vendor Attestation Ledger | `vendor_attestation_ledger.py` | Third-party model attestation chain-of-custody | Treasury FS AI RMF · DORA Art. 28 |
| Retraining Cadence Monitor | `retraining_cadence_monitor.py` | Weekly / monthly / continuous fine-tune validation cadence | SR 11-7 · OCC 2026-13 |
| Deprecation Watch | `deprecation_watch.py` | Vendor model deprecation calendar with sunset-date assertions | SR 11-7 |
| Customer-Facing Chatbot Guardrail | `customer_facing_chatbot_guardrail.py` | Policy-grounded RAG + commitment interception + fabricated-policy block | *Moffatt v. Air Canada* · EU AI Act Art. 13 |

**Four Protocol seams** (audit-chain integrity layer, [ADR-0014](docs/adr/0014-persistence-witness-timestamp-pattern.md) + [ADR-0015](docs/adr/0015-mi-proxy-module-integrity.md))

| Seam | Module | Default backend (stdlib-only) | Opt-in stronger backends |
|---|---|---|---|
| Ledger persistence | `ledger_store.py` + `_sqlite` + `_jsonl` + `_worm` | `InMemoryLedgerStore` | SQLite · JSONL · WORM (SEC 17a-4) · deployer DynamoDB / S3 Object Lock |
| Trusted time | `timestamp_source.py` + `rfc3161_codec.py` | `LocalClock` | `RFC3161Source` (stdlib DER ASN.1 codec) |
| External witness | `witness_anchor.py` | none | `RekorWitness` (Sigstore) · `OpenTimestampsWitness` · `anchor_to_witness()` helper |
| Verifier integrity | `mi_proxy.py` | `LocalMIProxy` (HMAC-SHA256) | deployer SLSA / in-toto / cosign |

**FSI-specific governance** (net-new for the financial-services vertical)

| Pattern | Module | Covers | Regulation |
|---|---|---|---|
| Vendor Score Gate | `vendor_score_gate.py` | Drift detection on `(vendor_id, input_hash, model_version)` | [ADR-0016](docs/adr/0016-vendor-score-gate.md) |
| Model Inventory | `model_inventory.py` | SR 11-7 three-lines-of-defense model registry | [ADR-0007](docs/adr/0007-sr-11-7-overlay.md) |
| Adverse-Action Gate | `adverse_action_gate.py` | Fails closed on missing reason-code mapping | FCRA § 615 · [CFPB Circular 2022-03](docs/cfpb_circular_2022_03_mapping.md) |
| SAR Workflow Audit | `sar_workflow_audit.py` | AI-influenced SAR decision audit trail | BSA / AML 31 U.S.C. § 5318(g)/(h) |
| Equity Audit | `equity_audit.py` | ECOA / Reg-B fair-lending pre-flight | ECOA 12 C.F.R. § 1002.9 |
| Best-Interest Check | `best_interest_check.py` | Broker-dealer / RIA recommendation gate | SEC Reg-BI |
| Protected-Class Proxy Detector | `protected_class_proxy_detector.py` | Mutual-information arm shipped in v1.2 (closes the v1.1 deferral) | [ADR-0019](docs/adr/0019-protected-class-proxy-detector-deferred.md) |

**Reference agents** (`src/finserv_agent_audit/agents/`)

| Surface | Module | Purpose |
|---|---|---|
| `AuditConsumer` base | `base.py` | Accepts 4 Protocol seams + VendorScoreGate via one injection contract |
| `AuditAgent` · `MonitorAgent` · `OrchestratorAgent` | `audit.py` · `monitor.py` · `orchestrator.py` | Reference wiring |

**Reference integrations** (`examples/integration/`, all stdlib-only by default; opt-in deps import-guarded)

`splunk_audit_sink.py` (HEC) · `datadog_audit_sink.py` (Logs API v2) · `sigstore_rekor_witness_demo.py` (public-good Rekor) · `aws_dynamo_ledger_store.py` (conditional-write split-brain prevention)

**v2.0 Agentic-AI ecosystem adapters** (`src/finserv_agent_audit/integrations/`)

| Adapter | Module | Wraps | Install extra |
|---|---|---|---|
| A2A Audit Adapter | `a2a_adapter.py` | Google / Linux-Foundation Agent2Agent (A2A) Protocol — task-lifecycle and message-exchange events ([ADR-0027](docs/adr/0027-a2a-audit-adapter.md)) | `pip install finserv-agent-audit[a2a]` |
| LangGraph Audit Callback | `langgraph_adapter.py` | LangGraph node / edge / conditional / human-in-the-loop interrupt callbacks ([ADR-0028](docs/adr/0028-langgraph-audit-callback.md)) | `pip install finserv-agent-audit[langgraph]` |
| MAF Audit Adapter | `maf_adapter.py` | Microsoft Agent Framework agent-step + tool-call + orchestrator-handoff hooks ([ADR-0029](docs/adr/0029-maf-audit-adapter.md)) | `pip install finserv-agent-audit[maf]` |
| CrewAI Audit Adapter | `crewai_adapter.py` | CrewAI Crew / Agent / Task lifecycle hooks + tool-invocation events ([ADR-0030](docs/adr/0030-crewai-audit-adapter.md)) | `pip install finserv-agent-audit[crewai]` |

Convenience bundle: `pip install finserv-agent-audit[all-agentic]` installs all four adapters at once.

**v2.0 Platform surfaces**

| Surface | Location | Purpose |
|---|---|---|
| AIBOM Generator | `src/finserv_agent_audit/governance/aibom.py` (`AIBOMGenerator`) | One governance call -> CycloneDX 1.7 ML-BOM + SPDX 3.0 AI Profile dual emit ([ADR-0031](docs/adr/0031-aibom-generator.md)) |
| Governance API | `src/finserv_agent_audit/integrations/governance_api.py` (`create_app`) | FastAPI REST surface (OpenAPI 3.1) + Server-Sent Events live stream for DEFCON, veto log, audit-chain verify, vendor-score drift, deprecation calendar, AIBOM emit; opt-in extra `[api]` ([ADR-0032](docs/adr/0032-fastapi-governance-endpoint.md)) |
| Kubernetes Operator | `deploy/k8s/` | Three CRDs (`AuditChain`, `SovereignVeto`, `ChainSink`) + reconciler skeleton + Kyverno / OPA sample admission policies ([ADR-0033](docs/adr/0033-kubernetes-operator.md)) |
| Adversarial Test Pack | `tests/adversarial/` | Garak probes + Promptfoo scenarios + Python harness coordinating both; per [ADR-0034](docs/adr/0034-adversarial-test-pack.md) and the ADR-0018 threat model |

---

## Regulatory mapping documents (20+ in `docs/`)

**Interagency MRM (post-April 17, 2026):** [Interagency MRM 2026 Overlay](docs/interagency_mrm_2026_overlay.md) · [MRM Bridge Whitepaper Template](docs/MRM_BRIDGE_TEMPLATE.md) — operational reference for agentic-AI workloads during the period between OCC Bulletin 2026-13 (joint OCC/FRB/FDIC, rescinds OCC 2011-12 and excludes generative + agentic AI from scope) and the forthcoming joint RFI.
US Federal Reserve / OCC (legacy citation lineage): [SR 11-7](docs/sr11_7_mapping.md) · [OCC 2011-12](docs/occ_2011_12_mapping.md) — **rescinded by OCC Bulletin 2026-13 (April 17, 2026); retained as conceptual ancestry.**
Consumer protection: [GLBA Safeguards](docs/glba_safeguards_mapping.md) · [FCRA / Reg V](docs/fcra_reg_v_mapping.md) · [ECOA / Reg B](docs/ecoa_reg_b_mapping.md)
BSA / SOX / broker-dealer: [BSA / AML](docs/bsa_aml_mapping.md) · [SOX 404 ITGC](docs/sox_404_itgc_mapping.md) · [SEC 17a-4](docs/sec_17a_4_mapping.md)
SEC + CFPB algorithmic posture: [SEC Reg-BI](docs/sec_reg_bi_mapping.md) · [CFPB Circular 2022-03](docs/cfpb_circular_2022_03_mapping.md) · [CFPB Circular 2023-09](docs/cfpb_circular_2023_09_mapping.md) (AVMs / algorithmic appraisal) · [CFPB AI Lending Supervisory Landscape](docs/cfpb_ai_lending_supervisory_landscape.md)
State + multi-jurisdiction posture: [NYDFS Part 500 AI Mapping](docs/nydfs_part_500_ai_mapping.md) · [State-AG Enforcement Matrix](docs/state_ag_enforcement_matrix.md)
AI-management standards: [NIST AI RMF](docs/nist_ai_rmf_mapping.md) · [NIST AI 600-1 GenAI Profile](docs/nist_ai_600_1_genai_profile_mapping.md) · [Treasury FS AI RMF](docs/treasury_fs_ai_rmf_mapping.md) · [ISO/IEC 42001](docs/iso_42001_mapping.md) · [COSO ICAIR](docs/coso_icair_mapping.md) · [EU AI Act](docs/eu_ai_act_mapping.md)
Incident + disclosure artifacts: [AI Incident Retrospective Template](docs/ai_incident_retrospective_template.md) (NIST AI RMF GOVERN-6.2) · [Disclosure Artifact Templates](docs/disclosure_artifact_templates.md) (adverse-action / model-use / vendor-AI)
Liability anchors: [FSI Settled Matters](docs/fsi_settled_matters.md) (Apple Card / NYDFS · CFPB Circular 2022-03 · CFPB v. Wells Fargo · SEC v. Schwab Intelligent Portfolios · cross-vertical TransUnion)

## Procurement companion (`vendor-clauses/`)

Sales-tool-grade vendor-contract addenda for 6 FSI vendor classes: [KYC](vendor-clauses/kyc_vendor_clauses.md) · [Fraud-Score](vendor-clauses/fraud_score_vendor_clauses.md) · [Credit-Decision](vendor-clauses/credit_decision_vendor_clauses.md) · [Robo-Advisor](vendor-clauses/robo_advisor_vendor_clauses.md) · [AML Transaction Monitoring](vendor-clauses/aml_transaction_monitoring_vendor_clauses.md) · [Foundation-Model API](vendor-clauses/foundation_model_api_vendor_clauses.md) (v1.3 — OpenAI / Anthropic / Google / AWS Bedrock / Azure OpenAI)

## Governance surfaces

[ARCHITECTURE.md](ARCHITECTURE.md) · [FAILURE-MODES.md](FAILURE-MODES.md) (matrix-as-contract, 8 classes) · [LIMITATIONS.md](LIMITATIONS.md) · [DISCLAIMER.md](DISCLAIMER.md) · [SHIP-RECEIPT.md](SHIP-RECEIPT.md) · [VERSIONING.md](VERSIONING.md) · [NEGATIVE-USE-CASES.md](NEGATIVE-USE-CASES.md) · [RESEARCH.md](RESEARCH.md) · [ASSURANCE-GUIDE.md](ASSURANCE-GUIDE.md) (Big-4 audit-evidence walkthrough; v2.0 PCAOB AS 2201 amendments appendix at [docs/pcaob_as_2201_amendments_appendix.md](docs/pcaob_as_2201_amendments_appendix.md)) · [DEPLOY-CHECKLIST.md](DEPLOY-CHECKLIST.md) · [OWNERSHIP.md](OWNERSHIP.md) · [docs/adr/](docs/adr/) (34 governance ADRs)

## v2.1 Hardening Pack (May 2026)

v2.1 closes all 12 Critical findings from a May 2026 6-chamber adversarial deep-dive (architecture · code · security · test strategy · DevOps · deployment lenses) calibrated to the questionnaire bar applied by Tier-1 FSI buyer review boards (JPMC Tech Risk, BoA AppSec, Schwab Compliance Tech, BNY Mellon Trust Architecture, Fidelity Risk, Citi Model Risk, UBS Group Information Security, Broadridge InfoSec, First Data).

**Numbers:** 532 → 630 tests (+98 across the 12 CRs) · 91.74% → 93.47% coverage · `mypy --strict` clean on 46 source files · ruff + format + banned-term + tamper-language drift lints clean · CI now SHA-pins every GitHub Action and runs CodeQL + Bandit + pip-audit + gitleaks + OSV-Scanner per push.

**Tier-1 buyer pre-fills:** v2.1 ships pre-filled vendor questionnaires at [`docs/tier1_buyer_prefills/`](docs/tier1_buyer_prefills/) — SIG Lite 2025 (~60% pre-fill rate) · CSA CAIQ v4.0.3 (~45%) · BITS Shared Assessments AUP (FS-ISAC member-bank deep-review questionnaire).

**Buyer-facing companion docs:** [`docs/ETHICS_WALL.md`](docs/ETHICS_WALL.md) (NTCI buy-side / advisory separation) · [`docs/SOC2_ENGAGEMENT_RFP.md`](docs/SOC2_ENGAGEMENT_RFP.md) (Schellman / A-LIGN / Coalfire RFP template) · [`docs/TRADEMARK.md`](docs/TRADEMARK.md) (Autonomy Ladder™ usage) · [`docs/COHORT_ZERO_PRICING_PUBLIC.md`](docs/COHORT_ZERO_PRICING_PUBLIC.md) (formal $1K pilot publication for the first 5 logos) · [`docs/LFAI_SANDBOX_APPLICATION_DRAFT.md`](docs/LFAI_SANDBOX_APPLICATION_DRAFT.md) · [`docs/CO_MAINTAINER_RECRUITMENT_DRAFT.md`](docs/CO_MAINTAINER_RECRUITMENT_DRAFT.md).

**License optionality (Apache 2.0 standby):** [`LICENSE-APACHE-2.0`](LICENSE-APACHE-2.0) is staged alongside the existing MIT [`LICENSE`](LICENSE) (not replacing it). Adopters whose legal review requires the Apache 2.0 §3 express patent grant can request dual-license election by opening an issue. Rationale in [`MANUAL_REMEDIATION_AUTHOR.md`](MANUAL_REMEDIATION_AUTHOR.md) §2.

Full per-CR remediation detail in [CHANGELOG.md § 2.1.0](CHANGELOG.md). Release notes at [.github/releases/v2.1.0-notes.md](.github/releases/v2.1.0-notes.md).

---

## Real-World Use Cases

These patterns are not academic. They were extracted from an operational autonomous trading research system and have been applied in the following scenarios:

**1. Ransomware recovery — no DR, 12-day window**
When production infrastructure was hard-downed with no disaster recovery available, the Audit Chain and DEFCON patterns provided a verifiable trail of every system decision during the reconstruction period — essential for post-incident regulatory reporting.

**2. Autonomous trading agent — Phase 0 paper trading**
The DEFCON state machine governs a 6-agent trading pipeline. It has prevented over 40 simulated runaway conditions during the paper-trading phase by halting execution before loss thresholds were breached.

**3. EU AI Act readiness assessment**
The EU AI Act mapping document was used as a pre-audit checklist for a wealth management platform serving $750M+ AUM, mapping each automated decision point to the relevant Article requirements.

**4. Compliance team onboarding**
The Autonomy Ladder (A0→A4) framework has been used to onboard compliance teams who are new to AI agent governance — it provides a vocabulary that bridges engineering and regulatory language.

---

## How It Compares

| | finserv-agent-audit | LangChain callbacks | Microsoft agent-governance-toolkit | OWASP LLM Top 10 |
|---|---|---|---|---|
| **Target** | FSI regulated systems | General LLM apps | Enterprise Azure | Security awareness |
| **Kill switch** | ✅ Sovereign Veto | ❌ | ✅ Partial | ❌ |
| **Audit trail** | ✅ Hash-chain | ❌ | ✅ Partial | ❌ |
| **Risk-state machine** | ✅ DEFCON 5-level | ❌ | ❌ | ❌ |
| **Regulation mapping** | ✅ EU AI Act, MiFID II, SEC | ❌ | ✅ EU AI Act | ❌ |
| **Zero dependencies** | ✅ | ❌ (heavy) | ❌ (Azure SDK) | N/A |
| **Runnable examples** | ✅ < 60 sec | ✅ | ⚠️ Complex setup | ❌ |
| **Python 3.12+ typed** | ✅ mypy strict | ⚠️ Partial | ⚠️ Partial | N/A |
| **Agentic-runtime adapters** | ✅ v2.0 — A2A · LangGraph · MAF · CrewAI | ⚠️ LangChain only | ⚠️ Azure-runtime only | ❌ |
| **AIBOM (CycloneDX 1.7 + SPDX 3.0)** | ✅ v2.0 dual emit | ❌ | ❌ | ❌ |
| **REST governance endpoint** | ✅ v2.0 FastAPI + SSE | ❌ | ⚠️ Azure-portal only | ❌ |
| **Kubernetes operator + CRDs** | ✅ v2.0 (AuditChain · SovereignVeto · ChainSink) | ❌ | ❌ | ❌ |
| **Adversarial test pack** | ✅ v2.0 — Garak + Promptfoo + Python harness | ❌ | ❌ | ⚠️ Awareness only |

---

## Who This Is For

- **Engineers** building autonomous agents that execute in regulated environments (trading, lending, insurance, compliance)
- **Risk architects** designing kill-switch and override mechanisms for AI systems
- **Compliance teams** mapping AI agent behavior to EU AI Act, SEC Rule 15c3-5, MiFID II, or SOC 2 requirements
- **CTOs and Chief AI Officers** establishing governance frameworks before regulators ask for them

---

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the full versioned roadmap.

**Shipped in v1.1:** Shadow Mode Rollout · four Protocol seams (LedgerStore + WORM, TimestampSource + RFC3161, WitnessRegister + Sigstore Rekor, MIProxy) · VendorScoreGate with 5 FSI vendor classes · AuditConsumer base + 3 reference agents · 6 FSI-specific governance modules (ModelInventory · AdverseActionGate · SARWorkflowAudit · EquityAudit · BestInterestCheck · v1.1 ProtectedClassProxyDetector API reservation) · 19 governance ADRs · 14 regulatory mapping documents · vendor-clauses procurement companion · 4 reference integrations · mypy --strict CI · 90% coverage gate.

**Shipped in v1.2:** ProtectedClassProxyDetector mutual-information arm (closes the ADR-0019 v1.1 deferral) · OCC 2026-13 overlay · Treasury FS AI RMF + NIST AI 600-1 GenAI Profile mappings · MCP server adapter · OpenTelemetry GenAI emitter · CLI tool (`finserv-audit verify` + `finserv-audit maturity`) · GitHub Actions composite action + reusable workflow · 4 buyer-conversation closers · MRM BRIDGE template · PyPI Trusted Publishing + PEP 740 Sigstore-attested wheels · `tests/test_failure_modes_matrix.py` + `tests/test_doc_staleness.py` drift-detection pack.

**Shipped in v1.3:** LDA Search · LLM Disparate-Impact Harness · Effective Challenge Harness · Vendor Attestation Ledger · Retraining Cadence Monitor · Deprecation Watch · Customer-Facing Chatbot Guardrail · 6 new regulatory + incident + disclosure docs (NYDFS Part 500 · CFPB AI lending supervisory landscape · CFPB Circular 2023-09 · State-AG enforcement matrix · AI incident retrospective template · Disclosure artifact templates) · foundation-model API vendor-clauses (sixth vendor class) · 7 new ADRs (0020-0026).

**Shipped in v2.0:** Four agentic-AI runtime adapters (Google A2A · LangGraph · Microsoft Agent Framework · CrewAI) · AIBOMGenerator (CycloneDX 1.7 ML-BOM + SPDX 3.0 AI Profile dual emit) · FastAPI governance endpoint (OpenAPI 3.1 + SSE) · Kubernetes operator + three CRDs (AuditChain · SovereignVeto · ChainSink) · Kyverno + OPA sample admission policies · adversarial test pack (Garak + Promptfoo + Python harness) · 5 new strategic docs (NAIC Model Bulletin on AI Systems by Insurers · DORA · EU AI Act August 2026 compliance pack · PE portfolio playbook · PCAOB AS 2201 amendments ASSURANCE-GUIDE appendix) · PE portfolio dashboard reference · 8 new ADRs (0027-0034).

**Shipped in v2.1 (Tier-1 FSI-buyer hardening release, 2026-05-28):** All 12 Critical findings (CR-1..CR-12) from the May 2026 6-chamber adversarial deep-dive closed — `AuditChainTamperError` consolidated · `AuditEvent` frozen + self-verifying on replay · TSA pre-digest bound to event content · `AuditChain` thread- and process-safe · DEFCON `metrics_snapshot` covered by canonical hash · RFC 3161 codec bounded + structural ASN.1 walk + Hypothesis fuzz · domain-separated genesis hash · PII hashing via `HashedSubjectId` + `SubjectIdHasher` · `--mi-proxy-key` argv rejected · `BestEffortWORMLedgerStore` rename + filesystem-capability probe · `LocalMIProxyFreshnessCheck` + new `BaselineMIProxy` scaffold · `Authorizer` Protocol + self-clearing rule. SHA-pinned every GitHub Action + CodeQL/Bandit/pip-audit/gitleaks/OSV-Scanner workflows · K8s operator hardening (multi-stage Dockerfile, probes, PDB, network policy, fail-closed Kyverno + OPA) · 11 Tier-2 author-action drafts (`MANUAL_REMEDIATION_AUTHOR.md` + `LICENSE-APACHE-2.0` standby + `ETHICS_WALL.md` + `SOC2_ENGAGEMENT_RFP.md` + `TRADEMARK.md` + `CO_MAINTAINER_RECRUITMENT_DRAFT.md` + `LFAI_SANDBOX_APPLICATION_DRAFT.md` + `COHORT_ZERO_PRICING_PUBLIC.md` + SIG Lite/CAIQ/BITS AUP pre-fills). 532 → 630 tests · 91.74% → 93.47% coverage · `mypy --strict` clean on 46 source files.

**Coming in v1.4 (operational refinements):** Drift Monitor · Explainability Stub · Rate Limiter / Throttle · MiFID II Art. 17 Checklist · additional state-AG enforcement cases as they emerge.

**Coming in v2.2 (ecosystem completion — carried forward from the originally-scoped v2.1):** DSPy adapter · LlamaIndex Workflows adapter · GraphQL governance endpoint (Strawberry-GraphQL alternative to the v2.0 REST surface) · removal of the v1.1 deprecation re-export shims at `patterns/` · `schemas/` · `examples/defcon_state_machine.py` · UK FCA mapping · Singapore MAS mapping · `ProtectedClassProxyDetector` SHAP / CDD arms · LDA-search continuous-feature quantile-binning helper · Sigstore cosign signature verification of `BaselineMIProxy` pinned manifest · `Authorizer` OIDC + SAML reference adapters.

**Coming in v3.0 (async + multi-region + WASM):** Async-native pattern variants for high-throughput pipelines · multi-region audit-chain federation with quorum-anchored witness commits · WASM runtime for client-side guardrail evaluation.

---

## Deployment

Two v2.0 platform surfaces ship deployment artifacts that adopters can lift directly into a regulated environment:

- **Kubernetes operator + CRDs** — `deploy/k8s/` contains the controller manifests, three custom resource definitions (`AuditChain`, `SovereignVeto`, `ChainSink`), and Kyverno + OPA sample admission-policy bundles. See [`deploy/k8s/README.md`](deploy/k8s/README.md) for the one-page deploy walkthrough.
- **FastAPI governance endpoint** — `src/finserv_agent_audit/integrations/governance_api.py` builds an OpenAPI 3.1 REST surface plus a Server-Sent Events live stream for `AuditEvent` flow. Install with `pip install finserv-agent-audit[api]`; serve via `uvicorn finserv_agent_audit.integrations.governance_api:create_app --factory`. See [ADR-0032](docs/adr/0032-fastapi-governance-endpoint.md) for the design rationale, route inventory, and authn / authz integration points.

---

## Commercial Services

The framework is MIT — fork it, ship it, adopt it. The author offers paid productized advisory + assurance services for FSI institutions, Big-4 firms, BigLaw counsel, and PE operating partners that want hands-on deployment or examination-ready audit-evidence packs:

- **Diagnostic** — 2-week structured gap-assessment against the OCC 2026-13 white-space + Treasury FS AI RMF + NIST AI 600-1 GenAI Profile · 5 deliverables incl. scored pre-examination self-assessment + 12-month remediation roadmap
- **Audit** — 6-week implementation-grade engagement producing Big-4-handoff-ready evidence pack + SR 11-7 model-inventory + co-branded `ASSURANCE-GUIDE` walkthrough
- **Retainer** — ongoing access · weekly regulatory-change digest · quarterly maturity rescore · monthly office hours · written Audit/Risk Committee report each quarter
- **Expert Witness** — independent technical expert for fair-lending, model-risk-management, AI-audit-chain forensic depositions and reports
- **Fractional CAIO / CTO** — 6-12 month interim engagement at FSI institutions and PE portcos; DFW-preferred, remote-friendly

Pricing, methodology pages, and intake form: **[autonomy-ladder.io/services](https://autonomy-ladder.io/services)** · or LinkedIn DM with subject `Diagnostic inquiry` to [Kunjar Bhaduri](https://linkedin.com/in/kunjarbhaduri).

Authority moat sits on the public framework. The MIT artifact stays open; paid engagements adapt the framework to a buyer's specific risk surface, regulatory regime, and Big-4 audit-evidence requirements.

Earlier-version deployment walkthroughs (AWS / Azure) remain in [DEPLOY-CHECKLIST.md](DEPLOY-CHECKLIST.md).

---

## Community

- 💬 **Questions and use-case discussion** → [GitHub Discussions](https://github.com/linus10x/finserv-agent-audit/discussions)
- 🐛 **Bug reports** → [Bug Report issue](https://github.com/linus10x/finserv-agent-audit/issues/new?template=bug_report.yml)
- 💡 **Pattern requests** → [Pattern Request issue](https://github.com/linus10x/finserv-agent-audit/issues/new?template=pattern_request.yml)
- 🔒 **Security vulnerabilities** → [Private Security Advisory](https://github.com/linus10x/finserv-agent-audit/security/advisories/new)

If these patterns save you time in a compliance review or prevent a production incident, a ⭐ on the repo helps others find it.

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=linus10x/finserv-agent-audit&type=Date)](https://star-history.com/#linus10x/finserv-agent-audit&Date)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). This repository exists because the failure modes that produced these patterns are real — and the teams dealing with them rarely have reference implementations to work from.

First time contributing to open source? Start with issues labelled [`good first issue`](https://github.com/linus10x/finserv-agent-audit/issues?q=label%3A%22good+first+issue%22).

---

## Author

**Kunjar Bhaduri** — 25+ year FSI technology executive. Rescued a $750M multi-year wealth-management platform deal at Broadridge. Rebuilt production infrastructure on Azure during a 12-day ransomware attack with no DR available. Operator of a private quantitative options research program with Marcos López de Prado as named advisor on adjacent work; these governance patterns were extracted from that program's operational discipline (multi-year build; hundreds of engineering sessions; the source system operates in paper-trading Phase 0 — no live capital deployed).

[LinkedIn](https://linkedin.com/in/kunjarbhaduri) · [NTCI Portfolio](https://github.com/linus10x)

---

## Acknowledgements

Patterns in this repository were informed by:
- [EU AI Act](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689) — Regulation (EU) 2024/1689
- [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/) — LLM application security risks
- [Microsoft agent-governance-toolkit](https://github.com/microsoft/agent-governance-toolkit) — enterprise AI governance reference
- A private quantitative options research program — the operational source of these patterns; engineering discipline informed by Marcos López de Prado (named advisor on adjacent work). [NTCI portfolio at linus10x](https://github.com/linus10x).

---

## Related: the Autonomy Ladder™ family

`finserv-agent-audit` is the financial-services half of an MIT-licensed pattern family for governing AI in regulated industries. The commercial-real-estate half is here:

**[`linus10x/cre-agent-audit`](https://github.com/linus10x/cre-agent-audit)** — Nine governance patterns for AI-enabled commercial real estate workflows. Anchored to three CRE-AI regulatory matters: *In re Trans Union Rental Screening Solutions* (FTC/CFPB, Oct 2023, $15M), *Louis v. SafeRent Solutions* (D. Mass., Nov 2024, ~$2.275M class settlement), and *U.S. v. RealPage* (DOJ + 8 state AGs, filed Aug 23, 2024, ongoing Sherman § 1 litigation). Mapped to Fair Housing Act, ECOA, FCRA, Colorado AI Act (SB 24-205, signed May 17, 2024; substantive high-risk AI requirements effective February 1, 2026 per leg.colorado.gov), and HUD 24 C.F.R. § 100.500 (disparate-impact rule, post-*ICP v. Texas* 576 U.S. 519 (2015)).

| Pattern | finserv-agent-audit | cre-agent-audit |
|---|---|---|
| DEFCON state machine | ✅ | ✅ |
| Sovereign Veto | ✅ | ✅ |
| Hash-chained Audit Ledger | ✅ | ✅ |
| Autonomy Ladder A0→A4 | ✅ | ✅ |
| Shadow-Mode Rollout | ✅ v1.1 | ✅ |
| Four Protocol seams (Ledger / Timestamp / Witness / MI Proxy) | ✅ v1.1 | ✅ |
| VendorScoreGate | ✅ v1.1 (5 FSI vendor classes) | ✅ (CRE vendor classes) |
| AuditConsumer + reference agents | ✅ v1.1 | ✅ |
| FAILURE-MODES matrix-as-contract | ✅ v1.1 | ✅ |
| Regulation mapping (14 docs) | ✅ SR 11-7 · OCC · GLBA · FCRA · ECOA · BSA · SOX · 17a-4 · Reg-BI · CFPB Circular · NIST AI RMF · ISO 42001 · COSO ICAIR · EU AI Act | ✅ FHA · ECOA · FCRA · CO AI Act · EU AI Act |
| Lease-Abstraction Provenance | — | ✅ CRE-specific |
| Fair-Housing Pre-Flight Gate | — | ✅ CRE-specific |
| Tenant PII Data Residency | — | ✅ CRE-specific |
| Model Inventory · Adverse-Action Gate · SAR Workflow · Equity Audit · Best-Interest Check | ✅ v1.1 FSI-specific | — |
| Agentic-AI runtime adapters (A2A · LangGraph · MAF · CrewAI) | ✅ v2.0 | — |
| AIBOM generator (CycloneDX 1.7 + SPDX 3.0) | ✅ v2.0 | — |
| FastAPI governance endpoint (OpenAPI 3.1 + SSE) | ✅ v2.0 | — |
| Kubernetes operator + CRDs (AuditChain · SovereignVeto · ChainSink) | ✅ v2.0 | — |
| Adversarial test pack (Garak + Promptfoo + Python harness) | ✅ v2.0 | — |

Both repos: MIT, zero runtime dependencies, primary-source regulatory citations, mypy `--strict` clean in CI, and an enforced ≥90% coverage gate. v2.0 of `finserv-agent-audit` adds the agentic-AI ecosystem adapters (Google A2A, LangGraph, Microsoft Agent Framework, CrewAI), the AIBOMGenerator (CycloneDX 1.7 ML-BOM + SPDX 3.0 AI Profile dual emit), a FastAPI governance endpoint (OpenAPI 3.1 + SSE), a Kubernetes operator with three CRDs, and an adversarial test pack (Garak + Promptfoo + Python harness).

The umbrella discipline — **Regulated-Operations AI Governance** — is documented at [autonomy-ladder.io](https://autonomy-ladder.io). One framework, two named verticals, one author.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for full release history.

## License

Dual-licensed under either [MIT](LICENSE-MIT) or [Apache License 2.0](LICENSE-APACHE) at the adopter's election. `SPDX-License-Identifier: MIT OR Apache-2.0`. See [LICENSE](LICENSE), [LICENSING.md](LICENSING.md), and [NOTICE](NOTICE). For trademark posture (Autonomy Ladder™, ALO™ — governed separately from the source-code license per Apache 2.0 §6), see [docs/TRADEMARK.md](docs/TRADEMARK.md).

## Citation

If you use these patterns in your systems or research, please cite using [CITATION.cff](CITATION.cff).
