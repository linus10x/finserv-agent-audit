# ADR-0030 · CrewAI Audit Adapter

**Status:** Accepted (shipped in v2.0)
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit v2.0

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel for jurisdiction-specific applicability. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

---

## Context

CrewAI is one of the most-deployed open-source agentic-runtime frameworks in production as of May 2026. The public metrics: 51.4K GitHub stars, 27M+ PyPI downloads on the core package, 150+ named enterprise customers, and over 2 billion agent executions logged in the preceding 12 months. The PyPI package `crewai` was on version 1.14.6 by May 28, 2026.

CrewAI's defining model is `Agent -> Task -> Crew`. Each `Agent` carries a named `role` (e.g. "Senior Researcher", "Compliance Analyst", "Memo Writer") plus a goal and a backstory; each `Task` is a unit of work with a description and an expected output, assigned to a role; each `Crew` aggregates roles + tasks into a single orchestrated run with sequential or hierarchical task delegation. The role-based abstraction is what makes the framework attractive: a research workflow naturally decomposes into a Researcher who reads, an Analyst who reasons, and a Writer who drafts — three roles, three tasks, one crew.

For an FSI operator, the role-based decomposition maps cleanly to two regulatory expectations the audit chain has to satisfy. The first is the SR 11-7 effective-challenge expectation — a model decision should be subjected to challenge by a second model or human; CrewAI's hierarchical-crew pattern (a Manager role coordinating worker roles) is the operational implementation. The second is the audit-chain retention + privilege classification under ADR-0017 — the bank's Compliance Memo (drafted by a Writer role) carries different privilege weight than the Research Notes (produced by a Researcher role), and the audit chain has to surface the role on every entry so the privilege-classification step has the signal it needs.

The gap this ADR closes: there is no first-party adapter binding CrewAI's `Agent -> Task -> Crew` events into `finserv_agent_audit`'s hash-chained audit ledger. Without it, the bank either misses the role-level provenance (and runs every entry under one synthetic `agent_id`) or rolls a custom callback dispatcher and gets the autonomy-level + veto wiring wrong.

## Decision

Ship `CrewAIAuditAdapter` in v2.0 as the operator-side capture layer between the host application's CrewAI crew and the framework's `AuditChain`. The adapter exposes four `record_*` methods covering task lifecycle and crew lifecycle.

### Surface

```python
from finserv_agent_audit.governance.audit_chain import AuditChain
from finserv_agent_audit.integrations.crewai_adapter import (
    CrewAIAuditAdapter,
)

chain = AuditChain(log_file=Path("crewai_audit.jsonl"))
adapter = CrewAIAuditAdapter(audit_chain=chain, crew_id="research-crew")

# Crew kickoff:
adapter.record_crew_kickoff(agent_roles=["Researcher", "Analyst", "Writer"])

# Per task:
adapter.record_task_start(
    task_id=task.id,
    task_description=task.description,
    role=agent.role,
)
adapter.record_task_complete(
    task_id=task.id,
    role=agent.role,
    output_summary={"length": len(task.output), "citations": cite_count},
)

# Crew result:
adapter.record_crew_result(result_summary={"tasks_completed": 3, "total_tokens": 4221})
```

### Role-as-agent-id composition

For task-level events the adapter composes `agent_id` as `"{crew_id}:{role}"` — e.g. `"research-crew:Senior Researcher"`. This is the design decision that distinguishes the CrewAI adapter from the peer adapters: CrewAI's primary unit of identity is the role, and the audit chain has to surface the role directly so the SR 11-7 effective-challenge evidence stream and the ADR-0017 privilege classification can both query on it. Crew-level events (`record_crew_kickoff` / `record_crew_result`) use the bare `crew_id` because there is no single role responsible for the crew-level event.

### Sovereign-Veto wiring

The adapter accepts an optional `veto: SovereignVeto`. When wired, every `record_*` call checks `veto.allow_execution()` BEFORE writing to the audit chain. A held veto raises `VetoBlockedError` so a crew run halts at the next task boundary. The pre-write order is deliberate.

### Import-guard

The `crewai` dependency is import-guarded behind `HAS_CREWAI`. Adopters opt in with `pip install finserv-agent-audit[crewai]`.

### Optional dependency pin

`crewai>=0.140` (verified against PyPI on May 28, 2026; current version 1.14.6). The 0.140 floor pins a pre-1.0 release with the stable `Agent` / `Task` / `Crew` surface the adapter wraps; 1.x continues that surface.

## Alternatives Considered

