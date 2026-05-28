# ADR-0024 · Retraining Cadence Monitor — Bridge Framework for Generative + Agentic AI

**Status:** Accepted — Design + Reference Implementation (v1.3)
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit v1.3

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel. No attorney-client relationship is formed by use of this ADR. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

---

## Context

SR 11-7 (April 4, 2011) was written for a world of quarterly-recalibrated credit, market, and operational-risk models with named owners and a stable specification. The validation cadence it implies is **annual** with an inventory entry per material change. OCC Bulletin 2026-13 — the April 17, 2026 joint OCC / FRB / FDIC issuance that superseded OCC Bulletin 2011-12 — preserves the annual cadence as the floor but **explicitly excludes generative + agentic AI from scope**, deferring those workloads to a forthcoming joint RFI.

That scope exclusion is the problem. The bank cannot stop validating its foundation-model surface for a year while the RFI runs. The Databricks MRM 2026 commentary named the issue: "Models that drift weekly will need conditional approvals; lineage-based controls must shift to vendor-transparency reviews." The Cyber Risk Institute's FS AI RMF (February 2026, 108 contributing institutions) carries the same message in the regulatory voice: continuous-monitoring controls become first-class obligations alongside (not in place of) pre-deployment validation.

The bank's MRM team needs a classification scheme that distinguishes the cadence regimes that real foundation-model surfaces sit in — vendor-pinned static deployments, monthly-retrained in-house adapters, weekly-retrained vendor models, and continuous fine-tune pipelines — and emits the required validation cadence per class. This monitor is the bridge framework that closes the OCC 2026-13 scope-exclusion gap.

## Decision

Define a `RetrainingCadenceMonitor` that classifies each inventoried model into one of four `RetrainingClass` regimes and computes a per-class required validation cadence. Each registration and each recorded validation emits a `COMPLIANCE_CHECK` audit-chain event so the third line can replay the cadence-validation evidence trail.

### Class-to-cadence table (the load-bearing contract)

| `RetrainingClass`         | Vendor / build profile                                                  | Required validation cadence                                          |
|---------------------------|-------------------------------------------------------------------------|----------------------------------------------------------------------|
| `STATIC`                  | Vendor-pinned foundation model; no in-house fine-tuning                 | Annual (365 days)                                                    |
| `MONTHLY_RETRAIN`         | In-house or vendor model retrained monthly on a stable feature set      | Quarterly minimum (90 days)                                          |
| `WEEKLY_RETRAIN`          | Vendor or in-house model retrained weekly; feature drift first-class    | Monthly (30 days) plus continuous monitoring                         |
| `CONTINUOUS_FINE_TUNE`    | RLHF / RLAIF / continuous adapter pipelines                             | Continuous monitoring; pre-deployment validation per material change (7-day freshness floor) |

The cadences are the floor the framework enforces. Deployers can shorten — the monitor will treat anything tighter than the floor as still-compliant — but cannot lengthen without an ADR that explicitly supersedes this one.

### Module surface

```python
from finserv_agent_audit.governance.retraining_cadence_monitor import (
    RetrainingCadenceMonitor,
    RetrainingClass,
)

monitor = RetrainingCadenceMonitor(ledger_store=worm_store)
monitor.register_model(
    model_id="anthropic_claude_sonnet_4_7_static",
    retraining_class=RetrainingClass.STATIC,
    last_trained=datetime(2026, 1, 1, tzinfo=UTC),
    owner="mrm@bank.example",
)
monitor.record_validation(
    "anthropic_claude_sonnet_4_7_static",
    validated_at=datetime(2026, 5, 1, tzinfo=UTC),
    actor_id="mrm@bank.example",
)
report = monitor.evaluate("anthropic_claude_sonnet_4_7_static")
overdue = monitor.query_overdue()
```

## Alternatives Considered

