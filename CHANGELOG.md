# Changelog

All notable changes to `finserv-agent-audit` are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned (v2.2) — Ecosystem Completion (carried forward from the originally-scoped v2.1)
- DSPy adapter — Stanford-originated framework with production usage at Moody's; prestige play for the FSI buyer conversation
- LlamaIndex Workflows adapter — agentic-runtime adapter for the LlamaIndex Workflows event-driven orchestration surface
- GraphQL governance endpoint — Strawberry-GraphQL alternative to the v2.0 REST surface for adopters standardized on GraphQL
- Remove v1.1 deprecation re-export shims at `patterns/*`, `schemas/*`, `examples/defcon_state_machine.py` (originally targeted for v1.2; carried forward through v2.1 for one additional minor-bump grace window)
- `docs/fca_mapping.md` — UK FCA AI governance control mapping
- `docs/mas_mapping.md` — Singapore MAS control mapping
- `ProtectedClassProxyDetector` SHAP / CDD arms (per ADR-0019 v1.2 reconciliation; v1.3 shipped the LDA arm via `LDASearchHarness`)
- LDA-search continuous-feature quantile-binning helper (per `ProtectedClassProxyDetector` v1.2 docstring deferral)
- Sigstore cosign signature verification of the `BaselineMIProxy` pinned manifest (CR-11 follow-up; v2.1 shipped the deploy-time-pinned baseline scaffold, v2.2 adds Sigstore signature verification via a `[sigstore]` extra)
- `Authorizer` reference implementations (CR-12 follow-up; v2.1 shipped the `Authorizer` Protocol + self-clearing rule; v2.2 adds OIDC + SAML reference adapters)
- Defer-and-document for the latent `AuditChain.verify()` interaction with deployer-keyed genesis chains (called out during the CR-4 concurrency port; tracked as v2.2 hardening work)

### Planned (v3.0) — Async-Native + Multi-Region + WASM
- Async-native pattern variants — `asyncio`-compatible versions of every governance pattern for high-throughput agent pipelines
- Multi-region audit-chain federation — cross-region replication with quorum-anchored witness commits and a regional-failure de-conflict protocol
- WASM runtime for client-side guardrail evaluation — compile the customer-facing chatbot guardrail and the autonomy-ladder runtime helper to WebAssembly for in-browser pre-flight enforcement

---

## [2.1.3] — 2026-06-09

Frontier-autonomy README section ('Why this exists for frontier autonomy stacks') + 'for reviewers & safety teams' note; added a non-financial `examples/agent_coordination/` demo proving the control primitives are domain-agnostic. No core source changes.

## [2.1.2] — 2026-06-09

Documentation release: README rebuilt to the conversion standard (badge row, proof strip, Autonomy Ladder family block), fixed broken doc/ADR links, reconciled version metadata across pyproject/__init__/CITATION. No source changes.

## [2.1.1] — 2026-05-29

### Fixed (CI/SCM, no source changes)
- Closed all post-v2.1.0-push workflow failures: `ci.yml` mypy `--strict` (install the full optional-extra set so import-guard `type: ignore` comments stay live), `bandit.yml` (SARIF formatter extra), `pip-audit.yml` (direct invocation against the installed tree), `osv-scanner.yml` (drop removed `--skip-git` flag), `gitleaks.yml` (direct SHA-pinned binary invocation). The published v2.1.0 PyPI wheel is unaffected — all changes are CI configuration. Full detail in [`.github/releases/v2.1.1-notes.md`](.github/releases/v2.1.1-notes.md).

### Documentation
- Reconciled package metadata and README to a single version of record (`2.1.1`): bumped `pyproject.toml` from `2.1.0`, updated the README header.
- README upgrade: badge row keyed to verified receipts (630 tests · 93% coverage · zero deps · `mypy --strict` on 46 source files · 34 ADRs · 46 docs); buyer-first failure-mode hook; surfaced the CR-1..CR-12 hardening story and the zero-runtime-deps principle in a dedicated "Security & assurance" section; replaced the two-vertical "Related" section with the six co-equal Autonomy Ladder™ family block; moved the long roadmap to a 3-line teaser pointing at `ROADMAP.md`.
- Fixed 8 broken relative links and the Apache-license filename references (`LICENSE-APACHE-2.0` → `LICENSE-APACHE`): the NYDFS Part 500, State-AG fair-lending matrix, and PCAOB AS 2201 mapping docs, plus the 0027–0030 and 0032 ADR links, now point to their real filenames. All 71 relative links in the README verified to resolve.

