# VERSIONING.md — SemVer policy and the v1.0 → v1.1 leap

**Status:** v1.1.0 · Last reviewed: 2026-05-28.

---

## Why finserv-agent-audit is at v1.x and cre-agent-audit is at v0.x

A common question from adopters reviewing both repos: `finserv-agent-audit` is at v1.1 while the companion `cre-agent-audit` is at v0.2.x. Both ship the same kind of governance primitives. Why the version asymmetry?

The two packages were authored in parallel during May 2026 and serve different verticals (financial services vs commercial real estate). They are sister patterns of the same Autonomy Ladder discipline, but they ship on independent release cycles.

- **finserv-agent-audit v1.0.0 (2026-05-15)** was cut as the "Foundation" release covering DEFCON, Sovereign Veto, Autonomy Ladder, and the hash-chain audit primitive. v1.0 was published before the cre-agent-audit hardening cycle had concluded; the FSI vertical needed a stable surface for engagement conversations earlier than CRE did.
- **cre-agent-audit v0.x** has been iterating openly. The cross-vertical-discipline framework — Protocol seams, MIProxy, VendorScoreGate, FailureModes matrix-as-contract — was developed inside the cre repo's hardening cycle. When that framework stabilizes across both verticals, cre-agent-audit will cut v1.0.0.
- **finserv-agent-audit v1.1.0 (this release)** ports the matured cross-vertical discipline back into the FSI repo as a minor bump. Once the cross-vertical contract is locked, both repos will tick forward together.

The result: finserv's version number reflects when its **public surface** stabilized; cre's version number reflects when its **shared-discipline contract** stabilized. The numbers will converge in the v1.x line going forward.

---

## SemVer policy

