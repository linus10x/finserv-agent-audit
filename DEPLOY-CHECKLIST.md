# DEPLOY-CHECKLIST.md — AWS / Azure go-live walkthrough

**Status:** v1.1.0 · Last reviewed: 2026-05-28.

This document is the FSI CTO's checklist for taking `finserv-agent-audit` from a development demo to a production deployment in a regulated environment. It is calibrated for an AWS or Azure substrate; on-premises and other clouds use the same shape with substrate-specific substitutions.

> Companion to [`ARCHITECTURE.md`](ARCHITECTURE.md), [`ASSURANCE-GUIDE.md`](ASSURANCE-GUIDE.md), [`FAILURE-MODES.md`](FAILURE-MODES.md).

The checklist is ordered from T-7 days (one week before go-live) to T+7 days (one week after). Each day's items can be parallelized within the day; the across-day ordering matters.

---

## Day -7 — Substrate selection

### Pick a `LedgerStore` backend

The four shipped backends correspond to four deployment postures:

- **`InMemoryLedgerStore`** — development and test only. Not for any non-test deployment.
- **`JsonlLedgerStore`** — staging and small-scale production. Append-only file; deployer's storage substrate (S3 versioning, EBS snapshot) provides durability.
- **`SqliteLedgerStore`** — moderate-scale production where a relational query surface helps. Pair with regular SQLite-to-S3 archival.
- **`WORMLedgerStore`** — production where SEC 17a-4(f) WORM applies. **Pair with S3 Object Lock in COMPLIANCE mode** (not GOVERNANCE mode); see ADR-0013. The Python WORM enforcement is best-effort within OS controls — the substrate enforcement is what satisfies the rule.

For deployments at large scale, write a substrate-native backend that implements the `LedgerStore` Protocol — for example, a DynamoDB-backed store with conditional-write semantics on `(partition_key, sequence)` per ADR-0014 § Seam 1. The Protocol is the contract.

### Pick a `TimestampSource`

- **`LocalClock`** — development only. Production deployments under any timestamp-integrity-mapped regime (SOX 404 ITGC, SEC 17a-4) should not use `LocalClock`.
- **`RFC3161Source`** — production. Configure against your TSA (FreeTSA for public-good usage; Sectigo, DigiCert, GlobalSign for commercial; an internal TSA for fully-private posture). Set `fallback_to_local_on_failure` deliberately: True is the documented degradation; False is fail-closed.

### Pick a `WitnessRegister`

- **None** — development.
- **`RekorWitness`** against `rekor.sigstore.dev` — staging; appropriate for public-good usage where the chain head is non-sensitive.
- **`RekorWitness`** against a private Rekor instance — production where examination posture demands a deployer-controlled transparency log.
- **`OpenTimestampsWitness`** — supplemental or primary, depending on the deployer's Bitcoin-anchor posture preference.

### Pick an `MIProxy`

- **`LocalMIProxy`** — default. HMAC-SHA256 over the verifier source + canonical config; key supplied by the deployer.
- **Substrate-pluggable** — SLSA provenance, in-toto attestations, or a custom backend implementing the `MIProxy` Protocol. Higher-assurance posture for deployments where the verifier itself is part of the regulated surface (SOX 404 ITGC § privileged software).

Store the MIProxy signing key in **KMS (AWS) or Key Vault (Azure)**. The `LocalMIProxy.from_env()` constructor reads the key from environment; the deployment substrate's secrets-management integration is how the env gets populated.

---

## Day -1 — Policy and wiring

### WORM retention policy

The default retention window is **seven years** (SEC 17a-4(b)(4) for broker-dealer records; SOX 404 retention is also seven years; BSA / FCRA / ECOA windows are shorter but the framework defaults to the longest applicable window). Configure the deployer's substrate-level retention policy:

- AWS S3: Object Lock COMPLIANCE mode with seven-year retention period at the bucket level.
- Azure Blob: Immutable storage with time-based retention policy, seven years.
- On-prem: WORM storage appliance with the equivalent configuration.

Deployers with different retention obligations (a state-specific record-retention statute, an ongoing legal hold, an internal records-management policy) override the default in their substrate configuration.

### `VendorScoreGate` vendor classes wired

For each vendor whose model output enters an agent decision flow, register the vendor with the appropriate `VendorClass`:

- `CREDIT_SCORING` — credit bureau, credit-decisioning vendor
- `FRAUD_SCORING` — fraud detection / device intelligence vendor
- `KYC_AML_SCORING` — identity verification / sanctions screening vendor
- `AI_ML_DECISIONING` — generic third-party ML scoring
- `GENERATIVE_AI_SCORING` — LLM-based scoring or routing vendor