1. **Use the bare `crew_id` as `agent_id` for every event.** Rejected — that loses the role-level provenance the SR 11-7 effective-challenge stream and the ADR-0017 privilege classification both need. The `crew_id:role` composition for task-level events is the right factoring.
2. **Subclass CrewAI's `Agent` base.** Rejected — the base wheel cannot import `crewai` without violating the zero-runtime-dependency contract. The host application is the right boundary for the SDK-shaped subclassing.
3. **Skip the crew-level events (record only task-level).** Rejected — the regulator inquiring about a crew-aggregated result will want the crew-result entry as the chain's terminal anchor. Skipping it makes the chain's outcome ambiguous.
4. **Capture the raw task output in the chain payload.** Rejected — task outputs can be 10K+ tokens and carry privilege-classified content. The adapter accepts an optional `output_summary` dict; the host application decides what to surface.
5. **Treat the Manager role in a hierarchical crew specially.** Rejected for v2.0 — the role-as-agent-id composition handles the Manager naturally (its role is `"research-crew:Manager"`). A future ADR could add a `MANAGER_DELEGATION` event kind if the hierarchical-crew evidence pattern justifies it.

## Consequences

**Positive.** A v2.0 bank running a CrewAI research crew, compliance crew, or memo-drafting crew gets a role-by-role decomposition in its hash-chained audit ledger. The SR 11-7 effective-challenge evidence stream is queryable directly off the chain. The ADR-0017 privilege classification step has the role-level signal it needs. The 2B-execution production base of CrewAI makes the adapter immediately useful for the FSI operators already on the framework.

**Negative.** The role-as-agent-id composition assumes role names are stable across runs. A crew that renames the Senior Researcher to Lead Researcher mid-flight will produce chain entries under two distinct agent_ids that the operator has to reconcile downstream. Mitigation: the docstring is explicit about the composition rule; the operator owns the role-naming discipline.

**Architectural.** The adapter introduces no new persistence and no new network call beyond what CrewAI already does. It composes onto the existing `AuditChain` (ADR-0003) and the optional `SovereignVeto` (ADR-0002). No changes to `schemas/audit_event.py`.

## Regulatory Mapping

- SR 11-7 (Supervisory Guidance on Model Risk Management) — Section V (Governance, Policies, and Controls) — effective challenge is a named expectation; the role-by-role chain replay is the evidence stream.
- OCC Bulletin 2013-29 + 2026-13 — third-party risk management for the framework dependency.
- FFIEC IT Examination Handbook — third-party operational dependencies + logging expectations.
- EU AI Act Article 12 (logging) + Article 14 (human oversight).
- finserv-agent-audit ADR-0002 (Sovereign Veto), ADR-0003 (Hash-Chained Audit Ledger), ADR-0017 (Audit-Chain Retention, Privilege & Discovery), ADR-0022 (Effective-Challenge Harness — the role-decomposition pattern this adapter operationalizes).

## Pre-mortem

The failure mode this ADR prevents: a bank running a CrewAI compliance-memo crew can answer the next privilege inquiry from counsel with a role-by-role decomposition showing which content originated from the Researcher (likely discoverable), which from the Analyst (work product), and which from the Writer (potentially privileged final-form drafts). The chain surfaces the role on every entry; counsel's classification has the signal it needs.

The failure mode this ADR creates if mishandled: a buyer wires only `record_task_complete` (skips `record_task_start`), and the chain shows outputs without inputs. The "what did the role see before producing this output" question cannot be answered from the chain. Mitigation: the README example wires both task-lifecycle events; the test suite exercises the full pair including the multi-agent crew sequence.

## Reversibility

Reversible. The four `record_*` methods are the contract; the payload schema (`crewai_event_kind` + the event-specific fields + the `crew_id:role` composition for task events) is the load-bearing piece. A future ADR could add `record_manager_delegation` for the hierarchical-crew Manager pattern, or `record_human_input` for the human-in-the-loop input primitive — additive changes are non-breaking.

## Cross-references

- ADR-0002 (Sovereign Veto) — the kill switch the adapter wires into for pre-write veto checks.
- ADR-0003 (Hash-Chained Audit Ledger) — the substrate the adapter's events land on.
- ADR-0017 (Audit-Chain Retention, Privilege & Discovery) — retention schedule and privilege classification; the role surface this adapter exposes is the input to the privilege-classification step.
- ADR-0022 (Effective-Challenge Harness) — the SR 11-7 effective-challenge pattern this adapter operationalizes through the role-by-role decomposition.
- ADR-0027 (A2A Adapter), ADR-0028 (LangGraph Adapter), ADR-0029 (MAF Adapter) — peer agentic-runtime adapters shipped in v2.0.

---

*Patterns are software, not legal advice. Regulatory citations are reference mappings; consult counsel for applicability to your control environment.*
