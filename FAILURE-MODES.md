# FAILURE-MODES.md — Adversarial, partition, and corruption matrix

**Status:** v1.1.0 · companion to ADR-0014 (persistence + timestamp + witness seams) and ADR-0015 (MI Proxy verifier chain-of-custody).
**Last reviewed:** 2026-05-28.

> **Patterns are software, not legal advice.** Regulatory citations below are reference mappings; consult counsel for applicability to your control environment. See repo-root [`DISCLAIMER.md`](DISCLAIMER.md).

## How to read this document

The audit chain in this package is **tamper-detecting within its trust boundary by default**. Tamper-*evidence* against an attacker who controls the ledger host requires an external witness — RFC 3161 trusted timestamps (ADR-0014 Seam 2) and/or Sigstore Rekor + OpenTimestamps anchoring (ADR-0014 Seam 3). The matrix below names, per failure-mode class, what gets detected by which mechanism and what the recovery action looks like.

Each detection mechanism resolves to either:
- a fully-qualified callable in this codebase, rendered in the matrix below as `(F)` followed by the dotted Python path, or
- an explicit `NOT YET IMPLEMENTED · tracking: ADR-XXXX` marker — the v1.2 ship-gate fails the build if either the marker disappears or the named callable goes missing.

The classes are ordered from "in-trust-boundary" (rows 1–3) to "across-trust-boundary" (rows 4–8). The first three are addressable today; the last five are why ADR-0014 and ADR-0015 exist.

---

## Matrix

