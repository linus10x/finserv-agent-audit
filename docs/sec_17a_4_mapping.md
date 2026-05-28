# SEC Rule 17a-4 — Control Mapping for Autonomous AI Agents

This document maps the governance patterns in this repository to the
broker-dealer record-retention requirements of SEC Rule 17a-4
(17 C.F.R. § 240.17a-4), as amended in 2022 to restate the electronic-
storage-media requirements at paragraph (f). Autonomous agents working
inside a broker-dealer — trade surveillance, KYC adjudication, order-
ticket annotation, SAR-narrative drafting, customer-correspondence
composition — produce records that fall within the 17a-4 retention
perimeter. The audit ledger that records what those agents did is itself
in scope.

> **Disclaimer:** Reference pattern, not legal advice. Regulatory
> characterizations are summaries; engage qualified securities counsel and
> the firm's records-management function. See repo-root
> [`DISCLAIMER.md`](../DISCLAIMER.md).

---

## Framework Overview

SEC Rule 17a-4 is the records-retention companion to Rule 17a-3 (which
specifies the records a broker-dealer must make). 17a-4(b) sets the
retention periods by record class: most operational records are preserved
for at least three years, with the first two years in an "easily
accessible place"; records under 17a-3(a)(1)-(3), (5), (21)-(22) and
several other categories are preserved for at least six years with the
same first-two-years accessibility constraint. Account records run for
six years after the account is closed; organizational documents run for
the life of the enterprise; compliance manuals run for three years after
termination of use.

17a-4(f) governs the substrate on which electronic records are stored.
The 2022 SEC amendment (Release 34-96034) restated the substrate
requirement as a choice between two compliant approaches:

- **WORM (Write-Once, Read-Many).** Records are preserved "exclusively in
  a non-rewriteable, non-erasable format."
- **Audit-trail alternative.** Systems "maintain a complete time-stamped
  audit trail that includes: (1) All modifications to and deletions of the
  record or any part thereof; (2) The date and time of actions."

Both options carry additional operational requirements: human-readable
and reasonably-usable electronic-format download, backup and redundancy,
automatic verification of storage completeness, and the paragraph (i)
third-party-access undertaking — either a Designated Third Party (DTP)
file or, where the broker-dealer has independent access to records held
on an outside-operated server, an alternative undertaking confirming that
independent access.

The pattern coverage below treats the WORMLedgerStore as the substrate
that produces the 17a-4(f) WORM safe harbor, and treats every supporting
pattern (retention, witness anchoring, substrate attestation) as the
artifact set a FINRA examiner samples on a records-retention review.

---

## Primary-Source Citations

| Source | Retrieved | Status |
|---|---|---|
| 17 C.F.R. § 240.17a-4 (Cornell LII mirror) | 2026-05-28, https://www.law.cornell.edu/cfr/text/17/240.17a-4 | Verified — retention periods, paragraph (f) WORM vs audit-trail alternative, and paragraph (i) third-party access requirement quoted verbatim above |
| 17 C.F.R. § 240.17a-4 (eCFR primary) | 2026-05-28, https://www.ecfr.gov/current/title-17/chapter-II/part-240/section-240.17a-4 | `[UNVERIFIED — primary source not fetched: 302 redirect to unblock.federalregister.gov]`; Cornell mirror above carries the operative text |
| SEC Release 34-96034 — Electronic Recordkeeping Requirements for Broker-Dealers, Security-Based Swap Dealers, and Major Security-Based Swap Participants (October 12, 2022) | 2026-05-28, https://www.sec.gov/rules/final/2022/34-96034.pdf | `[UNVERIFIED — primary source not fetched: HTTP 403]`; the amendment framing follows the SEC's public summary |
| 17 C.F.R. § 240.17a-3 (records to be made) | Referenced as the companion rule | Not re-fetched in this pass |
| FINRA Rule 4511 (books and records cross-reference) | Referenced in ADR-0013 | `[UNVERIFIED — primary source not fetched]` |

---

## Control Mapping Table

