# Roadmap

This roadmap reflects the current development priorities for `finserv-agent-audit`. Items are not promises — they reflect intent and community interest. Use [GitHub Discussions](https://github.com/linus10x/finserv-agent-audit/discussions) to influence priority.

---

## v1.0 — Foundation ✅ Released 2026-05-15

- [x] DEFCON Risk-State Machine with hysteresis
- [x] Sovereign Veto (human-only kill switch)
- [x] Tamper-detecting hash-chain Audit Chain (within-trust-boundary)
- [x] Autonomy Ladder (A0 → A4 governance classification)
- [x] EU AI Act article-by-article control mapping
- [x] CI: ruff lint + format, mypy, pytest ≥ 80% coverage, Python 3.12 + 3.13
- [x] Community: CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, CITATION

---

## v1.1 — Parity Port + FSI Overlay + Council Additions ✅ Released

- [x] **Shadow Mode Rollout** (`src/finserv_agent_audit/governance/shadow_mode.py`) — SR 11-7 pre-promotion parallel runs
- [x] **Four Protocol seams** — LedgerStore (+ WORM for SEC 17a-4) · TimestampSource (+ RFC3161) · WitnessRegister (+ Sigstore Rekor) · MIProxy (HMAC-SHA256)
- [x] **VendorScoreGate** — drift detection on `(vendor_id, input_hash, model_version)` across 5 FSI vendor classes (KYC · fraud-score · credit-decision · robo-advisor signal · AML transaction monitoring)
- [x] **AuditConsumer base + 3 reference agents** (`AuditAgent`, `MonitorAgent`, `OrchestratorAgent`)
- [x] **6 FSI-specific governance modules** — ModelInventory (SR 11-7) · AdverseActionGate (FCRA + CFPB Circular 2022-03) · SARWorkflowAudit (BSA/AML) · EquityAudit (ECOA/Reg B) · BestInterestCheck (SEC Reg-BI) · ProtectedClassProxyDetector (v1.1 shipped the API reservation; v1.2 ships the MI arm per ADR-0019)
- [x] **19 governance ADRs** in `docs/adr/` (0001-0019)
- [x] **14 FSI regulatory mapping docs** in `docs/` (SR 11-7 · OCC 2011-12 · GLBA · FCRA · ECOA · BSA/AML · SOX 404 · 17a-4 · Reg-BI · CFPB Circular · NIST AI RMF · ISO 42001 · COSO ICAIR · FSI Settled Matters)
- [x] **12 repo-root governance + release surfaces** — FAILURE-MODES, LIMITATIONS, ARCHITECTURE, DISCLAIMER, SHIP-RECEIPT, VERSIONING, NEGATIVE-USE-CASES, RESEARCH, ASSURANCE-GUIDE, DEPLOY-CHECKLIST, OWNERSHIP, RELEASE-INSTRUCTIONS
- [x] **vendor-clauses/** procurement companion (5 FSI vendor classes)
- [x] **4 reference integrations** in `examples/integration/` (Splunk HEC · Datadog Logs · Sigstore Rekor · AWS DynamoDB)
- [x] **3 CI lint scripts** — banned_term_lint, banned_names_lint, tamper_language_lint
- [x] **mypy --strict** flipped on (was non-strict in v1.0); 6 fixes landed in-line
- [x] **Coverage gate raised from 80% to 90%** (current TOTAL 91.20%)

---

## v1.2 — OCC 2026-13 Response + Ecosystem Onramps ✅ Released

- [x] **ProtectedClassProxyDetector implementation** per ADR-0019 (mutual-information threshold; HMDA + GiveMeSomeCredit benchmark; FPR/FNR-published failure-mode list)
- [x] **OCC 2026-13 overlay** (`docs/occ_2026_13_overlay.md`) — the white-space play; maps every v1.1 governance pattern to OCC's post-rescission posture
- [x] **Treasury FS AI RMF mapping** (`docs/treasury_fs_ai_rmf_mapping.md`)
- [x] **NIST AI 600-1 GenAI Profile mapping** (`docs/nist_ai_600_1_genai_profile_mapping.md`)
- [x] **MCP server adapter** — DEFCON, veto, audit-chain verification, vendor-score drift as Model Context Protocol tools (optional extra `[mcp]`)
- [x] **OpenTelemetry GenAI emitter** — `AuditEventType` -> OTEL spans aligned to OTel GenAI semconv (optional extra `[otel]`)
- [x] **CLI tool** — `finserv-audit verify --jsonl PATH` + `finserv-audit maturity`
- [x] **Maturity-model self-score** — 5-level FSI-AI-governance rubric
- [x] **GitHub Actions composite action** — `.github/actions/finserv-audit-verify/`
- [x] **Reusable workflow** — `.github/workflows/finserv-audit-verify.reusable.yml`
- [x] **4 buyer-conversation closers** — pre-examination self-assessment, Big-4 engagement-letter exhibit, sample evidence pack, CAIO first-90-days playbook
- [x] **MRM BRIDGE template** — SR 11-7 model-risk lifecycle owners ↔ v1.1 governance gate owners
- [x] **PyPI Trusted Publishing + PEP 740 Sigstore-attested wheels** — `.github/workflows/publish.yml` + `docs/PYPI_TRUSTED_PUBLISHING_SETUP.md`
- [x] **test_failure_modes_matrix.py** drift-detection test + **test_doc_staleness.py** drift-detection test (lifted from v1.1 deferred)

---

## v1.3 — Discrimination Frontier + Vendor Surface ✅ Released

- [x] **Discrimination-frontier patterns** — `LDASearchHarness` (EALD search beyond mutual-information, ADR-0020) · `LLMDisparateImpactHarness` (EEOC 4/5ths-rule DI testing for LLM-agent outputs, anchored to *Mobley v. Workday*, ADR-0021) · `EffectiveChallengeHarness` (frontier-API model validation per SR 11-7, ADR-0022) · `CustomerFacingChatbotGuardrail` (policy-grounded RAG + commitment interception + fabricated-policy block, anchored to *Moffatt v. Air Canada* and EU AI Act Art. 13, ADR-0026)
- [x] **Vendor-clauses foundation-model class** — sixth vendor class covering foundation-model API providers (OpenAI / Anthropic / Google / AWS Bedrock / Azure OpenAI)
- [x] **NYDFS Part 500 AI mapping** — `docs/nydfs_part_500_ai_mapping.md`
- [x] **CFPB AI lending supervisory landscape** — `docs/cfpb_ai_lending_supervisory_landscape.md`
- [x] **CFPB Circular 2023-09 mapping** — `docs/cfpb_circular_2023_09_mapping.md` (AVMs / algorithmic appraisal)
- [x] **State-AG enforcement matrix** — `docs/state_ag_enforcement_matrix.md` (multi-jurisdiction state attorney-general AI-enforcement actions catalog)
- [x] **AI incident retrospective template** — `docs/ai_incident_retrospective_template.md` aligned to NIST AI RMF GOVERN-6.2
- [x] **Disclosure artifact templates** — `docs/disclosure_artifact_templates.md` (adverse-action / model-use / vendor-AI)
- [x] **VendorAttestationLedger** — append-only ledger of vendor attestations (model cards, eval reports, incident notices) per Treasury FS AI RMF + DORA Art. 28 (ADR-0023)
- [x] **RetrainingCadenceMonitor** — weekly / monthly / continuous fine-tune validation cadence per SR 11-7 + OCC 2026-13 (ADR-0024)
- [x] **DeprecationWatch** — model + vendor deprecation calendar with sunset-date assertions; new `AuditEventType.DEPRECATION_ALERT` enum value (ADR-0025)
- [x] **Seven new governance ADRs** (0020-0026)
- [x] **Seven new per-pattern tests** wiring the new modules into the existing 90% coverage gate
- [x] **`__init__.py` + `CITATION.cff` abstract** refreshed to enumerate the v1.3 public-API additions

---

## v1.4 — Operational Refinements _(planned)_

- [ ] **Drift Monitor** — statistical divergence detection between shadow and live agent outputs; triggers DEFCON escalation (carried from prior v1.2 plan)
- [ ] **Explainability Stub** — structured rationale capture per agent decision; EU AI Act Art. 13 mapping (carried)
- [ ] **Rate Limiter / Throttle** — per-agent execution budget (carried)
- [ ] **MiFID II Art. 17 Checklist** — algorithmic trading pre-approval checklist as executable Python assertions (carried)
- [ ] **Additional state-AG enforcement cases** as they emerge

> v2.0 absorbed the v1.4-planned NAIC Model Bulletin mapping (via `docs/naic_model_bulletin_ai_insurers_mapping.md`), the PCAOB AS 2201 amendment overlay (via `docs/pcaob_as_2201_amendments_appendix.md`), and the LDA arm of `ProtectedClassProxyDetector` (via `LDASearchHarness` in v1.3). The remaining `LDA-search continuous-feature quantile-binning helper`, `SHAP / CDD arms`, `UK FCA mapping`, and `Singapore MAS mapping` items moved to the v2.1 ecosystem-completion planned section below.

---

## v2.0 — Agentic-AI Ecosystem + Platform Surfaces ✅ Released

- [x] **Agentic-AI ecosystem adapters** — Google A2A (ADR-0027) · LangGraph (ADR-0028) · Microsoft Agent Framework (ADR-0029) · CrewAI (ADR-0030); each ships under its own optional extra (`[a2a]`, `[langgraph]`, `[maf]`, `[crewai]`) plus the `[all-agentic]` convenience bundle
- [x] **AIBOM generator** — `AIBOMGenerator` emits CycloneDX 1.7 ML-BOM + SPDX 3.0 AI Profile from one governance state (ADR-0031)
- [x] **FastAPI governance endpoint** — REST surface for DEFCON state, veto log, audit-chain verification, vendor-score drift, deprecation calendar, AIBOM emit, plus an SSE live stream; OpenAPI 3.1; opt-in extra `[api]` (ADR-0032)
- [x] **Kubernetes operator + CRDs** — controller-pattern operator with three custom resource definitions (`AuditChain`, `SovereignVeto`, `ChainSink`) under `deploy/k8s/` (ADR-0033)
- [x] **Kyverno + OPA sample admission policies** — pre-cleared bundles for the two most-deployed Kubernetes policy engines
- [x] **Adversarial test pack** — Garak probes + Promptfoo configs + Python harness coordinating both; targets the customer-facing chatbot guardrail, LangGraph audit callback boundary, EALD-search / effective-challenge / disparate-impact harnesses (ADR-0034)
- [x] **PE portfolio playbook** — `docs/pe_portfolio_playbook.md` + `docs/pe_portfolio_dashboard.md` (operating-partner 30 / 60 / 90 / 180-day rollout sequence + dashboard reference)
- [x] **NAIC Model Bulletin on Use of AI Systems by Insurers mapping** — `docs/naic_model_bulletin_ai_insurers_mapping.md` (carried forward from v1.4)
- [x] **DORA mapping** — `docs/dora_mapping.md` (Regulation (EU) 2022/2554 Art. 28 + ICT incident-reporting overlay)
- [x] **EU AI Act August 2026 compliance pack** — `docs/eu_ai_act_aug_2026_compliance_pack.md` (deployer checklist timed to the high-risk-AI substantive-obligation entry into force)
- [x] **PCAOB AS 2201 amendments ASSURANCE-GUIDE appendix** — `docs/pcaob_as_2201_amendments_appendix.md` (carried forward from v1.4)
- [x] **Eight new governance ADRs** (0027-0034)
- [x] **`__init__.py` + `CITATION.cff` abstract** refreshed to enumerate the v2.0 public-API additions

---

## v2.1 — Ecosystem Completion _(planned)_

- [ ] **DSPy adapter** — Stanford-originated framework with production usage at Moody's; prestige play for the FSI buyer conversation
- [ ] **LlamaIndex Workflows adapter** — agentic-runtime adapter for the LlamaIndex Workflows event-driven orchestration surface
- [ ] **GraphQL governance endpoint** — Strawberry-GraphQL alternative to the v2.0 REST surface for adopters standardized on GraphQL
- [ ] **Remove v1.1 deprecation re-export shims** at `patterns/`, `schemas/`, `examples/defcon_state_machine.py` (originally targeted for v1.2; carried forward through v2.0 for one additional minor-bump grace window)
- [ ] **UK FCA mapping** (`docs/fca_mapping.md`)
- [ ] **Singapore MAS mapping** (`docs/mas_mapping.md`)
- [ ] **`ProtectedClassProxyDetector` SHAP / CDD arms** — per ADR-0019 v1.2 reconciliation deferral; v1.3 shipped the LDA arm via `LDASearchHarness`
- [ ] **LDA-search continuous-feature quantile-binning helper** — per `ProtectedClassProxyDetector` v1.2 docstring deferral

---

## v3.0 — Async + Multi-Region + WASM _(planned)_

- [ ] **Async-native pattern variants** — `asyncio`-compatible versions of every governance pattern for high-throughput agent pipelines
- [ ] **Multi-region audit-chain federation** — cross-region replication with quorum-anchored witness commits and a regional-failure de-conflict protocol
- [ ] **WASM runtime for client-side guardrail evaluation** — compile the customer-facing chatbot guardrail and the autonomy-ladder runtime helper to WebAssembly for in-browser pre-flight enforcement

---

## Community Requests _(under consideration)_

- [ ] AWS Lambda / ECS Fargate deployment example
- [ ] Multi-agent (supervisor + worker) DEFCON propagation
- [ ] DORA compliance mapping
- [ ] Insurance / claims automation variant

> To request a pattern, open a [Pattern Request issue](https://github.com/linus10x/finserv-agent-audit/issues/new?template=pattern_request.yml) or start a [Discussion](https://github.com/linus10x/finserv-agent-audit/discussions).