| # | Class | Example | Detection | Recovery | Regulatory mapping |
|---|---|---|---|---|---|
| 1 | **Storage drift** | Local JSONL truncated; SQLite row UPDATEd out-of-band; S3 object overwritten; EFS rename race; WORM file `chmod 644`'d by privileged user | Hash-chain verify-on-read · `(F) finserv_agent_audit.governance.audit_chain.AuditChain.verify` and the stricter `(F) finserv_agent_audit.governance.audit_chain.AuditChain.verify_strict`; WORM backend rejects any open-for-write on a finalized file · `(F) finserv_agent_audit.governance.ledger_store_worm.WORMLedgerStore.append` raises `WORMViolationError` | Reconstruct from external witness anchor if enabled (`(F) finserv_agent_audit.governance.witness_anchor.anchor_to_witness`); otherwise quarantine the affected range and surface to operator | SOC 2 CC7.2 (system monitoring); SOX 404 ITGC (audit-trail integrity); SEC 17a-4(f) (WORM electronic recordkeeping); FFIEC IT Handbook App J (third-party storage) |
| 2 | **Sequence gap / split-brain** | Two processes write the same backend concurrently; sequence numbers skip or repeat; one writer wins, the other's entries are lost | Monotonic sequence invariant inside chain verify · `(F) finserv_agent_audit.governance.audit_chain.AuditChain.verify_strict` (rejects non-contiguous `sequence`); plus backend-level conditional write (Postgres unique constraint, DynamoDB conditional write, S3 Object Lock + Versioning) per ADR-0014 § Seam 1 integration shape | Reject the second writer at the backend layer; manual reconcile from the witness anchor or from operator review of the gap | SOC 2 CC7.2; SOX 404 ITGC change management; FFIEC App J § "Concurrency"; SR 11-7 § V.4 (model output integrity) |
| 3 | **In-trust-boundary replay** | A previously-appended chain segment is re-inserted later in the same ledger | Sequence monotonicity + prior-hash invariant · `(F) finserv_agent_audit.governance.audit_chain.AuditChain.verify` (re-inserted entries fail prior-hash + sequence checks); within a tamper-evident witness boundary (hash-chain mechanism), sequence + timestamp window cross-check is `NOT YET IMPLEMENTED · tracking: ADR-0014-A1 (rfc3161_verify extra)` | Reject the replayed segment at verify time; do not auto-resolve | SOC 2 CC7.2; RFC 3161 (signed timestamps make replay across the witness boundary detectable); SEC 17a-4(f)(3) (non-rewritable recordkeeping) |
| 4 | **Timestamp tampering** | System clock skew at append; monotonic counter rewind; deployer with `CAP_SYS_TIME` backdates entries | Within trust boundary: timestamps in chain order are non-decreasing (deployer policy, enforced at append by the `TimestampSource`); across trust boundary: RFC 3161 token verification disagrees with claimed time · `NOT YET IMPLEMENTED · tracking: ADR-0014-A1 (audit-verify extra wires rfc3161_verify against the TSA's certificate chain)` | Quarantine the affected chain segment; flag for review; do not auto-rewrite | RFC 3161 (TSA-signed time); SOC 2 CC7.2; SOX 404 ITGC (time integrity for change records); SEC 17a-4(f)(2)(ii)(A) (time-date stamped) |
| 5 | **Witness disagreement** | Rekor returns a different inclusion proof than the receipt on file; OpenTimestamps calendar drops the commitment; multiple anchors disagree | Cross-check witness receipts on verify · `NOT YET IMPLEMENTED · tracking: ADR-0014-A2 (witness re-verification on read)`. Today: `(F) finserv_agent_audit.governance.witness_anchor.anchor_to_witness` writes the receipt back to the ledger as a `WITNESS_ANCHOR` chain entry; mismatch between two anchor entries with the same `chain_head_anchored` is detectable by operator inspection but not yet by automated verify | Escalate; do not auto-resolve. Operator decides which witness to trust based on substrate posture. | RFC 6962 (Certificate Transparency model); SOC 2 CC7.2; ISO/IEC 42001:2023 § 8 (operational controls) |
| 6 | **Backend permission revocation** | IAM/EFS permissions removed mid-write; SQLite file becomes read-only; S3 bucket policy revokes `PutObject`; WORM directory ACL revoked | Backend `append()` raises a structured exception · `(F) finserv_agent_audit.governance.audit_chain.AuditChain.append` (propagates the underlying `LedgerStore.append` failure); deployers wire alerting in the operational substrate | Fail-closed: refuse to continue the operation that needed the audit entry; surface to operator. The audit chain prefers a missing operation over a missing audit record. | SOC 2 CC7.2 (continuous monitoring); FFIEC App J § "Vendor incident response"; SOX 404 ITGC; GLBA Safeguards Rule § 314.4(c) (access controls) |
| 7 | **Verifier compromise** | The verifier binary or canonical config is swapped for one that returns false-positive `verify()`; the trust boundary is shifted under the operator's feet | Out-of-band MI Proxy attestation on each verify · `(F) finserv_agent_audit.governance.mi_proxy.LocalMIProxy.verify_integrity` (ADR-0015); default backend hashes the verifier source + canonical config and signs HMAC-SHA256 with a deployer key; `(F) finserv_agent_audit.governance.mi_proxy.enforce_attestation` is the helper that callers wrap verify-side with; `AuditChain.verify_strict(mi_proxy=...)` is the opt-in hook | Quarantine the verifier and switch to a backup attested verifier; refuse to return a verified result while attestation fails (fail-closed; raises `IntegrityVerificationError`) | SOC 2 CC7.2 (system monitoring of integrity); SOX 404 ITGC change management (the verifier is privileged software); FFIEC App J (external attestation when out-of-band backend is used); RFC 6962 (Rekor as one external backend option); SR 11-7 § V.5 (control over model implementation) |
| 8 | **Vendor AI scoring drift** | A third-party scorer silently changes its model; same input produces a different score; vendor patches without changelog | Score-drift emission diff against the audit chain · `(F) finserv_agent_audit.governance.vendor_score_gate.InMemoryVendorScoreGate.record_score` (ADR-0016); same `(vendor_id, input_hash, model_version)` tuple plus a different `score` surfaces as a flagged `VENDOR_SCORE_DRIFT_DETECTED` chain entry; default posture raises `VendorScoreDriftDetected` so the pipeline halts rather than silently absorbing the change | Flag in audit chain; trigger vendor-review playbook; operator decides whether to quarantine the vendor's signal; `raise_on_drift=False` available for shadow-mode rollouts | FFIEC IT Handbook App J § "Third-party model risk"; SOC 2 CC7.2; ISO/IEC 42001:2023 (third-party model controls); EU AI Act (2024/1689) Annex IV § 1(g) (third-party component records); SR 11-7 § VI (third-party model risk); OCC Bulletin 2011-12 § "vendor models" |

