# ADR-0027 · A2A (Agent2Agent) Protocol Audit Adapter

**Status:** Accepted (shipped in v2.0)
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit v2.0

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel for jurisdiction-specific applicability. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

---

## Context

The Agent2Agent (A2A) Protocol was originated by Google in early 2025 and donated to the Linux Foundation later that year. By April 2026 the LF announced >150 production-deployment organizations spanning Python, JavaScript, Java, Go, and .NET SDKs, with financial services named as one of the production-deployment verticals. The protocol's GitHub repository (`a2aproject/A2A`) had crossed 22K stars by the same window.

A2A defines a JSON-RPC + Server-Sent-Events surface over HTTP for one agent (the "client") to invoke another agent (the "server"). The protocol's core abstraction is the **task** — a long-running unit of work whose lifecycle covers `created -> updated -> input-required -> completed | cancelled | failed`, with messages exchanged at every transition. A2A makes cross-organization agent invocation a real production surface: a bank's compliance agent can be invoked by a broker-dealer's risk agent over A2A; a custodian's settlement agent can call out to a counterparty's KYC agent over A2A.

For an FSI operator, the audit posture must follow the call graph. The bank that exposes an A2A endpoint to a counterparty needs an audit-chain record of every inbound task and every outbound response — both for the SR 11-7 model-validation evidence stream and for the OCC's 2026 expectations around third-party orchestration logging. The signal a regulator inquiring into a cross-organization agent decision will demand is the task_id, the peer_agent_id, the message-classification, and the autonomy level at which the bank's side made its decision. None of that is on the wire by default; the bank's side has to capture it.

