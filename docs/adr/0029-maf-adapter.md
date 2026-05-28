# ADR-0029 · Microsoft Agent Framework (MAF) Audit Adapter

**Status:** Accepted (shipped in v2.0)
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit v2.0

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel for jurisdiction-specific applicability. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

---

## Context

The Microsoft Agent Framework (MAF) reached v1.0 GA in April 2026 as the production-grade successor to AutoGen (now in maintenance mode) and the Semantic Kernel agent layer. The PyPI package `agent-framework` was on version 1.7.0 by May 28, 2026, reflecting a fast post-GA cadence. MAF unifies the AutoGen multi-agent model and the Semantic Kernel skill-orchestration model into one framework with native interop for the Agent2Agent (A2A) Protocol and the Model Context Protocol (MCP).

For any Azure-anchored FSI customer — which is to say a large fraction of the US bank, insurance, and capital-markets fleet — MAF is the default agentic-runtime surface. The framework ships in the Azure AI Foundry path, integrates with Microsoft Entra (formerly AAD) identity, runs on AKS and Azure Container Apps, and emits OpenTelemetry by default. The bank that has standardized on Azure for the rest of the stack will reach for MAF first when the agent project starts.

MAF's primitives are agents, conversations, tool calls, and workflows. The interop surface is the bridge — an agent in a MAF workflow can call out to an A2A peer (cross-organization) or pull context from an MCP server (external context source) without leaving the framework. The audit posture has to follow all four: conversation events for the per-message provenance, tool calls for the framework-dispatched actions, workflow steps for the orchestration-stage record, and cross-protocol interop events so the call graph does not stop at the framework boundary.

The gap this ADR closes: there is no first-party adapter binding MAF's event surface into `finserv_agent_audit`'s hash-chained audit ledger. Without it, the Azure-anchored bank either relies on the OTel emission MAF ships (which is not the operator-side system of record) or rolls its own callback wrapper and loses the cross-protocol fidelity.

## Decision

Ship `MAFAuditAdapter` in v2.0 as the operator-side capture layer between the host application's MAF agents / workflows and the framework's `AuditChain`. The adapter exposes four `record_*` methods covering the four MAF event surfaces.

### Surface

```python
from finserv_agent_audit.governance.audit_chain import AuditChain
from finserv_agent_audit.integrations.maf_adapter import (
    MAFAuditAdapter,
    MAFEventKind,
    MAFInteropProtocol,
)

chain = AuditChain(log_file=Path("maf_audit.jsonl"))
adapter = MAFAuditAdapter(audit_chain=chain, agent_id="bank:cs-agent")

# Per-message:
adapter.record_conversation_event(
    conversation_id=conv.id,
    kind=MAFEventKind.MESSAGE_RECEIVED,
    summary={"role": "user", "len": len(text)},
)

# Per-tool-call:
adapter.record_tool_call(
    conversation_id=conv.id,
    tool_name="lookup_account",
    arguments_summary={"account_id_hash": h},
)

# Per-workflow-step:
adapter.record_workflow_step(
    workflow_id=wf.id,
    step_name="risk_check",
    status="completed",
)

# Per-A2A or MCP interop event:
adapter.record_interop_event(
    protocol=MAFInteropProtocol.A2A,
    conversation_id=conv.id,
    peer_id="counterparty:agent-7",
    summary={"task_id": peer_task_id},
)
```

### Cross-protocol interop

The `MAFInteropProtocol` enum names the two surfaces MAF natively bridges: `A2A` (cross-organization agent invocation) and `MCP` (external context source). The audit chain captures the cross-protocol envelope so a regulator inquiring about a cross-organization decision or an external-context retrieval can reconstruct the call graph without subpoenaing the peer.

### Sovereign-Veto wiring

The adapter accepts an optional `veto: SovereignVeto`. When wired, every `record_*` call checks `veto.allow_execution()` BEFORE writing to the audit chain. A held veto raises `VetoBlockedError`. The pre-write order is deliberate.

### Import-guard

The `agent-framework` dependency is import-guarded behind `HAS_MAF`. Adopters opt in with `pip install finserv-agent-audit[maf]`.

### Optional dependency pin

`agent-framework>=1.0` (verified against PyPI on May 28, 2026; current version 1.7.0). The 1.0 floor pins the GA release; the April 2026 GA event is the operative version boundary for an FSI production deployment.

## Alternatives Considered

