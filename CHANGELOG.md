# Changelog

All notable changes to `finserv-agent-audit` are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- `patterns/shadow_mode.py` — parallel dry-run before live execution
- `patterns/circuit_breaker.py` — per-agent (not system-level) suspension
- `patterns/consensus.py` — multi-agent agreement before execution
- `docs/fca_mapping.md` — UK FCA AI governance control mapping
- `docs/mas_mapping.md` — Singapore MAS control mapping

---

## [1.0.0] — 2026-05-15

### Added

#### Core Patterns
- **`examples/defcon_state_machine.py`** — DEFCON state machine reference implementation.
  Five risk levels (NORMAL → HALT) with hysteresis-controlled de-escalation. Escalation
  is immediate; de-escalation requires `HYSTERESIS_CONFIRMATIONS` (default: 3) consecutive
  evaluations at a lower risk level. HALT level requires `manual_override()` — no
  automatic de-escalation. State persists to disk; reloads last confirmed level on restart.
  All transitions logged to a tamper-detecting hash-chain audit trail (within-trust-boundary; external witness anchoring required for full tamper-evidence — see ADR-0014 in v1.1).

- **`patterns/sovereign_veto.py`** — Sovereign Veto pattern. Human-only kill switch:
  no agent can clear its own veto. Veto can be triggered by human operator, risk state
  machine, policy engine, or peer agent. All clearances logged with operator identity
  and documented reason. Integrates with `DEFCONMachine` at ALERT level and above.

- **`schemas/audit_event.py`** — Tamper-detecting hash-chain audit log (within-trust-boundary).
  `AuditEvent` dataclass with SHA-256 hash-chain: `event_hash = SHA-256(event_payload + prev_hash)`.
  `AuditChain.verify()` detects any inserted, modified, or deleted event. External tamper-evidence
  via the witness pattern lands in v1.1 (see ADR-0014).
  `AuditEventType` covers 15 event categories. `AutonomyLevel` enum maps to A0–A4.

#### Documentation
- **`docs/autonomy_ladder.md`** — A0→A4 governance classification framework. EU AI Act
  cross-reference table. Governing principle: autonomy level is a function of risk state,
  decision category, regulatory context, and system health — not a fixed agent property.

- **`docs/eu_ai_act_mapping.md`** — Article 9–15 control mapping for high-risk AI systems.
  Gap analysis table covering conformity assessment, registration, post-market monitoring,
  and fundamental rights impact assessment. Annex III high-risk classification checklist.

- **`docs/DEFCON_ARCHITECTURE.md`** — Design rationale for hysteresis, threshold calibration
  guidance, state persistence design, and HALT de-escalation policy.

#### Infrastructure
- CI pipeline: GitHub Actions on Python 3.12 and 3.13 — ruff lint, mypy type check,
  pytest with coverage.
- `pyproject.toml`: PEP 517/518 build system, full project metadata, ruff/mypy/pytest
  configuration, PyPI classifiers.
- `pre-commit` configuration: ruff, ruff-format, mypy, standard file hygiene hooks.
- `CITATION.cff`: citable metadata for academic and compliance use.
- `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`: full community infrastructure.
- Issue template: Governance Pattern Request with regulatory context and priority fields.
- PR template with compliance checklist.

### Design Decisions
- Zero runtime dependencies — all patterns use only the Python standard library.
- MIT license — permissive for both commercial and academic use.
- Illustrative threshold values only — all numeric thresholds in `defcon_state_machine.py`
  are clearly marked as examples and must be calibrated per system before deployment.
- No strategy logic or alpha signals — this repository is governance-layer only.

[1.0.0]: https://github.com/linus10x/finserv-agent-audit/releases/tag/v1.0.0
[Unreleased]: https://github.com/linus10x/finserv-agent-audit/compare/v1.0.0...HEAD
