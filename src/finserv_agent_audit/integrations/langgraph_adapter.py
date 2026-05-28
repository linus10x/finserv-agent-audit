"""LangGraph audit callback adapter — ADR-0028.

LangGraph v1.0 GA shipped in late 2025 and is in production at Klarna
(serving ~85M users), Uber, LinkedIn, and AppFolio. It is the
graph-execution layer most commonly chosen for multi-step LLM
orchestration with checkpointed state. The framework's primitives —
nodes, edges, channels, checkpoints — map cleanly to audit-chain
provenance: every node-entry is a decision, every edge-traversal is a
control-flow transition, every channel update is a state change, every
checkpoint is a recoverable snapshot.

What this adapter does
----------------------
``LangGraphAuditCallback`` is a callback object the host application
wires into its LangGraph graph as a node-entry / node-exit hook. Each
hook method captures one structural event and emits one
``AuditEvent`` to the framework's hash-chained audit ledger.

The adapter does NOT subclass LangGraph's own callback base because the
project's stdlib-only contract forbids importing the framework at the
module level. The caller resolves the LangGraph callback signature into
the adapter's hook arguments — a thin layer the host application owns.

LangGraph is import-guarded behind ``HAS_LANGGRAPH`` so the base wheel
keeps the zero-runtime-dependency contract (ADR D2.2 / ADR-0028). To
enable::

    pip install finserv-agent-audit[langgraph]

When ``audit_chain=None`` every ``on_*`` call is a graceful no-op.

Sovereign-veto wiring
---------------------
A ``SovereignVeto`` may be injected at construction. When wired, every
``on_*`` call checks ``veto.allow_execution()`` BEFORE writing to the
audit chain; a held veto raises ``VetoBlockedError`` so the graph
runtime halts at the next node-entry boundary. The pre-write order is
deliberate — the veto is the operator-side kill switch, and a vetoed
graph must not be able to quietly log into the chain past the veto.

FSI use case
------------
A wealth-management firm running a LangGraph orchestration that calls
out to a fraud-score vendor, a KYC vendor, and a robo-advisor signal
vendor in sequence wires the adapter at every node boundary. The audit
chain then carries a node-by-node replay of the orchestration — useful
for both the SR 11-7 model-validation evidence stream AND the FFIEC IT
Examination Handbook expectations on third-party orchestration logging.

References
----------
- LangGraph (GitHub): https://github.com/langchain-ai/langgraph
- LangGraph 1.0 release notes (late 2025).
- ADR-0028 (this adapter) and ADR-0002 (Sovereign Veto).

> Patterns are software, not legal advice. Regulatory citations in
> ADR-0028 are reference mappings; consult counsel for applicability
> to your control environment.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Protocol

from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)

try:
    import langgraph as _langgraph

    HAS_LANGGRAPH = True
    _LANGGRAPH_MODULE: Any = _langgraph
except ImportError:
    HAS_LANGGRAPH = False
    _LANGGRAPH_MODULE = None


# --------------------------------------------------------------------------- #
# Veto seam                                                                   #
# --------------------------------------------------------------------------- #


class _VetoLike(Protocol):
    def allow_execution(self) -> bool: ...


class _ChainLike(Protocol):
    def append(
        self,
        event_type: AuditEventType,
        autonomy_level: AutonomyLevel,
        agent_id: str,
        payload: dict[str, Any],
        actor_id: str | None = None,
    ) -> AuditEvent: ...


# --------------------------------------------------------------------------- #
# LangGraph structural-event taxonomy                                         #
# --------------------------------------------------------------------------- #


class LangGraphEventKind(Enum):
    """Structural-event taxonomy for LangGraph audit emission.

    The five kinds cover the entire structural surface of a LangGraph
    run: node lifecycle (start/end), edge traversal, channel-level
    state transitions, and checkpoint emission.
    """

    NODE_START = "node_start"
    NODE_END = "node_end"
    EDGE = "edge"
    STATE_TRANSITION = "state_transition"
    CHECKPOINT = "checkpoint"


def _raise_veto_blocked() -> None:
    """Raise ``VetoBlockedError`` without forcing an import cycle."""
    from finserv_agent_audit.governance.sovereign_veto import VetoBlockedError

    raise VetoBlockedError(
        "LangGraph node entry blocked by sovereign veto; clear the veto "
        "with an authorized operator before retrying."
    )


# --------------------------------------------------------------------------- #
# Callback                                                                    #
# --------------------------------------------------------------------------- #


class LangGraphAuditCallback:
    """Capture LangGraph node-lifecycle, edge, state, and checkpoint events.

    Usage::

        from finserv_agent_audit.governance.audit_chain import AuditChain
        from finserv_agent_audit.integrations.langgraph_adapter import (
            LangGraphAuditCallback,
        )

        chain = AuditChain(log_file=Path("lg_audit.jsonl"))
        cb = LangGraphAuditCallback(audit_chain=chain, agent_id="bank:orchestrator")

        # Wire cb.on_node_start / on_node_end / on_edge_traversal /
        # on_state_transition / on_checkpoint into your LangGraph
        # callback dispatch.

    Usage (with Sovereign-Veto)::

        veto = SovereignVeto(agent_id="bank:orchestrator")
        cb = LangGraphAuditCallback(
            audit_chain=chain,
            agent_id="bank:orchestrator",
            veto=veto,
        )
        # Every on_* call checks veto.allow_execution() first; a held
        # veto halts the graph at the next node boundary.
    """

    DEFAULT_AUTONOMY_LEVEL = AutonomyLevel.A2

    def __init__(
        self,
        audit_chain: _ChainLike | None,
        agent_id: str,
        *,
        veto: _VetoLike | None = None,
        autonomy_level: AutonomyLevel = DEFAULT_AUTONOMY_LEVEL,
    ) -> None:
        self._chain = audit_chain
        self.agent_id = agent_id
        self._veto = veto
        self.autonomy_level = autonomy_level

    # ------------------------------------------------------------------ #
    # Node lifecycle                                                     #
    # ------------------------------------------------------------------ #

    def on_node_start(
        self,
        *,
        node_name: str,
        run_id: str,
        inputs_summary: dict[str, Any] | None = None,
        actor_id: str | None = None,
    ) -> AuditEvent | None:
        """Record a node-entry event. Veto-checked first."""
        self._check_veto()
        if self._chain is None:
            return None
        payload: dict[str, Any] = {
            "langgraph_event_kind": LangGraphEventKind.NODE_START.value,
            "node_name": node_name,
            "run_id": run_id,
        }
        if inputs_summary is not None:
            payload["inputs_summary"] = inputs_summary
        return self._chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=self.autonomy_level,
            agent_id=self.agent_id,
            payload=payload,
            actor_id=actor_id,
        )

    def on_node_end(
        self,
        *,
        node_name: str,
        run_id: str,
        output_summary: dict[str, Any] | None = None,
        actor_id: str | None = None,
    ) -> AuditEvent | None:
        """Record a node-exit event. Veto-checked first."""
        self._check_veto()
        if self._chain is None:
            return None
        payload: dict[str, Any] = {
            "langgraph_event_kind": LangGraphEventKind.NODE_END.value,
            "node_name": node_name,
            "run_id": run_id,
        }
        if output_summary is not None:
            payload["output_summary"] = output_summary
        return self._chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=self.autonomy_level,
            agent_id=self.agent_id,
            payload=payload,
            actor_id=actor_id,
        )

    # ------------------------------------------------------------------ #
    # Edges, state transitions, checkpoints                              #
    # ------------------------------------------------------------------ #

    def on_edge_traversal(
        self,
        *,
        from_node: str,
        to_node: str,
        run_id: str,
        actor_id: str | None = None,
    ) -> AuditEvent | None:
        """Record an edge traversal between two nodes."""
        self._check_veto()
        if self._chain is None:
            return None
        payload: dict[str, Any] = {
            "langgraph_event_kind": LangGraphEventKind.EDGE.value,
            "from_node": from_node,
            "to_node": to_node,
            "run_id": run_id,
        }
        return self._chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=self.autonomy_level,
            agent_id=self.agent_id,
            payload=payload,
            actor_id=actor_id,
        )

    def on_state_transition(
        self,
        *,
        run_id: str,
        channel: str,
        updates_summary: dict[str, Any] | None = None,
        actor_id: str | None = None,
    ) -> AuditEvent | None:
        """Record a state-channel update (LangGraph channel-write)."""
        self._check_veto()
        if self._chain is None:
            return None
        payload: dict[str, Any] = {
            "langgraph_event_kind": LangGraphEventKind.STATE_TRANSITION.value,
            "channel": channel,
            "run_id": run_id,
        }
        if updates_summary is not None:
            payload["updates_summary"] = updates_summary
        return self._chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=self.autonomy_level,
            agent_id=self.agent_id,
            payload=payload,
            actor_id=actor_id,
        )

    def on_checkpoint(
        self,
        *,
        run_id: str,
        checkpoint_id: str,
        thread_id: str | None = None,
        actor_id: str | None = None,
    ) -> AuditEvent | None:
        """Record a checkpoint emission. Checkpoints are recoverable snapshots."""
        self._check_veto()
        if self._chain is None:
            return None
        payload: dict[str, Any] = {
            "langgraph_event_kind": LangGraphEventKind.CHECKPOINT.value,
            "checkpoint_id": checkpoint_id,
            "run_id": run_id,
        }
        if thread_id is not None:
            payload["thread_id"] = thread_id
        return self._chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=self.autonomy_level,
            agent_id=self.agent_id,
            payload=payload,
            actor_id=actor_id,
        )

    # ------------------------------------------------------------------ #
    # Internal                                                           #
    # ------------------------------------------------------------------ #

    def _check_veto(self) -> None:
        if self._veto is not None and not self._veto.allow_execution():
            _raise_veto_blocked()


# --------------------------------------------------------------------------- #
# Demo                                                                        #
# --------------------------------------------------------------------------- #


def _run_demo() -> None:
    """Print a one-line status report. Safe whether or not langgraph is present."""
    print(f"LangGraphAuditCallback demo: HAS_LANGGRAPH={HAS_LANGGRAPH}")
    if not HAS_LANGGRAPH:
        print("  langgraph not installed.")
        print("  Install with: pip install finserv-agent-audit[langgraph]")
        print("  No-op mode active when audit_chain=None.")
        return
    print("  langgraph import succeeded.")
    print("  Wire LangGraphAuditCallback hooks into your graph's callback dispatch.")


if __name__ == "__main__":
    _run_demo()


__all__ = [
    "HAS_LANGGRAPH",
    "LangGraphAuditCallback",
    "LangGraphEventKind",
]