---

## [2.1.0] — 2026-05-28

**Tier-1 FSI-buyer hardening release.** Closes all 12 Critical findings from the May 2026 6-chamber adversarial deep-dive (architecture · code · security · test strategy · DevOps · deployment lenses) targeting the questionnaire bar that JPMC Tech Risk, BoA AppSec, Schwab Compliance Tech, BNY Mellon Trust Architecture, Fidelity Risk, Citi Model Risk, UBS Group Information Security, Broadridge InfoSec, and First Data review boards apply to an OSS package before authorizing inbound supply-chain inclusion. Test count 532 → 630 (+98); coverage 91.74% → 93.47%; `mypy --strict` clean across 46 source files; ruff + format + banned-term + tamper-language drift lints clean; CI now SHA-pins every GitHub Action and runs CodeQL + Bandit + pip-audit + gitleaks + OSV-Scanner per push.

### Security + correctness (CR-1 through CR-12)
- **CR-1 — Consolidate duplicate `AuditChainTamperError`.** Both `governance.audit_chain` and `agents.base` defined the exception independently; adopter `except` clauses silently failed to catch the sibling. Single canonical class in `governance.audit_chain`; `agents.base` re-imports. New `tests/test_tamper_error_identity.py` asserts class identity across import paths.
- **CR-2 — Make `AuditEvent` frozen + self-verifying on replay.** `AuditEvent` is now `@dataclass(frozen=True)` with `AuditEvent.create(...)` + `AuditEvent.from_jsonl(data)` classmethods; `from_jsonl` recomputes the hash on every replay and raises `AuditChainTamperError` on mismatch. Updated 5 replay sites (`audit_chain._load_existing`, JSONL/WORM/SQLite decoders, `cli._iter_jsonl`).
- **CR-3 — Bind TSA pre-digest to event content.** `TimestampSource.stamp()` was being called with empty bytes — TSA signed nothing, didn't bind to the event content; the SEC 17a-4 + eIDAS Art. 42 trusted-timestamp story was structurally invalid. Fixed: compute a canonical pre-timestamp digest of `{event_id, event_type, autonomy_level, agent_id, payload, actor_id, prev_hash, schema_version}`; pass it to the TSA; embed the TSR token in `payload["_tsr_token_b64"]` so verifiers can re-check `messageImprint == pre_digest`.
- **CR-4 — Thread- and process-safe `AuditChain.append`.** Added `threading.RLock` wrapping `append`/`verify`/`verify_strict`; `fcntl.flock(LOCK_EX)` added to `JsonlLedgerStore.append` for multi-process safety with a Windows fallback. `tests/test_concurrent_append.py` (5 tests: 16 threads × 50 events, 4 processes × 100 events) confirms no fork / no byte interleaving.
- **CR-5 — Embed DEFCON `metrics_snapshot` in the canonical hash.** `DEFCONMachine` shipped its own duplicate `AuditEvent` class whose `_compute_hash` omitted `metrics_snapshot`; attacker rewriting metrics evaded chain verification. Deleted both duplicates; `DEFCONMachine` now uses the canonical `AuditEvent` with `metrics_snapshot` embedded in `payload` (covered by the canonical hash).
- **CR-6 — Bounded structural ASN.1 walk in the RFC 3161 DER codec.** `parse_timestamp_response` byte-scanned for the first `0x18` (GeneralizedTime tag) — that byte appears in INTEGER bodies, OCTET STRINGs, signature blobs, and cert serial numbers, so an adversarial TSA could return an attacker-chosen timestamp. `_decode_length_at` lacked a bounds check (`0x84 FF FF FF FF` → 4GB length claim, CWE-190/-400). Fixed: bounded length decode (4-byte cap, 100KB field cap, past-buffer guard, indefinite-length rejection); replaced byte-scan with structural ASN.1 walk (`TimeStampResp → SignedData → eContent → TSTInfo → genTime`), validating OIDs at each level. Added `tests/test_rfc3161_codec_fuzz.py` Hypothesis harness — 2000 iterations, zero crashes.
- **CR-7 — Domain-separated genesis hash.** Hard-coded `"0" * 64` genesis sentinel meant every chain in every deployment shared the same genesis → forgery via replacement was trivial. Genesis is now `SHA256("finserv-agent-audit/genesis/v1/{deployer_id}/{chain_creation_iso}")` and seeds chain entry #0 (`AGENT_STARTED`). Legacy chains without `deployer_id` keep the `"0"*64` sentinel with a `DeprecationWarning` on load.
- **CR-8 — Hash PII before it enters the chain.** `customer_id` / `consumer_id` / `suspect_party_ids` were written cleartext into the hash-chained payload across 3 FSI gates — GLBA Safeguards violation; GDPR Art. 17 right-to-erasure collision (a tamper-detecting chain + PII = an unerasable chain). New `governance.subject_id` ships `HashedSubjectId` + `SubjectIdHasher` Protocol + `HMACSubjectIdHasher` reference (peppered, ≥32-byte key, rotatable `pepper_version` for GDPR effective erasure). Wired optional `subject_id_hasher` into `AdverseActionGate`, `SARWorkflowAudit`, `CustomerFacingChatbotGuardrail`; unwired gates log a WARNING naming GLBA + GDPR.
- **CR-9 — Reject `--mi-proxy-key` on the CLI argv.** Argv-passed secrets leak via `ps aux`, `/proc/$pid/cmdline`, container labels, CI logs, and shell history (NIST SP 800-63 violation). Argv flag now hard-rejects with an explicit pointer to `FINSERV_AUDIT_MI_PROXY_KEY`; `action.yml` composite action injects the key via env var only.
- **CR-10 — Honest WORM naming + filesystem-capability probe.** `WORMLedgerStore` was chmod 0o400 theatre (same-UID process reverses in one syscall; NFS/SMB/EFS/S3 ignore mode bits). Renamed `BestEffortWORMLedgerStore` with a docstring naming S3 Object Lock COMPLIANCE / AWS QLDB / Azure Confidential Ledger as the production path; alias retained with `DeprecationWarning`. Added filesystem-capability probe — logs a WARNING if chmod is not honored on the mount.
- **CR-11 — Rename `LocalMIProxy` → `LocalMIProxyFreshnessCheck` + ship `BaselineMIProxy` scaffold.** `LocalMIProxy.enforce_attestation` was a self-loop (same key signed + verified in the same process; `_hash_component` read the live source file at both ends — no chain-of-custody). Renamed with a `⚠ NOT CHAIN-OF-CUSTODY ⚠` docstring; shipped `BaselineMIProxy` that loads a deploy-time-pinned manifest (signed out-of-process by the operator key) and raises `IntegrityVerificationError` on live-source/baseline mismatch. v2.2 will add Sigstore cosign signature verification of the baseline.
- **CR-12 — `Authorizer` Protocol + self-clearing rule on Sovereign Veto + DEFCON override.** `SovereignVeto.clear()` + `DEFCONMachine.manual_override()` accepted any operator_id with no authentication. Added the `Authorizer` Protocol; `SovereignVeto.clear` hard-blocks `operator_id == self.agent_id` even when the authorizer would allow (the "no agent can clear its own veto" docstring claim is now enforced); when an authorizer is wired, `authorize(operator_id, action, context)` is consulted and raises `VetoBlockedError` / `DEFCONOverrideRejectedError` on deny.