| 17a-4 Requirement | Citation | Pattern in This Repo | File |
|---|---|---|---|
| Retention period — six years, first two easily accessible (blotters, ledgers, customer account records, others) | 17a-4(b)(1)-(2) | `WORMLedgerStore(retention_years=7)` default exceeds the six-year floor; configurable upward | `src/finserv_agent_audit/governance/ledger_store_worm.py` |
| Retention period — three years, first two easily accessible (communications, written agreements, others) | 17a-4(b)(4) | Same backend; same retention parameter calibrated to the longer floor in the default | `src/finserv_agent_audit/governance/ledger_store_worm.py` |
| Account records — six years after account closure | 17a-4(c) | `WORMLedgerStore` retention floor; account-closure event recorded on chain triggers the post-closure retention clock | `src/finserv_agent_audit/governance/ledger_store_worm.py` |
| Organizational documents — life of enterprise | 17a-4(d) | Out of scope for an agent-audit ledger; the firm's corporate-records function owns this class | n/a |
| Compliance manuals — three years after termination of use | 17a-4(e)(7) | Out of scope; the firm's compliance function owns this class | n/a |
| Electronic-storage substrate — WORM safe harbor | 17a-4(f)(2)(i)(A) | `WORMLedgerStore` refuses overwrite at the API level (`WORMViolationError`); substrate hooks for true-WORM storage (S3 Object Lock Compliance mode, Azure Immutable Storage, on-prem 17a-4(f) appliances) | `src/finserv_agent_audit/governance/ledger_store_worm.py` (ADR-0013) |
| Electronic-storage substrate — audit-trail alternative | 17a-4(f)(2)(i)(B) | Not the default; deployers electing this path wire an alternative backend behind the LedgerStore Protocol (ADR-0014); the hash chain itself supplies the required complete time-stamped trail | `src/finserv_agent_audit/governance/ledger_store.py` Protocol |
| Human-readable and reasonably-usable electronic-format download | 17a-4(f)(2)(ii) | Audit ledger entries are JSONL / SQLite-queryable; export utilities produce human-readable transcripts and machine-readable archives | `src/finserv_agent_audit/governance/ledger_store_jsonl.py`, `src/finserv_agent_audit/governance/ledger_store_sqlite.py` |
| Storage-process completeness verification | 17a-4(f)(2)(iii) | Hash-chain verification (`AuditChain.verify()`) detects any inserted, modified, or deleted event; witness-anchor receipts bound the verification window | `src/finserv_agent_audit/schemas/audit_event.py`, `src/finserv_agent_audit/governance/witness_anchor.py` |
| Time-stamped audit trail with date and time of actions | 17a-4(f)(2)(i)(B); paragraph (ii) | RFC 3161 timestamp source on chain-head digests; per-entry timestamp captured at append | `src/finserv_agent_audit/governance/rfc3161_codec.py`, `src/finserv_agent_audit/governance/timestamp_source.py` |
| Third-party access — Designated Third Party undertaking | 17a-4(i) (formerly 17a-4(f)(3)(vii)) | Out of scope for the pattern itself; the firm's records-management function files the DTP undertaking. The substrate-attestation field records which DTP covers a given entry, so the firm's filing is cross-referenced from the chain | `src/finserv_agent_audit/governance/ledger_store_worm.py` `SubstrateAttestation` |
| Third-party access — alternative for independent access on outside-operated server | 17a-4(i) | Same substrate-attestation pattern; the firm's independent-access posture is recorded on the chain via the attestation field at append time | `src/finserv_agent_audit/governance/ledger_store_worm.py` `SubstrateAttestation` |
| Backup and redundancy | 17a-4(f)(2)(iv) | Substrate-layer concern; the LedgerStore Protocol composes with redundant backends (multi-region S3, cross-region replication) at the substrate layer | `src/finserv_agent_audit/governance/ledger_store.py` Protocol |

---

## Retention Walkthrough — How the WORMLedgerStore Closes the Gap

The hash-chained audit ledger introduced in ADR-0003 is internally tamper-
evident. Its v1.0 reference implementation was backed by an in-memory
list and by file-system writes whose substrate immutability depended on
the deployer's storage stack. For a broker-dealer adopter, "depends on
the deployer's storage stack" is not a sufficient answer to a FINRA
examiner's records-retention review. ADR-0013 closes that gap with three
load-bearing properties:

**1. API-layer refusal of overwrite.** The `WORMLedgerStore` raises
`WORMViolationError` on any attempt to modify or delete a previously-
written entry. The exception is fail-closed; callers cannot suppress it
without removing the safety. The exception type is exported from the
public package surface so adopters can write defensive tests against it.

**2. Configurable retention period, calibrated default.** The constructor
accepts `retention_years: int` defaulting to 7. The default is calibrated
against the 17a-4(b)(4) six-year floor for the broader record category; a
7-year default exceeds the floor and accommodates the common 6-year-post-
account-closure case under 17a-4(c). Adopters operating under longer
retention regimes (Investment Advisers Act recordkeeping, state-specific
schedules, litigation hold) override the parameter upward; the backend
never silently expires below the configured floor.