This project follows [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

| Bump | Meaning |
|---|---|
| **MAJOR** | Breaking change to a public API — removed export, changed callable signature, removed Protocol method, changed dataclass field name, removed `AuditEventType` enum value, changed hash-chain serialization format, raised exception type changed |
| **MINOR** | New patterns, new modules, new ADRs, new Protocol seam, new `AuditEventType` enum value (additive), new optional parameter (with default), new mapping document |
| **PATCH** | Bug fixes, internal refactor with no public-surface change, documentation correction, test additions, regulatory citation refresh |

The public surface is everything in `finserv_agent_audit.governance.__all__`, `finserv_agent_audit.agents.__all__`, `finserv_agent_audit.schemas.__all__`, and the Protocol signatures referenced by these exports. Anything underscore-prefixed (`_chain_head`, `_validate_inputs`, etc.) is private; we may rename it in a patch.

Deprecation path: A removal-grade change is marked `DeprecationWarning` in one MINOR release before removal in the next MAJOR. Mapping documents may be re-cited at PATCH cadence; they are reference material, not API.

---

## v1.1.0 changelog summary (this release)

The full Keep-a-Changelog entry lives in [`CHANGELOG.md`](CHANGELOG.md) § `[1.1.0]`. The high-level delta:

**Added — Protocol seams (ADR-0014, ADR-0015):**
- `LedgerStore` Protocol + four implementations (`InMemoryLedgerStore`, `JsonlLedgerStore`, `SqliteLedgerStore`, `WORMLedgerStore`)
- `TimestampSource` Protocol + two implementations (`LocalClock`, `RFC3161Source`) with RFC 3161 ASN.1 codec (`build_timestamp_request`, `parse_timestamp_response`)
- `WitnessRegister` Protocol + two implementations (`RekorWitness`, `OpenTimestampsWitness`) + `anchor_to_witness()` helper
- `MIProxy` Protocol + `LocalMIProxy` HMAC-SHA256 backend + `enforce_attestation` helper + `IntegrityVerificationError`

**Added — Vendor-mediated AI (ADR-0016):**
- `VendorScoreGate` Protocol + `InMemoryVendorScoreGate` backend
- `VendorScoreEntry` dataclass, `VendorClass` enum with five FSI categories, `VendorScoreDriftDetected` exception

**Added — FSI-specific governance (ADRs 0007–0011, 0013, 0019):**
- `ModelInventory` (SR 11-7 three-lines-of-defense recordkeeping)
- `AdverseActionGate` (FCRA § 615 + CFPB Circular 2022-03)
- `SARWorkflowAudit` (BSA/AML § 5318(g)/(h))
- `EquityAudit` (ECOA / Reg-B fair-lending pre-flight)
- `BestInterestCheck` (SEC Reg-BI care obligation)
- `ProtectedClassProxyDetector` (stub-with-tracking per ADR-0019)

**Added — Operational patterns:**
- `ShadowRouter` and supporting types (`DecisionClass`, `DecisionOutcome`, `PromotionVerdict`, `VetoDirection`) — SR 11-7 pre-promotion parallel runs (ADR-0006)
- `AutonomyLadder` runtime helper (`check_a2_to_a3_promotion`, `PromotionRequirements`, `PromotionGateReport`, `PromotionGateNotMet`)

**Added — Agent surface (Tranche 2B):**
- `agents/` package with `Agent`, `AuditConsumer`, `AgentResult`, and three reference agents (`AuditAgent`, `MonitorAgent`, `OrchestratorAgent`)

**Added — ADRs:** 0006–0019 (fourteen new ADRs covering Shadow Mode, SR 11-7 overlay, GLBA Safeguards, FCRA / Reg-V, ECOA / Reg-B, BSA/AML, SOX 404 ITGC, SEC 17a-4 WORM, the three Protocol-seam ADRs, MIProxy, VendorScoreGate, retention / privilege / discovery, adversarial agent threat model, and the ProtectedClassProxyDetector deferral)

**Added — Regulatory mapping documents:** 14 docs in `docs/` (SR 11-7, OCC 2011-12, SOX 404 ITGC, SEC 17a-4, SEC Reg-BI, FCRA / Reg-V, ECOA / Reg-B, BSA/AML, GLBA Safeguards, EU AI Act, NIST AI RMF, ISO/IEC 42001, COSO ICAIR, CFPB Circular 2022-03)

**Added — Repo-root governance / release surfaces:** This document + `FAILURE-MODES.md`, `LIMITATIONS.md`, `ARCHITECTURE.md`, `DISCLAIMER.md`, `SHIP-RECEIPT.md`, `NEGATIVE-USE-CASES.md`, `RESEARCH.md`, `ASSURANCE-GUIDE.md`, `DEPLOY-CHECKLIST.md`, `OWNERSHIP.md`, `RELEASE-INSTRUCTIONS.md`

**Added — Schema extensions:**
- `AuditEventType` extended with: `VENDOR_SCORE_RECORDED`, `VENDOR_SCORE_DRIFT_DETECTED`, `WITNESS_ANCHOR`, `MODEL_VALIDATED`, `ADVERSE_ACTION_TAKEN`, `SAR_FILED`, `BEST_INTEREST_CHECKED` (additive — MINOR-compatible)

**Changed — internal layout:**
- `AuditChain` moved from `schemas/audit_event.py` to `governance/audit_chain.py` so it can consume the four Protocol seams. The v1.0 import path (`from finserv_agent_audit.schemas import AuditChain`) is preserved via a `__getattr__` shim in `schemas/__init__.py`. No deprecation warning is emitted — the import remains supported indefinitely.

**Tests:** 273 passing on Python 3.12 + 3.13 in CI (v1.0 baseline: ~80 tests).

**Runtime dependencies:** Zero. The package continues to depend only on the Python ≥ 3.12 standard library.

---

## Backward compatibility

v1.0 → v1.1 is a strict MINOR bump:
- All v1.0 exports are still importable from their v1.0 paths.
- The `AuditChain` relocation is transparent to callers; the `schemas.__init__.py` `__getattr__` shim handles the import.
- `AuditEventType` additions are additive (no enum value renamed or removed).
- No callable signature in the v1.0 public surface has changed.
- No default behavior in v1.0 callables has changed.

If an adopter on v1.0 upgrades to v1.1 without touching their import statements, their existing code keeps working. To use the new Protocol seams, the adopter opts in by constructing the seam instances and passing them to the new constructors.

## Related

- [`CHANGELOG.md`](CHANGELOG.md)
- [`ROADMAP.md`](ROADMAP.md)
- [`SHIP-RECEIPT.md`](SHIP-RECEIPT.md)
- [`RELEASE-INSTRUCTIONS.md`](RELEASE-INSTRUCTIONS.md)
