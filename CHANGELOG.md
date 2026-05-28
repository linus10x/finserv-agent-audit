# Changelog

All notable changes to `finserv-agent-audit` are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned (v1.4) — Operational Refinements
- `ProtectedClassProxyDetector` SHAP / CDD arms (per ADR-0019 v1.2 reconciliation; v1.3 ships the LDA arm via the new `LDASearchHarness`, SHAP + CDD remain deferred)
- LDA-search continuous-feature quantile-binning helper (per `ProtectedClassProxyDetector` v1.2 docstring deferral)
- NAIC Model Bulletin on Use of AI Systems by Insurers — insurance-vertical mapping
- PCAOB AS 2201 amendment overlay as a separate `ASSURANCE-GUIDE` appendix
- Additional state-AG enforcement cases as they emerge
- `docs/fca_mapping.md` — UK FCA AI governance control mapping
- `docs/mas_mapping.md` — Singapore MAS control mapping

### Planned (v2.0)
- Agentic-AI ecosystem adapters — Google A2A · LangGraph · Microsoft Agent Framework · CrewAI
- AIBOM generator (CISA + EU specs)
- FastAPI governance endpoint
- Kubernetes operator (DEFCON as CRD)
- Adversarial test pack per ADR-0018 threat model
- PE portfolio playbook

---

## [1.3.0] — 2026-XX-XX (release date set at tag time)

**Discrimination frontier + vendor surface.** Ships seven new governance modules across the discrimination frontier (LDA search beyond mutual-information, LLM-as-classifier disparate-impact harness, effective-challenge harness, customer-facing chatbot guardrail) and the third-party vendor surface (vendor-attestation ledger, retraining-cadence monitor, deprecation-watch), seven new ADRs (0020-0026), six new regulatory + incident + disclosure docs, and the sixth vendor class (foundation-model API providers).

> Maintainer: the bullets below anticipate the full shape of v1.3 across Tranches A-D. Refresh from the actual landed commits at tag time — keep only what shipped; move anything that slipped to `[Unreleased]` `### Planned (v1.4)`.

### Added — Code

#### Discrimination-frontier patterns (Tranche A)
- `lda_search.py` — `LDASearchHarness`: equally-accurate-less-discriminatory alternative search per ECOA / CFPB Circular 2023-09. Iterates feature-removal + threshold-shift + monotonic-constraint candidate set; surfaces the EALD frontier (per ADR-0020).
- `llm_disparate_impact_harness.py` — `LLMDisparateImpactHarness`: EEOC 4/5ths-rule disparate-impact testing for LLM-agent outputs. Anchored to *Mobley v. Workday* (per ADR-0021).
- `effective_challenge_harness.py` — `EffectiveChallengeHarness`: frontier-API model-validation surface satisfying SR 11-7 effective-challenge + OCC 2026-13 third-party-model expectations. Pluggable challenger-model interface (per ADR-0022).

#### Vendor-surface patterns (Tranche B)
- `vendor_attestation_ledger.py` — `VendorAttestationLedger`: append-only chain-of-custody ledger for third-party model attestations (model cards, eval reports, incident notices) per Treasury FS AI RMF + DORA Art. 28 (per ADR-0023).
- `retraining_cadence_monitor.py` — `RetrainingCadenceMonitor`: weekly / monthly / continuous fine-tune cadence validation against declared model-card cadence; emits drift events when vendor cadence slips beyond the declared window (per ADR-0024).
- `deprecation_watch.py` — `DeprecationWatch`: vendor model deprecation calendar with sunset-date assertions; emits `AuditEventType.DEPRECATION_ALERT` when a model's sunset enters the configured warning horizon (per ADR-0025).

#### Customer-facing chatbot guardrail (Tranche C)
- `customer_facing_chatbot_guardrail.py` — `CustomerFacingChatbotGuardrail`: policy-grounded RAG + commitment-interception + fabricated-policy block. Anchored to *Moffatt v. Air Canada* and EU AI Act Art. 13 (per ADR-0026).

#### Schema extension (Tranche B)
- `AuditEventType` enum gains `DEPRECATION_ALERT = "vendor.deprecation_alert"` for the `DeprecationWatch` surface.

### Added — Documentation

#### Seven new ADRs in `docs/adr/`
0020 LDA Search · 0021 LLM Disparate-Impact Harness · 0022 Effective Challenge Harness · 0023 Vendor Attestation Ledger · 0024 Retraining Cadence Monitor · 0025 Deprecation Watch · 0026 Customer-Facing Chatbot Guardrail.

