# ADR-0023 · Vendor Attestation Ledger for Foundation-Model + AI-Vendor Surface

**Status:** Accepted — Design + Reference Implementation (v1.3)
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit v1.3

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel and the firm's TPRM function. No attorney-client relationship is formed by use of this ADR. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

---

## Context

The 2026 vendor-surface posture for a US-regulated financial institution consuming foundation-model APIs (Anthropic, OpenAI, Google, Mistral, Cohere, AWS Bedrock, Azure OpenAI) is dominated by trust-portal pages and "audit reports on request" promises. Anthropic publishes its SOC 2 Type II under NDA on its trust portal; OpenAI provides "audit reports on request" gated by procurement engagement; smaller foundation-model providers ship either a single-page summary or nothing at all. None of those mechanisms produce **chain-of-custody evidence** that an OCC examiner can replay sixty seconds after the question is asked.

The bank's TPRM team also faces the **fourth-party** problem the DORA RTS on subcontracting (Commission Delegated Regulation 2024/1773) made explicit: when Anthropic uses AWS Bedrock as a deployment surface, the bank's attestation chain must reach Bedrock, not stop at Anthropic. The Treasury FS AI RMF (February 2026) and the Cyber Risk Institute's FS AI RMF (February 2026, 108 contributing institutions) both devote substantial control objectives to third-party + fourth-party AI oversight; the bank's primary deliverable to satisfy those objectives is an attestation ledger the second and third lines can read.

SR 11-7 and OCC Bulletin 2026-13 carry the model-validation pass-through requirement forward — the operator's first line carries the regulatory exposure even when the model is rented. Without an attestation ledger, the bank's evidence that it acted on each vendor's most recent SOC 2 / ISO 27001 / ISO 42001 / FedRAMP / PCI / HITRUST / SR 11-7 validation token is a sticky note in someone's Notion workspace.

This ADR closes the gap by shipping the ledger as a first-class primitive of the audit-chain framework.

## Decision

Define a `VendorAttestationLedger` that records every vendor attestation as a hashed entry, emits a `COMPLIANCE_CHECK` audit-chain event on each record, and supports point-in-time, expiry-window, and missing-requirement queries. The ledger is the chain-of-custody record the third-line auditor reads.

### Module surface

```python
from finserv_agent_audit.governance.vendor_attestation_ledger import (
    VendorAttestationLedger,
    VendorAttestation,
    AttestationGap,
)

ledger = VendorAttestationLedger(ledger_store=worm_store)
ledger.record_attestation(
    vendor_id="anthropic",
    attestation_type="SOC2_TYPE_II",
    attesting_entity="anthropic_pbc",
    version="2025-Q4",
    attestation_hash=sha256_of_pdf,
    valid_from=datetime(2025, 10, 1, tzinfo=UTC),
    valid_until=datetime(2026, 9, 30, tzinfo=UTC),
    evidence_url="https://trust.anthropic.com/soc2",
)
gaps = ledger.query_missing([
    ("anthropic", "SOC2_TYPE_II"),
    ("anthropic", "ISO_42001"),
    ("openai", "SOC2_TYPE_II"),
])
expiring = ledger.query_expired(grace_period_days=30)
```

Supported `AttestationType` values: `SOC2_TYPE_I`, `SOC2_TYPE_II`, `ISO_27001`, `ISO_42001`, `FedRAMP_Moderate`, `FedRAMP_High`, `PCI_DSS`, `HITRUST`, `SR_11_7_validation`, `SR_11_7_validation_independent_review`. Adding a value is additive; removing one is a breaking change because chain entries reference the value in their payload.

### Pairs with vendor clauses

The ledger only works when the vendor delivers the receipt the operator records. The contractual companion is the foundation-model API vendor-clauses document (`vendor-clauses/foundation_model_api_vendor_clauses.md`, v1.3) — Clause 5 covers the cadence and content of the receipts the bank can record.

## Alternatives Considered

1. **Spreadsheet plus SharePoint folder.** Rejected — not hash-chained, not replayable, not regulator-grade. The TPRM team that lives in spreadsheets is the team that misses a SOC 2 renewal and gets an MRA finding for it.
2. **Stand up a third-party GRC tool (OneTrust, Drata, Vanta).** Rejected as the primary record. Those tools have a place in the operator's stack but they are not the audit-chain-of-custody record the framework owes the bank; the ledger is the framework-native artifact every other ADR can hash-reference.
3. **Embed the attestation fields inside `ModelInventory` (ADR-0007).** Rejected — model-inventory entries track in-house and inventoried-vendor models. Foundation-model API surfaces span dozens of model versions per vendor with shared underlying controls; coupling the attestation lifecycle to per-model entries inflates the inventory and obscures the vendor-level control posture.
4. **Wait for the OCC 2026 RFI to ship guidance.** Rejected — the RFI's expected close is 2027; the bank's exposure is in production today. The ledger is the bridge framework.

