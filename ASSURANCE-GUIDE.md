# ASSURANCE-GUIDE.md — Audit-evidence walkthrough for SOX 404 / SOC 2 / OCC examination

**Status:** v1.1.0 · Last reviewed: 2026-05-28.

This document is the assurance-side guide a Big-4 audit team, an SOC 2 examiner, or an OCC examination team can read end-to-end to understand what evidence the framework produces and how to interview the deployer about it.

It is organized around three audit lenses commonly applied to FSI deployments: **SOX 404 ITGC** (internal controls over financial reporting), **SOC 2 Trust Services Criteria** (security and availability), and **OCC examination procedures** (model risk management, third-party risk, BSA/AML).

> Companion to [`FAILURE-MODES.md`](FAILURE-MODES.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), [`DEPLOY-CHECKLIST.md`](DEPLOY-CHECKLIST.md), and the per-regime mapping docs in `docs/`.
>
> **Citation update (April 17, 2026):** Where this guide references SR 11-7 / OCC Bulletin 2011-12 as the prudential MRM citation, note that those instruments were superseded for new examinations / rescinded by the joint OCC / FRB / FDIC issuance of April 17, 2026 (OCC Bulletin 2026-13), which **excluded generative + agentic AI from scope** pending a forthcoming joint RFI. The SR-11-7-flavored walkthroughs below survive as analytical scaffolding; the binding-citation header on the exam exhibit shifts. See [`docs/interagency_mrm_2026_overlay.md`](docs/interagency_mrm_2026_overlay.md) for the framework's pre-RFI positioning and [`docs/MRM_BRIDGE_TEMPLATE.md`](docs/MRM_BRIDGE_TEMPLATE.md) for the forkable internal-whitepaper template a second-line MRM team can submit.

---

## Claim scope — implemented controls vs documented patterns

Before an examiner reads the evidence below, two obligations referenced in the mapping docs are **documented design patterns, NOT implemented controls** in this package — there is no validator to test for either:

- **SEC Rule 15c3-5 (market-access / pre-trade risk controls)** — documented pattern, not implemented. No pre-trade 15c3-5 risk-check validator ships here; the DEFCON ladder and audit chain are scaffolding an adopter wires to their own 15c3-5 controls.
- **OFAC sanctions screening** — documented pattern, not implemented. No OFAC list ingestion / name-matching / screening validator ships here; the vendor-score gate governs a screening **vendor's** output and maps the obligation, but performs no screening.

Do not record a test result for a 15c3-5 or OFAC *control* against this library — there is none to exercise. See [`FAILURE-MODES.md`](FAILURE-MODES.md) § "Documented-pattern obligations".

---

## Part 1 — Using the audit chain as evidence

### Chain integrity

**Control objective.** The audit log accurately reflects the operations the agent performed, and any modification to a prior entry is detectable.

**Evidence the framework produces:**
- `AuditChain.verify()` returns `True` when the chain is intact; raises `AuditChainTamperError` otherwise.
- `AuditChain.verify_strict()` adds sequence-monotonicity checks and an optional `mi_proxy=` parameter to attest the verifier itself.

**How to test (auditor walkthrough):**
1. Ask the deployer to run `AuditChain.verify()` on the production chain in the auditor's presence.
2. Ask the deployer to demonstrate the failure mode: mutate one byte of a JSONL entry in a non-production copy; re-run `verify()`; observe `AuditChainTamperError`.
3. Tie the chain entries to the operational record: pick three entries from the chain at random; ask the deployer to show what operation each entry corresponds to and how the operation's outcome was acted on.

### Chain immutability

**Control objective.** The audit log is non-rewritable for the regulatory retention period.

**Evidence the framework produces:**
- `JsonlLedgerStore` is append-only by design; no `update()` or `delete()` callable exists.
- `WORMLedgerStore` raises `WORMViolationError` on any attempt to mutate a finalized file.
- The deployer's substrate (S3 Object Lock COMPLIANCE mode, equivalent) provides the storage-layer enforcement that complements the framework-layer enforcement.