### CI + supply-chain (H1.A)
- SHA-pinned every GitHub Action across `.github/workflows/{ci,publish,audit-chain-verify}.yml` and `action.yml` to immutable 40-char SHAs with `# version` comments. Closes the `tj-actions/changed-files`-2025-incident class of supply-chain risk.
- New workflows: `codeql.yml` (Python SAST, weekly + PR; `security-extended` + `security-and-quality` queries), `bandit.yml` (Python SAST), `pip-audit.yml` (daily + PR), `gitleaks.yml` (full-history secret scan), `osv-scanner.yml` (multi-ecosystem vuln scan).
- All workflows declare top-level `permissions: contents: read` (least-privilege default); security-event-writing workflows override per-job. `concurrency:` blocks added — `cancel-in-progress: true` on `ci`, `false` on `publish` (tag pushes must complete), `audit-chain-verify` keys on `inputs.audit-jsonl-path`.
- pre-commit hooks added: `gitleaks`, `actionlint`, `yamllint`, `shellcheck`. New `.yamllint.yml`.
- New `pyproject.toml` optional-dep groups: `test-property` (`hypothesis>=6.115` for the CR-6 fuzz harness) and `security-dev` (`bandit[toml]>=1.7` + `pip-audit>=2.7` for local SAST/SCA). `slow` pytest marker registered.