#### Six new regulatory + incident + disclosure docs in `docs/` (Tranche D)
- `docs/nydfs_part_500_ai_mapping.md` — New York DFS 23 NYCRR 500 AI overlay (cybersecurity-program controls applied to third-party model risk).
- `docs/cfpb_ai_lending_supervisory_landscape.md` — CFPB supervisory landscape on AI in consumer lending (adverse-action, marketing, model risk, third-party oversight).
- `docs/cfpb_circular_2023_09_mapping.md` — CFPB Circular 2023-09 (AVMs / algorithmic appraisal) overlay.
- `docs/state_ag_enforcement_matrix.md` — multi-jurisdiction state attorney-general AI enforcement actions catalog.
- `docs/ai_incident_retrospective_template.md` — post-incident retrospective template aligned to NIST AI RMF GOVERN-6.2.
- `docs/disclosure_artifact_templates.md` — drop-in adverse-action / model-use / vendor-AI disclosure templates.

#### Foundation-model vendor-clauses (Tranche B)
- `vendor-clauses/foundation_model_api_vendor_clauses.md` — sixth FSI vendor class covering foundation-model API providers (OpenAI · Anthropic · Google · AWS Bedrock · Azure OpenAI). Sales-tool-grade addendum covering data-handling, training-data exclusion, model-version pinning, deprecation-notice SLAs, and incident-disclosure obligations.

### Added — Tests

- `tests/test_lda_search.py` — `LDASearchHarness` per-pattern test.
- `tests/test_llm_disparate_impact_harness.py` — `LLMDisparateImpactHarness` per-pattern test.
- `tests/test_effective_challenge_harness.py` — `EffectiveChallengeHarness` per-pattern test.
- `tests/test_vendor_attestation_ledger.py` — `VendorAttestationLedger` per-pattern test.
- `tests/test_retraining_cadence_monitor.py` — `RetrainingCadenceMonitor` per-pattern test.
- `tests/test_deprecation_watch.py` — `DeprecationWatch` per-pattern test (covers the new `DEPRECATION_ALERT` enum value).
- `tests/test_customer_facing_chatbot_guardrail.py` — `CustomerFacingChatbotGuardrail` per-pattern test.

### Changed
- `README.md` Patterns Included section re-versioned to v1.3; seven new rows added under Core Governance; Procurement-companion callout updated to six vendor classes; regulatory-mapping doc count raised; Roadmap "Shipped in v1.3" + "Coming in v1.4" + "Coming in v2.0" lines refreshed.
- `ROADMAP.md` v1.3 section flipped from `_planned_` to `✅ Released` with the 14 v1.3 items checked; new `v1.4 — Operational Refinements` planned section added; v2.0 retitled "Agentic-AI Ecosystem + Platform Surfaces".
- `CITATION.cff` abstract expanded to cite the seven new modules + foundation-model API vendor class + six new docs.
- `src/finserv_agent_audit/__init__.py` docstring updated to enumerate the v1.3 public-API additions.

### Fixed
- Drift-test allow-lists (`tests/doc_staleness_allow_list.py`, `tests/test_failure_modes_matrix.py`) refreshed to acknowledge the seven new modules and the seven new ADRs.
- `ProtectedClassProxyDetector` docstring now references `LDASearchHarness` as the LDA-arm complement to the v1.2 mutual-information arm (closes the v1.2 docstring deferral; SHAP / CDD arms remain on the v1.4 roadmap).

---

## [1.2.0] — 2026-XX-XX (release date set at tag time)

**OCC 2026-13 response + ecosystem onramps.** Treats the OCC's rescission of Bulletin 2011-12 as the v1.2 buyer-conversation opener, lands the Treasury FS AI RMF + NIST AI 600-1 GenAI Profile mappings, ships the first wave of ecosystem onramps (MCP server adapter, OpenTelemetry GenAI emitter, GitHub Actions composite action + reusable workflow, CLI tool), the buyer-conversation closers (pre-examination self-assessment, Big-4 engagement-letter exhibit, sample evidence pack, CAIO first-90-days playbook), the maturity model + CLI self-score, the drift-detection test pack, the `ProtectedClassProxyDetector` real implementation (closes v1.1 stub per ADR-0019), and the PyPI Trusted Publishing release pipeline.

> Maintainer: the bullets below anticipate the full shape of v1.2 across Tranches A-D. Refresh from the actual landed commits at tag time — keep only what shipped; move the rest to `[Unreleased]` `### Planned (v1.3)`.

