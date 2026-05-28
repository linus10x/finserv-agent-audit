# ADR-0014: Pluggable Persistence, Trusted Timestamps, External Witness Anchoring, and Verifier Integrity

**Status:** Accepted
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit v1.1

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel. No attorney-client relationship is formed by use of this ADR. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).
>
> **Citation update (April 17, 2026):** Where this ADR references SR 11-7 / OCC Bulletin 2011-12 as the prudential MRM citation, note that those instruments were superseded for new examinations / rescinded by the joint OCC / FRB / FDIC issuance of April 17, 2026 (OCC Bulletin 2026-13), which **excluded generative + agentic AI from scope** pending a forthcoming joint RFI. The persistence + witness + timestamp pattern described here is independent of the MRM citation lineage; it is the evidence substrate that survives any plausible RFI outcome. See [`docs/interagency_mrm_2026_overlay.md`](../interagency_mrm_2026_overlay.md).

---

## Context

ADR-0003 introduced a hash-chained `AuditLedger` for FSI agent workflows. The v1.0 reference implementation had three named limitations:

1. **In-memory persistence only.** Entries lived in a single `list[AuditEntry]` — adequate for unit tests and demos, not for SOX 404 ITGC retention (ADR-0012), SEC 17a-4 substrate requirements (ADR-0013), or the FFIEC IT Examination Handbook's audit-trail expectations.
2. **Local-clock timestamps.** `AuditEntry.timestamp = datetime.now(timezone.utc)` carried no trusted-time attestation. A deployer with system-clock control could backdate; an external auditor or regulator had no way to bind a chain entry to a verifiable wall-clock time.
3. **Internally consistent, not externally tamper-evident.** Hash-chaining detects modification by an honest holder of the chain head. An attacker with full ledger-host write access can regenerate the chain end-to-end and `verify_chain()` will still pass. The chain is tamper-detecting *within the trust boundary of the ledger host*; it is not, by itself, tamper-evident against an adversary who controls that boundary.

There is a fourth limitation that becomes load-bearing once the first three are addressed: **the verifier itself is part of the trust boundary.** `AuditLedger.verify_chain()` is what auditors, regulators, and downstream consumers rely on to attest to chain integrity. A compromised verifier — swapped binary, modified configuration, supply-chain attack, undetected change-management drift — can return false-positive `verify_chain()` across the entire chain. The hash chain remains internally consistent; the *verifier* is the lie.

This ADR introduces the four Protocol seams that close all four limitations behind clean injection points. The pattern preserves the Zero-Runtime-Dependencies posture: every optional integration ships behind `extras_require` and is never imported by `finserv_agent_audit/__init__.py`.

The internal audit named the gap as Finding D9.1 (Critical) on 2026-05-28. This ADR is the architectural answer; ADR-0015 details the MI Proxy seam separately.

### Tamper-detection vs tamper-evidence — the load-bearing distinction

This distinction is the entire point of the pattern. The two are not synonyms.

- **Tamper-detection within trust boundary.** A hash chain detects modification by a holder who is bound by the trust boundary's rules — an honest operator, a non-malicious application bug, a partial-corruption hardware failure. The verifier reads the chain head, recomputes the predecessor hashes, and reports inconsistency. This is what the v1.0 audit ledger provides.

- **Tamper-evidence outside trust boundary.** External tamper-evidence requires anchoring the chain head into an append-only public log the local trust boundary does not control. A regenerated chain (the attacker who controls the boundary recomputes every hash end-to-end) will produce a head digest that *does not match* the digest the external log recorded at time T. The contradiction between local-claimed-head and external-recorded-head is the evidence. The local boundary cannot rewrite the external log.

The audit ledger as designed provides tamper-detection. **External tamper-evidence requires witness anchoring** (Seam 3 below). A repository that claims tamper-evidence without anchoring is conflating the two; this ADR refuses the conflation and ships both layers with the distinction documented at the API.

