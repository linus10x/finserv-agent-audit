"""A2A (Agent2Agent) protocol audit adapter — ADR-0027.

The Agent2Agent (A2A) Protocol was donated to the Linux Foundation in 2025
and crossed >150 production-deployment organizations by April 2026, with
SDKs across Python, JavaScript, Java, Go, and .NET. FSI was named a
production-deployment vertical in the LF announcement. The protocol
defines a JSON-RPC + Server-Sent-Events surface for one agent (the
"client") to invoke another agent (the "server") over HTTP, exchanging
messages tied to a long-running ``task`` whose lifecycle covers
``created -> updated -> input-required -> completed | cancelled |
failed``.

What this adapter does
----------------------
``A2AAuditAdapter`` wraps the host application's A2A surface — either an
A2A server (your agent receiving cross-organization invocations) or an
A2A client (your agent calling another organization's agent) — and emits
one ``AuditEvent`` per task-lifecycle transition AND one
``AuditEvent`` per message exchange. The adapter is deliberately
transport-agnostic: the caller resolves the A2A SDK event into the
adapter's ``A2ATaskState`` enum and message-classification string, and
the adapter routes the result into the framework's hash-chained audit
ledger.

The adapter does NOT subclass or monkey-patch any A2A SDK type. The
A2A SDK is import-guarded behind ``HAS_A2A`` so the base wheel keeps
the zero-runtime-dependency contract (ADR D2.2 / ADR-0027). To enable::

    pip install finserv-agent-audit[a2a]

When ``HAS_A2A`` is False or the caller passes ``audit_chain=None``
every ``record_*`` call is a graceful no-op.

Sovereign-veto wiring
---------------------
A ``SovereignVeto`` may be injected at construction. When wired, every
task-event and message-exchange call checks ``veto.allow_execution()``
BEFORE writing to the audit chain; a held veto raises
``VetoBlockedError``. The pre-write order is deliberate — the veto is
the operator-side kill switch, and a vetoed agent must not be able to
quietly log into the chain past the veto.

FSI use case
------------
A bank running an A2A-exposed compliance agent serves cross-organization
invocations from broker-dealers, custodians, and counterparties. Every
inbound task and every outbound response sits in the operator-side
audit chain with the A2A task_id, peer_agent_id, and
message-classification fields named explicitly so a regulator inquiring
about a cross-organization decision can reconstruct the message graph
without subpoenaing the counterparty's logs.

References
----------
- Agent2Agent Protocol (Linux Foundation): https://github.com/a2aproject/A2A
- a2a-sdk on PyPI: https://pypi.org/project/a2a-sdk/
- ADR-0027 (this adapter) and ADR-0002 (Sovereign Veto)

> Patterns are software, not legal advice. Regulatory citations in
> ADR-0027 are reference mappings; consult counsel for applicability to
> the cross-organization invocation surface in your jurisdiction.
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
    import a2a as _a2a

    HAS_A2A = True
    _A2A_MODULE: Any = _a2a
except ImportError:
    HAS_A2A = False
    _A2A_MODULE = None


# --------------------------------------------------------------------------- #
# Veto seam — narrow Protocol so we don't hard-import SovereignVeto here     #
# --------------------------------------------------------------------------- #


class _VetoLike(Protocol):
    """Minimal veto surface used by every v2.0 runtime adapter."""

    def allow_execution(self) -> bool: ...


# --------------------------------------------------------------------------- #
# AuditChain seam — narrow Protocol matching AuditChain.append signature      #
# --------------------------------------------------------------------------- #


class _ChainLike(Protocol):
    """Minimal chain surface used by every v2.0 runtime adapter."""

    def append(
        self,
        event_type: AuditEventType,
        autonomy_level: AutonomyLevel,
        agent_id: str,
        payload: dict[str, Any],
        actor_id: str | None = None,
    ) -> AuditEvent: ...


# --------------------------------------------------------------------------- #
# A2A task-lifecycle enum                                                     #
# --------------------------------------------------------------------------- #


class A2ATaskState(Enum):
    """A2A task lifecycle states recorded into the audit chain.

    Mirrors the canonical A2A task lifecycle. The adapter does not
    require the caller to use the SDK's own state objects — the
    operator resolves the SDK event into this enum so the audit chain
    sees a stable, framework-version-independent label.
    """

    CREATED = "created"
    UPDATED = "updated"
    INPUT_REQUIRED = "input_required"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


# --------------------------------------------------------------------------- #
# Veto-blocked exception (locally raised; mirrors SovereignVeto's contract)   #
# --------------------------------------------------------------------------- #


def _raise_veto_blocked() -> None:
    """Raise ``VetoBlockedError`` without forcing an import cycle.

    Imported lazily so the integrations subpackage can stay decoupled
    from ``governance.sovereign_veto`` at module-import time.
    """
    from finserv_agent_audit.governance.sovereign_veto import VetoBlockedError

    raise VetoBlockedError(
        "A2A action blocked by sovereign veto; clear the veto with an "
        "authorized operator before retrying."
    )


# --------------------------------------------------------------------------- #
# Adapter                                                                     #
# --------------------------------------------------------------------------- #


class A2AAuditAdapter:
    """Capture A2A task-lifecycle and message events into the audit chain.

    Usage (host A2A server)::

        from finserv_agent_audit.governance.audit_chain import AuditChain
        from finserv_agent_audit.integrations.a2a_adapter import (
            A2AAuditAdapter,
            A2ATaskState,
        )

        chain = AuditChain(log_file=Path("a2a_audit.jsonl"))
        adapter = A2AAuditAdapter(audit_chain=chain, agent_id="bank:compliance-agent")

        # In your A2A request handler:
        adapter.record_task_event(
            task_id=request.task_id,
            state=A2ATaskState.CREATED,
            message_classification="suitability-check",
        )

    Usage (with Sovereign-Veto wired)::

        veto = SovereignVeto(agent_id="bank:compliance-agent")
        adapter = A2AAuditAdapter(
            audit_chain=chain,
            agent_id="bank:compliance-agent",
            veto=veto,
        )
        # Every record_* call now checks veto.allow_execution() first.
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
    # Task lifecycle                                                     #
    # ------------------------------------------------------------------ #

    def record_task_event(
        self,
        *,
        task_id: str,
        state: A2ATaskState,
        message_classification: str,
        extra: dict[str, Any] | None = None,
        actor_id: str | None = None,
    ) -> AuditEvent | None:
        """Record an A2A task-state transition. Veto-checked first."""
        self._check_veto()
        if self._chain is None:
            return None
        payload: dict[str, Any] = {
            "a2a_task_id": task_id,
            "a2a_state": state.value,
            "message_classification": message_classification,
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
    # Message exchange                                                   #
    # ------------------------------------------------------------------ #

    def record_message(
        self,
        *,
        task_id: str,
        peer_agent_id: str,
        direction: str,
        message_classification: str,
        payload_size: int | None = None,
        extra: dict[str, Any] | None = None,
        actor_id: str | None = None,
    ) -> AuditEvent | None:
        """Record a single A2A message exchange (inbound or outbound)."""
        self._check_veto()
        if self._chain is None:
            return None
        if direction not in ("inbound", "outbound"):
            raise ValueError(
                f"A2A message direction must be 'inbound' or 'outbound'; got {direction!r}"
            )
        payload: dict[str, Any] = {
            "a2a_task_id": task_id,
            "a2a_peer_agent_id": peer_agent_id,
            "a2a_direction": direction,
            "message_classification": message_classification,
        }
        if payload_size is not None:
            payload["payload_size"] = payload_size
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
    # Internal                                                           #
    # ------------------------------------------------------------------ #

    def _check_veto(self) -> None:
        if self._veto is not None and not self._veto.allow_execution():
            _raise_veto_blocked()


# --------------------------------------------------------------------------- #
# Demo                                                                        #
# --------------------------------------------------------------------------- #


def _run_demo() -> None:
    """Print a one-line status report. Safe whether or not a2a-sdk is present."""
    print(f"A2AAuditAdapter demo: HAS_A2A={HAS_A2A}")
    if not HAS_A2A:
        print("  a2a-sdk not installed.")
        print("  Install with: pip install finserv-agent-audit[a2a]")
        print("  No-op mode active when audit_chain=None.")
        return
    print("  a2a-sdk import succeeded.")
    print("  Wire A2AAuditAdapter(audit_chain=chain, agent_id='...') in your server.")


if __name__ == "__main__":
    _run_demo()


__all__ = [
    "A2AAuditAdapter",
    "A2ATaskState",
    "HAS_A2A",
]
