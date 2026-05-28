# ADR-0013: SEC Rule 17a-4 WORM Persistence for the Audit Chain

**Status:** Accepted
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit v1.1

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel and the firm's records-retention function. No attorney-client relationship is formed by use of this ADR. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

---

## Context

A broker-dealer adopter — and, by analog application, many investment advisers, swap dealers, and FCMs — falls under SEC Rule 17a-4 (17 C.F.R. § 240.17a-4) for the retention of records required by SEC Rule 17a-3. The 2022 SEC amendments to 17a-4(f) restated the substrate requirement: a registered broker-dealer must preserve electronic records in either (a) a non-rewriteable, non-erasable format (Write-Once-Read-Many, or "WORM"), or (b) a substrate that maintains a complete time-stamped audit trail of every modification or deletion, including the original record. The amendment retained the WORM option as the default safe harbor; the audit-trail option is permitted but raises the evidentiary burden on the firm. [UNVERIFIED — primary source not fetched]

The hash-chained audit ledger introduced in ADR-0003 is internally tamper-evident but, in its v1.0 reference implementation, was backed by an in-memory `list[AuditEntry]` and by file-system writes whose substrate immutability depends on the deployer's storage stack. For an SEC-registrant adopter, "depends on the deployer's storage stack" is not a sufficient answer to a FINRA examiner's records-retention review.

The 2026-05-28 internal audit named this gap (Finding D8.1, Critical). This ADR closes it.

## Decision

Adopt a `WORMLedgerStore` backend (shipped as part of the Tranche 2A persistence work, alongside `InMemoryLedgerStore`, `SqliteLedgerStore`, and `JsonlLedgerStore` — see ADR-0014 for the Protocol). The WORM backend has three load-bearing properties:

1. **Refuses overwrite at the API level.** Any attempt to overwrite, modify, or delete a previously-written entry raises `WORMViolationError`. The exception is fail-closed: the caller cannot suppress it without removing the safety. The exception type is exported from the public package surface so callers can write defensive tests against it.

2. **Configurable retention period.** The constructor accepts `retention_years: int` defaulting to 7. The default is calibrated against the 17a-4(b)(4) default for the broader category of records (six years for the first two years in an "easily accessible place" and a longer total period for many record classes); a 7-year default exceeds the common floor. Adopters operating under longer retention regimes (Investment Advisers Act recordkeeping, state-specific schedules, litigation hold) override the parameter upward; the backend never silently expires below the configured floor. [UNVERIFIED — exact 17a-4(b)(4) retention period not re-fetched in this session]

3. **Substrate hooks for true-WORM storage.** The reference implementation enforces WORM at the Python API layer. Production-grade deployments wire the backend to an underlying substrate that enforces WORM at the storage layer — Amazon S3 Object Lock in Compliance mode, Azure Blob Immutable Storage with legal hold, IBM FlashSystem WORM tier, Hitachi HCAP, or an on-prem appliance certified for 17a-4(f) by an independent assessor. The Python-layer enforcement is necessary-but-not-sufficient; the substrate-layer enforcement is what the FINRA examiner will sample.

### Protocol surface

```python
class WORMLedgerStore:
    def __init__(
        self,
        underlying: LedgerStore,
        retention_years: int = 7,
        substrate_attestation: SubstrateAttestation | None = None,
    ) -> None: ...

    def append(self, entry: AuditEntry) -> None:
        # Delegates to underlying; never permits modification.
        ...

    def attempt_modify(self, sequence: int, entry: AuditEntry) -> None:
        raise WORMViolationError(...)  # always

    def attempt_delete(self, sequence: int) -> None:
        raise WORMViolationError(...)  # always
```

`SubstrateAttestation` is a pluggable interface that records the underlying-storage retention configuration (Object Lock mode, retention duration, legal-hold state) at append time, so the audit chain itself carries evidence of the substrate posture. A FINRA examiner asking "prove the underlying bucket was in Compliance-mode Object Lock on the day this entry was written" can read the answer from the chain, not from a separately-maintained ops document.

### What this ADR does NOT do