### Added — Code
- `protected_class_proxy_detector.py` — real implementation per ADR-0019; mutual-information threshold on `(feature, protected_class)` pairs; HMDA + GiveMeSomeCredit benchmark; published FPR/FNR failure-mode list. Closes the v1.1 stub.
- MCP server adapter — exposes DEFCON state, veto log, audit-chain verification, and vendor-score drift status as Model Context Protocol tools. Optional extra `[mcp]`.
- OpenTelemetry GenAI emitter — emits the v1.1 `AuditEventType` taxonomy as OTEL spans + attributes aligned to OTel GenAI semantic conventions. Optional extra `[otel]`.
- CLI tool — `finserv-audit verify --jsonl PATH` and `finserv-audit maturity`; exit codes 0/1 for CI consumption.
- Maturity-model self-score helper — evaluates current repo surface coverage against the 5-level FSI-AI-governance maturity rubric.

### Added — Documentation
- `docs/occ_2026_13_overlay.md` — the white-space play. Maps every v1.1 governance pattern to OCC's post-rescission posture and the model-risk governance principles surviving via SR 11-7 + the interagency Statement of Principles.
- `docs/treasury_fs_ai_rmf_mapping.md` — Treasury's Financial Services AI Risk Management framework crosswalked to NIST AI RMF + the 14 v1.1 FSI mappings.
- `docs/nist_ai_600_1_genai_profile_mapping.md` — GenAI-specific risk controls (confabulation, dangerous-content, data-integrity, IP, obscene/abusive/illegal content, information-security, value-chain).
- 4 buyer-conversation closers: `docs/pre_examination_self_assessment.md` · `docs/big_four_engagement_letter_exhibit.md` · `docs/sample_evidence_pack.md` · `docs/caio_first_90_days_playbook.md`.
- `docs/mrm_bridge_template.md` — MRM BRIDGE artifact reconciling SR 11-7 model-risk lifecycle owners with v1.1 governance gate owners.

### Added — CI + tooling
- `.github/workflows/publish.yml` — PyPI Trusted Publishing (OIDC, no API tokens) + PEP 740 Sigstore-attested wheels via `pypa/gh-action-pypi-publish@release/v1`. Two-stage flow: TestPyPI smoke -> required-reviewer gate -> production PyPI.
- `docs/PYPI_TRUSTED_PUBLISHING_SETUP.md` — one-time maintainer setup walkthrough + troubleshooting.
- `.github/actions/finserv-audit-verify/` — composite action; adopters gate a PR on an audit-stream verify in three lines of YAML.
- `.github/workflows/finserv-audit-verify.reusable.yml` — reusable workflow alternative for adopters preferring `workflow_call`.
- `tests/test_failure_modes_matrix.py` — drift detection between `FAILURE-MODES.md` and code (deferred from v1.1).
- `tests/test_doc_staleness.py` — drift detection between `__all__` exports and "v0.X candidate" markers in docs (deferred from v1.1).
- Project entry point `finserv-audit` declared in `pyproject.toml`.

### Changed
- Cross-cutting OCC 2011-12 citation updates note the OCC 2026-13 rescission while preserving the historical citation in `docs/occ_2011_12_mapping.md` (rebadged "historical reference; supersession context in `docs/occ_2026_13_overlay.md`"). The model-risk governance principles continue to apply via SR 11-7 + interagency Statement of Principles.
- `pyproject.toml` gains optional extras `[mcp]`, `[otel]`, `[all-integrations]`. Default install remains zero-runtime-dependency.

### Fixed
- `ProtectedClassProxyDetector` stub from v1.1 raises `NotImplementedError` no longer; real implementation lands per ADR-0019 ship-gate.
- Two v1.1-deferred drift tests (`test_failure_modes_matrix.py`, `test_doc_staleness.py`) lift to CI-required green status.

### Removed — Pending Tranche A confirmation
- v1.1 deprecation re-export shims at `patterns/*`, `schemas/*`, `examples/defcon_state_machine.py` (announced for v1.2 removal in the v1.1 release notes). Maintainer: confirm Tranche A actually landed the removal before keeping this line in the final CHANGELOG; if deferred, move to `[Unreleased]` `### Planned (v1.3)`.

---

## [1.1.0] — 2026-XX-XX (release date set at tag time)

**Parity port + FSI overlay + 8-chamber council additions.** Brings finserv-agent-audit to feature parity with cre-agent-audit's v0.2.2.dev0 hardening cycle and adds the FSI-specific regulatory overlay + 8 council-driven additions that drive Tier-1 FSI adoption.

### Added — Code

#### Repo restructure
- `src/finserv_agent_audit/{governance,schemas,agents}/` package layout matching cre-agent-audit. Old `patterns/`, `schemas/`, `examples/` paths preserved as deprecation re-export shims (removed in v1.2).

