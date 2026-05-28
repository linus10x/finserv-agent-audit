# ADR-0028 · LangGraph Audit Callback Adapter

**Status:** Accepted (shipped in v2.0)
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit v2.0

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel for jurisdiction-specific applicability. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

---

## Context

LangGraph v1.0 shipped GA in late 2025 from the LangChain team as a low-level orchestration framework for stateful multi-actor LLM applications. Production references named in the GA announcement include Klarna (serving ~85M users), Uber, LinkedIn, and AppFolio. By May 2026 the package was on version 1.2.2 (released May 26, 2026), with continued production traction in financial services and customer-service orchestration.

LangGraph's core abstractions are nodes (units of compute), edges (control-flow transitions, conditional or static), channels (named state slots updated by node returns), and checkpoints (recoverable snapshots of channel state at a step boundary). The framework is among the most-deployed orchestration layers for multi-step LLM workflows that require state persistence, conditional branching, and human-in-the-loop interruption — the exact shape an FSI agent serving a multi-step compliance review or a multi-step customer-onboarding flow takes.

For an FSI operator running a LangGraph orchestration, the audit posture is structural. Every node-entry is a model decision; every edge-traversal is a control-flow choice; every state-channel update is a state mutation; every checkpoint is a recoverable snapshot the bank can replay. The SR 11-7 model-validation expectations and the FFIEC IT Examination Handbook expectations on third-party orchestration logging both assume the bank has a node-by-node replay of the orchestration. LangGraph's own observability surface (LangSmith) is a vendor surface; the bank's audit chain is the system of record.

The gap this ADR closes: there is no first-party adapter binding LangGraph's structural events into `finserv_agent_audit`'s hash-chained audit ledger. Without it, the bank rolls its own callback dispatcher and gets the autonomy-level + veto wiring wrong, or relies on LangSmith and ships without an operator-side chain of custody.

## Decision

Ship `LangGraphAuditCallback` in v2.0 as the operator-side capture layer between the host application's LangGraph graph and the framework's `AuditChain`. The callback is intentionally NOT a subclass of LangGraph's own callback base — the base wheel's zero-runtime-dependency contract forbids importing the framework at module level. The host application's callback dispatcher resolves LangGraph callback signatures into the adapter's hook arguments.

### Surface

```python
from finserv_agent_audit.governance.audit_chain import AuditChain
from finserv_agent_audit.integrations.langgraph_adapter import (
    LangGraphAuditCallback,
)

chain = AuditChain(log_file=Path("lg_audit.jsonl"))
cb = LangGraphAuditCallback(audit_chain=chain, agent_id="bank:orchestrator")

# Wire cb.on_node_start / on_node_end / on_edge_traversal /
# on_state_transition / on_checkpoint into your LangGraph callback
# dispatch.
```

### Five hook methods

- `on_node_start(node_name, run_id, inputs_summary=None, actor_id=None)`
- `on_node_end(node_name, run_id, output_summary=None, actor_id=None)`
- `on_edge_traversal(from_node, to_node, run_id, actor_id=None)`
- `on_state_transition(run_id, channel, updates_summary=None, actor_id=None)`
- `on_checkpoint(run_id, checkpoint_id, thread_id=None, actor_id=None)`

Each emits one `AuditEvent` with `event_type=DECISION_MADE`, the autonomy level configured on the callback, and a payload carrying `langgraph_event_kind` (a `LangGraphEventKind` enum value) plus the hook-specific fields.

### Sovereign-Veto wiring

The callback accepts an optional `veto: SovereignVeto`. When wired, every hook checks `veto.allow_execution()` BEFORE writing to the audit chain. A held veto raises `VetoBlockedError`, halting the graph at the next node-entry boundary. The pre-write order is deliberate — a vetoed graph must not be able to quietly log into the chain past the veto.

### Import-guard

The `langgraph` dependency is import-guarded behind `HAS_LANGGRAPH`. Adopters opt in with `pip install finserv-agent-audit[langgraph]`.

### Optional dependency pin

`langgraph>=1.0` (verified against PyPI on May 28, 2026; current version 1.2.2). The 1.0 floor pins the GA-stable API surface — pre-1.0 LangGraph reshaped the callback contract repeatedly.

## Alternatives Considered