A trusted timestamp (Seam 2) sits between the two: it does not, on its own, prevent ledger-rewrite, but it binds each entry to a TSA-attested wall-clock time. An attacker rewriting the chain must also forge a TSA signature (computationally hard) or use a different TSA whose signing chain will not validate against the original. Combined with witness anchoring, the chain becomes evidentially defensible at audit and at discovery.

## Decision

Four Protocol-based seams added to the audit-chain layer. Each is injectable into `AuditLedger.__init__`; each ships at least one stdlib-only reference implementation in this repository; each documents an integration shape that downstream deployers implement against without pulling driver libraries into the core package.

### Seam 1 — `LedgerStore` (persistence)

```python
class LedgerStore(Protocol):
    def append(self, entry: AuditEntry) -> None: ...
    def __iter__(self) -> Iterator[AuditEntry]: ...
    def __len__(self) -> int: ...
    def get(self, sequence: int) -> AuditEntry: ...
    def head_sequence(self) -> int: ...
    def head_self_hash(self) -> str: ...
```

The Protocol is **append-only by absence** — no `update`, `delete`, `truncate`, or `set` method appears in the surface. Production stores enforce immutability in the substrate (Postgres row-level-immutability, S3 + Object Lock, DynamoDB conditional writes, Kafka log compaction off). The in-repo stores enforce it by not exposing mutation methods.

Reference implementations shipped in Tranche 2A under `src/finserv_agent_audit/governance/`:

| Backend | Module | Use case |
|---|---|---|
| `InMemoryLedgerStore` | `ledger_store.py` | v1.0 behavior preserved — tests, demos, ephemeral pipelines |
| `SqliteLedgerStore` | `ledger_store_sqlite.py` | Single-node durability via stdlib `sqlite3`; one row per entry; no UPDATE codepath |
| `JsonlLedgerStore` | `ledger_store_jsonl.py` | Append-only file for high-throughput ingestion; opt-out `fsync=False` |
| `WORMLedgerStore` | `worm_ledger_store.py` | SEC 17a-4 WORM enforcement (ADR-0013); wraps an underlying store with `WORMViolationError` on modify/delete |

Downstream deployers implementing Postgres+WAL, S3+Object Lock, DynamoDB, Kafka, QLDB, or an FSI-grade records-management appliance (Cohasset-certified or equivalent) write ~60 LOC against the Protocol. This repository does not pull psycopg, boto3, or any driver library — that would violate Zero-Deps.

`AuditLedger` accepts `store: LedgerStore | None = None`; defaults to `InMemoryLedgerStore()` via `__post_init__`. v1.0 callers calling `AuditLedger()` get v1.0 behavior unchanged.

### Seam 2 — `TimestampSource` (trusted time)

```python
class TimestampSource(Protocol):
    def stamp(self, payload_digest: bytes) -> TrustedTimestamp: ...
```

Reference implementations in `src/finserv_agent_audit/governance/timestamp_source.py`:

| Source | Behavior |
|---|---|
| `LocalClockTimestampSource` | `datetime.now(timezone.utc)`; no token. Default; preserves v1.0 semantics. |
| `RFC3161TimestampSource` | POSTs a Time-Stamp Request to a deployer-chosen TSA (FreeTSA, DigiCert, Sectigo, an internal TSA, or an FSI consortium TSA); receives a signed Time-Stamp Response; stores the opaque token base64-encoded. Fallback-to-local on TSA failure is the default so a TSA outage does not stall the audit pipeline; set `fallback_to_local_on_failure=False` to fail closed. |

The TSQ/TSR codec is hand-rolled in `rfc3161_codec.py` against the DER ASN.1 subset RFC 3161 actually uses (OID, INTEGER, OCTET STRING, NULL, BOOLEAN, SEQUENCE, GeneralizedTime). No `cryptography`, no `asn1crypto` in the core package. Signature-chain re-validation against the TSA's signing chain (needed years later when auditors re-verify) belongs to the optional `audit-verify` extra (pyca/cryptography).

