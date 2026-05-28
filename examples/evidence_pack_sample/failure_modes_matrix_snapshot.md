# FAILURE-MODES Matrix — Snapshot for Audit-Pack Reference

**Status:** Snapshot copy. The canonical version is at repo-root [`FAILURE-MODES.md`](../../FAILURE-MODES.md).
**Snapshot date:** 2026-05-28 (framework version v1.1.0).

> This snapshot is included in the sample evidence pack so an audit team can carry the matrix offline alongside the chain export. **Verify the snapshot against the canonical file before relying on it for fieldwork** — the framework's failure-mode coverage advances as new ADRs ship.

---

## How to read this document

The audit chain in this package is **tamper-detecting within its trust boundary by default**. Tamper-*evidence* against an attacker who controls the ledger host requires an external witness — RFC 3161 trusted timestamps (ADR-0014 Seam 2) and/or Sigstore Rekor + OpenTimestamps anchoring (ADR-0014 Seam 3). The matrix below names, per failure-mode class, what gets detected by which mechanism and what the recovery action looks like.

Each detection mechanism resolves to either:
- a fully-qualified callable in this codebase, rendered in the matrix below as `(F)` followed by the dotted Python path, or
- an explicit `NOT YET IMPLEMENTED · tracking: ADR-XXXX` marker — the v1.2 ship-gate fails the build if either the marker disappears or the named callable goes missing.

The classes are ordered from "in-trust-boundary" (rows 1-3) to "across-trust-boundary" (rows 4-8). The first three are addressable today; the last five are why ADR-0014 and ADR-0015 exist.

---

## Matrix (8 failure-mode classes)

| # | Class | Example | Detection mechanism (hash-chain / SHA-256) | Recovery | Regulatory mapping |
|---|---|---|---|---|---|
| 1 | **Storage drift** | Local JSONL truncated; SQLite row UPDATEd out-of-band; S3 object overwritten; EFS rename race; WORM file permission-modified by privileged user | Hash-chain verify-on-read · `(F) finserv_agent_audit.governance.audit_chain.AuditChain.verify` and `verify_strict`; WORM backend rejects any open-for-write on a finalized file | Reconstruct from external witness anchor if enabled; otherwise quarantine the affected range and surface to operator | SOC 2 CC7.2; SOX 404 ITGC; SEC 17a-4(f); FFIEC IT Handbook App J |
| 2 | **Sequence gap / split-brain** | Two processes write the same backend concurrently; sequence numbers skip or repeat | Monotonic sequence invariant inside chain verify · `(F) verify_strict` rejects non-contiguous `sequence`; plus backend-level conditional write per ADR-0014 § Seam 1 | Reject second writer at backend layer; manual reconcile from witness anchor or operator review | SOC 2 CC7.2; SOX 404 ITGC; SR 11-7 § V.4 |
| 3 | **In-trust-boundary replay** | A previously-appended chain segment re-inserted later in the same ledger | Sequence monotonicity + prior-hash invariant · `(F) verify` rejects re-inserted entries; tamper-evident witness boundary (hash-chain mechanism) cross-check tracked under ADR-0014-A1 | Reject replayed segment at verify time; do not auto-resolve | SOC 2 CC7.2; RFC 3161; SEC 17a-4(f)(3) |
| 4 | **Timestamp tampering** | System clock skew at append; monotonic counter rewind; deployer with `CAP_SYS_TIME` backdates entries | Within trust boundary: timestamps in chain order are non-decreasing (deployer policy enforced by `TimestampSource`); across boundary: RFC 3161 token verification — `NOT YET IMPLEMENTED · tracking: ADR-0014-A1` | Quarantine affected segment; flag for review | RFC 3161; SOC 2 CC7.2; SOX 404 ITGC; SEC 17a-4(f)(2)(ii)(A) |
| 5 | **Witness disagreement** | Rekor returns a different inclusion proof; OpenTimestamps calendar drops commitment; multiple anchors disagree | Cross-check witness receipts on verify — `NOT YET IMPLEMENTED · tracking: ADR-0014-A2`. Today: `(F) anchor_to_witness` writes receipt back as a `WITNESS_ANCHOR` chain entry; operator inspection detects mismatch | Escalate; do not auto-resolve | RFC 6962; SOC 2 CC7.2; ISO/IEC 42001:2023 § 8 |
| 6 | **Backend permission revocation** | IAM/EFS permissions removed mid-write; SQLite file becomes read-only; S3 bucket policy revokes `PutObject` | Backend `append()` raises a structured exception · `(F) AuditChain.append` propagates the underlying `LedgerStore.append` failure | Fail-closed: refuse to continue the operation that needed the audit entry; surface to operator | SOC 2 CC7.2; FFIEC App J; SOX 404 ITGC; GLBA Safeguards Rule § 314.4(c) |
| 7 | **Verifier compromise** | The verifier binary or canonical config is swapped for one that returns false-positive `verify()` | Out-of-band MI Proxy attestation on each verify · `(F) finserv_agent_audit.governance.mi_proxy.LocalMIProxy.verify_integrity` (ADR-0015); `(F) enforce_attestation` is the caller-side helper; `AuditChain.verify_strict(mi_proxy=...)` is the opt-in hook | Quarantine the verifier; switch to backup attested verifier; refuse to return a verified result while attestation fails | SOC 2 CC7.2; SOX 404 ITGC; FFIEC App J; RFC 6962; SR 11-7 § V.5 |
| 8 | **Vendor AI scoring drift** | A third-party scorer silently changes its model; same input produces a different score | Score-drift emission diff against the audit chain · `(F) InMemoryVendorScoreGate.record_score` (ADR-0016); same `(vendor_id, input_hash, model_version)` plus different `score` surfaces as a flagged `VENDOR_SCORE_DRIFT_DETECTED` chain entry; default raises `VendorScoreDriftDetected` | Flag in audit chain; trigger vendor-review playbook; operator decides whether to quarantine the vendor's signal | FFIEC App J; SOC 2 CC7.2; ISO/IEC 42001:2023; EU AI Act 2024/1689 Annex IV § 1(g); SR 11-7 § VI; OCC Bulletin 2011-12 |

---

## Coverage summary

- **Shipped detection (rows 1, 2, 3, 6, 7, 8):** six of eight classes have a named callable in v1.1.
- **Deferred detection (rows 4, 5):** RFC 3161 verify-side cross-check and witness re-verification on read are tracked under ADR-0014-A1 / A2; targeted for v1.2.

---

## How to use this snapshot during fieldwork

1. **Pick a row.** Walk the client through the named detection callable for that row in their own deployment.
2. **Demonstrate the no-op case.** Confirm the callable returns the expected success result against the production chain.
3. **Demonstrate the failure case.** In a non-production sandbox, induce the failure (mutate a byte, swap the verifier source, force a vendor-score change); confirm the named exception raises.
4. **Tie to recovery.** Confirm the client's runbook references the recovery action named in the matrix for that row.

If the client cannot perform steps 2-4 for a row, the auditor's working paper records the gap.

---

*Patterns are software, not legal advice. Refresh this snapshot from the canonical `FAILURE-MODES.md` at the start of every engagement.*
