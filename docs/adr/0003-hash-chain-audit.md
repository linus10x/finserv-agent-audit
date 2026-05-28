# ADR-0003: Internally-Consistent Hash-Chained Audit Ledger

**Status:** Accepted
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel. No attorney-client relationship is formed by use of this ADR. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

---

## Context

A regulator inquiring about an FSI-AI decision twelve to eighty-four months after the fact (SEC 17a-4 retention windows for broker-dealer books-and-records run three to six years; some categories run permanently) needs an answer that does not depend on whether the agent code, the prompt, the model weights, or the operator's intentions have changed in the interim. The answer must be a record that was true when the decision was made and cannot have been tampered with since.

Standard application logging is insufficient. Logs are mutable. Logs are deletable. Logs are reconstructable in ways that survive scrutiny by an adversarial third party. A FINRA examiner asking "show me every order this agent generated for symbol X across this trading day" or a CFPB examiner asking "show me every adverse-action notice this credit-decisioning agent emitted in Q2 against the applicant population" needs a stronger guarantee than "trust the log file."

## Decision

Adopt a **hash-chain audit ledger** — every decision event is appended to a chain in which each entry contains the SHA-256 hash of the previous entry. Tampering with any entry invalidates every entry that follows. Periodic anchor checkpoints write the chain head to an external durable system. Reference implementation: `src/finserv_agent_audit/governance/ledger_store.py` (in-memory), `ledger_store_jsonl.py` (filesystem), `ledger_store_sqlite.py` (Postgres-class durability via SQLite reference).

```python
@dataclass(frozen=True)
class AuditEntry:
    sequence: int                       # monotonically increasing
    timestamp: datetime
    actor_kind: ActorKind               # AGENT | HUMAN | SYSTEM
    actor_id: str
    decision_type: str                  # order · credit-decision · kyc-clear · transition · ...
    action_payload: bytes               # the decision itself, structured
    gate_verdicts: dict[str, str]       # which gates ran, what they returned
    prior_hash: str                     # sha256(prior entry)
    self_hash: str                      # sha256(this entry minus self_hash)
```

The ledger is append-only. Reads are by sequence number, by actor, by decision type, by time window, or by cross-referenced entity (customer ID, order ID, account ID). The ledger does **not** support deletion or in-place edits. A correction is a new entry that references the prior entry's sequence with `decision_type = "correction"`.

Anchor checkpoints are external. Every 1,000 entries or 24 hours (whichever comes first) the current chain head hash is written to a separate durable system — in the reference repo this is a configurable backend (filesystem · S3 Object Lock · DynamoDB conditional writes · Postgres with row-level immutability via constraints).

## Tamper-DETECTING vs Tamper-EVIDENCE — Critical Distinction

This pattern produces **tamper-detecting** evidence within a trust boundary. It does **not**, on its own, produce **tamper-evident** evidence in the adversarial-witness sense the regulator may require. The distinction matters and is load-bearing:

- **Tamper-detecting (what this pattern provides).** Within a single deployment, any modification to a past entry breaks the SHA-256 chain at the modified point and every entry downstream. `verify_chain()` returns the first broken sequence. This is sufficient to detect a careless modification, a partial-corruption incident, or an internal-actor edit that did not also regenerate the chain.

- **Tamper-evident (what requires an external witness; see ADR-0014).** Against an attacker with full write access to the ledger host, an internal hash-chain alone is insufficient — the attacker can regenerate the entire chain end-to-end and the regenerated chain is internally consistent. Producing tamper-evidence in the adversarial sense requires an **external witness**: periodic publication of `chain_head()` to an independent append-only register (RFC 3161 trusted timestamps, OpenTimestamps, Sigstore Rekor, a regulator-side log, a notarized public blockchain anchor). With the external witness in place, the deployer can prove post-incident what the chain head was at time T — and any regenerated chain whose head at T does not match the witnessed head is detectably forged.

ADR-0014 covers the external-witness pattern. ADR-0003 explicitly does NOT claim adversarial tamper-evidence on its own. Use the framing *"internally-consistent hash-chained ledger; tamper-evident when anchored to [external witness]"* in any external assertion. Any public claim of tamper-evidence without the witness anchor is overclaim and is a documented banned framing.

## Alternatives Considered

1. **Application logs to ELK/Splunk only.** Rejected. Logs are mutable by anyone with write access to the index. A FINRA examiner asking for evidence of non-tampering will not accept "Splunk is configured to be append-only" without the cryptographic chain.
2. **Database with audit columns (created_at, updated_at, updated_by).** Rejected. Audit columns are themselves mutable rows; a privileged actor can edit a past row and update the audit columns. No cryptographic guarantee.
3. **Public-blockchain-per-decision.** Rejected as primary backend. Latency, cost, and PII-on-chain concerns are disqualifying. Blockchain is acceptable as a periodic-anchor witness (see ADR-0014) but not as the per-decision storage layer.

