# SHIP-RECEIPT.md — v1.1.0 export classification

**Status:** v1.1.0 · Last reviewed: 2026-05-28.

Every public name in `finserv_agent_audit.governance.__all__`, `finserv_agent_audit.agents.__all__`, and `finserv_agent_audit.schemas.__all__` is classified below as one of:

- **shipped** — real implementation, tested, exercised by 273-test CI suite
- **stub-with-tracking** — `NotImplementedError` raise with ADR pointer; reserved API surface
- **deferred-with-tracking** — planned, not yet in `__all__`; placeholder for ADR ledger

Schema names in the ledger that resolve via a `__getattr__` shim (the v1.0 → v1.1 `AuditChain` import-path preservation) are noted in the row.

> Companion to [`FAILURE-MODES.md`](FAILURE-MODES.md), [`LIMITATIONS.md`](LIMITATIONS.md).

---

## `finserv_agent_audit.governance` exports

| Name | Status | Module | Notes |
|---|---|---|---|
| `AuditChain` | shipped | `governance.audit_chain` | Extracted from `schemas/` in v1.1; v1.0 import path preserved via `schemas/__init__.py` `__getattr__` |
| `AuditChainTamperError` | shipped | `governance.audit_chain` | Raised by `verify` / `verify_strict` on hash-chain mismatch |
| `DEFCON` | shipped | `governance.defcon` | Enum: NORMAL → MONITOR → ALERT → CRITICAL → HALT |
| `DEFCONMachine` | shipped | `governance.defcon` | Hysteresis-controlled state machine (ADR-0001) |
| `RiskMetrics` | shipped | `governance.defcon` | Input dataclass for DEFCON evaluation |
| `SovereignVeto` | shipped | `governance.sovereign_veto` | Human-only kill switch (ADR-0002) |
| `VetoBlockedError` | shipped | `governance.sovereign_veto` | Raised on action attempt while vetoed |
| `VetoReason` | shipped | `governance.sovereign_veto` | Enum: HUMAN_OVERRIDE / RISK_STATE / POLICY / PEER_AGENT |
| `VetoRecord` | shipped | `governance.sovereign_veto` | Veto event dataclass |
| `InMemoryLedgerStore` | shipped | `governance.ledger_store` | Default in-process backend; test fixture |
| `LedgerStore` | shipped | `governance.ledger_store` | Protocol (ADR-0014 Seam 1) |
| `JsonlLedgerStore` | shipped | `governance.ledger_store_jsonl` | Append-only JSONL backend |
| `SqliteLedgerStore` | shipped | `governance.ledger_store_sqlite` | SQLite backend with unique-constraint conditional write |
| `WORMLedgerStore` | shipped | `governance.ledger_store_worm` | SEC 17a-4 best-effort WORM (ADR-0013); pair with S3 Object Lock COMPLIANCE for production |
| `WORMViolationError` | shipped | `governance.ledger_store_worm` | Raised on append-to-finalized attempts |
| `LocalClock` | shipped | `governance.timestamp_source` | Default `TimestampSource`; `time.time_ns()` |
| `RFC3161Source` | shipped | `governance.timestamp_source` | RFC 3161 TSA client; `fallback_to_local_on_failure` default True |
| `TimestampSource` | shipped | `governance.timestamp_source` | Protocol (ADR-0014 Seam 2) |
| `build_timestamp_request` | shipped | `governance.rfc3161_codec` | RFC 3161 ASN.1 request encoder (stdlib only) |
| `parse_timestamp_response` | shipped | `governance.rfc3161_codec` | RFC 3161 ASN.1 response decoder; **verify-side cross-check** against TSA cert is `NOT YET IMPLEMENTED · tracking ADR-0014-A1` |
| `OpenTimestampsWitness` | shipped | `governance.witness_anchor` | OTS calendar client (ADR-0014 Seam 3) |
| `RekorWitness` | shipped | `governance.witness_anchor` | Sigstore Rekor client (ADR-0014 Seam 3) |
| `WitnessRegister` | shipped | `governance.witness_anchor` | Protocol (ADR-0014 Seam 3) |
| `anchor_to_witness` | shipped | `governance.witness_anchor` | Helper: anchor chain head + write `WITNESS_ANCHOR` chain entry |
| `IntegrityVerificationError` | shipped | `governance.mi_proxy` | Raised by `enforce_attestation` on attestation failure |
| `LocalMIProxy` | shipped | `governance.mi_proxy` | HMAC-SHA256 stdlib backend (ADR-0015) |
| `MIProxy` | shipped | `governance.mi_proxy` | Protocol (ADR-0014 Seam 4) |
| `enforce_attestation` | shipped | `governance.mi_proxy` | Verify-side helper; raises on attestation failure |
| `InMemoryVendorScoreGate` | shipped | `governance.vendor_score_gate` | Default vendor-drift backend (ADR-0016) |
| `VendorClass` | shipped | `governance.vendor_score_gate` | Five FSI vendor categories pre-registered |
| `VendorScoreDriftDetected` | shipped | `governance.vendor_score_gate` | Raised on (vendor_id, input_hash, model_version) collision with diff score |
| `VendorScoreEntry` | shipped | `governance.vendor_score_gate` | Vendor-score record dataclass |
| `VendorScoreGate` | shipped | `governance.vendor_score_gate` | Protocol (ADR-0016) |
| `AdverseActionGate` | shipped | `governance.adverse_action_gate` | FCRA § 615 + CFPB Circular 2022-03 (ADR-0009) |
| `AdverseActionViolation` | shipped | `governance.adverse_action_gate` | Raised when reason codes are generic / lack traceability |
| `BestInterestCheck` | shipped | `governance.best_interest_check` | SEC Reg-BI care obligation (ADR-0007 family) |
| `BestInterestViolation` | shipped | `governance.best_interest_check` | Raised on Reg-BI care-obligation failure |
| `RecommendationProfile` | shipped | `governance.best_interest_check` | Investor / recommendation input dataclass |
| `EquityAudit` | shipped | `governance.equity_audit` | ECOA / Reg-B fair-lending pre-flight (ADR-0010) |
| `EquityAuditViolation` | shipped | `governance.equity_audit` | Raised on fair-lending gate failure |
| `ProtectedClass` | shipped | `governance.equity_audit` | Enum: protected-class categories for Reg-B |
| `ImplementationStatus` | shipped | `governance.model_inventory` | SR 11-7 model-status state machine |
| `Model` | shipped | `governance.model_inventory` | Model record dataclass |
| `ModelInventory` | shipped | `governance.model_inventory` | SR 11-7 second-line recordkeeping surface |
| `ProtectedClassProxyDetector` | **stub-with-tracking** | `governance.protected_class_proxy_detector` | Raises `NotImplementedError` per ADR-0019 by design; v1.2 ship-gate |
| `SARWorkflowAudit` | shipped | `governance.sar_workflow_audit` | BSA/AML § 5318(g)/(h) workflow recordkeeping (ADR-0011) |
| `AutonomyTier` | shipped | `governance.autonomy_ladder` | Enum: A0 / A1 / A2 / A3 / A4 |
| `PromotionGateNotMet` | shipped | `governance.autonomy_ladder` | Raised on A2→A3 promotion failure |
| `PromotionGateReport` | shipped | `governance.autonomy_ladder` | Promotion-gate outcome dataclass |
| `PromotionRequirements` | shipped | `governance.autonomy_ladder` | A2→A3 requirements config |
| `check_a2_to_a3_promotion` | shipped | `governance.autonomy_ladder` | Promotion-gate evaluation helper (ADR-0004 + 0007) |
| `DecisionClass` | shipped | `governance.shadow_mode` | Shadow-mode decision-category enum |
| `DecisionOutcome` | shipped | `governance.shadow_mode` | Shadow vs live outcome dataclass |
| `PromotionVerdict` | shipped | `governance.shadow_mode` | Shadow→live promotion verdict |
| `ShadowRouter` | shipped | `governance.shadow_mode` | SR 11-7 pre-promotion parallel-run router (ADR-0006) |
| `VetoDirection` | shipped | `governance.shadow_mode` | Shadow-mode veto direction enum |

