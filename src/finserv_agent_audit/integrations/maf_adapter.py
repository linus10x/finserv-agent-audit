"""Microsoft Agent Framework (MAF) audit adapter — ADR-0029.

The Microsoft Agent Framework reached v1.0 GA on April 2026 as the
production successor to AutoGen (now in maintenance mode) and the
Semantic Kernel agent layer. MAF unifies the two into one framework
with native interop for the Agent2Agent (A2A) Protocol and the Model
Context Protocol (MCP). For any Azure-anchored FSI customer it is the
default agentic-runtime surface.

What this adapter does
----------------------
``MAFAuditAdapter`` wraps the host application's MAF agent / workflow
surface and emits one ``AuditEvent`` per:

  - **Conversation event** — message-received, message-sent, agent
    started, agent stopped, escalation, error.
  - **Tool call** — every framework-dispatched tool invocation with
    a payload summary that never carries raw arguments (the operator
    decides what to hash and surface).
  - **Workflow step** — MAF workflow-orchestrated stages with status.
  - **Cross-protocol interop event** — A2A or MCP message exchange
    flowing through MAF's native interop surface. The audit chain
    captures the cross-protocol envelope so a regulator inquiring
    about a cross-organization (A2A) or external-context (MCP) event
    can reconstruct the call graph without subpoenaing the peer.

The adapter is import-guarded behind ``HAS_MAF`` so the base wheel
keeps the zero-runtime-dependency contract (ADR D2.2 / ADR-0029). To
enable::

    pip install finserv-agent-audit[maf]

When ``audit_chain=None`` every ``record_*`` call is a graceful no-op.

Sovereign-veto wiring
---------------------
A ``SovereignVeto`` may be injected at construction. When wired, every
``record_*`` call checks ``veto.allow_execution()`` BEFORE writing to
the audit chain; a held veto raises ``VetoBlockedError``. The
pre-write order is deliberate — a vetoed agent must not be able to
quietly log into the chain past the veto.

FSI use case
------------
An Azure-anchored bank running a MAF-orchestrated customer-service
agent that calls a cross-organization KYC service over A2A and reads
a fee-schedule policy over MCP wires the adapter at every event
boundary. The audit chain then carries a unified replay across all
three surfaces — useful for the OCC's 2026 third-party-orchestration
expectations and the EU AI Act Article 14 human-oversight evidence.

References
----------
- agent-framework on PyPI: https://pypi.org/project/agent-framework/
- MAF 1.0 GA announcement (April 2026).
- A2A Protocol: https://github.com/a2aproject/A2A
- MCP Protocol: https://modelcontextprotocol.io
- ADR-0029 (this adapter), ADR-0027 (A2A), ADR-0002 (Sovereign Veto).

> Patterns are software, not legal advice. Regulatory citations in
> ADR-0029 are reference mappings; consult counsel for applicability
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
    import agent_framework as _maf

    HAS_MAF = True
    _MAF_MODULE: Any = _maf
except ImportError:
    HAS_MAF = False
    _MAF_MODULE = None


# --------------------------------------------------------------------------- #
# Veto + chain seams                                                          #
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
# MAF event taxonomy                                                          #
# --------------------------------------------------------------------------- #


class MAFEventKind(Enum):
    """Structural-event taxonomy for MAF audit emission."""

    MESSAGE_RECEIVED = "message_received"
    MESSAGE_SENT = "message_sent"
    TOOL_CALL = "tool_call"
    WORKFLOW_STEP = "workflow_step"
    AGENT_STARTED = "agent_started"
    AGENT_STOPPED = "agent_stopped"
    ESCALATION = "escalation"
    ERROR = "error"
    INTEROP = "interop"


class MAFInteropProtocol(Enum):
    """Cross-protocol interop surface MAF natively bridges."""

    A2A = "a2a"
    MCP = "mcp"


def _raise_veto_blocked() -> None:
    """Raise ``VetoBlockedError`` without forcing an import cycle."""
    from finserv_agent_audit.governance.sovereign_veto import VetoBlockedError

    raise VetoBlockedError(
        "MAF action blocked by sovereign veto; clear the veto with an "
        "authorized operator before retrying."
    )


# --------------------------------------------------------------------------- #
# Adapter                                                                     #
# --------------------------------------------------------------------------- #


class MAFAuditAdapter:
    """Capture MAF conversation / tool-call / workflow / interop events.

    Usage::

        from finserv_agent_audit.governance.audit_chain import AuditChain
        from finserv_agent_audit.integrations.maf_adapter import (
            MAFAuditAdapter,
            MAFEventKind,
            MAFInteropProtocol,
        )

        chain = AuditChain(log_file=Path("maf_audit.jsonl"))
        adapter = MAFAuditAdapter(audit_chain=chain, agent_id="bank:cs-agent")

        # In your MAF agent's event handler:
        adapter.record_conversation_event(
            conversation_id=conv.id,
            kind=MAFEventKind.MESSAGE_RECEIVED,
            summary={"role": "user", "len": len(text)},
        )
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
    # Conversation events                                                #
    # ------------------------------------------------------------------ #

    def record_conversation_event(
        self,
        *,
        conversation_id: str,
        kind: MAFEventKind,
        summary: dict[str, Any] | None = None,
        actor_id: str | None = None,
    ) -> AuditEvent | None:
        """Record a generic MAF conversation event."""
        self._check_veto()
        if self._chain is None:
            return None
        payload: dict[str, Any] = {
            "maf_event_kind": kind.value,
            "conversation_id": conversation_id,
        }
        if summary is not None:
            payload["summary"] = summary
        return self._chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=self.autonomy_level,
            agent_id=self.agent_id,
            payload=payload,
            actor_id=actor_id,
        )

    # ------------------------------------------------------------------ #
    # Tool calls                                                         #
    # ------------------------------------------------------------------ #

    def record_tool_call(
        self,
        *,
        conversation_id: str,
        tool_name: str,
        arguments_summary: dict[str, Any] | None = None,
        actor_id: str | None = None,
    ) -> AuditEvent | None:
        """Record a framework-dispatched tool call."""
        self._check_veto()
        if self._chain is None:
            return None
        payload: dict[str, Any] = {
            "maf_event_kind": MAFEventKind.TOOL_CALL.value,
            "conversation_id": conversation_id,
            "tool_name": tool_name,
        }
        if arguments_summary is not None:
            payload["arguments_summary"] = arguments_summary
        return self._chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=self.autonomy_level,
            agent_id=self.agent_id,
            payload=payload,
            actor_id=actor_id,
        )

    # ------------------------------------------------------------------ #
    # Workflow steps                                                     #
    # ------------------------------------------------------------------ #

    def record_workflow_step(
        self,
        *,
        workflow_id: str,
        step_name: str,
        status: str,
        extra: dict[str, Any] | None = None,
        actor_id: str | None = None,
    ) -> AuditEvent | None:
        """Record a workflow-orchestrator step transition."""
        self._check_veto()
        if self._chain is None:
            return None
        payload: dict[str, Any] = {
            "maf_event_kind": MAFEventKind.WORKFLOW_STEP.value,
            "workflow_id": workflow_id,
            "step_name": step_name,
            "status": status,
        }
        if extra:
            payload.update(extra)
        return self._chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=self.autonomy_level,
            agent_id=self.agent_id,
            payload=payload,
            actor_id=actor_id,
        )

    # ------------------------------------------------------------------ #
    # Cross-protocol interop (A2A + MCP)                                 #
    # ------------------------------------------------------------------ #

    def record_interop_event(
        self,
        *,
        protocol: MAFInteropProtocol,
        conversation_id: str,
        peer_id: str,
        summary: dict[str, Any] | None = None,
        actor_id: str | None = None,
    ) -> AuditEvent | None:
        """Record an A2A or MCP interop event flowing through MAF."""
        self._check_veto()
        if self._chain is None:
            return None
        payload: dict[str, Any] = {
            "maf_event_kind": MAFEventKind.INTEROP.value,
            "interop_protocol": protocol.value,
            "conversation_id": conversation_id,
            "peer_id": peer_id,
        }
        if summary is not None:
            payload["summary"] = summary
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
    """Print a one-line status report. Safe whether or not MAF is present."""
    print(f"MAFAuditAdapter demo: HAS_MAF={HAS_MAF}")
    if not HAS_MAF:
        print("  agent-framework not installed.")
        print("  Install with: pip install finserv-agent-audit[maf]")
        print("  No-op mode active when audit_chain=None.")
        return
    print("  agent-framework import succeeded.")
    print("  Wire MAFAuditAdapter into your MAF agent's event handler.")


if __name__ == "__main__":
    _run_demo()


__all__ = [
    "HAS_MAF",
    "MAFAuditAdapter",
    "MAFEventKind",
    "MAFInteropProtocol",
]
