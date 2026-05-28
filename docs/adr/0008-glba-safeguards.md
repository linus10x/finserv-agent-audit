# ADR-0008 · GLBA Safeguards Rule — Customer NPI Partitioning

**Status:** Accepted · FSI-native
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel. No attorney-client relationship is formed by use of this ADR. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

## Context

A financial-services AI program touches **customer non-public personal information (NPI)** on every meaningful workflow: account opening, transaction monitoring, credit-decision support, marketing personalization, retention scoring, complaint triage. Under the GLBA Safeguards Rule as revised by the FTC effective June 9, 2023 (16 C.F.R. Part 314), a covered "financial institution" is required to maintain a written information-security program with nine designated elements — including risk assessment, access controls, encryption of customer NPI in transit and at rest, multi-factor authentication for systems containing customer NPI, change management, and **periodic monitoring of system activity by authorized users including a means of detecting unauthorized access to or use of customer information**. The 2023 revision added a 30-day notice-of-incident obligation to the FTC for security events affecting ≥500 consumers (16 C.F.R. § 314.5).

An autonomous-agent stack changes the meaning of "authorized user." If an LLM-backed agent reads a customer's NPI to draft a retention email, the agent is the user-of-record on that read. If the agent reads twenty customers' NPI to compose an aggregate insight, the read fan-out is not visible to a conventional access-control system designed for human session boundaries. The conventional "we encrypt customer NPI" answer is necessary and insufficient: the Safeguards Rule asks not only whether the data was protected in motion but whether each access was **authorized, monitored, and recorded for the specific purpose for which it was used**.

The pattern that works is **NPI partitioning at the storage layer, agent-boundary gating on every NPI read, and per-read purpose tagging recorded on the audit chain.**

## Decision

Customer NPI is segregated at the storage layer behind a `CustomerNPIStore` interface. Every read by an agent must carry an `NPIAccessIntent` carrying the requesting actor's identity-provider-verified principal, the specific business purpose, and the named GLBA element under which the read is authorized. The `GLBASafeguardsGate` runs ahead of any agent action that touches the store; vetoes fire under the sovereign-veto pattern (ADR-0002) and entries are recorded on the hash-chain audit ledger (ADR-0003).

### The data model

```python
class GLBAElement(Enum):
    ACCESS_CONTROL = "314.4(c)(1)"
    DATA_INVENTORY = "314.4(c)(2)"
    ENCRYPTION = "314.4(c)(3)"
    SECURE_DEV = "314.4(c)(4)"
    MFA = "314.4(c)(5)"
    DISPOSAL = "314.4(c)(6)"
    CHANGE_MGMT = "314.4(c)(7)"
    MONITORING = "314.4(c)(8)"
    INCIDENT_RESPONSE = "314.4(h)"

@dataclass(frozen=True)
class NPIAccessIntent:
    requesting_actor: str            # identity-provider-verified principal
    actor_kind: ActorKind            # HUMAN | AGENT | BATCH_JOB
    purpose: str                     # specific use case · not "analytics"
    glba_element: GLBAElement        # the named authorization basis
    mfa_proof_id: str | None         # required when actor_kind == HUMAN
    record_ids: tuple[str, ...]      # explicit · no wildcard reads
```

### The Safeguards veto

Vetoes fire on any of:

1. **`GLBA-PURPOSE-VAGUE`** — `purpose` matches the generic-purpose blocklist (e.g., "analytics", "operations", "improvement").
2. **`GLBA-RECORD-WILDCARD`** — the read carries no enumerated `record_ids` or the count exceeds the per-actor per-window ceiling (default: 1,000 records per agent per hour, calibrated per program).
3. **`GLBA-MFA-MISSING`** — `actor_kind == HUMAN` without an attached MFA proof.
4. **`GLBA-ENCRYPTION-DOWNGRADE`** — the response would be routed through a transport or sink that does not meet the encryption-in-motion or encryption-at-rest standard recorded in the data-inventory map.
5. **`GLBA-INCIDENT-WINDOW`** — the program is in incident-response state and the read is not on the incident-response allowlist.

### Aggregation rule

Aggregate reads across customers (e.g., a portfolio-wide attrition-risk dashboard) require either anonymization at the gate (the aggregator receives only counts and bucketed ratios, never per-customer rows) or a documented blanket authorization signed by the Qualified Individual designated under 16 C.F.R. § 314.4(a). The default is anonymization.