1. **Use `ModelInventory` (ADR-0007) alone.** Rejected — `ModelInventory` tracks lifecycle status (proposed / in-validation / approved-for-X / retired); it does not classify retraining cadence and does not emit overdue-by-cadence-class queries. The two primitives are complementary, not redundant.
2. **Wait for OCC 2026-13's joint RFI to ship binding guidance.** Rejected — the RFI is expected to close in 2027; the bank's exposure is live today. The bridge framework is the operating posture.
3. **Defer to vendor-supplied cadence (whatever Anthropic / OpenAI publishes).** Rejected — vendor-side cadence is a marketing fact, not a control fact. The bank's MRM owes the regulator a cadence the bank defends.
4. **Three classes (drop `MONTHLY_RETRAIN`).** Rejected — the monthly cadence is real for in-house adapter pipelines and for vendor models with monthly safety-eval refresh cycles; collapsing it into `WEEKLY_RETRAIN` over-tightens validation cost and into `STATIC` under-tightens it.

## Consequences

**Positive.** The bank's MRM function has a single primitive that produces a defensible answer to "which inventoried models are overdue for validation under their declared retraining-class cadence?" The audit-chain emission gives the third line the replayable evidence trail the FFIEC examination expects. Pairs cleanly with `VendorAttestationLedger` (ADR-0023) — vendor attestations are the artifacts the second line reviews on each cadence boundary — and with `DeprecationWatch` (ADR-0025) — a sunset notice forces a class re-evaluation.

**Negative.** Misclassification at registration produces silently-wrong cadence reports. The mitigation is procedural: the registration step emits a chain entry that records the declared class, so a misclassification is replayable and recoverable. The cost of misclassification is bounded by how long the third line takes to spot it.

**Architectural.** The monitor is a runtime helper, not a workflow engine. Deployers wire `query_overdue` to their alerting substrate (PagerDuty, ServiceNow, Splunk) and route the alerts to the named owner the registration recorded.

## Regulatory Mapping

- **SR 11-7** (Federal Reserve, April 4, 2011) § IV (Model Validation) — independent validation cadence floor.
- **OCC Bulletin 2026-13** (April 17, 2026) — model risk revised guidance; generative + agentic AI scope-excluded. This monitor is the bridge framework.
- **FFIEC IT Examination Handbook** § "Model Risk" — examination expectations for ongoing-monitoring evidence.
- **Treasury FS AI RMF** (February 2026) — continuous-monitoring control objectives.
- **Databricks MRM 2026 commentary** — vendor-transparency-review cadence shift; the conceptual frame this ADR encodes.
- **OCC Heightened Standards** — 12 CFR Part 30 Appendix D — three-lines-of-defense framework; the cadence-validation evidence trail this monitor produces is the second-line + third-line surface.

## Pre-mortem

What fails:

1. **The OCC 2026 RFI ships replacement guidance that contradicts the class-to-cadence table.** Mitigation: this ADR is reversible — a superseding ADR can update the table without breaking the audit-chain entries already written. The chain entries record the cadence-in-force at the time of validation; historical posture stays defensible.
2. **Deployer registers a `CONTINUOUS_FINE_TUNE` model and never records a validation.** Mitigation: the monitor surfaces the model as non-compliant immediately when evaluated; `query_overdue` returns it. The first cadence window is the operator's grace period for the initial validation — that is policy, not a free pass.
3. **Vendor changes the model's retraining cadence without notice.** Mitigation: pairs with `DeprecationWatch` (ADR-0025) — a vendor-side cadence shift is a vendor-side change-of-material-fact event; the bank's procurement clause (foundation-model API, Clause 2) makes the disclosure a contract obligation.
4. **Different bank functions disagree on the retraining class.** Mitigation: the registration writes the declared class to the audit chain with the owner's identifier. Reconciliation is a governance escalation, not a missing-data problem.

## Reversibility

High. Removing the monitor reverts the bank to whatever ad-hoc cadence-tracking mechanism was in place. The chain entries already written stand on their own as evidence. The class-to-cadence table can be revised under a superseding ADR without invalidating prior entries.

## Cross-references

- **Implementation:** `src/finserv_agent_audit/governance/retraining_cadence_monitor.py`
- **Tests:** `tests/test_retraining_cadence_monitor.py`
- **Related ADRs:** ADR-0007 (SR 11-7 overlay — the three-lines-of-defense framing) · ADR-0014 (Persistence + timestamp + witness seams — the chain substrate) · ADR-0023 (Vendor Attestation Ledger — the second-line companion artifact) · ADR-0025 (Deprecation Watch — the lifecycle companion)
