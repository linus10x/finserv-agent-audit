"""CrewAI audit adapter — ADR-0030.

CrewAI is among the most-deployed open-source agentic-runtime frameworks
in production: 51.4K GitHub stars as of May 2026, 27M+ PyPI downloads on
the core package, 150+ named enterprise customers, and over 2 billion
agent executions logged in the preceding 12 months. The framework's
``Agent -> Task -> Crew`` model maps cleanly to audit-chain provenance:
each ``Agent`` carries a named ``role``, each ``Task`` is a unit of
work assigned to a role, and each ``Crew`` aggregates roles + tasks
into one orchestrated run.

What this adapter does
----------------------
``CrewAIAuditAdapter`` wraps the host application's CrewAI crew and
emits one ``AuditEvent`` per:

  - **Task start** — a role accepting a task description; agent_id is
    composed as ``"{crew_id}:{role}"`` so the role is queryable.
  - **Task complete** — a role producing an output; output is
    summarized into the payload (callers decide what to surface).
  - **Crew kickoff** — the crew starting a run; carries the agent
    roles participating in the run.
  - **Crew result** — the crew aggregated result with a summary.

The adapter is import-guarded behind ``HAS_CREWAI`` so the base wheel
keeps the zero-runtime-dependency contract (ADR D2.2 / ADR-0030). To
enable::

    pip install finserv-agent-audit[crewai]

When ``audit_chain=None`` every ``record_*`` call is a graceful no-op.

Sovereign-veto wiring
---------------------
A ``SovereignVeto`` may be injected at construction. When wired, every
``record_*`` call checks ``veto.allow_execution()`` BEFORE writing to
the audit chain; a held veto raises ``VetoBlockedError`` so a crew run
halts at the next task boundary. The pre-write order is deliberate.

FSI use case
------------
A bank running a CrewAI research crew that pairs a Researcher
(literature review), an Analyst (model-validation pre-flight), and a
Writer (regulator-facing memo draft) wires the adapter at every task
boundary. The audit chain then carries the role-by-role decomposition
of the memo's authorship — useful for the SR 11-7 effective-challenge
evidence stream and for the bank's privilege classification (ADR-0017)
when the memo is later subject to a discovery request.

References
----------
- CrewAI (GitHub): https://github.com/crewAIInc/crewAI
- crewai on PyPI: https://pypi.org/project/crewai/
- ADR-0030 (this adapter) and ADR-0002 (Sovereign Veto).

> Patterns are software, not legal advice. Regulatory citations in
> ADR-0030 are reference mappings; consult counsel for applicability
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
    import crewai as _crewai

    HAS_CREWAI = True
    _CREWAI_MODULE: Any = _crewai
except ImportError:
    HAS_CREWAI = False
    _CREWAI_MODULE = None


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
# CrewAI event taxonomy                                                       #
# --------------------------------------------------------------------------- #


class CrewAIEventKind(Enum):
    """Structural-event taxonomy for CrewAI audit emission."""

    TASK_START = "task_start"
    TASK_COMPLETE = "task_complete"
    CREW_KICKOFF = "crew_kickoff"
    CREW_RESULT = "crew_result"


def _raise_veto_blocked() -> None:
    """Raise ``VetoBlockedError`` without forcing an import cycle."""
    from finserv_agent_audit.governance.sovereign_veto import VetoBlockedError

    raise VetoBlockedError(
        "CrewAI action blocked by sovereign veto; clear the veto with "
        "an authorized operator before retrying."
    )


# --------------------------------------------------------------------------- #
# Adapter                                                                     #
# --------------------------------------------------------------------------- #


class CrewAIAuditAdapter:
    """Capture CrewAI task-start, task-complete, crew-kickoff, crew-result events.

    Usage::

        from finserv_agent_audit.governance.audit_chain import AuditChain
        from finserv_agent_audit.integrations.crewai_adapter import (
            CrewAIAuditAdapter,
        )

        chain = AuditChain(log_file=Path("crewai_audit.jsonl"))
        adapter = CrewAIAuditAdapter(audit_chain=chain, crew_id="research-crew")

        # In your CrewAI Task callback:
        adapter.record_task_start(
            task_id=task.id,
            task_description=task.description,
            role=agent.role,
        )

    Note. ``agent_id`` for task events is composed as
    ``"{crew_id}:{role}"`` so the role is queryable directly off the
    audit chain. Crew-level events use the bare ``crew_id``.
    """

    DEFAULT_AUTONOMY_LEVEL = AutonomyLevel.A2

    def __init__(
        self,
        audit_chain: _ChainLike | None,
        crew_id: str,
        *,
        veto: _VetoLike | None = None,
        autonomy_level: AutonomyLevel = DEFAULT_AUTONOMY_LEVEL,
    ) -> None:
        self._chain = audit_chain
        self.crew_id = crew_id
        self._veto = veto
        self.autonomy_level = autonomy_level

    # ------------------------------------------------------------------ #
    # Task lifecycle                                                     #
    # ------------------------------------------------------------------ #

    def record_task_start(
        self,
        *,
        task_id: str,
        task_description: str,
        role: str,
        extra: dict[str, Any] | None = None,
        actor_id: str | None = None,
    ) -> AuditEvent | None:
        """Record a task-start event. ``role`` becomes part of ``agent_id``."""
        self._check_veto()
        if self._chain is None:
            return None
        payload: dict[str, Any] = {
            "crewai_event_kind": CrewAIEventKind.TASK_START.value,
            "task_id": task_id,
            "task_description": task_description,
            "role": role,
            "crew_id": self.crew_id,
        }
        if extra:
            payload.update(extra)
        return self._chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=self.autonomy_level,
            agent_id=f"{self.crew_id}:{role}",
            payload=payload,
            actor_id=actor_id,
        )

    def record_task_complete(
        self,
        *,
        task_id: str,
        role: str,
        output_summary: dict[str, Any] | None = None,
        actor_id: str | None = None,
    ) -> AuditEvent | None:
        """Record a task-complete event with the role's output summary."""
        self._check_veto()
        if self._chain is None:
            return None
        payload: dict[str, Any] = {
            "crewai_event_kind": CrewAIEventKind.TASK_COMPLETE.value,
            "task_id": task_id,
            "role": role,
            "crew_id": self.crew_id,
        }
        if output_summary is not None:
            payload["output_summary"] = output_summary
        return self._chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=self.autonomy_level,
            agent_id=f"{self.crew_id}:{role}",
            payload=payload,
            actor_id=actor_id,
        )

    # ------------------------------------------------------------------ #
    # Crew-level events                                                  #
    # ------------------------------------------------------------------ #

    def record_crew_kickoff(
        self,
        *,
        agent_roles: list[str],
        extra: dict[str, Any] | None = None,
        actor_id: str | None = None,
    ) -> AuditEvent | None:
        """Record a crew kickoff (run-start) event."""
        self._check_veto()
        if self._chain is None:
            return None
        payload: dict[str, Any] = {
            "crewai_event_kind": CrewAIEventKind.CREW_KICKOFF.value,
            "agent_roles": list(agent_roles),
            "crew_id": self.crew_id,
        }
        if extra:
            payload.update(extra)
        return self._chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=self.autonomy_level,
            agent_id=self.crew_id,
            payload=payload,
            actor_id=actor_id,
        )

    def record_crew_result(
        self,
        *,
        result_summary: dict[str, Any] | None = None,
        actor_id: str | None = None,
    ) -> AuditEvent | None:
        """Record a crew aggregated-result event."""
        self._check_veto()
        if self._chain is None:
            return None
        payload: dict[str, Any] = {
            "crewai_event_kind": CrewAIEventKind.CREW_RESULT.value,
            "crew_id": self.crew_id,
        }
        if result_summary is not None:
            payload["result_summary"] = result_summary
        return self._chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=self.autonomy_level,
            agent_id=self.crew_id,
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
    """Print a one-line status report. Safe whether or not crewai is present."""
    print(f"CrewAIAuditAdapter demo: HAS_CREWAI={HAS_CREWAI}")
    if not HAS_CREWAI:
        print("  crewai not installed.")
        print("  Install with: pip install finserv-agent-audit[crewai]")
        print("  No-op mode active when audit_chain=None.")
        return
    print("  crewai import succeeded.")
    print("  Wire CrewAIAuditAdapter into your CrewAI Task and Crew callbacks.")


if __name__ == "__main__":
    _run_demo()


__all__ = [
    "HAS_CREWAI",
    "CrewAIAuditAdapter",
    "CrewAIEventKind",
]