The `(vendor_id, vendor_class, input_hash, model_version, score)` tuple is the drift-detection key. The deployer's vendor-management process owns updating `model_version` when the vendor publishes a documented version bump; an undocumented score change with the same `model_version` is the drift signal the gate exists to catch.

### Wire the alerting

The framework raises exceptions; the deployer routes them to the operational substrate. At minimum:

- `AuditChainTamperError` and `IntegrityVerificationError` → PagerDuty / Opsgenie at the highest severity.
- `VendorScoreDriftDetected` → vendor-review queue (ServiceNow / Jira).
- `AdverseActionViolation`, `BestInterestViolation`, `EquityAuditViolation` → compliance officer queue.
- `WORMViolationError` → security operations queue at high severity (a WORM violation in production is presumptively a control failure).

---

## Day 0 — Smoke test

Run the full path end-to-end against the production substrate with a non-customer-facing synthetic transaction:

1. Construct the agent with the four production seams wired (`LedgerStore`, `TimestampSource`, `WitnessRegister`, `MIProxy`) and the `VendorScoreGate`.
2. Issue the synthetic agent call. Confirm:
   - An `AuditEvent` is appended to the production ledger.
   - The timestamp is signed by the production TSA (if `RFC3161Source`).
   - The chain head is anchored to the production witness (if configured).
   - `AuditChain.verify_strict(mi_proxy=production_proxy)` returns `True`.
3. Confirm the synthetic transaction does not appear in any customer-facing report.

If any step fails, do not proceed to live traffic.

---

## Day +1 — First verification cron

Schedule the first hourly verification cron:

```
0 * * * * /opt/finserv-agent-audit/scripts/verify_chain.sh
```

The script wraps `AuditChain.verify_strict(mi_proxy=...)`, captures the result, and pushes the success/failure metric to the deployer's observability platform (Datadog, CloudWatch, Azure Monitor, internal Prometheus). The alerting wired on Day -1 fires on failure.

For higher-stakes deployments, run the verification on every audit-chain append in addition to the hourly cron. The append-side cost is bounded (the verifier re-hashes only the new entries against the chain head). The choice between hourly cron and per-append verification is a deployer's substrate-cost-vs-detection-latency tradeoff.

---

## Day +7 — First witness-anchoring cadence

Schedule the first daily witness-anchoring cron:

```
0 2 * * * /opt/finserv-agent-audit/scripts/anchor_to_witness.sh
```

The script calls `anchor_to_witness(audit_chain, witness)` once per day. The choice of daily cadence is the documented default in ADR-0014; deployers under examination postures that demand sub-daily anchoring increase the cadence (hourly, per-N-entries). Each anchoring writes a `WITNESS_ANCHOR` entry back into the chain; the chain becomes self-documenting about its anchoring cadence.

---

## Ongoing — Operational rhythms

| Cadence | Activity |
|---|---|
| Per audit-chain append (or hourly) | `verify_strict()` with MIProxy attestation |
| Daily (or higher) | `anchor_to_witness()` to Rekor / OpenTimestamps |
| Weekly | Review `ModelInventory.query_overdue()` |
| Monthly | Review all `VENDOR_SCORE_DRIFT_DETECTED` entries against vendor-review queue dispositions |
| Quarterly | MIProxy signing-key rotation (per institutional KMS policy) |
| Annually | Re-evaluate substrate selection against compliance posture changes; refresh deployer-side mapping of `docs/` to the institution's current regulatory inventory |

## Pre-go-live sign-offs

Before flipping live customer traffic to the framework-instrumented path, capture explicit sign-offs from:

- **Information security** — on the substrate selection (LedgerStore backend, KMS key handling, alerting destinations).
- **Model risk management (second line)** — on `ModelInventory` integration with the institution's MRM inventory of record.
- **Compliance** — on the `AdverseActionGate` / `BestInterestCheck` / `EquityAudit` / `SARWorkflowAudit` wiring into the institution's compliance workflows.
- **Internal audit (third line)** — on the verification cron, alerting, and incident-response procedure.
- **Legal** — on the disclaimers, regulatory mapping interpretations, and `OWNERSHIP.md` posture.

The framework does not produce these sign-offs; the deployer's governance process does.

## Related

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`ASSURANCE-GUIDE.md`](ASSURANCE-GUIDE.md)
- [`FAILURE-MODES.md`](FAILURE-MODES.md)
- [`LIMITATIONS.md`](LIMITATIONS.md)
- ADR-0013 (SEC 17a-4 WORM), ADR-0014 (Protocol seams), ADR-0015 (MIProxy), ADR-0016 (VendorScoreGate), ADR-0017 (retention)