**How to test:**
1. Ask the deployer to show the bucket policy / Object Lock configuration for the production ledger backend.
2. Ask the deployer to attempt a mutation against the production substrate (e.g. `aws s3api put-object` with a key that already exists under Object Lock COMPLIANCE); observe the AccessDenied.
3. For the WORM backend in particular: ask the deployer to demonstrate the framework-level `WORMViolationError` raise on a non-production file.

### Chain attestation

**Control objective.** The verifier binary that produced a "chain intact" result is the verifier the deployer says it is.

**Evidence the framework produces:**
- `MIProxy.attest()` produces an attestation over the verifier's source + canonical config.
- `MIProxy.verify_integrity(claim, attestation)` and the `enforce_attestation(proxy, component_id)` helper raise `IntegrityVerificationError` on failure.
- `LocalMIProxy` (HMAC-SHA256 default) is the stdlib backend; substrate-pluggable backends (SLSA provenance, in-toto attestations) are the higher-assurance path per ADR-0015.

**How to test:**
1. Ask the deployer to show which MIProxy backend is wired in production.
2. Ask the deployer to demonstrate `enforce_attestation()` on the production verifier; observe the no-raise result.
3. Ask the deployer to demonstrate the failure: swap the verifier source in a non-production environment; re-run; observe `IntegrityVerificationError`.

---

## Part 2 — Using ModelInventory for SR 11-7 second-line validation

**Control objective.** The institution maintains an effective inventory of models in production, with documented validation status, validation date, and overdue-for-revalidation tracking.

**Evidence the framework produces:**
- `ModelInventory.register(model)` writes a model to the inventory.
- `ModelInventory.transition_status(model_id, new_status)` records each state transition through `PRE_VALIDATION` → `IN_VALIDATION` → `APPROVED_FOR_PRODUCTION` → `RETIRED`.
- The `IN_VALIDATION → APPROVED_FOR_PRODUCTION` transition is the SR 11-7 § V.4 validation-completion checkpoint; the framework emits a `MODEL_VALIDATED` chain entry.
- `ModelInventory.query_overdue(as_of=...)` returns models past their scheduled revalidation window.
- `ModelInventory.query_by_status(status)` supports examination-prep reports.

**How to test (SR 11-7 walkthrough):**
1. Ask the deployer for the full output of `ModelInventory.query_by_status(ImplementationStatus.APPROVED_FOR_PRODUCTION)`. Spot-check three models against the institution's model-risk inventory of record.
2. For each spot-checked model: ask the deployer to produce the validation memo, the second-line sign-off, and the operational performance monitoring report.
3. Ask the deployer for `ModelInventory.query_overdue()`. For any model past its window: ask for the remediation memo and the model-risk-committee notification.
4. Pull the `MODEL_VALIDATED` chain entries; tie each to the corresponding second-line validation memo.

---

## Part 3 — Using VendorScoreGate for vendor-risk management

**Control objective.** The institution detects silent changes in third-party model outputs and routes them through a vendor-review process.

**Evidence the framework produces:**
- `InMemoryVendorScoreGate.record_score(vendor_id, input_hash, model_version, score, ...)` writes a `VENDOR_SCORE_RECORDED` chain entry per call.
- On the second call with the same `(vendor_id, input_hash, model_version)` but a different `score`, the gate emits a `VENDOR_SCORE_DRIFT_DETECTED` chain entry and raises `VendorScoreDriftDetected`.
- The deployer wires the resulting alert into their vendor-review queue (ServiceNow, Jira, internal ticketing).
- Five FSI `VendorClass` values are pre-registered (credit scoring, fraud scoring, KYC/AML scoring, AI/ML decisioning, generative-AI scoring).