### Kubernetes hardening (H1.D)
- Operator `Dockerfile` is now multi-stage (`python:3.13-bookworm` builder + `python:3.13-slim-bookworm` runtime), digest-pinned, non-root UID 1000, read-only root filesystem, with a `HEALTHCHECK`. Image tag bumped 2.0.0 → 2.1.0.
- `controller.py` adds an `http.server` thread for `/healthz`, `/readyz`, `/metrics` (Prometheus exposition); ServiceAccount token re-read per API call (was cached at startup — projected-volume token rotation would silently 401 the controller); watch-loop resync every 5 min to recover from edge-network partitions.
- `rbac.yaml` drops list/watch on Pods + events.create (least-privilege); Deployment adds liveness/readiness probes, `PodDisruptionBudget(minAvailable: 1)`, `priorityClassName: system-cluster-critical`, `topologySpreadConstraints` across zones, explicit resource requests/limits, hardened `securityContext` (`runAsNonRoot`, `readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`, `capabilities.drop=[ALL]`, `seccompProfile=RuntimeDefault`).
- New manifests: `servicemonitor.yaml` (Prometheus Operator scraping), `pvc-sample.yaml` (reference PVC), `networkpolicy.yaml` (default-deny ingress; egress allowlist for kube-apiserver + DNS + optional TSA + optional Sigstore Rekor).
- Kyverno policies: `verify-chain-sink.yaml` nested-condition syntax fixed (was silently passing on multi-sink configurations); `require-audit-chain.yaml` + `require-sovereign-veto-armed.yaml` get `failurePolicy: Fail` + `validationFailureAction: Enforce` (was the default `Ignore`/`Audit`, which let admission-controller outages let unaudited workloads in). `match` block constrains to `linus10x.io/v1alpha1/AutonomousAgent`; `background: true` flags existing resources on policy creation.
- OPA Gatekeeper Rego policies rewritten to fail-closed; `default allow = false` at the top of each ConstraintTemplate.

### Author-action drafts (H2.A — `MANUAL_REMEDIATION_AUTHOR.md` index)
The following 11 documents land as DRAFTS for author review — they are not in-effect by virtue of landing in the repo. Each carries an "Author Action Required" preamble naming the decision, the recommendation, and the consequence of inaction.
- `LICENSE-APACHE-2.0` — full Apache 2.0 text staged alongside MIT (does not replace). Tier-1 bank legal review at JPMC / BoA / Schwab / BNY routinely declines MIT projects for inbound supply-chain inclusion because MIT lacks an explicit patent grant; Apache 2.0 §3's express patent license is the standard they ask for. Author decision: keep MIT · dual-license · replace with Apache 2.0. Default recommendation: dual-license at adopter election.
- `docs/ETHICS_WALL.md` — formalizes the information barrier between NTCI research lab (builder of APEX et al — buy-side surface) and NTCI Consulting LLC (advisory entity that delivers paid Diagnostics + Audits using this framework). Required disclosure for any Tier-1 buyer asking "do you trade against your clients."
- `docs/SOC2_ENGAGEMENT_RFP.md` — RFP template for Schellman / A-LIGN / Coalfire engaging a SOC 2 Type I (point-in-time, 4-6 weeks, $25-40K) as the first attestation artifact, then a Type II (observation window, 6-12 months, $60-100K) gated on Cohort-Zero customers.
- `docs/TRADEMARK.md` — "Autonomy Ladder" + "ALO" usage guidelines pending the USPTO classes 9/35/41/42 filing scheduled for 2026-06-15 per the AL v3 LOCKED plan.
- `docs/CO_MAINTAINER_RECRUITMENT_DRAFT.md` — LinkedIn post draft (under 300 words, voice-rules compliant) recruiting 1-2 co-maintainers from the 8K-follower base.
- `docs/LFAI_SANDBOX_APPLICATION_DRAFT.md` — LF AI & Data Foundation Sandbox-track application per the AL v3 LOCKED plan's neutrality-foundation move. Sandbox (not Incubation) is the right starting point — Incubation requires multi-org maintainership, which the co-maintainer recruitment item above is the path to.
- `docs/COHORT_ZERO_PRICING_PUBLIC.md` — formal publication of the $1K pilot pricing for the first 5 logos (recruiting tool, not profit center). Standard $5K Diagnostic pricing remains out-of-repo at autonomy-ladder.io/services per the existing brand-asset strategy.
- `docs/tier1_buyer_prefills/SIG_LITE_PREFILL.md` — pre-filled SIG Lite (Shared Assessment Group, 2025, ~125 questions; ~60% pre-fill rate).
- `docs/tier1_buyer_prefills/CAIQ_PREFILL.md` — pre-filled CSA CAIQ v4.0.3 (~261 questions; ~45% pre-fill rate).
- `docs/tier1_buyer_prefills/BITS_AUP_PREFILL.md` — pre-filled BITS Shared Assessments AUP (FS-ISAC member-bank deep-review questionnaire).