`AuditEntry` gains an optional `timestamp_token_b64: str | None = None` field. The token is included in `canonical_bytes_for_hashing` ONLY when present, so v1.0 ledgers (token-free) remain hash-stable under v1.1 `verify_chain()`. Mixing local-clock and TSA-stamped entries in the same ledger is supported — the per-entry mode is recorded by the presence/absence of the field.

For FSI adopters, the typical TSA selection is either (a) an internal enterprise TSA backed by an HSM (treasury function or compliance function operates it), or (b) a public TSA from a CA already in the firm's PKI trust store. Public TSA selection is a procurement decision; the pattern is agnostic.

`AuditLedger` accepts `timestamp_source: TimestampSource | None = None`; defaults to `LocalClockTimestampSource()`.

### Seam 3 — `WitnessRegister` (external anchoring — the tamper-evidence layer)

```python
class WitnessRegister(Protocol):
    def anchor(self, chain_head_hex: str) -> WitnessReceipt: ...
```

Reference implementations in `src/finserv_agent_audit/governance/witness_anchor.py`:

| Register | Behavior |
|---|---|
| `RekorWitness` | POSTs a `hashedrekord` entry to Sigstore Rekor's public transparency log; receives an inclusion UUID + logIndex. Default endpoint is the public Sigstore instance; air-gapped deployers point to a private Rekor. |
| `OpenTimestampsWitness` | Submits the chain head digest to the OpenTimestamps calendar API; receives a pending-commitment receipt that upgrades to a Bitcoin attestation by re-submitting the opaque blob. Multiple calendar URLs supported for redundancy. |

The `anchor_to_witness(ledger, witness)` helper writes the receipt back to the ledger as a `decision_type="witness_anchor"` entry. **This binds the anchor into the same hash chain it protects: tampering with the anchor record requires tampering with every entry after it.** That is the core architectural commitment behind the tamper-evidence claim. The local boundary cannot rewrite the external log; the external receipt is bound back into the chain via hash; therefore a rewrite-the-chain attack must also produce a forged external receipt that the witness log will not return on lookup.

Scheduling is the deployer's responsibility — cron, Kubernetes CronJob, AWS EventBridge, an FSI batch scheduler. The package ships the function; the deployer schedules the cadence. Typical FSI cadence is end-of-trading-day plus end-of-month, with intra-day anchors for high-criticality flows (large-order surveillance, intraday risk-system events).

### Seam 4 — `MIProxy` (verifier integrity)

The fourth seam — Module Integrity Proxy for the verifier itself — has its own ADR (ADR-0015) due to scope and the recursive-verifier problem. It is named here to make the four-seam architecture complete: the chain's contents (Seams 1–3) and the function that reads them (Seam 4) are both inside the trust boundary, and both need explicit treatment.

## Alternatives Considered

1. **Single monolithic "audit storage backend" interface.** Rejected — conflates persistence, time, and external anchoring. Adopters who need WORM-substrate persistence but not external anchoring (e.g., a firm whose regulatory posture is satisfied by SEC 17a-4 alone) would be forced to wire all three. Independent Protocols compose cleanly; a monolithic interface does not.
2. **Embed witness-anchor receipts in a separate sidecar log.** Rejected — two logs introduce a coordination problem. If the anchor sidecar and the chain disagree at audit time, which is canonical? Binding the receipt back into the chain as a regular entry collapses the question: the chain is the canonical record, and the witness receipt is just another link in it.
3. **Make trusted timestamping mandatory.** Rejected — would force every adopter to provision and operate a TSA relationship before they can run the patterns. The pattern remains useful at the local-clock layer for development and for small-scale deployments; trusted time is an additive hardening, not a precondition.
4. **Use a blockchain anchor (Ethereum, Polygon, Bitcoin via OTS) instead of a transparency log.** Considered — Bitcoin via OpenTimestamps is supported as one of the reference backends. Direct Ethereum anchoring was rejected as a default due to gas-cost volatility and dependency on a specific chain's continued operation; transparency logs (Rekor) provide the same evidentiary property at lower operational cost.
5. **Re-derive the timestamp from the witness anchor.** Rejected — couples Seam 2 to Seam 3, and the witness-anchor cadence (batch, end-of-day) is wrong for per-entry timestamping. Independent seams give the deployer the right knob on each.