**How to test (third-party risk walkthrough):**
1. Ask the deployer to show all `VENDOR_SCORE_DRIFT_DETECTED` chain entries for the last quarter.
2. For each: ask for the corresponding vendor-review ticket, the disposition decision, and (if the vendor's model change was accepted) the re-validation memo.
3. Ask the deployer to demonstrate the gate end-to-end on a vendor in scope; observe the chain entries and the raised exception.

---

## Part 4 — Sample audit-evidence excerpts (sanitized JSONL)

The shapes below are illustrative. Field names match `AuditEvent` in `finserv_agent_audit.schemas.audit_event`.

**Example A — chain head with intact prior-hash chain (three entries):**

```jsonl
{"sequence": 1247, "timestamp": "2026-05-28T14:03:22.117Z", "event_type": "ADVERSE_ACTION_TAKEN", "actor": "agent-credit-decisioning-v3", "payload": {"decision_id": "dec_01HX...", "reason_codes": ["INCOME_DTI_HIGH", "DELINQ_30_LAST_24M"], "model_id": "credit-scoring-v7.2"}, "prev_hash": "9c4f...a812", "event_hash": "1d2e...b9f7"}
{"sequence": 1248, "timestamp": "2026-05-28T14:03:22.184Z", "event_type": "BEST_INTEREST_CHECKED", "actor": "agent-recommendation-v2", "payload": {"recommendation_id": "rec_01HX...", "investor_profile_hash": "f80a...", "result": "PASS"}, "prev_hash": "1d2e...b9f7", "event_hash": "7a01...3c44"}
{"sequence": 1249, "timestamp": "2026-05-28T14:03:22.219Z", "event_type": "WITNESS_ANCHOR", "actor": "anchor-cron", "payload": {"witness": "rekor.sigstore.dev", "chain_head_anchored": "7a01...3c44", "receipt_uuid": "01HX9..."}, "prev_hash": "7a01...3c44", "event_hash": "ee31...5b08"}
```

**Example B — VENDOR_SCORE_DRIFT_DETECTED entry:**

```jsonl
{"sequence": 1532, "timestamp": "2026-05-28T16:11:09.402Z", "event_type": "VENDOR_SCORE_DRIFT_DETECTED", "actor": "vendor-score-gate", "payload": {"vendor_id": "vendor-credit-bureau-A", "vendor_class": "CREDIT_SCORING", "input_hash": "3f...", "model_version": "bureau-A-v2024.07", "prior_score": 0.742, "current_score": 0.681, "delta": -0.061, "prior_recorded_at": "2026-05-21T09:14:00.000Z"}, "prev_hash": "...", "event_hash": "..."}
```

**Example C — MODEL_VALIDATED transition entry:**

```jsonl
{"sequence": 1611, "timestamp": "2026-05-28T17:42:00.000Z", "event_type": "MODEL_VALIDATED", "actor": "second-line-mrm-team", "payload": {"model_id": "credit-scoring-v7.2", "prior_status": "IN_VALIDATION", "new_status": "APPROVED_FOR_PRODUCTION", "validation_date": "2026-05-28", "validation_memo_ref": "MRM-2026-Q2-007", "next_revalidation_due": "2027-05-28"}, "prev_hash": "...", "event_hash": "..."}
```

**Example D — SAR_FILED workflow entry:**

```jsonl
{"sequence": 1702, "timestamp": "2026-05-28T18:30:11.000Z", "event_type": "SAR_FILED", "actor": "bsa-officer-jdoe", "payload": {"alert_id": "alert_01HX...", "filing_id": "BSA-EFiling-receipt-...", "rationale": "Structuring pattern across 14 days, 9 transactions just below $10K threshold; supporting evidence in case file CASE-2026-...", "filing_deadline_met": true}, "prev_hash": "...", "event_hash": "..."}
```

---

## Part 5 — Audit-trail evidence diagram

```
[Agent decision]
       │
       ▼
[FSI gate emits AuditEvent]
       │
       ▼
[AuditConsumer routes to AuditChain.append()]
       │
       ├──► [TimestampSource.now() — LocalClock or RFC3161Source]
       │
       ├──► [Compute event_hash = SHA-256(payload || prev_hash)]
       │
       ├──► [LedgerStore.append(event) — JSONL / SQLite / WORM]
       │
       └──► (async cron) ──► [anchor_to_witness() ──► Rekor / OpenTimestamps]
                                       │
                                       └──► [WITNESS_ANCHOR entry written back]

[Operator-triggered verify or scheduled cron]
       │
       ▼
[AuditChain.verify_strict(mi_proxy=...)]
       │
       ├──► [MIProxy.verify_integrity() — attest the verifier itself]
       │
       ├──► [Re-hash chain; check prior-hash links]
       │
       └──► [Check sequence monotonicity]
                │
                ├──► PASS → return True
                └──► FAIL → raise AuditChainTamperError / IntegrityVerificationError
```

---

## Part 6 — Auditor interview script (10 questions)

The questions below are calibrated for a Big-4 IT auditor or an OCC examination team conducting a walkthrough of an FSI deployment of this framework. Each question targets a control objective and an expected evidence shape.

1. **Which `LedgerStore` backend is in production, and what is the storage-substrate posture (S3 Object Lock mode, DynamoDB conditional-write configuration, Postgres replication topology)?**
   *Expected:* Named backend; substrate-level immutability enforcement.

2. **Which `TimestampSource` is wired? If `RFC3161Source`, which TSA, and what is the fallback-on-failure policy?**
   *Expected:* Named TSA; explicit `fallback_to_local_on_failure` setting and rationale.

3. **Is witness anchoring enabled? If yes, which `WitnessRegister` backend(s), at what cadence?**
   *Expected:* Named backend(s); cron schedule; alerting on anchor failure.

4. **Which `MIProxy` backend is in production, and where does the signing key live?**
   *Expected:* Named backend; HSM / KMS reference; key-rotation policy.

5. **Show me the most recent successful `AuditChain.verify_strict()` run and the alerting that would fire on failure.**
   *Expected:* Timestamped log; named alerting destination; on-call escalation path.

6. **For the `ModelInventory`: what is the count by status, and what is the overdue list as of today?**
   *Expected:* Live query results; remediation plan for any overdue entries.

7. **For the `VendorScoreGate`: how many `VENDOR_SCORE_DRIFT_DETECTED` entries have been written in the last 90 days, and what was the disposition of each?**
   *Expected:* Count; per-entry vendor-review ticket reference.

8. **For the `AdverseActionGate`: spot-check one `ADVERSE_ACTION_TAKEN` entry; produce the corresponding consumer notice and the reason-code rationale.**
   *Expected:* Notice on file; reason codes are specific and traceable (FCRA § 615, CFPB Circular 2022-03).

9. **For the `SARWorkflowAudit`: how many `SAR_FILED` entries are in the chain, and were all 30-day (or 60-day extension) deadlines met?**
   *Expected:* Count; deadline-compliance metric; extension rationale where applicable.

10. **Which `ProtectedClassProxyDetector` arms are in use? What compensating controls cover the arms not yet shipped?**
    *Expected:* Acknowledgement that v1.2 ships the mutual-information arm per ADR-0019 § "v1.2 ship reconciliation"; named compensating control (third-party SHAP audit, qualified fair-lending analytics resource, conditional-demographic-disparity review) for the SHAP / CDD arms that land in v1.3.

---

## Related

- [`FAILURE-MODES.md`](FAILURE-MODES.md) — adversarial matrix
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — system diagram
- [`DEPLOY-CHECKLIST.md`](DEPLOY-CHECKLIST.md) — go-live walkthrough
- [`docs/sox_404_itgc_mapping.md`](docs/sox_404_itgc_mapping.md)
- [`docs/sr11_7_mapping.md`](docs/sr11_7_mapping.md)
- [`docs/sec_17a_4_mapping.md`](docs/sec_17a_4_mapping.md)
- [`docs/coso_icair_mapping.md`](docs/coso_icair_mapping.md)
- [`docs/ecoa_reg_b_mapping.md`](docs/ecoa_reg_b_mapping.md)
- [`docs/fcra_reg_v_mapping.md`](docs/fcra_reg_v_mapping.md)
- [`docs/bsa_aml_mapping.md`](docs/bsa_aml_mapping.md)
- [`docs/sec_reg_bi_mapping.md`](docs/sec_reg_bi_mapping.md)
