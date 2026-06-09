"""Domain-agnostic agent-swarm governance — an illustrative reference example.

This script shows the *same* governance primitives shipped in this library —
the **sovereign veto**, the **hard envelope**, the **hash-chained audit
ledger**, and **autonomy-rung demotion** — applied to a generic multi-agent
swarm with NO financial-services assumptions. The point: these controls govern
general multi-agent autonomy, not just finance. The fact that the library's
top-level vocabulary is FSI-flavored is a packaging choice; the primitives are
domain-agnostic.

Scenario
--------
A small swarm of worker agents executes a multi-step job pipeline. Most steps
are reversible (``fetch``, ``transform``, ``stage``). One step is
**irreversible** — a generic ``dispatch`` action that commits/destroys/sends
something that cannot be undone (think: launching a job, deleting a volume,
sending an external message). There is no money and no loan anywhere in this
file.

What this example demonstrates, end to end, with the real library API
-------------------------------------------------------------------
1. A worker agent sitting at a high autonomy rung (A3) attempts the
   irreversible ``dispatch`` action.
2. The **hard envelope** classifies ``dispatch`` as out-of-envelope and routes
   it to a human instead of letting the swarm self-approve it.
3. The **sovereign veto** is triggered and BLOCKS execution; the agent that
   raised the action cannot clear its own veto (self-clearing is hard-blocked).
4. The **audit ledger** records every step in a tamper-evident hash chain and
   ``verify()`` confirms the chain is internally consistent.
5. On detected behavioral **drift** (the agent repeatedly pushing past its
   envelope), the agent is **demoted** one autonomy rung (A3 -> A2), and the
   demotion itself is written to the ledger.

This is an *illustrative reference example* of domain-agnostic primitives —
NOT a deployed control. Calibrate envelopes, drift thresholds, and the human
authorization path to your own system before relying on any of it.

Run it
------
    python examples/agent_coordination/coordination.py

(see ``examples/agent_coordination/README.md`` for the 60-second block).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from finserv_agent_audit.governance.autonomy_ladder import AutonomyTier
from finserv_agent_audit.governance.ledger_store import InMemoryLedgerStore
from finserv_agent_audit.governance.sovereign_veto import (
    SovereignVeto,
    VetoBlockedError,
    VetoReason,
)
from finserv_agent_audit.schemas.audit_event import (
    AuditChain,
    AuditEventType,
    AutonomyLevel,
)

logger = logging.getLogger("agent_coordination")

# Tier -> wire-format short code written onto the ledger. The ladder enum
# (semantics) and the AutonomyLevel enum (wire format) share the A0..A4 codes.
_TIER_TO_LEVEL = {
    AutonomyTier.A0_INFORMATIONAL: AutonomyLevel.A0,
    AutonomyTier.A1_ASSISTED: AutonomyLevel.A1,
    AutonomyTier.A2_DELEGATED: AutonomyLevel.A2,
    AutonomyTier.A3_SUPERVISED_AUTONOMOUS: AutonomyLevel.A3,
    AutonomyTier.A4_PRODUCTION_AUTONOMOUS: AutonomyLevel.A4,
}

# One rung down, by ordinal. Demotion is "step toward more oversight".
_DEMOTION_LADDER = [
    AutonomyTier.A0_INFORMATIONAL,
    AutonomyTier.A1_ASSISTED,
    AutonomyTier.A2_DELEGATED,
    AutonomyTier.A3_SUPERVISED_AUTONOMOUS,
    AutonomyTier.A4_PRODUCTION_AUTONOMOUS,
]


@dataclass
class Task:
    """One step in the pipeline. ``irreversible`` marks an out-of-envelope action."""

    name: str
    action: str  # "fetch" | "transform" | "stage" | "dispatch"
    irreversible: bool = False


@dataclass
class WorkerAgent:
    """A swarm worker. Carries its own autonomy rung and a drift counter."""

    agent_id: str
    tier: AutonomyTier = AutonomyTier.A3_SUPERVISED_AUTONOMOUS
    out_of_envelope_attempts: int = 0
    veto: SovereignVeto = field(init=False)

    def __post_init__(self) -> None:
        # No Authorizer wired in this illustrative example -> the library
        # logs a WARNING that operator_id on the chain is an unauthenticated
        # assertion. A real deployment injects an Authorizer here.
        self.veto = SovereignVeto(agent_id=self.agent_id)


# Drift threshold: this many out-of-envelope attempts demotes the agent a rung.
DRIFT_DEMOTION_THRESHOLD = 2

# Human operator who can clear vetos and approve out-of-envelope actions.
HUMAN_OPERATOR_ID = "operator_alex"


def _in_envelope(agent: WorkerAgent, task: Task) -> bool:
    """The hard envelope.

    At A2/A3 the envelope is the load-bearing control: reversible, in-scope
    actions execute autonomously; an irreversible action is OUT of envelope
    and must be routed to a human — the swarm cannot self-approve it.
    """
    if task.irreversible:
        return False
    return agent.tier.can_write


def _demote(agent: WorkerAgent, chain: AuditChain, reason: str) -> None:
    """Demote the agent one autonomy rung and record it on the ledger."""
    idx = _DEMOTION_LADDER.index(agent.tier)
    if idx == 0:  # pragma: no cover - floor guard; the demo never starts at A0
        return  # already at the floor (A0)
    new_tier = _DEMOTION_LADDER[idx - 1]
    old_tier = agent.tier
    agent.tier = new_tier
    chain.append(
        event_type=AuditEventType.RISK_ESCALATION,
        autonomy_level=_TIER_TO_LEVEL[new_tier],
        agent_id=agent.agent_id,
        payload={
            "event": "autonomy_demotion",
            "from_tier": old_tier.value,
            "to_tier": new_tier.value,
            "reason": reason,
        },
    )
    logger.warning(
        "DEMOTED %s: %s -> %s (%s)",
        agent.agent_id,
        old_tier.value,
        new_tier.value,
        reason,
    )
    print(
        f"  [DEMOTE]  drift detected -> {agent.agent_id!r} demoted "
        f"{old_tier.value} -> {new_tier.value} ({reason})"
    )


def run_pipeline() -> AuditChain:
    """Execute the pipeline, exercising every primitive. Returns the audit chain.

    The returned chain has ``verify() is True`` and contains the veto, the
    human routing, and the demotion as hash-chained events.
    """
    # In-memory store so the example is side-effect free and stdlib-only (no
    # JSONL file written). Legacy-mode genesis (no deployer_id) so end-to-end
    # ``verify()`` walks from the GENESIS sentinel and returns True — see the
    # test_concurrent_append note. A production deployer passes an explicit
    # ``deployer_id`` to engage the domain-separated genesis seed (CR-7) and
    # verifies via the cross-host re-derivation path instead.
    chain = AuditChain(ledger_store=InMemoryLedgerStore())

    agent = WorkerAgent(agent_id="worker-7")
    print(f"\n  Swarm worker {agent.agent_id!r} starts at rung {agent.tier.value}\n")

    pipeline = [
        Task("ingest", "fetch"),
        Task("normalize", "transform"),
        Task("stage_output", "stage"),
        # The irreversible step. Attempted twice — the agent keeps pushing past
        # its envelope, which is the drift signal that triggers demotion.
        Task("dispatch_irreversible", "dispatch", irreversible=True),
        Task("dispatch_irreversible_retry", "dispatch", irreversible=True),
    ]

    for task in pipeline:
        # 1. Veto gate — check before EVERY action. (Defensive: in this demo
        #    the human clears each veto before the next step, so the gate is
        #    open by the time the loop comes around again.)
        if not agent.veto.allow_execution():  # pragma: no cover - defensive gate
            print(f"  [BLOCKED] {task.name}: an active sovereign veto halts the swarm")
            continue

        # 2. Hard envelope check.
        if _in_envelope(agent, task):
            chain.append(
                event_type=AuditEventType.DECISION_MADE,
                autonomy_level=_TIER_TO_LEVEL[agent.tier],
                agent_id=agent.agent_id,
                payload={"action": task.action, "task": task.name, "in_envelope": True},
            )
            print(f"  [OK]      {task.name}: in-envelope ({task.action}) executed autonomously")
            continue

        # 3. Out of envelope -> route to human + trigger the sovereign veto.
        #    The agent CANNOT self-approve an irreversible action.
        agent.out_of_envelope_attempts += 1
        chain.append(
            event_type=AuditEventType.DECISION_VETOED,
            autonomy_level=_TIER_TO_LEVEL[agent.tier],
            agent_id=agent.agent_id,
            payload={
                "action": task.action,
                "task": task.name,
                "in_envelope": False,
                "routed_to": HUMAN_OPERATOR_ID,
            },
        )
        veto_record = agent.veto.trigger(
            reason=VetoReason.POLICY_VIOLATION,
            triggered_by="envelope_monitor",
            description=(
                f"{task.name!r}: irreversible 'dispatch' is out-of-envelope; "
                f"routed to {HUMAN_OPERATOR_ID} — swarm cannot self-approve"
            ),
        )
        print(
            f"  [VETO]    {task.name}: irreversible action routed to human "
            f"{HUMAN_OPERATOR_ID!r}; sovereign veto {veto_record.veto_id[:8]} active"
        )

        # 3a. Prove the agent cannot clear its own veto.
        try:
            agent.veto.clear(operator_id=agent.agent_id, reason="self-approve")
            print(  # pragma: no cover - unreachable; self-clear always raises
                "  [BUG]     agent cleared its OWN veto — this should never happen"
            )
        except VetoBlockedError:
            print("  [GOOD]    self-clear refused: no agent can clear its own veto")

        # 3b. Detected drift -> demote a rung. Then a human clears the veto.
        if agent.out_of_envelope_attempts >= DRIFT_DEMOTION_THRESHOLD:
            _demote(
                agent,
                chain,
                reason=(
                    f"{agent.out_of_envelope_attempts} out-of-envelope attempts "
                    f">= drift threshold {DRIFT_DEMOTION_THRESHOLD}"
                ),
            )

        # Human reviews and clears the veto so the swarm can continue.
        cleared = agent.veto.clear(
            operator_id=HUMAN_OPERATOR_ID,
            reason="reviewed irreversible dispatch; declined to proceed autonomously",
        )
        chain.append(
            event_type=AuditEventType.HUMAN_OVERRIDE,
            autonomy_level=_TIER_TO_LEVEL[agent.tier],
            agent_id=agent.agent_id,
            actor_id=HUMAN_OPERATOR_ID,
            payload={
                "event": "veto_cleared_by_human",
                "cleared_count": len(cleared),
                "task": task.name,
            },
        )
        print(f"  [HUMAN]   {HUMAN_OPERATOR_ID!r} cleared the veto after review\n")

    return chain


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="  %(levelname)s %(message)s")

    print("=" * 70)
    print("  Domain-agnostic agent-swarm governance (illustrative reference)")
    print("=" * 70)

    chain = run_pipeline()

    # The SHA-256 hash-chained ledger is tamper-evident within-trust-boundary.
    verified = chain.verify()
    event_count = len(list(chain._events))

    print("-" * 70)
    print(f"  Audit chain: {event_count} hash-chained events; verify() = {verified}")
    print(f"  Chain head:  {chain.chain_head()[:16]}...")
    print("=" * 70)

    assert verified, "audit chain failed verification"


if __name__ == "__main__":
    main()