## Alternatives Considered

- **Per-table column encryption only.** Insufficient — encryption protects data at rest but does not satisfy 16 C.F.R. § 314.4(c)(8) monitoring of authorized-user access, and provides no per-read audit record.
- **DLP scanning on egress.** Necessary as a backstop but reactive; the agent has already composed the read. The Safeguards Rule expectation is **prevention plus monitoring**, not detection-after-the-fact.
- **Token vault with field-level masking only.** Useful for analytics on de-identified fields but does not address the agent's need for re-identified NPI on legitimate workflows (e.g., a retention email must address the customer by name).

## Consequences

**Positive.** Every NPI access is authorized against a named Safeguards element, tagged to a specific business purpose, attributable to an identity-provider-verified principal, and recorded immutably on the audit chain. A regulator inquiry under the Safeguards Rule can be answered by query: "show me every NPI read on customer X in the prior 90 days, the actor, the purpose, and the authorization element." Incident-response timing (30-day FTC notification for ≥500-consumer events) is supported by a single audit-chain scan rather than a forensic reconstruction.

**Negative.** Latency on every NPI-touching action. Mitigated by in-process caching of authorization decisions for 60 seconds on the same `(actor, purpose, glba_element)` triple, with force-invalidation on any DEFCON transition (ADR-0001).

**Architectural.** Agents cannot bypass by reading "the database directly" — the `CustomerNPIStore` is the only path, and the gate is in front of it.

## Regulatory Mapping

- **GLBA, 15 U.S.C. § 6801 et seq.** — statutory foundation; financial institutions shall protect customer NPI.
- **Safeguards Rule, 16 C.F.R. Part 314 (FTC, revised June 9, 2023).** § 314.4(c)(1) access controls; § 314.4(c)(3) encryption; § 314.4(c)(5) MFA; § 314.4(c)(8) monitoring of authorized-user activity — the `NPIAccessIntent` per-read record is the operational artifact this gate produces to evidence § 314.4(c)(8) compliance for agent activity.
- **§ 314.4(h) Incident Response.** The `GLBA-INCIDENT-WINDOW` veto state is the operational arm of the program's written incident-response plan.
- **§ 314.5 Notice of security events.** 30-day FTC notification for events affecting ≥500 consumers; the audit chain supplies the affected-record count without a forensic project.
- **Interagency parallel.** Federal banking-agency Safeguards expectations under 12 C.F.R. Part 30 App. B (OCC), 12 C.F.R. Part 208 App. D-2 (FRB), 12 C.F.R. Part 364 App. B (FDIC) — substantively parallel where a covered institution is bank-regulated rather than FTC-regulated. `[UNVERIFIED — primary source not fetched]` on exact citation numbers; verify before publication.

## Pre-mortem

The way this gate fails is **purpose-inflation**: agents and engineers cycle a small number of approved purposes to bypass the specificity requirement. Mitigation: the audit chain is sampled monthly by Compliance; purpose-string entropy is a monitored metric; a purpose string that recurs on >5% of reads is treated as a blocklist candidate.

The other failure mode is **wildcard creep**: the per-actor-per-window record ceiling gets raised under operational pressure. Mitigation: ceiling raises require GC sign-off and are themselves audit-chain entries with a 90-day review.

## Reversibility

High. The `CustomerNPIStore` interface is a wrapper; the underlying storage is unchanged. The gate can be disabled by configuration in an incident — but the disable is itself an audit-chain entry, and the program drops to DEFCON-3 (ADR-0001) for the duration.

## Cross-references

- ADR-0001 (DEFCON State Machine) — gate-disable triggers DEFCON-3
- ADR-0002 (Sovereign Veto) — the enforcement layer
- ADR-0003 (Hash-chain Audit) — every read and every exception is recorded
- ADR-0009 (FCRA/Reg V Adverse Action) — adverse-action reason-code reads are GLBA-gated
- ADR-0010 (ECOA/Reg B Fair Lending) — protected-class screening reads are GLBA-gated
- ADR-0011 (BSA/AML SAR Workflow) — SAR-narrative reads are GLBA-gated with elevated purpose specificity

## Implementation status

**Deferred to Tranche 2C.** The reference implementation lands at `src/finserv_agent_audit/governance/glba_safeguards_gate.py`. This ADR is the design contract; the module is not yet committed.
