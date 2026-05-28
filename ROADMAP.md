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

## v1.3 — Discrimination Frontier + Vendor Surface _(planned)_

- [ ] **Discrimination-frontier patterns** — LDA search for protected-class proxies beyond mutual-information · LLM-as-classifier disparate-impact harness · effective-challenge harness · customer-facing chatbot guardrail
- [ ] **Vendor-clauses foundation-model class** — sixth vendor class covering foundation-model API providers (OpenAI / Anthropic / Google / AWS Bedrock / Azure OpenAI)
- [ ] **NYDFS Part 500 AI mapping** — New York DFS cybersecurity regulation, AI overlay
- [ ] **State-AG enforcement matrix** — multi-jurisdiction state attorney-general AI-enforcement actions catalog
- [ ] **Retraining-cadence monitor** — drift-trigger-based retraining recommendation gate
- [ ] **Deprecation-watch** — model + vendor deprecation calendar with sunset-date assertions
- [ ] **Vendor-attestation ledger** — append-only ledger of vendor attestations (model cards, eval reports, incident notices)
- [ ] **Disclosure templates** — adverse-action, model-use, vendor-AI
- [ ] **Incident-retrospective template** — aligned to NIST AI RMF GOVERN-6.2
- [ ] **Drift Monitor** — statistical divergence detection between shadow and live agent outputs; triggers DEFCON escalation (carried from prior v1.2 plan)
- [ ] **Explainability Stub** — structured rationale capture per agent decision; EU AI Act Art. 13 mapping (carried)
- [ ] **Rate Limiter / Throttle** — per-agent execution budget (carried)
- [ ] **MiFID II Art. 17 Checklist** — algorithmic trading pre-approval checklist as executable Python assertions (carried)

---

## v2.0 — Agentic-AI Ecosystem + Platform Surfaces _(planned)_

- [ ] **Agentic-AI ecosystem adapters** — Google A2A · LangGraph · Microsoft Agent Framework (MAF) · CrewAI — governance wrappers for each
- [ ] **AIBOM generator** — AI Bill of Materials per emerging CISA + EU specs
- [ ] **FastAPI governance endpoint** — REST surface exposing DEFCON state, veto log, audit-chain verification
- [ ] **Kubernetes operator** — DEFCON as a Kubernetes custom resource with controller-driven escalation
- [ ] **Adversarial test pack** — red-team scenarios per ADR-0018 threat model
- [ ] **PE portfolio playbook** — operating-partner-facing rollout sequence for portco AI governance
- [ ] **NAIC insurance mapping** — NAIC Model Bulletin on Use of AI Systems by Insurers
- [ ] **Async-native patterns** — `asyncio`-compatible versions of all patterns for high-throughput pipelines
- [ ] **UK FCA mapping** (`docs/fca_mapping.md`)
- [ ] **Singapore MAS mapping** (`docs/mas_mapping.md`)

---

## Community Requests _(under consideration)_

- [ ] AWS Lambda / ECS Fargate deployment example
- [ ] Multi-agent (supervisor + worker) DEFCON propagation
- [ ] DORA compliance mapping
- [ ] Insurance / claims automation variant

> To request a pattern, open a [Pattern Request issue](https://github.com/linus10x/finserv-agent-audit/issues/new?template=pattern_request.yml) or start a [Discussion](https://github.com/linus10x/finserv-agent-audit/discussions).