#### Four Protocol seams (audit-chain integrity layer, ADR-0014 + ADR-0015)
- `LedgerStore` Protocol + `InMemoryLedgerStore` default + `SqliteLedgerStore` + `JsonlLedgerStore` + `WORMLedgerStore` (SEC 17a-4-compliant write-once-read-many; default 7-year retention).
- `TimestampSource` Protocol + `LocalClock` + `RFC3161Source` (hand-rolled stdlib DER ASN.1 codec; `fallback_to_local_on_failure` opt-in).
- `WitnessRegister` Protocol + `RekorWitness` (Sigstore public-good) + `OpenTimestampsWitness` + `anchor_to_witness()` helper (emits `AuditEventType.WITNESS_ANCHOR`).
- `MIProxy` Protocol + `LocalMIProxy` HMAC-SHA256 + `IntegrityVerificationError` fail-closed.

#### Vendor-mediated AI (ADR-0016)
- `VendorScoreGate` + `VendorScoreDriftDetected` + 5 FSI `VendorClass` values (KYC, FRAUD_SCORE, CREDIT_DECISION, ROBO_ADVISOR_SIGNAL, AML_TRANSACTION_MONITORING). Drift detection on `(vendor_id, input_hash, model_version)`; default `raise_on_drift=True`.

#### Reference agents (ADR-0014 + ADR-0015)
- `AuditConsumer` base accepts the 4 Protocol seams + VendorScoreGate via one injection contract; exposes `verify_integrity()` + `record_vendor_score()`.
- `AuditAgent`, `MonitorAgent`, `OrchestratorAgent` reference wiring.

#### FSI-specific governance modules (NEW — not in cre-agent-audit)
- `model_inventory.py` — SR 11-7 model registry (status lifecycle: PROPOSED → IN_VALIDATION → APPROVED_FOR_LIMITED_USE → APPROVED_FOR_PRODUCTION → RETIRED; emits `MODEL_VALIDATED`).
- `adverse_action_gate.py` — FCRA § 615 + Reg V + CFPB Circular 2022-03 enforcement. Fails closed on missing reason-code mapping; ships 10-entry `REFERENCE_REASON_CODES`.
- `sar_workflow_audit.py` — BSA/AML 31 U.S.C. § 5318(g)/(h). Emit-mandatory with § 5318(g)(2) safe-harbor metadata.
- `equity_audit.py` — ECOA / Reg-B fair-lending pre-flight. Full 9-class ProtectedClass enum.
- `best_interest_check.py` — SEC Reg-BI broker-dealer / RIA recommendation gate.
- `protected_class_proxy_detector.py` — STUB per ADR-0019; raises `NotImplementedError` pointing to v1.2 ship-gate.

#### Operational patterns
- `shadow_mode.py` ported from cre-agent-audit; SR 11-7 pre-promotion parallel runs.
- `autonomy_ladder.py` runtime helper; A2→A3 promotion-gate check.
- `AuditChain` extracted from `schemas/audit_event.py` to `governance/audit_chain.py` so it can consume the Protocol seams (backward-compat re-export preserved via `__getattr__`).

#### AuditEventType enum extension
- `VENDOR_SCORE_RECORDED`, `VENDOR_SCORE_DRIFT_DETECTED`, `WITNESS_ANCHOR`, `MODEL_VALIDATED`, `ADVERSE_ACTION_TAKEN`, `SAR_FILED`, `BEST_INTEREST_CHECKED`.

### Added — Documentation

#### 19 governance ADRs in `docs/adr/`
0001 DEFCON · 0002 Sovereign Veto · 0003 Hash-Chain Audit · 0004 Autonomy Ladder A0→A4 · 0005 EU AI Act Mapping · 0006 Shadow Mode · 0007 SR 11-7 Overlay (foundational, 10-row three-lines-of-defense mapping table) · 0008 GLBA Safeguards · 0009 FCRA/Reg V Adverse Action · 0010 ECOA/Reg B Fair Lending · 0011 BSA/AML SAR Workflow · 0012 SOX 404 ITGC · 0013 SEC 17a-4 WORM · 0014 Persistence/Witness/Timestamp Pattern · 0015 MI Proxy · 0016 Vendor Score Gate · 0017 Audit-Chain Retention/Privilege/Discovery · 0018 Adversarial Agent Threat Model · 0019 Protected-Class Proxy Detector — Deferred-Implementation. Existing CI ops ADR moved to `docs/adr/ops/OPS-001-ci-self-heal-loop.md`.