- Ship a certified-by-third-party WORM substrate. Substrate certification (e.g., 17a-4 LLC's Designated Third Party assessment, Cohasset Associates attestation) is the deployer's procurement decision. The pattern provides the integration shape.
- Manage records destruction. After the retention period expires (and absent a litigation hold), records destruction is the deployer's operational responsibility. The backend supports a `tombstone(sequence, destruction_certificate)` path that records the destruction as an audit-chain entry without removing the chain-link.
- Address physical-records retention. 17a-4 applies to both electronic and physical records; this ADR addresses the electronic-records substrate only.
- Make the firm's filing of the Designated Third Party (DTP) undertaking under 17a-4(f)(3)(vii). That filing is a separate compliance action the firm's records-management function owns.

## Alternatives Considered

1. **Treat WORM as deployer responsibility entirely; do not ship a backend.** Rejected — the deployer needs to know what API contract to enforce. Without a reference, every deployer reinvents `WORMViolationError` differently, and the test surface for FINRA examination becomes inconsistent across firms.
2. **Default retention to the most permissive floor (3 years).** Rejected — the cost of over-retention is storage; the cost of under-retention is examination finding. Default high; deployers override down only with documented basis.
3. **Use the audit-trail option under 17a-4(f)(2)(i)(B) instead of WORM.** Rejected as the default — the audit-trail option requires a complete time-stamped trail of every modification, which raises the evidentiary burden and the operational complexity. The WORM safe harbor is the lower-friction default. Deployers who have already implemented the audit-trail option can wire a separate backend; this ADR does not preclude it.
4. **Use a blockchain anchor as the WORM substitute.** Rejected — the SEC has not issued guidance recognizing public blockchain as a 17a-4-compliant substrate. Blockchain anchoring is useful for external tamper-evidence (see ADR-0014 witness-anchor pattern) but is additive to, not a substitute for, the 17a-4 WORM requirement.

## Consequences

**Positive.** A broker-dealer adopter has a clean answer to the FINRA examiner's records-retention review: "the audit chain runs on `WORMLedgerStore` backed by [substrate], with retention attestation captured on every entry." The pattern produces examination-ready evidence without a year-end extraction sprint. The `WORMViolationError` exception forces defensive callers to handle the failure rather than silently dropping the modification.

**Negative.** WORM substrates carry real cost — both storage cost (records cannot be aged out below the retention floor) and operational cost (mistaken writes are permanent; recovery from operational error requires careful tombstone-with-correction workflow). Adopters must train operators on the cost of a mistaken append.

**Operational.** The substrate-attestation field requires the deployer's storage stack to expose its retention configuration to the Python layer. Most modern object stores expose this via API; legacy NAS-based WORM appliances may not. Deployers on legacy substrates wire a manual attestation source documented in their internal-control matrix.

## Regulatory Mapping

- **SEC Rule 17a-4** (17 C.F.R. § 240.17a-4) — broker-dealer record retention; 17a-4(f) substrate requirements for electronic records. [UNVERIFIED — primary source not fetched]
- **SEC 17a-4(f) amendments, 2022** — restated the WORM and audit-trail options; retained WORM as the default safe harbor. [UNVERIFIED — primary source not fetched]
- **FINRA Rule 4511** — books and records cross-reference to SEC 17a-3 and 17a-4. [UNVERIFIED — primary source not fetched]
- **Investment Advisers Act Rule 204-2** (17 C.F.R. § 275.204-2) — analogous recordkeeping for registered investment advisers; substrate requirements differ but the pattern is portable. [UNVERIFIED — primary source not fetched]
- **CFTC Rule 1.31** — analogous recordkeeping for futures and swap intermediaries. [UNVERIFIED — primary source not fetched]
- **MiFID II Article 16(7)** — recordkeeping for investment firms operating in the EU; five-year retention floor with extensions on regulator request.

## Pre-mortem

What fails:

1. **A deployer wires `WORMLedgerStore` over a non-WORM substrate.** Mitigation — the `SubstrateAttestation` field is required (not optional) in production configuration; a missing attestation raises on first append. The deployer cannot configure the backend without naming the substrate.
2. **An operator forces a "fix" via direct substrate write, bypassing the Python API.** Mitigation — the substrate-layer WORM enforcement is what prevents this. If the substrate permits the write, the firm has a 17a-4 finding regardless of what the pattern does.
3. **Retention floor is set below 17a-4 minimum by misconfiguration.** Mitigation — the constructor validates `retention_years >= 6` and refuses initialization below; firms with documented basis for a shorter floor (non-broker-dealer subsidiaries, etc.) override the validator explicitly.
4. **A litigation hold suspends destruction; firm later destroys without lifting the hold.** Mitigation — the `tombstone()` path requires a destruction certificate; the certificate's pre-condition (no active hold for the matter) is the deployer's workflow responsibility, but the pattern records the certificate in the chain. A post-hoc audit can detect the inconsistency.

## Reversibility

Low. Once entries are written to a WORM substrate, the substrate's retention floor controls. Switching backends mid-flight produces a heterogeneous ledger (some entries on WORM, some on non-WORM) which is itself an audit finding. Adopters select the WORM backend at program inception or at a clean cutover with documented basis.

## Cross-references

- **Implementation:** `src/finserv_agent_audit/governance/worm_ledger_store.py` (Tranche 2A)
- **Tests:** `tests/test_worm_ledger_store.py` — overwrite-refused, retention-floor-validated, tombstone-with-certificate, substrate-attestation-required
- **Related ADRs:** ADR-0003 (Hash-chained audit ledger) · ADR-0010 (Audit-chain retention policy) · ADR-0012 (SOX 404 ITGC, computer-operations category) · ADR-0014 (Persistence/Witness/Timestamp seams — `WORMLedgerStore` is one `LedgerStore` implementation)
- **Companion artifacts:** `docs/substrate-attestation/s3-object-lock.md` (Tranche 3 — sample attestation for S3 Object Lock Compliance mode)