### Breaking changes (semver-minor — `!` on commit, minor bump)
- `AuditEvent` is now frozen — code that mutated `event.event_hash` post-construction now raises `FrozenInstanceError`. Replay code MUST use `AuditEvent.from_jsonl`.
- DEFCON audit-event on-disk JSONL schema changed (`metrics_snapshot` now embedded in canonical `payload`, not a top-level field). v2.0 DEFCON JSONL replay requires one-time migration — see release notes.
- CLI `--mi-proxy-key` flag is now hard-rejected; existing CI/CD using the argv form will fail with a clear error directing operators to the env var.
- `LocalMIProxy` → `LocalMIProxyFreshnessCheck`; `WORMLedgerStore` → `BestEffortWORMLedgerStore`. Backward-compat aliases emit `DeprecationWarning`.

---

## [2.0.0] — 2026-XX-XX (release date set at tag time)

**Agentic-AI ecosystem + platform surfaces.** Ships four agentic-runtime audit adapters (Google A2A, LangGraph, Microsoft Agent Framework, CrewAI), the `AIBOMGenerator` (CycloneDX 1.7 ML-BOM + SPDX 3.0 AI Profile dual emit), a FastAPI governance endpoint with OpenAPI 3.1 + Server-Sent Events, a Kubernetes operator stub with three custom resource definitions (AuditChain, SovereignVeto, ChainSink) and Kyverno + OPA sample admission policies, an adversarial test pack (Garak probes + Promptfoo scenarios + Python harness) per the ADR-0018 threat model, eight new ADRs (0027-0034), and five new strategic docs (NAIC insurance, DORA, EU AI Act August 2026 compliance pack, PE portfolio playbook, PCAOB AS 2201 amendments) plus a PE portfolio dashboard reference.

> Maintainer: the bullets below anticipate the full shape of v2.0 across Tranches A-E. Refresh from the actual landed commits at tag time — keep only what shipped; move anything that slipped to `[Unreleased]` `### Planned (v2.1)`.

### Added — Code

#### Agentic-runtime adapters (Tranche A — `src/finserv_agent_audit/integrations/`)
- `a2a_adapter.py` — `A2AAuditAdapter`: wraps an A2A (Agent2Agent, Linux-Foundation-donated 2025) server or client and emits one `AuditEvent` per task-lifecycle transition and per message exchange. Transport-agnostic; integrates SovereignVeto on inbound-task pre-execution (per ADR-0027).
- `langgraph_adapter.py` — `LangGraphAuditCallback`: LangGraph node / edge callback that emits an `AuditEvent` per node-entry, node-exit, conditional-edge resolution, and human-in-the-loop interrupt. Wires SovereignVeto checks at the node-pre-execution boundary (per ADR-0028).
- `maf_adapter.py` — `MAFAuditAdapter`: Microsoft Agent Framework adapter; emits one `AuditEvent` per agent-step, tool-call, and orchestrator-handoff. Supports both single-agent and group-chat orchestration patterns (per ADR-0029).
- `crewai_adapter.py` — `CrewAIAuditAdapter`: CrewAI adapter wrapping Crew, Agent, and Task lifecycle hooks; emits per-task-start / per-task-end / per-tool-invocation AuditEvents and surfaces SovereignVeto at the Crew kickoff boundary (per ADR-0030).