**3. Substrate hooks for true-WORM storage.** The reference implementation
enforces WORM at the Python API layer; production-grade deployments wire
the backend to an underlying substrate that enforces WORM at the storage
layer — Amazon S3 Object Lock in Compliance mode, Azure Blob Immutable
Storage with legal hold, IBM FlashSystem WORM tier, or an on-prem appliance
independently assessed against 17a-4(f). The Python-layer enforcement is
necessary-but-not-sufficient; the substrate-layer enforcement is what the
FINRA examiner samples. The `SubstrateAttestation` field carries the
underlying-storage configuration (Object Lock mode, retention duration,
legal-hold state, DTP identifier) on every append, so a question like
"prove the underlying bucket was in Compliance-mode Object Lock on the day
this entry was written" is answered from the chain rather than from a
separately-maintained ops document.

---

## Records Destruction and Tombstoning

After the retention period expires (and absent a litigation hold), records
destruction is the deployer's operational responsibility. The
`WORMLedgerStore` supports a `tombstone(sequence, destruction_certificate)`
path that records the destruction event as an audit-chain entry without
removing the chain-link itself — the entry's hash still participates in
the chain, but its payload is replaced with a destruction-certificate
reference. This preserves chain-verification continuity across destruction
events. The firm's records-management function owns the destruction
certificate substance; the pattern supplies the chain integration.

---

## What This Mapping Does NOT Cover

- **17a-3 record-creation requirements.** This document maps retention,
  not creation. The firm's books-and-records function defines which 17a-3
  records flow through the audit ledger.
- **Investment Adviser recordkeeping (Rule 204-2).** Substantively
  similar retention regime under the Investment Advisers Act; distinct
  authority. The WORMLedgerStore retention model maps; the citation does
  not.
- **Designated Third Party filing.** The firm's records-management
  function files the DTP undertaking with FINRA; the pattern records which
  DTP covers a given entry but does not file on the firm's behalf.
- **CFTC recordkeeping (17 C.F.R. § 1.31).** Co-resident obligation for
  FCM and swap-dealer registrants; substantively similar substrate
  requirements; distinct authority and distinct examination process.
- **State-law parallels** (e.g., NYDFS Part 504 for transaction monitoring
  records, state blue-sky retention overlays).
- **Substrate certification.** Third-party 17a-4(f) attestation (Cohasset
  Associates and similar) remains the deployer's procurement decision.

---

## Gap Analysis

| Concern | Gap | Guidance |
|---|---|---|
| 17a-4(f) substrate certification | Pattern provides API contract and substrate-attestation hook; third-party certification is procurement | Engage 17a-4(f) assessor; record certificate identifier in `SubstrateAttestation` |
| DTP undertaking filing | Pattern records DTP identifier; firm files undertaking | Owned by records-management function |
| 17a-4(b) record-class mapping | Pattern enforces a single retention floor; firm maps each 17a-3 record class to the correct floor | Firm's books-and-records policy; pattern enforces the longest floor configured |
| Litigation hold | Pattern never expires below configured floor; legal-hold escalation extends the floor | Owned by legal / records-management; substrate-attestation field carries hold state |
| Physical-records retention | 17a-4 covers both electronic and physical; pattern covers electronic only | Firm's records-management owns physical retention |
| Records destruction certificate substance | Pattern integrates the certificate reference; substance owned by records function | Records-management policy |

---

## References

- 17 C.F.R. § 240.17a-4 — Records to be preserved by certain exchange
  members, brokers and dealers. Retrieved 2026-05-28 via Cornell LII;
  eCFR returned a 302 redirect on direct fetch.
- 17 C.F.R. § 240.17a-3 — Records to be made by certain exchange members,
  brokers and dealers.
- SEC Release 34-96034 — Electronic Recordkeeping Requirements (Oct 12,
  2022). `[UNVERIFIED — primary source not fetched]`
- FINRA Rule 4511 — books and records cross-reference. `[UNVERIFIED —
  primary source not fetched]`
- ADR-0013 · SEC Rule 17a-4 WORM Persistence for the Audit Chain.
- ADR-0014 · Persistence / Witness / Timestamp Protocol.
- ADR-0003 · Hash-Chain Audit.
- ADR-0017 · Audit-Chain Retention, Privilege, and Discovery.
- Cross-references: ADR-0012 (SOX 404 ITGC — Computer Operations row
  cross-references this mapping), ADR-0008 (GLBA Safeguards — disposal
  envelope), ADR-0011 (BSA / AML — SAR records retention).