1. **Rely on MAF's native OpenTelemetry emission as the audit source.** Rejected — OTel is the analyst-facing read path (and is well-served by `OTELGenAIEmitter` in the same `integrations/` package); the audit chain is the system of record. The two have different durability and tamper-detection (hash-chain mechanism) profiles. The audit chain is the regulator-facing surface; OTel is the operator's debugging surface.
2. **Subclass MAF's own agent base.** Rejected — the base wheel cannot import MAF without violating the zero-runtime-dependency contract.
3. **Capture only the conversation + tool-call surfaces (skip workflow + interop).** Rejected — workflows are how MAF orchestrates multi-stage flows, and interop is the cross-protocol bridge. Skipping either leaves the regulator inquiring about a multi-stage cross-organization decision without a chain replay.
4. **Combine A2A + MCP interop into one event kind.** Rejected — the two protocols carry different regulatory weight. A2A is a cross-organization call (third-party / fourth-party risk); MCP is an external context source (potentially privileged content, ADR-0017 implications). The enum keeps them distinguishable on the chain.

## Consequences

**Positive.** A v2.0 Azure-anchored bank running a MAF agent gets a unified replay across conversation, tool-call, workflow, and cross-protocol interop surfaces in its hash-chained audit ledger. The April 2026 GA inflection is the production wave; the adapter ships into that wave with the regulator-grade evidence the FSI buyer will demand.

**Negative.** The adapter introduces a fourth event-kind enum (`MAFEventKind`) and a second protocol enum (`MAFInteropProtocol`) to the integrations surface. The audit-chain payload schema grows accordingly. Mitigation: the enum values are stable strings; the payload schema is documented in the module docstring and exercised in the test suite.

**Architectural.** The adapter introduces no new persistence and no new network call beyond what MAF already does. It composes onto the existing `AuditChain` (ADR-0003) and the optional `SovereignVeto` (ADR-0002). It interoperates with `A2AAuditAdapter` (ADR-0027) for the A2A side of the interop surface — both record the same A2A task_id, allowing the operator to reconcile a single A2A invocation across both adapters when both are wired.

## Regulatory Mapping

- SR 11-7 (Supervisory Guidance on Model Risk Management) — Section IV (Model Validation) — workflow-step and tool-call evidence is part of the model-validation stream.
- OCC Bulletin 2013-29 + 2026-13 — third-party risk management; the `interop_protocol` + `peer_id` fields are the audit-chain handle for the third-party (A2A) and external-context (MCP) dependencies.
- FFIEC IT Examination Handbook — third-party operational dependencies + logging expectations.
- EU AI Act Article 12 (logging) + Article 14 (human oversight) — the per-event logging and the `SovereignVeto` wiring respectively.
- DORA Article 28 + RTS 2024/1773 — third-party ICT risk + fourth-party disclosure; the A2A peer and the MCP context source are both DORA-relevant third parties.
- NYDFS Part 500 (Cybersecurity Requirements for Financial Services Companies) — third-party service-provider security; the audit chain is the institution's evidence of monitoring the third-party agent surface.
- finserv-agent-audit ADR-0002 (Sovereign Veto), ADR-0003 (Hash-Chained Audit Ledger), ADR-0017 (Audit-Chain Retention, Privilege & Discovery).

## Pre-mortem

The failure mode this ADR prevents: an Azure-anchored bank shipping a MAF agent that participates in an A2A graph AND pulls context from MCP can answer the next regulator inquiry with a unified chain replay across conversation, tool-call, workflow, and cross-protocol surfaces.

The failure mode this ADR creates if mishandled: a buyer wires `record_conversation_event` and `record_tool_call` but forgets `record_interop_event`. The chain shows the MAF-internal events but is silent on the cross-protocol calls; the regulator asks about the A2A peer's contribution and the bank cannot answer from its own chain. Mitigation: the README example covers the full surface; the test suite exercises every kind including both interop protocols.

## Reversibility

Reversible. The four `record_*` methods are the contract; the payload schema (`maf_event_kind` + the event-specific fields + `interop_protocol` for interop events) is the load-bearing piece. A future ADR could add new event kinds (e.g., `agent_started` / `agent_stopped` lifecycle events with dedicated methods rather than the generic `record_conversation_event`) — additive changes are non-breaking.

## Cross-references

- ADR-0002 (Sovereign Veto) — the kill switch the adapter wires into for pre-write veto checks.
- ADR-0003 (Hash-Chained Audit Ledger) — the substrate the adapter's events land on.
- ADR-0017 (Audit-Chain Retention, Privilege & Discovery) — retention schedule and privilege classification for the chain entries the adapter emits.
- ADR-0027 (A2A Adapter) — the peer adapter for the A2A side of the interop surface.
- ADR-0028 (LangGraph Adapter), ADR-0030 (CrewAI Adapter) — peer agentic-runtime adapters shipped in v2.0.

---

*Patterns are software, not legal advice. Regulatory citations are reference mappings; consult counsel for applicability to your control environment.*