## Consequences

**Positive.**
- Four of the v1.1 deferred limitations close behind clean Protocols with backward-compat defaults.
- Zero-Runtime-Deps badge intact. `pyproject.toml` `[project.dependencies]` remains `[]`. Optional `[audit-verify]` extra is documented but not required for core audit semantics.
- Stdlib-only network code (`http.client` + `ssl`) in the timestamp and witness modules. No `requests`, no `urllib3`.
- v1.0 ledgers and v1.0 callers continue to work unchanged. Hash semantics are stable across versions for token-free entries.
- The tamper-detection vs tamper-evidence distinction is documented at the API; adopters cannot accidentally claim more than the configuration supports.

**Negative.**
- DER ASN.1 codec is hand-rolled. The RFC 3161 subset is small but the maintenance burden is real. The optional `audit-verify` extra delegates full DER work to `pyca/cryptography`; the in-repo codec covers the build-and-parse path that delivers 80% of audit value.
- Mid-flight migration from `LocalClockTimestampSource` to `RFC3161TimestampSource` produces a heterogeneous ledger (some entries with tokens, some without). The per-entry `timestamp_token_b64` field documents which mode produced each entry, but deployers should document the cutover in their own ops runbooks.
- `RekorWitness` and `OpenTimestampsWitness` create hard dependencies on external services at anchor time. Deployers instrument the anchor cron with retry and alerting. The pattern recovers (the next cron run anchors the new head); the audit is not blocked.

**Architectural.**
- The four seams are independent. A deployer can adopt `SqliteLedgerStore` without `RFC3161TimestampSource` or vice versa. The seams compose without coordination.
- The anchor-receipt-becomes-a-regular-ledger-entry decision was the load-bearing design choice. The alternative (separate witness log) was rejected on coordination grounds, and the consequences of the rejection are encoded in the regulator-facing claim: there is one canonical chain, and the witness receipts are entries in it.

## What this ADR does NOT cover

- **Signature-chain re-verification of stored RFC 3161 tokens.** Implemented behind the `audit-verify` extra. The opaque token is preserved verbatim so a downstream verifier (any RFC 3161-aware tool) can validate the TSA chain at any time.
- **Production-grade `LedgerStore` backends for Postgres / S3 / DynamoDB / vendor records-management appliances.** The Protocol is the contract; deployers implement against it. This ADR documents the integration shape and the conditional-write idiom per backend. The repo does not pull driver libraries.
- **Anchor scheduling and retry orchestration.** Deployers wire the anchor cron in their own infrastructure. The pattern is idempotent against repeated submission of the same head — multiple anchor entries with the same `chain_head_anchored` value are valid.
- **Cross-region replication of the audit ledger.** Deployers operating in multi-region failover wire replication at the substrate layer; the Protocol surface assumes a single logical store.
- **MI Proxy verifier integrity.** Seam 4 is named here but specified in ADR-0015 (next).
- **Vendor Score Gate.** Separate pattern; see ADR-0016.

## Regulatory Mapping

