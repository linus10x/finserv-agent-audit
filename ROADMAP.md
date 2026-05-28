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
- [x] **6 FSI-specific governance modules** — ModelInventory (SR 11-7) · AdverseActionGate (FCRA + CFPB Circular 2022-03) · SARWorkflowAudit (BSA/AML) · EquityAudit (ECOA/Reg B) · BestInterestCheck (SEC Reg-BI) · ProtectedClassProxyDetector (stub per ADR-0019)
- [x] **19 governance ADRs** in `docs/adr/` (0001-0019)
- [x] **14 FSI regulatory mapping docs** in `docs/` (SR 11-7 · OCC 2011-12 · GLBA · FCRA · ECOA · BSA/AML · SOX 404 · 17a-4 · Reg-BI · CFPB Circular · NIST AI RMF · ISO 42001 · COSO ICAIR · FSI Settled Matters)
- [x] **12 repo-root governance + release surfaces** — FAILURE-MODES, LIMITATIONS, ARCHITECTURE, DISCLAIMER, SHIP-RECEIPT, VERSIONING, NEGATIVE-USE-CASES, RESEARCH, ASSURANCE-GUIDE, DEPLOY-CHECKLIST, OWNERSHIP, RELEASE-INSTRUCTIONS
- [x] **vendor-clauses/** procurement companion (5 FSI vendor classes)
- [x] **4 reference integrations** in `examples/integration/` (Splunk HEC · Datadog Logs · Sigstore Rekor · AWS DynamoDB)
- [x] **3 CI lint scripts** — banned_term_lint, banned_names_lint, tamper_language_lint
- [x] **mypy --strict** flipped on (was non-strict in v1.0); 6 fixes landed in-line
- [x] **Coverage gate raised from 80% to 90%** (current TOTAL 91.20%)

---

## v1.2 — Operational Refinements _(planned)_

- [ ] **ProtectedClassProxyDetector implementation** per ADR-0019 (mutual-information threshold; HMDA + GiveMeSomeCredit benchmark; FPR/FNR-published failure-mode list ship-gate)
- [ ] **Drift Monitor** — statistical divergence detection between shadow and live agent outputs; triggers DEFCON escalation
- [ ] **Explainability Stub** — structured rationale capture per agent decision; EU AI Act Art. 13 (transparency) mapping
- [ ] **Rate Limiter / Throttle** — per-agent execution budget; prevents runaway loops in autonomous pipelines
- [ ] **MiFID II Art. 17 Checklist** — algorithmic trading pre-approval checklist as executable Python assertions
- [ ] **Remove deprecation re-export shims** at `patterns/`, `schemas/`, `examples/defcon_state_machine.py`
- [ ] **test_failure_modes_matrix.py** drift-detection test + **test_doc_staleness.py** drift-detection test

---

## v2.0 — Integration & Ecosystem _(planned)_

- [ ] **LangChain / LangGraph adapter** — drop-in governance wrapper for LangGraph agent graphs
- [ ] **CrewAI adapter** — DEFCON + Sovereign Veto as CrewAI task guardrails
- [ ] **OpenTelemetry export** — emit audit events as OTEL spans for observability platform integration (Datadog, Grafana, Splunk)
- [ ] **Async-native patterns** — `asyncio`-compatible versions of all patterns for high-throughput agent pipelines
- [ ] **FastAPI governance endpoint** — expose DEFCON state, veto log, and audit chain verification over REST
- [ ] **Packaging on PyPI** — `pip install finserv-agent-audit`
- [ ] **UK FCA mapping** (`docs/fca_mapping.md`)
- [ ] **Singapore MAS mapping** (`docs/mas_mapping.md`)

---

## Community Requests _(under consideration)_

- [ ] AWS Lambda / ECS Fargate deployment example
- [ ] Multi-agent (supervisor + worker) DEFCON propagation
- [ ] DORA compliance mapping
- [ ] Insurance / claims automation variant

> To request a pattern, open a [Pattern Request issue](https://github.com/linus10x/finserv-agent-audit/issues/new?template=pattern_request.yml) or start a [Discussion](https://github.com/linus10x/finserv-agent-audit/discussions).
