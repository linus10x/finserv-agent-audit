# Domain-agnostic agent-swarm governance

The governance primitives in this library are **not finance-specific**. The
package vocabulary is FSI-flavored, but the controls — the **sovereign veto**,
the **hard envelope**, the **hash-chained audit ledger**, and **autonomy-rung
demotion** — govern general multi-agent autonomy.

This example proves that with a non-financial scenario: a small swarm of worker
agents running a multi-step job pipeline, one step of which is **irreversible**
(a generic `dispatch` — launch a job / delete a volume / send an external
message). No money, no trades, no loans anywhere in the code.

> This is an **illustrative reference example**, not a deployed control.
> Calibrate envelopes, drift thresholds, and the human authorization path to
> your own system before relying on any of it.

## What it demonstrates (end to end, with the real library API)

| Primitive | Library API used | Shown in the run |
|---|---|---|
| **Sovereign veto** (hard stop) | `SovereignVeto.trigger` / `allow_execution` / `clear` (`VetoReason`, `VetoBlockedError`) | `[VETO]` blocks the irreversible action; agent **cannot self-clear** (`[GOOD]`) |
| **Hard envelope** | `AutonomyTier` (A2/A3 `requires_envelope` / `can_write`) | reversible steps run autonomously (`[OK]`); the irreversible step is out-of-envelope and routed to a human |
| **Audit chain** (tamper-evident) | `AuditChain.append` / `verify` / `chain_head` (`AuditEventType`, `AutonomyLevel`) | every step is hash-chained; `verify() = True` |
| **Demotion on drift** | `AutonomyTier` rung step-down, recorded via `AuditChain.append` | repeated out-of-envelope attempts demote the agent `A3 -> A2` (`[DEMOTE]`) |

## Run in 60 seconds

```bash
git clone https://github.com/linus10x/finserv-agent-audit.git
cd finserv-agent-audit
python3 -m venv .venv && source .venv/bin/activate
pip install -e .                 # zero runtime deps — stdlib only
python examples/agent_coordination/coordination.py
```

### Expected output (the veto firing and the demotion)

```
======================================================================
  Domain-agnostic agent-swarm governance (illustrative reference)
======================================================================

  Swarm worker 'worker-7' starts at rung A3

  [OK]      ingest: in-envelope (fetch) executed autonomously
  [OK]      normalize: in-envelope (transform) executed autonomously
  [OK]      stage_output: in-envelope (stage) executed autonomously
  [VETO]    dispatch_irreversible: irreversible action routed to human 'operator_alex'; sovereign veto ... active
  [GOOD]    self-clear refused: no agent can clear its own veto
  [HUMAN]   'operator_alex' cleared the veto after review

  [VETO]    dispatch_irreversible_retry: irreversible action routed to human 'operator_alex'; sovereign veto ... active
  [GOOD]    self-clear refused: no agent can clear its own veto
  [DEMOTE]  drift detected -> 'worker-7' demoted A3 -> A2 (2 out-of-envelope attempts >= drift threshold 2)
  [HUMAN]   'operator_alex' cleared the veto after review

----------------------------------------------------------------------
  Audit chain: 8 hash-chained events; verify() = True
  Chain head:  ...
======================================================================
```

A `WARNING` is emitted on stderr noting that no `Authorizer` is wired (so the
`operator_id` on the chain is an unauthenticated assertion). That is the
library being honest: a real deployment injects an `Authorizer` to gate
`clear()` and trust the recorded operator identity. The veto's self-clearing
block (`CR-12`) fires regardless of the Authorizer.