## Consequences

**Positive.** The bank's TPRM team has a single-call answer to "show me every attestation we hold for `anthropic`" and "show me every (vendor, attestation_type) pair that is expired or expiring within 30 days." The audit chain entries hash-reference the underlying attestation document so the third line can verify the document on file matches the version the second line recorded. Pairs cleanly with `RetrainingCadenceMonitor` (ADR-0024) — an attestation is one of the cadence-tracked artifacts that ages out.

**Negative.** The ledger is only as good as the receipts that go into it. A vendor that refuses to share a SOC 2 Type II report is a vendor with a hole in the bank's attestation set; the ledger surfaces the hole but does not fill it. The remediation is contractual (foundation-model API vendor clauses, Clause 4) plus procurement-side negotiating posture during renewal.

**Architectural.** The ledger is a thin shim over `LedgerStore` — every persistence backend that satisfies the `LedgerStore` Protocol (in-memory, JSONL, SQLite, WORM) works without modification. Production deployments should pair this primitive with `WORMLedgerStore` for SEC 17a-4 broker-dealer alignment.

## Regulatory Mapping

- **SR 11-7** (Federal Reserve, April 4, 2011) § VII (Third-party models) — pass-through validation requirement; the ledger records the second-line evidence that vendor-side validation occurred and was on file.
- **OCC Bulletin 2026-13** (April 17, 2026) — model risk revised guidance; generative + agentic AI scope-excluded pending joint RFI. The ledger is part of the bridge framework that lets the bank evidence vendor controls in the gap window.
- **DORA Article 28** (Regulation (EU) 2022/2554) — ICT third-party risk management; written-agreement + audit-access requirements.
- **DORA RTS on subcontracting** (Commission Delegated Regulation 2024/1773) — fourth-party disclosure cadence.
- **Treasury FS AI RMF** (February 2026) — third-party + fourth-party AI oversight control objectives.
- **Cyber Risk Institute FS AI RMF** (February 2026, 108 contributing institutions) — vendor-attestation control objectives.
- **OCC Bulletin 2013-29** — original third-party risk-management framework; superseded for AI workloads by the 2026 interagency RFI process.
- **NIST AI 600-1** § "Value Chain and Component Integration" — generative-AI third-party component control objective.

## Pre-mortem

What fails:

1. **Vendor furnishes an attestation but withholds the underlying audit report.** Mitigation: the ledger records `attestation_hash` plus `evidence_url`; if the operator never received the underlying document, the hash is of a placeholder and the third-line audit catches it on first review. The contractual remedy is foundation-model API vendor clauses, Clause 4.
2. **Attestation expires unnoticed.** Mitigation: `query_expired(grace_period_days=30)` is the cron-friendly read path. Deployers wire it to their alerting substrate.
3. **Vendor revokes an attestation retroactively.** Mitigation: the ledger is append-only by `LedgerStore` contract. The operator records a new attestation with a shorter `valid_until`; the historical record persists with hash continuity.
4. **Operator records a forward-dated attestation by mistake.** Mitigation: `query(valid_as_of=now)` excludes attestations whose `valid_from` is in the future. The audit chain entry is still recorded — accountability for the data-entry mistake is preserved.

## Reversibility

High. The ledger is a recording primitive — removing it is a configuration change that reverts the operator to whatever pre-existing record-keeping mechanism was in place. The hash-chain entries already written stand on their own as evidence even if the primitive is removed from new deployments.

## Cross-references

- **Implementation:** `src/finserv_agent_audit/governance/vendor_attestation_ledger.py`
- **Tests:** `tests/test_vendor_attestation_ledger.py`
- **Companion artifact:** `vendor-clauses/foundation_model_api_vendor_clauses.md` (v1.3 — Clause 4 + Clause 5 fully wire to this ADR)
- **Related ADRs:** ADR-0003 (Hash-chained Audit Ledger — substrate) · ADR-0007 (SR 11-7 overlay — second-line attestation surface) · ADR-0014 (Persistence + timestamp + witness seams) · ADR-0016 (Vendor Score Gate — the runtime companion; this ADR is the procurement-side companion) · ADR-0024 (Retraining Cadence Monitor — the temporal companion) · ADR-0025 (Deprecation Watch — the lifecycle companion)