## Defaults

| Posture | Default behavior |
|---|---|
| Verifier sees a hash-chain mismatch | Raise `AuditChainTamperError`; refuse to return a verified result |
| Verifier cannot attest its own binary (MI Proxy fail) | Raise `IntegrityVerificationError`; refuse to return a verified result |
| Vendor score gate sees drift | Record a flagged chain entry; raise `VendorScoreDriftDetected` by default |
| Backend `append` raises | Propagate the exception; the audit chain prefers a missing operation over a missing audit record |
| WORM backend asked to mutate a finalized file | Raise `WORMViolationError`; the deployer pairs this with S3 Object Lock COMPLIANCE mode for production |
| Timestamp source raises | Fallback-to-local-clock is the default for `RFC3161Source`; set `fallback_to_local_on_failure=False` to fail closed |
| Witness anchor `anchor()` raises | The pattern recovers on the next cron run; the audit chain is not blocked; deployer instruments alerting |

The framework is **fail-closed for verify-side checks** and **best-effort with explicit fallback for append-side dependencies on external services**. A missing or untrusted verify result is a hard error; a missing trusted-timestamp token on a single entry is a documented, recoverable degradation.

## Coverage summary

- **Shipped detection (rows 1, 2, 3, 6, 7, 8):** six of eight classes have an `(F)` callable in v1.1.
- **Deferred detection (rows 4, 5):** RFC 3161 verify-side cross-check and witness re-verification on read are tracked under ADR-0014-A1 / A2; targeted for v1.2.

## What this document is NOT

- **Not a threat model for the trust boundary itself.** The matrix describes failures within and across the boundary; perimeter posture (who can `kubectl exec`, who holds the signing key, who can SSH to the ledger host) is the deployer's threat model, not this document's. See ADR-0018 for adversarial-agent scope.
- **Not legal advice.** Regulatory citations are reference mappings to help the deployer point counsel and auditors at relevant clauses; applicability is a deployer-and-counsel determination.
- **Not a substitute for vendor due diligence.** Row 8 detects emission diff; it does not validate the vendor's underlying model, training data, or fair-lending posture.
- **Not a substitute for the operational runbook.** Recovery actions are framework defaults; the deployer's incident-response procedure is where the actual response lives.
- **Not exhaustive.** The matrix names eight classes the framework addresses today. Threat surfaces outside these (denial-of-service against the TSA, regulator subpoena for the signing key, insider revocation of the audit role) are deployer responsibilities by design.

## Related

- ADR-0003 — Internally-consistent hash-chained audit ledger
- ADR-0013 — SEC 17a-4 WORM persistence
- ADR-0014 — Persistence + timestamp + witness anchor (the three Protocol seams)
- ADR-0015 — MI Proxy (Module Integrity verifier chain-of-custody)
- ADR-0016 — VendorScoreGate (third-party scoring drift)
- ADR-0017 — Audit-chain retention, privilege, and discovery posture
- ADR-0018 — Adversarial agent threat model
- ADR-0019 — ProtectedClassProxyDetector deferred-implementation stub
- [`LIMITATIONS.md`](LIMITATIONS.md) — bounded claims for the v1.1 baseline

---

*Patterns are software, not legal advice. Regulatory citations are reference mappings; consult counsel for applicability to your control environment.*
