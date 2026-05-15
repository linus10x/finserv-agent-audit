# Roadmap

This roadmap reflects the current development priorities for `finserv-agent-audit`. Items are not promises — they reflect intent and community interest. Use [GitHub Discussions](https://github.com/linus10x/finserv-agent-audit/discussions) to influence priority.

---

## v1.0 — Foundation ✅ Released

- [x] DEFCON Risk-State Machine with hysteresis
- [x] Sovereign Veto (human-only kill switch)
- [x] Tamper-evident Audit Chain (SHA-256 hash chain)
- [x] Autonomy Ladder (A0 → A4 governance classification)
- [x] EU AI Act article-by-article control mapping
- [x] CI: ruff lint + format, mypy strict, pytest ≥ 80% coverage, Python 3.12 + 3.13
- [x] Community: CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, CITATION

---

## v1.1 — Operational Patterns _(in progress)_

- [ ] **Shadow Mode Rollout** (`patterns/shadow_mode.py`) — parallel dry-run execution before live agent promotion; SR 11-7 model validation alignment
- [ ] **Drift Monitor** — statistical divergence detection between shadow and live agent outputs; triggers DEFCON escalation
- [ ] **Explainability Stub** — structured rationale capture per agent decision; EU AI Act Art. 13 (transparency) mapping
- [ ] **Rate Limiter / Throttle** — per-agent execution budget; prevents runaway loops in autonomous pipelines
- [ ] **MiFID II Art. 17 Checklist** — algorithmic trading pre-approval checklist as executable Python assertions

---

## v2.0 — Integration & Ecosystem _(planned)_

- [ ] **LangChain / LangGraph adapter** — drop-in governance wrapper for LangGraph agent graphs
- [ ] **CrewAI adapter** — DEFCON + Sovereign Veto as CrewAI task guardrails
- [ ] **OpenTelemetry export** — emit audit events as OTEL spans for observability platform integration (Datadog, Grafana, Splunk)
- [ ] **Async-native patterns** — `asyncio`-compatible versions of all patterns for high-throughput agent pipelines
- [ ] **FastAPI governance endpoint** — expose DEFCON state, veto log, and audit chain verification over REST
- [ ] **Packaging on PyPI** — `pip install finserv-agent-audit`

---

## Community Requests _(under consideration)_

- [ ] AWS Lambda / ECS Fargate deployment example
- [ ] Multi-agent (supervisor + worker) DEFCON propagation
- [ ] DORA compliance mapping
- [ ] Insurance / claims automation variant

> To request a pattern, open a [Pattern Request issue](https://github.com/linus10x/finserv-agent-audit/issues/new?template=pattern_request.yml) or start a [Discussion](https://github.com/linus10x/finserv-agent-audit/discussions).