## `finserv_agent_audit.agents` exports

| Name | Status | Module | Notes |
|---|---|---|---|
| `Agent` | shipped | `agents.base` | Reference base; production deployers subclass |
| `AgentResult` | shipped | `agents.base` | Agent-call result dataclass |
| `AuditAgent` | shipped | `agents.audit` | Reference agent demonstrating AuditConsumer wiring |
| `AuditChainTamperError` | shipped | `agents.base` | Re-export from `governance.audit_chain` for agent-side convenience |
| `AuditConsumer` | shipped | `agents.base` | One-injection-contract base for the 4 Protocol seams + optional VendorScoreGate |
| `MonitorAgent` | shipped (reference stub body) | `agents.monitor` | Class shipped; method body is a reference stub — production deployers fill in the chain-scan logic |
| `OrchestratorAgent` | shipped (reference stub body) | `agents.orchestrator` | Class shipped; method body is a reference stub — production deployers wire routing |

## `finserv_agent_audit.schemas` exports

| Name | Status | Module | Notes |
|---|---|---|---|
| `AuditChain` | shipped (re-export) | `schemas` → `governance.audit_chain` | v1.0 import-path preservation via `__getattr__` shim |
| `AuditEvent` | shipped | `schemas.audit_event` | Core event dataclass; SHA-256 hashed in `AuditChain` |
| `AuditEventType` | shipped | `schemas.audit_event` | Extended in v1.1: VENDOR_SCORE_RECORDED, VENDOR_SCORE_DRIFT_DETECTED, WITNESS_ANCHOR, MODEL_VALIDATED, ADVERSE_ACTION_TAKEN, SAR_FILED, BEST_INTEREST_CHECKED |
| `AutonomyLevel` | shipped | `schemas.audit_event` | Maps to A0–A4 |

---

## Classification counts

| Status | Count |
|---|---|
| shipped | 64 |
| stub-with-tracking | 1 (`ProtectedClassProxyDetector` per ADR-0019) |
| deferred-with-tracking | 0 |
| reference-stub-body (class ships; method body is a reference) | 2 (`MonitorAgent`, `OrchestratorAgent`) |
| **Total** | **67** |

Two RFC 3161 verify-side cross-checks (TSA cert chain validation, witness re-verification on read) are tracked as `NOT YET IMPLEMENTED · ADR-0014-A1 / A2` inside callable bodies, not as separate `__all__` entries.

## Related

- [`FAILURE-MODES.md`](FAILURE-MODES.md) — which classes have an `(F)` callable
- [`LIMITATIONS.md`](LIMITATIONS.md) — bounded claims
- [`VERSIONING.md`](VERSIONING.md) — SemVer policy and v1.1 delta
- ADR-0019 — ProtectedClassProxyDetector deferred-implementation rationale
