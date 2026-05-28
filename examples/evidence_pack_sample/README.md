# Sample Audit-Evidence Pack

**Status:** v1.2.0-draft · Last reviewed: 2026-05-28.
**Audience:** Big-4 audit teams, internal audit trainees, FSI second-line / third-line reviewers, regulatory examination prep teams.

> **Patterns are software, not legal advice.** Every payload in this pack is synthetic — invented for training. No customer data, no real model output, no real vendor name is present. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

---

## What this pack is

A sanitized, end-to-end sample of the evidence artifacts a Big-4 audit team or an FSI internal-audit trainee will inspect when walking through a `finserv-agent-audit` v1.x deployment. The pack ships under `examples/` because it is reference material — production evidence lives in the deployer's audit-chain backend, not in this repository.

The pack covers two days of synthetic agent operation across a fictitious mid-size US bank ("North River Bank, N.A.") and is calibrated to show the full surface area an examiner can probe:

- A multi-day audit chain with intact prior-hash links across all major event types (`DECISION_MADE`, `DECISION_VETOED`, `VENDOR_SCORE_RECORDED`, `VENDOR_SCORE_DRIFT_DETECTED`, `MODEL_VALIDATED`, `ADVERSE_ACTION_TAKEN`, `SAR_FILED`, `BEST_INTEREST_CHECKED`, `WITNESS_ANCHOR`).
- A `ModelInventory` CSV export with 7 registered models across varied `ImplementationStatus` values.
- A `VendorScoreGate` log with 60 vendor-score records spanning all 5 `VendorClass` values plus 2 flagged drift events.
- A snapshot copy of the `FAILURE-MODES.md` matrix for the auditor's reference.
- A sample `MIProxy` attestation receipt for the verifier chain.
- A narrative walkthrough an audit-firm trainee can follow to inspect each artifact.

## Intended use

The pack is **training material**. Use it to:

1. Train new IT audit staff on what a finserv-agent-audit chain looks like before they sit across from a client.
2. Demonstrate the audit-evidence surface during a sales conversation with a prospective Big-4 engagement client.
3. Stand up an internal-audit walk-through exercise: hand the trainee `walkthrough.md` and the pack; they should reach the conclusions documented in the walkthrough.
4. Sanity-check that the verify-side tooling can read a chain produced by an unrelated environment (chain portability).

The pack is **not** a substitute for:

- The client's own production audit chain (this is synthetic data).
- The framework's own test suite (the pack is a single happy path, not a test matrix).
- A live demonstration during fieldwork (the auditor should still re-run `AuditChain.verify_strict()` against the client's production chain in the client's presence).

## Contents

| File | Purpose | Approximate size |
|---|---|---|
| [`README.md`](README.md) | This file | ~1.5 KB |
| [`sample_audit_chain.jsonl`](sample_audit_chain.jsonl) | 24-entry chain, intact prior-hash links | ~10 KB |
| [`model_inventory_export.csv`](model_inventory_export.csv) | 7 models, mixed status | ~2 KB |
| [`vendor_scores_log.csv`](vendor_scores_log.csv) | 60-row vendor-score log + 2 drift entries | ~7 KB |
| [`failure_modes_matrix_snapshot.md`](failure_modes_matrix_snapshot.md) | Snapshot copy of `FAILURE-MODES.md` matrix | ~5 KB |
| [`audit_consumer_attestation.md`](audit_consumer_attestation.md) | Sample MIProxy attestation receipt | ~3 KB |
| [`walkthrough.md`](walkthrough.md) | Narrative training walkthrough | ~8 KB |

## How the chain was produced

Every entry in `sample_audit_chain.jsonl` is hand-constructed so that:

- `event_hash` of entry *n* is the literal `prev_hash` of entry *n+1*.
- All hash values are placeholder SHA-256-shaped hex strings (synthetic) — the chain demonstrates the **shape** of a real chain, not a verifiable one. To produce a verifiable training chain, replay the events through `AuditChain.append()` in a sandbox; the helper at `examples/integration/` provides the wiring.
- All timestamps are within May 27-28, 2026.
- All `event_type` values exist in `finserv_agent_audit.schemas.audit_event.AuditEventType`.
- All `agent_id` values are namespaced under `bank.northriver.*` for clarity.

## How to refresh

When the framework adds a new `AuditEventType`, the pack should grow a representative entry. The owner is the framework maintainer; the trigger is the v-release cadence.

## Related

- [`ASSURANCE-GUIDE.md`](../../ASSURANCE-GUIDE.md) — full walk-through guide
- [`FAILURE-MODES.md`](../../FAILURE-MODES.md) — adversarial reference
- [`docs/big4_engagement_letter_exhibit.md`](../../docs/big4_engagement_letter_exhibit.md) — SOW exhibit
- [`docs/pre_examination_ai_self_assessment.md`](../../docs/pre_examination_ai_self_assessment.md) — client-side self-assessment