## Consequences

**Positive.** Internally consistent by construction. Regulator-reconstructable decision history is a one-query operation. Disputes between firm and counterparty can be resolved by reading the ledger, not by re-litigating intent — *provided the deployer has implemented persistence and external witness anchoring per ADR-0014.*

**Negative.** Storage cost grows linearly with decision volume. At realistic FSI scale (a single mid-size broker-dealer with algorithmic execution can generate millions of decision events per trading day) the chain grows to terabytes per year — manageable but non-trivial. Rotation policy: chains are partitioned by trading day or by week, anchor checkpoints carry the prior partition's terminal hash, and historical partitions can be cold-stored under SEC 17a-4 WORM (Write Once Read Many) requirements.

**Architectural.** Every gate verdict — DEFCON, Sovereign Veto, Autonomy Ladder, Shadow Mode router — is captured on every entry. A veto'd action is a ledger entry as full as an executed action. The ledger is the record of what was *considered*, not just what was *done*.

## Regulatory Mapping

- **SEC Rule 17a-4** (17 CFR § 240.17a-4) — broker-dealer books-and-records retention requirements; WORM storage requirement for electronic records under 17a-4(f). [UNVERIFIED — primary source not fetched]
- **EU AI Act Article 12** (Regulation (EU) 2024/1689) — automatic logging of events relevant to identifying risks for high-risk AI systems; retention "appropriate to the intended purpose" of the system, minimum six months unless otherwise required. [UNVERIFIED — primary source not fetched]
- **EU AI Act Article 19** — log-keeping obligations for providers of high-risk AI systems. [UNVERIFIED — primary source not fetched]
- **SOX 404** (Section 404, Sarbanes-Oxley Act of 2002) — IT general controls require audit-trail evidence for financial-reporting systems. [UNVERIFIED — primary source not fetched]
- **GLBA Safeguards Rule** (16 CFR Part 314) — written information-security program; audit-trail integrity is part of the safeguards expectation. [UNVERIFIED — primary source not fetched]
- **SOC 2 Trust Services Criteria CC7.2** (system operations monitoring) — application-control level: every consequential decision logged with reason, owner, and timestamp.
- **NIST AI RMF** GOVERN 1.1 — accountability mechanisms documented.

## Pre-mortem

- **In-memory-only persistence in v0.2.0 means a process crash loses the chain.** Mitigation — pluggable persistence backends (`ledger_store_sqlite.py`, `ledger_store_jsonl.py`) ship as the production path; in-memory is reference-only.
- **Local-clock timestamps are not trusted-time.** Timestamps come from `datetime.now(timezone.utc)`. Mitigation — RFC 3161 codec (`rfc3161_codec.py`) ships for trusted-timestamp integration; deployers select a TSA (FreeTSA, DigiCert, internal).
- **External witness anchoring is operationally easy to forget.** Mitigation — `chain_head()` is exposed as a first-class method; a deployer cron or sidecar publishes the head on a fixed schedule and the publication itself is a ledger entry.
- **PII in the action_payload field creates a GDPR / GLBA erase-on-request collision with the append-only ledger.** Mitigation — payload should be a structured reference (account-id hash, decision-id) plus content-addressed pointer; PII storage is in a separate, redactable system. The ledger holds the proof, not the PII. This is a deployer-side discipline; the pattern does not enforce it.

## Reversibility

The ledger itself is append-only and not reversible (this is the point). The choice of backend is reversible — a deployer can migrate from JSONL to SQLite to Postgres by replaying the chain. The choice to anchor externally is reversible going forward but not retroactively: an anchor not made at time T cannot be made later for time T. Persistence-backend selection is durable; backend swap requires a chain-migration script.

## Cross-references

- **Implementation:** `src/finserv_agent_audit/governance/ledger_store.py` · `ledger_store_jsonl.py` · `ledger_store_sqlite.py` · `rfc3161_codec.py`
- **Schema:** `src/finserv_agent_audit/schemas/audit_event.py`
- **Tests:** `tests/test_ledger_store.py` · `tests/test_rfc3161_codec.py`
- **Related ADRs:** ADR-0001 (DEFCON, every transition writes an entry) · ADR-0002 (Sovereign Veto, every veto writes an entry) · ADR-0004 (Autonomy Ladder, A2→A3 promotion requires ≥90 days of ledger history) · **ADR-0014 (External-Witness Anchoring, required for adversarial tamper-evidence)**