#### Platform surfaces (Tranches B + C)
- `governance/aibom.py` — `AIBOMGenerator`: dual-emit AI Bill of Materials per the CycloneDX 1.7 ML-BOM profile (machine-learning-model component type + modelCard extension) and the SPDX 3.0 AI Profile (ai_AIPackage class + AI-specific properties). One governance call -> two procurement-grade artifacts (per ADR-0031).
- `integrations/governance_api.py` — FastAPI governance endpoint exposing DEFCON state, veto log, audit-chain verification, vendor-score drift, deprecation calendar, and AIBOM emit as REST resources under OpenAPI 3.1. Includes a Server-Sent Events live stream of `AuditEvent` flow. Optional extra `[api]` (per ADR-0032).
- `deploy/k8s/operator/` — Kubernetes operator stub with reconciler skeletons for the three CRDs below. Designed to run as a controller-pattern Deployment in the governance namespace (per ADR-0033).

#### Schema extension
- `AuditEventType` enum picks up the runtime-adapter and operator surfaces (one event-type per adapter milestone class) where the tranche-A subagents landed enum amendments; the major-version bump validates the enum-vocabulary expansion without a wire-format break.

### Added — Documentation

#### Eight new ADRs in `docs/adr/`
0027 A2A Audit Adapter · 0028 LangGraph Audit Callback · 0029 Microsoft Agent Framework Audit Adapter · 0030 CrewAI Audit Adapter · 0031 AIBOM Generator (CycloneDX 1.7 + SPDX 3.0) · 0032 FastAPI Governance Endpoint · 0033 Kubernetes Operator + CRDs · 0034 Adversarial Test Pack.

#### Five new strategic docs in `docs/`
- `docs/naic_model_bulletin_ai_insurers_mapping.md` — NAIC Model Bulletin on the Use of AI Systems by Insurers; insurance-vertical mapping for the v1.4 carry-forward item.
- `docs/dora_mapping.md` — Regulation (EU) 2022/2554 (Digital Operational Resilience Act) crosswalk; Art. 28 third-party-ICT risk + ICT incident-reporting overlay aligned to `VendorAttestationLedger` + `AuditChain`.
- `docs/eu_ai_act_aug_2026_compliance_pack.md` — Consolidated EU AI Act compliance pack timed to the August 2026 high-risk-AI substantive-obligation entry into force; bundles the Art. 9 risk-management, Art. 12 logging, Art. 13 transparency, Art. 14 human-oversight, and Art. 15 accuracy / robustness / cybersecurity controls into a deployer checklist.
- `docs/pe_portfolio_playbook.md` — PE operating-partner-facing rollout sequence for portco AI governance; 30 / 60 / 90 / 180-day deliverables anchored to the v1.1-v2.0 surface.
- `docs/pcaob_as_2201_amendments_appendix.md` — PCAOB AS 2201 amendment overlay as a separate `ASSURANCE-GUIDE` appendix; Big-4 audit-evidence walkthrough refreshed to the amended ICFR-attestation surface.

#### One PE portfolio dashboard reference + adversarial-testing guide
- `docs/pe_portfolio_dashboard.md` — Reference dashboard schema (KPIs, status colors, escalation triggers) accompanying the playbook.
- `tests/adversarial/README.md` — Adversarial test pack guide covering the Garak probe set, Promptfoo scenario set, and the Python harness wiring.

#### Kubernetes deploy README
- `deploy/k8s/README.md` — One-page operator deployment guide covering the three CRDs, the controller Deployment, and the Kyverno / OPA sample admission policies.

### Added — Tests

#### Adversarial test pack (Tranche D — `tests/adversarial/`)
- `tests/adversarial/garak/` — Garak probe set targeting prompt-injection, sycophancy, and policy-bypass against the customer-facing chatbot guardrail and the LangGraph audit callback boundary.
- `tests/adversarial/promptfoo/` — Promptfoo configs for the EALD-search, effective-challenge, and LLM disparate-impact harness surfaces; deterministic-seed scenarios driving the assertion grid.
- `tests/adversarial/test_harness.py` — Python harness coordinating the Garak + Promptfoo runs and writing the consolidated report consumed by the `ASSURANCE-GUIDE` PCAOB AS 2201 appendix.