- **SOX 404 ITGC** (15 U.S.C. § 7262) — audit-trail integrity is a documented expectation; the WORM and TSA backends are the technical controls behind the change-management and computer-operations categories. See ADR-0012. [UNVERIFIED — primary source not fetched]
- **SEC Rule 17a-4** (17 C.F.R. § 240.17a-4) — broker-dealer record retention; `WORMLedgerStore` is the substrate-enforcing `LedgerStore` implementation. See ADR-0013. [UNVERIFIED — primary source not fetched]
- **FFIEC IT Examination Handbook — Audit Booklet** — IT Audit § "Audit Trail" expects time-attested, retention-policied, integrity-protected records. RFC 3161 trusted timestamps + external witness anchoring address two of three directly. [UNVERIFIED — primary source not fetched]
- **NYDFS 23 NYCRR Part 500** (Cybersecurity Regulation) — § 500.06 audit-trail integrity; tamper-evident logging (witness-anchored hash-chain mechanism) required for systems handling Nonpublic Information. [UNVERIFIED — primary source not fetched]
- **FINRA Rule 4511** — books and records cross-reference; tamper-evidence supports the 17a-4 substrate posture.
- **RFC 3161** — *Internet X.509 Public Key Infrastructure Time-Stamp Protocol (TSP)*. The TSA produces a signed time attestation verifiable at any future point against the TSA's signing chain.
- **RFC 6962** — *Certificate Transparency*. The design rationale for external-witness-as-tamper-evidence is the same: the witness records what existed at time T, and a later attempt to rewrite history must contradict the public record.
- **SOC 2 Type 2 CC6.1 / CC7.2** — Logical Access Controls and System Monitoring; tamper-evident audit trails (hash-chain mechanism with external witness) support both criteria.
- **EU AI Act Article 12** (Regulation (EU) 2024/1689) — logging over the AI system's lifetime; the chain + WORM + witness anchor is the architectural answer. [UNVERIFIED — primary OJ text not fetched]

## Pre-mortem

What fails:

1. **Adopter wires TSA but skips witness anchor.** Mitigation — documentation explicit on the tamper-detection vs tamper-evidence distinction; the `AuditLedger` `__repr__` reports which seams are configured so deployment-time inspection surfaces the gap.
2. **Witness log goes offline during a critical anchor window.** Mitigation — anchor function is idempotent; multiple registers configurable; failure surfaces as an audit-chain entry of `decision_type="witness_anchor_failed"` so the gap is itself part of the chain.
3. **TSA's signing certificate is revoked years later.** Mitigation — token is opaque and preserved; signature-chain re-verification at audit time validates against the historical certificate state. The optional `audit-verify` extra wires this.
4. **A deployer claims tamper-evidence in regulator-facing documents without wiring Seam 3.** Mitigation — the ADR documents the distinction at the architectural level; the README's "what you can claim with which configuration" matrix (forthcoming, Tranche 3) makes the gap visible at adoption time.
5. **A new `LedgerStore` backend lands without preserving the append-only-by-absence property.** Mitigation — the Protocol surface has no mutation method; a backend exposing one is non-conformant and the type checker catches it at deployer-side test time.

## Reversibility

High at the seam level — a deployer can swap `LocalClockTimestampSource` back in (loses trusted-time attestations on entries written under the new source, but the chain remains valid). Low at the substrate level — entries written to WORM cannot be moved off WORM without violating the substrate's retention contract. Once a witness-anchor receipt is written into the chain, removing the witness-register integration does not remove the receipt entries; they remain as historical evidence the integration was once active.

## Cross-references

- **Implementation:** `src/finserv_agent_audit/governance/ledger_store.py` · `ledger_store_sqlite.py` · `ledger_store_jsonl.py` · `worm_ledger_store.py` · `timestamp_source.py` · `rfc3161_codec.py` · `witness_anchor.py` (Tranche 2A)
- **Tests:** `tests/test_ledger_store_*.py` · `tests/test_timestamp_source.py` · `tests/test_witness_anchor.py` (Tranche 2A)
- **Related ADRs:** ADR-0003 (Hash-chained audit ledger — the original pattern) · ADR-0012 (SOX 404 ITGC overlay) · ADR-0013 (SEC 17a-4 WORM) · ADR-0015 (MI Proxy — Seam 4) · ADR-0016 (Vendor Score Gate)
- **Companion frameworks:** RFC 3161 (trusted timestamping) · RFC 6962 (transparency-log evidentiary model) · NIST AI RMF MEASURE 2.7 (model integrity over the lifecycle)
