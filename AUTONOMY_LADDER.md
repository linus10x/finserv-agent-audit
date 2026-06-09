# The Autonomy Ladder in this library

`finserv-agent-audit` is the flagship of six regulated-vertical reference
libraries that implement the **Autonomy Ladder** — a governance framework for
autonomous AI in regulated operations. The framework defines five
deployment-authority rungs, A0→A4, **every rung demotable**: an agent earns its
way up only when the lower rungs' controls are attested, and any breach demotes
it.

Framework + whitepaper: **[autonomy-ladder.io](https://autonomy-ladder.io)** ·
family index: **[autonomy-ladder-libraries](https://github.com/linus10x/autonomy-ladder-libraries)**.

## The rungs

| Rung | Posture | Required controls (this library) |
|---|---|---|
| **A0** Informational | Read-only; recommends, never writes | none |
| **A1** Assisted | Drafts; a human approves every write | human-approval workflow |
| **A2** Delegated | Writes inside an envelope; sampled human review | action envelope · sampled human review |
| **A3** Supervised autonomous | Autonomous; sovereign veto + full audit | sovereign veto · audit chain |
| **A4** Production autonomous | A3 + orchestration + escalation | orchestration guard · escalation path |

The rung semantics are encoded in the `AutonomyTier` enum in
[`src/finserv_agent_audit/governance/autonomy_ladder.py`](src/finserv_agent_audit/governance/autonomy_ladder.py);
the wire-format A0..A4 codes written onto the ledger are the `AutonomyLevel` enum
in [`src/finserv_agent_audit/schemas/audit_event.py`](src/finserv_agent_audit/schemas/audit_event.py).
Promotion is monotonic and second-line-gated: `check_a2_to_a3_promotion()`
refuses the A2→A3 step unless the lower-rung controls are attested and the
minimum supervised-autonomous observation window has elapsed — it returns a
`PromotionGateReport` and raises `PromotionGateNotMet` rather than silently
promoting.

## How this library's primitives map to the rungs

| Primitive | Module | What it guarantees | Rung it gates |
|---|---|---|---|
| **Autonomy gate** (`check_a2_to_a3_promotion`, `AutonomyTier`) | `governance/autonomy_ladder.py` | Refuses promotion on unmet lower-rung controls or a too-short observation window; reports the gap rather than promoting silently | every rung — it *is* the A0→A4 control |
| **Sovereign veto** (`SovereignVeto`) | `governance/sovereign_veto.py` | Fail-closed kill switch; an agent cannot clear its own veto (`VetoBlockedError`); clearing is an authenticated human-oversight act gated by an `Authorizer` | required at **A3+** |
| **Audit chain** (`AuditChain`, `AuditChainTamperError`) | `governance/audit_chain.py` | Tamper-detecting SHA-256 hash chain; domain-separated genesis; `verify()` walks the chain; pair with an external witness for chain-of-custody | required at **A3+** |
| **DEFCON state machine** (`DEFCONMachine`, `DEFCON`) | `governance/defcon.py` | Escalates immediately on a risk-metric breach; never auto-de-escalates; lowers one guarded level at a time only after sustained confirmation (hysteresis) | the demotion mechanism across all rungs |
| **Hard envelope** | encoded per decision class (see `examples/agent_coordination/coordination.py`) | An irreversible / out-of-scope action is out of envelope and must route to a human; the swarm cannot self-approve it | the load-bearing control at **A2 / A3** |
| **Effective-challenge harness** (`EffectiveChallengeHarness`) | `governance/effective_challenge_harness.py` | Rejects `challenger == primary`; records an independence attestation per SR 11-7 / OCC 2026-13 | qualifies a model before it operates at any writing rung |
| **Adverse-action gate** (`AdverseActionGate`) | `governance/adverse_action_gate.py` | Fails closed on a missing reason-code mapping; records the `ReasonCode` decomposition before emission (FCRA §615 · CFPB Circular 2022-03) | the FSI decision-class control an **A2+** agent operates under |
| **Best-interest check** (`BestInterestCheck`) | `governance/best_interest_check.py` | Records conflict-of-interest declarations on the recommendation surface (SEC Reg BI) | the FSI decision-class control an **A2+** agent operates under |

## Demotion is the point

The rungs are not a one-way ratchet. The DEFCON machine escalates the moment a
risk metric breaches a threshold and **never** auto-lowers; the sovereign veto
halts the agent on any drift or breach; and lowering risk state requires an
authenticated, authorized human moving one guarded level at a time.
[`WORKED_EXAMPLE.md`](WORKED_EXAMPLE.md) shows this concretely: a worker agent at
A3 repeatedly pushes an irreversible action past its envelope, the veto blocks
it, the agent cannot self-clear, and the accumulated drift demotes it A3→A2 —
the demotion itself written to the audit chain.

See the framework at **[autonomy-ladder.io](https://autonomy-ladder.io)** and the
five other vertical libraries linked from the [README](README.md#the-autonomy-ladder-family).