#### Per-adapter, AIBOM, and governance-API tests
- `tests/test_a2a_adapter.py` · `tests/test_langgraph_adapter.py` · `tests/test_maf_adapter.py` · `tests/test_crewai_adapter.py` — per-adapter unit tests covering each lifecycle-hook emission and the SovereignVeto wiring.
- `tests/test_aibom.py` — `AIBOMGenerator` round-trip tests covering both CycloneDX 1.7 and SPDX 3.0 emit paths plus the canonical hashing of both documents.
- `tests/test_governance_api.py` — FastAPI governance endpoint tests covering each REST resource + the SSE live stream + the OpenAPI 3.1 schema export.

### Added — CI + tooling
- `deploy/k8s/crds/` — Three custom resource definitions (`auditchain.yaml`, `sovereignveto.yaml`, `chainsink.yaml`) for the operator.
- `deploy/k8s/policies/kyverno/` + `deploy/k8s/policies/opa/` — Sample admission-policy bundles for the two most-deployed Kubernetes policy engines.
- `deploy/k8s/operator/Dockerfile` — Container build for the operator controller process.
- `pyproject.toml` gains five new optional-dependency groups: `[a2a]`, `[langgraph]`, `[maf]`, `[crewai]`, `[api]`. New convenience bundle `[all-agentic]` pulls every runtime adapter at once; `[all-integrations]` expands to include every v2.0 onramp.

### Changed
- `README.md` rewrite to v2.0 — Patterns Included section re-versioned, v2.0 agentic-AI ecosystem adapters sub-table added, v2.0 platform surfaces sub-table added, "How It Compares" table picks up v2.0 cells (adversarial-test pack as the named competitive moat), Roadmap section refreshed with "Shipped in v2.0", "Coming in v2.1", "Coming in v3.0", new "Deployment" section linking `deploy/k8s/README.md` + the FastAPI governance API doc, Related-family parity table picks up v2.0 rows, closing summary line picks up the v2.0 surfaces.
- `ROADMAP.md` — `v2.0 — Agentic-AI Ecosystem + Platform Surfaces` flipped from planned to `✅ Released` with every item checked; new `v2.1 — Ecosystem Completion` planned section added; new `v3.0 — Async + Multi-Region + WASM` planned section added.
- `CITATION.cff` abstract expanded to cite the four agentic-runtime adapters + AIBOM + FastAPI governance endpoint + Kubernetes operator + adversarial test pack + the five v2.0 strategic docs + DORA + PCAOB AS 2201 amendments + NAIC bulletin.
- `src/finserv_agent_audit/__init__.py` docstring rewritten to enumerate the v2.0 public-API additions.
- `src/finserv_agent_audit/integrations/__init__.py` exports refreshed to import-guard the four agentic-runtime adapter classes alongside the v1.2 OTEL emitter.
- `src/finserv_agent_audit/governance/__init__.py` exports add `AIBOMGenerator`.

### Breaking Changes
- **None.** v2.0 is fully additive against v1.3. The major-version bump signals ecosystem maturity (four runtime adapters + Kubernetes operator + REST endpoint + AIBOM dual emit) rather than a wire-format or import-path break. All v1.x imports continue to resolve. The v1.1 deprecation re-export shims at `patterns/`, `schemas/`, and `examples/defcon_state_machine.py` are still in place — their removal is now scheduled for v2.1 (one additional minor-bump grace window beyond the originally announced v1.2 removal).

### Fixed
- Drift-test allow-list (`tests/doc_staleness_allow_list.py`) refreshed to acknowledge the v2.0 prose co-occurrences (adapter-class names appearing in proximity to "deferred" markers that reference the v2.1 ecosystem-completion list, etc.).

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

[2.0.0]: https://github.com/linus10x/finserv-agent-audit/releases/tag/v2.0.0
[1.0.0]: https://github.com/linus10x/finserv-agent-audit/releases/tag/v1.0.0
[Unreleased]: https://github.com/linus10x/finserv-agent-audit/compare/v2.0.0...HEAD