The gap this ADR closes: there is no first-party adapter binding A2A's task-lifecycle events into `finserv_agent_audit`'s hash-chained audit ledger. Without it, the bank either rolls its own boilerplate (and gets the autonomy-level wiring wrong) or ships the agent without an audit trail (and answers a regulator inquiry with the counterparty's logs, which is the wrong system of record).

## Decision

Ship `A2AAuditAdapter` in v2.0 as the operator-side capture layer between an A2A SDK (host application's choice — `a2a-sdk` on Python, `a2a-js` on Node, etc.) and the framework's `AuditChain`. The adapter is transport-agnostic — the caller resolves the SDK's own task-state object into the adapter's `A2ATaskState` enum (`created | updated | input_required | completed | cancelled | failed`) and message-classification string, and the adapter emits one `AuditEvent` per call.

### Surface

```python
from finserv_agent_audit.governance.audit_chain import AuditChain
from finserv_agent_audit.integrations.a2a_adapter import (
    A2AAuditAdapter,
    A2ATaskState,
)

chain = AuditChain(log_file=Path("a2a_audit.jsonl"))
adapter = A2AAuditAdapter(audit_chain=chain, agent_id="bank:compliance-agent")

# In your A2A server's request handler:
adapter.record_task_event(
    task_id=request.task_id,
    state=A2ATaskState.CREATED,
    message_classification="suitability-check",
)

# At every message boundary:
adapter.record_message(
    task_id=request.task_id,
    peer_agent_id=request.from_agent,
    direction="inbound",
    message_classification="suitability-question",
    payload_size=len(request.body),
)
```

### Sovereign-Veto wiring

The adapter accepts an optional `veto: SovereignVeto`. When wired, every `record_*` call checks `veto.allow_execution()` BEFORE writing to the audit chain. A held veto raises `VetoBlockedError` so the host's A2A handler short-circuits at the next event boundary. The pre-write order is the contract — a vetoed agent must not be able to quietly log into the chain past the veto.

### Import-guard

The `a2a-sdk` dependency is import-guarded behind `HAS_A2A`. The base wheel stays zero-runtime-dependency (ADR D2.2). Adopters opt in with `pip install finserv-agent-audit[a2a]`.

### Optional dependency pin

`a2a-sdk>=1.0` (verified against PyPI on May 28, 2026; current version 1.0.3 released May 13, 2026). The 1.0 floor pins the first SDK release with stable typing on the Task / Message / Agent surfaces the adapter wraps.

## Alternatives Considered

1. **Subclass the A2A SDK's own request-handler base.** Rejected — the base wheel cannot import the SDK without violating the zero-runtime-dependency contract. The host application is the right boundary for the SDK-shaped subclassing; the adapter is the right boundary for the audit-chain emission.
2. **Auto-capture A2A events via an HTTP middleware proxy.** Rejected — the bank does not always control the HTTP layer (sidecar mesh, hosted-A2A surface). The adapter binds at the SDK event boundary so it works regardless of the underlying transport.
3. **Emit per-message events only (skip task lifecycle).** Rejected — the regulator will want both the message graph AND the task-lifecycle replay. Tasks are the SR 11-7 unit of validation; messages are the supporting evidence.
4. **Capture full message payloads in the audit chain.** Rejected — payload classification is the operator's call (some payloads are privileged under ADR-0017; some carry PII subject to GLBA). The adapter records a `message_classification` string and an optional `payload_size`; the operator decides what to hash and surface.

## Consequences

**Positive.** A v2.0 bank exposing an A2A endpoint can wire the adapter in five lines and ship with the audit-chain provenance a regulator inquiry will demand. The cross-organization invocation graph becomes queryable from the bank's own chain — no subpoena to the counterparty required. The autonomy-level wiring is centralized in the adapter rather than scattered across the host's A2A handlers.

**Negative.** The adapter is only as complete as the call-site instrumentation. A host that wires `record_task_event` only at `CREATED` (and forgets the other states) ships a chain with task-start events and no task-completion events — the gap is invisible until a regulator asks for a task's outcome. Mitigation: the README and the `A2ATaskState` enum are explicit about the full lifecycle; the test suite exercises every state.

**Architectural.** The adapter introduces no new persistence and no new network call beyond what the A2A SDK already does. It composes onto the existing `AuditChain` (ADR-0003) and on the optional `SovereignVeto` (ADR-0002) Protocol seam. No changes to `schemas/audit_event.py` — the adapter emits `DECISION_MADE` events whose payload carries the A2A-specific fields (`a2a_task_id`, `a2a_state`, `a2a_peer_agent_id`, `a2a_direction`, `message_classification`).

## Regulatory Mapping

- SR 11-7 (Supervisory Guidance on Model Risk Management) — Section IV.5 (Documentation) — cross-organization model invocations are model events; the audit chain is the bank-side documentation surface.
- OCC Bulletin 2013-29 + 2026-13 — third-party risk management; A2A peer agents are third parties for the OCC's purposes, and the adapter's `peer_agent_id` field is the audit-chain handle the bank's TPRM team uses.
- FFIEC IT Examination Handbook — third-party operational dependencies; A2A makes the dependency surface programmatic, and the adapter makes the dependency observable.
- EU AI Act Article 12 — logging capabilities for high-risk AI systems; the adapter is the call-site implementation of the logging obligation when the bank's high-risk agent participates in an A2A graph.
- EU AI Act Article 14 — human oversight; the `SovereignVeto` wiring is the human-oversight kill switch operationalized at the A2A boundary.
- DORA Article 28 (third-party ICT risk) — cross-organization agent invocation is an ICT third-party dependency; the adapter is the dependency observability surface.
- finserv-agent-audit ADR-0002 (Sovereign Veto), ADR-0003 (Hash-Chained Audit Ledger), ADR-0017 (Audit-Chain Retention, Privilege & Discovery).

## Pre-mortem

The failure mode this ADR prevents: a buyer reads the v2.0 README, sees A2A named as a first-class runtime, wires the adapter at every event boundary in the A2A handler, and the next cross-organization decision inquiry can be answered with a chain replay showing the task lifecycle, the peer agent, and the bank's autonomy level at every step.

The failure mode this ADR creates if mishandled: a buyer wires the adapter at task creation only, never at completion, and the chain shows tasks starting but never resolving. The buyer believes the chain is complete because every task they can see has a CREATED entry; the regulator asks for the COMPLETED entries and the gap surfaces under inquiry. Mitigation: the adapter's docstring and this ADR are explicit about lifecycle completeness; the test suite exercises every state; the example wiring in the README covers the full lifecycle.

## Reversibility

Reversible. The adapter's surface is `record_task_event` + `record_message`; the payload schema (`a2a_task_id` + `a2a_state` + `message_classification` + `a2a_peer_agent_id` + `a2a_direction`) is the load-bearing contract. A future ADR could replace the adapter with a different shim (for example, a different A2A SDK that ships first-party callbacks) while preserving the payload schema — that is a non-breaking change.

## Cross-references

- ADR-0002 (Sovereign Veto) — the kill switch the adapter wires into for pre-write veto checks.
- ADR-0003 (Hash-Chained Audit Ledger) — the substrate the adapter's events land on.
- ADR-0017 (Audit-Chain Retention, Privilege & Discovery) — retention schedule and privilege classification for the chain entries the adapter emits.
- ADR-0028 (LangGraph Adapter), ADR-0029 (MAF Adapter), ADR-0030 (CrewAI Adapter) — peer agentic-runtime adapters shipped in v2.0.

---

*Patterns are software, not legal advice. Regulatory citations are reference mappings; consult counsel for applicability to your control environment.*