1. **Subclass `BaseCallbackHandler` from LangGraph.** Rejected — the base wheel cannot import `langgraph` without violating the zero-runtime-dependency contract. The host application is the right boundary for the SDK-shaped subclassing.
2. **Capture only node-start + node-end (skip edges, state, checkpoints).** Rejected — the regulator inquiring about a conditional branch will want the edge-traversal evidence; the auditor inquiring about a recoverable snapshot will want the checkpoint evidence. Coverage of the full structural surface is the value.
3. **Auto-instrument LangGraph via monkey-patching.** Rejected — monkey-patching upstream framework internals breaks across upstream versions and produces a maintenance burden that compounds with every LangGraph point release. The explicit hook surface is the stable contract.
4. **Capture full node-inputs / node-outputs in the audit chain.** Rejected — payload sensitivity is the operator's call. The adapter accepts optional `inputs_summary` / `output_summary` dicts; the host application decides what to surface.

## Consequences

**Positive.** A v2.0 bank running a LangGraph orchestration gets a node-by-node, edge-by-edge, checkpoint-by-checkpoint replay in its hash-chained audit ledger. The Klarna / Uber / LinkedIn / AppFolio production pattern is repeatable with regulator-grade evidence. The `SovereignVeto` wiring gives the bank a kill switch that interrupts the graph at the next node boundary — the EU AI Act Article 14 human-oversight obligation operationalized at the orchestration layer.

**Negative.** The callback is only as complete as the host's dispatch wiring. A host that wires `on_node_start` but forgets `on_node_end` ships a chain with half the lifecycle. Mitigation: the README example covers the full dispatch; the test suite exercises every hook.

**Architectural.** The adapter introduces no new persistence, no new network call, and no new runtime dependency on the base install. It composes onto the existing `AuditChain` (ADR-0003) and the optional `SovereignVeto` (ADR-0002) Protocol seam. No changes to `schemas/audit_event.py`.

## Regulatory Mapping

- SR 11-7 (Supervisory Guidance on Model Risk Management) — Section IV (Model Validation) — orchestration-step replay is part of the model-validation evidence stream.
- OCC Bulletin 2013-29 + 2026-13 — third-party risk management for the framework dependency itself; the adapter records the per-node decisions the framework dispatched.
- FFIEC IT Examination Handbook — third-party operational dependencies + logging expectations.
- EU AI Act Article 12 (logging capabilities) + Article 14 (human oversight) — the per-node logging and the `SovereignVeto` wiring respectively.
- finserv-agent-audit ADR-0002 (Sovereign Veto), ADR-0003 (Hash-Chained Audit Ledger), ADR-0004 (Autonomy Ladder A0-A4), ADR-0017 (Audit-Chain Retention, Privilege & Discovery).

## Pre-mortem

The failure mode this ADR prevents: a wealth-management firm shipping a LangGraph-orchestrated suitability-check flow can answer the next SR 11-7 model-validation inquiry with a per-node replay showing inputs, decisions, and edge-traversal evidence.

The failure mode this ADR creates if mishandled: a buyer wires `on_node_start` only, the chain shows node-entries without exits, and the inferred outcome is the wrong one. Mitigation: the README example wires the full hook set; the test suite exercises every kind; `LangGraphEventKind` is an enum so the missing kinds are visible at the call site.

## Reversibility

Reversible. The five-hook surface is the contract; the payload schema (`langgraph_event_kind` + the hook-specific fields) is the load-bearing piece. A future ADR could collapse hooks or add new ones (e.g., `on_human_interrupt` for the human-in-the-loop pause primitive LangGraph ships) — additive changes are non-breaking.

## Cross-references

- ADR-0002 (Sovereign Veto) — the kill switch the callback wires into for pre-write veto checks.
- ADR-0003 (Hash-Chained Audit Ledger) — the substrate the callback's events land on.
- ADR-0004 (Autonomy Ladder A0-A4) — the autonomy-level wiring on every hook.
- ADR-0027 (A2A Adapter), ADR-0029 (MAF Adapter), ADR-0030 (CrewAI Adapter) — peer agentic-runtime adapters shipped in v2.0.

---

*Patterns are software, not legal advice. Regulatory citations are reference mappings; consult counsel for applicability to your control environment.*