#### 14 FSI regulatory mapping documents in `docs/` (WebFetch primary-source-verified where accessible)
`sr11_7_mapping.md` · `occ_2011_12_mapping.md` · `glba_safeguards_mapping.md` · `fcra_reg_v_mapping.md` · `ecoa_reg_b_mapping.md` · `bsa_aml_mapping.md` · `sox_404_itgc_mapping.md` · `sec_17a_4_mapping.md` · `sec_reg_bi_mapping.md` · `cfpb_circular_2022_03_mapping.md` · `nist_ai_rmf_mapping.md` · `iso_42001_mapping.md` · `coso_icair_mapping.md` · `fsi_settled_matters.md` (Apple Card / NYDFS · CFPB Circular 2022-03 · CFPB v. Wells Fargo $3.7B · SEC v. Schwab Intelligent Portfolios $187M · cross-vertical TransUnion).

#### Repo-root governance + release surfaces (12 new files)
`FAILURE-MODES.md` (matrix-as-contract, 8 failure-mode classes, 6 shipped with callable refs + 2 deferred-with-tracking) · `LIMITATIONS.md` · `ARCHITECTURE.md` · `DISCLAIMER.md` · `SHIP-RECEIPT.md` (67-entry classification) · `VERSIONING.md` · `NEGATIVE-USE-CASES.md` (BigLaw council) · `RESEARCH.md` (academic-source map) · `ASSURANCE-GUIDE.md` (Big-4 audit-evidence walkthrough — highest enterprise multiplier) · `DEPLOY-CHECKLIST.md` (AWS / Azure walkthrough) · `OWNERSHIP.md` · `RELEASE-INSTRUCTIONS.md`.

#### Procurement companion (`vendor-clauses/`)
5 sales-tool-grade FSI vendor-contract addenda: `kyc_vendor_clauses.md` · `fraud_score_vendor_clauses.md` · `credit_decision_vendor_clauses.md` · `robo_advisor_vendor_clauses.md` · `aml_transaction_monitoring_vendor_clauses.md`.

#### Reference integrations (`examples/integration/`)
`splunk_audit_sink.py` (HEC) · `datadog_audit_sink.py` (Logs API v2) · `sigstore_rekor_witness_demo.py` · `aws_dynamo_ledger_store.py` (conditional-write split-brain prevention). All stdlib-only by default; opt-in deps import-guarded.

### Added — CI + tooling
- `mypy --strict` flipped on; previous "mypy-checked" badge restored to "mypy-strict". 6 fixes landed in-line; no per-module exemptions.
- Coverage gate raised from 80% to 90%; current TOTAL 91.20%.
- 3 lint scripts in `scripts/`: `banned_term_lint.py` (13 banned terms with fence-block / `# noqa` / ADR Regulatory-Mapping exemptions) · `banned_names_lint.py` (env-driven via `BANNED_NAMES_FILE`; opt-in) · `tamper_language_lint.py` (flags any unhedged tamper-evident claim that lacks the hash-chain SHA-256 mechanism reference on the same line).
- `pytest.mark.network` marker registered.
- `.pre-commit-config.yaml`: 3 new `local` hooks.
- `.github/workflows/ci.yml`: 3 new lint steps after pytest.

### Fixed — Voice + brand discipline
- Tamper-detecting hash-chain (within-trust-boundary) hedging propagated across README, CHANGELOG, defcon module, ADRs 0003/0014/0015, mapping docs (per [audit](https://github.com/linus10x/finserv-agent-audit/issues) D8.1).
- APEX framing restored to "private quantitative options research program with Marcos López de Prado as named advisor on adjacent work" per author's CLAUDE.md rule (audit D5.3 + D5.4).
- Colorado AI Act citation reconciled to leg.colorado.gov primary source: SB 24-205, signed 2024-05-17, substantive high-risk AI requirements effective 2026-02-01 (audit D4.3).
- *U.S. v. RealPage* consistently described as ongoing antitrust litigation (M.D.N.C., filed Aug 23, 2024) — corrected from false "settled cases of record" framing in `docs/workbook_v0_outline.md`.
- Shadow Mode row removed from patterns table during Tranche 1 (file didn't exist at v1.0); re-added in v1.1 patterns table now that `shadow_mode.py` ships.
- `README_update.md` staging artifact removed (single-SoT discipline).

### Changed — Restructure
- Existing `patterns/sovereign_veto.py`, `schemas/audit_event.py`, `examples/defcon_state_machine.py` are now deprecation re-export shims pointing to the canonical `src/finserv_agent_audit/` locations. Removed in v1.2.

### Internal
- `ci-self-heal-loop.md` moved to `docs/adr/ops/OPS-001-ci-self-heal-loop.md` (scope clarification: governance ADRs in `docs/adr/`; operational tooling ADRs in `docs/adr/ops/`).

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
