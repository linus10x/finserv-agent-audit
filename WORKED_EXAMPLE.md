# Worked example — the five beats of an Autonomy Ladder gate

This walkthrough reads the **runnable** example
[`examples/agent_coordination/coordination.py`](examples/agent_coordination/coordination.py)
beat by beat, so you can see the library's primitives engaging on a live
decision instead of in the abstract. The example is deliberately
**domain-agnostic** — a generic worker-agent swarm with no money, trades, or
loans — to make the point that the controls govern coordinated autonomy, not
just finance. The FSI decision classes (adverse action, best interest, SAR) plug
into the same five beats.

> This is an **illustrative reference example**, not a deployed control.
> Calibrate envelopes, drift thresholds, and the human authorization path to
> your own system before relying on any of it.

## Run it first (≈30 seconds)

```bash
git clone https://github.com/linus10x/finserv-agent-audit.git
cd finserv-agent-audit
python3 -m venv .venv && source .venv/bin/activate
pip install -e .                 # zero runtime deps — stdlib only
python examples/agent_coordination/coordination.py
```

A worker agent (`worker-7`) starts at rung **A3** (supervised autonomous) and
runs a five-step pipeline: three reversible steps (`fetch`, `transform`,
`stage`) and one **irreversible** step (`dispatch`) attempted twice.

## The five beats

### 1 — Decision class

Each step is a `Task` carrying an `action` and an `irreversible` flag. The
decision class is a parameter, not a hard-coded finance concept: a reversible
in-scope action is inside the envelope; an irreversible action is the
high-consequence class that the swarm is **not** allowed to self-approve. In the
FSI libraries this same slot is "issue an adverse-action notice", "emit a
best-interest recommendation", or "file/suppress a SAR".

```python
Task("dispatch_irreversible", "dispatch", irreversible=True)
```

### 2 — Agent acts

At A3 the agent executes reversible, in-scope steps autonomously. Each one is
appended to the audit chain as a `DECISION_MADE` event, tagged with the agent's
current autonomy level. You see three `[OK]` lines — the agent doing real work
without a human in the loop.

```python
chain.append(event_type=AuditEventType.DECISION_MADE, autonomy_level=..., agent_id=...)
```

### 3 — Envelope / veto catches the irreversible action

The **hard envelope** (`_in_envelope`) classifies the irreversible `dispatch` as
out of envelope and routes it to a human. The **sovereign veto**
(`SovereignVeto.trigger`) blocks execution — and crucially, when the agent tries
to clear its own veto, the library hard-refuses with `VetoBlockedError` (the
`[GOOD]` line). An agent cannot grant itself authority it has not earned. This
is the load-bearing trust boundary: the veto is a separate-process control the
agent cannot switch off.

```python
veto_record = agent.veto.trigger(reason=VetoReason.POLICY_VIOLATION, ...)
# self-clear always raises VetoBlockedError
agent.veto.clear(operator_id=agent.agent_id, reason="self-approve")  # -> blocked
```

### 4 — Audit-chain entry

Every beat — the autonomous executions, the veto, the routing to a human, the
human's review-and-decline, and the demotion below — is written to a SHA-256
hash-chained ledger. At the end, `chain.verify()` returns `True`, proving the
chain is internally consistent — a tamper-evident hash chain (within trust
boundary; detection but not prevention). This is the artifact a regulator or risk
committee asks for: a per-decision trail you can reconstruct on demand, not from
team memory.

```python
verified = chain.verify()          # True
chain.chain_head()                 # the tamper-evident head hash
```

### 5 — Demotion A3 → A2

Repeated out-of-envelope attempts are the drift signal. When the count crosses
`DRIFT_DEMOTION_THRESHOLD`, the agent is **demoted one rung** (A3 → A2) and the
demotion itself is recorded as a `RISK_ESCALATION` event on the chain. The rungs
are not a one-way ratchet: an agent that keeps reaching past its authority loses
authority. Re-promotion has to be earned back through the gate
(`check_a2_to_a3_promotion`), not toggled.

```python
[DEMOTE]  drift detected -> 'worker-7' demoted A3 -> A2 (2 out-of-envelope attempts >= threshold 2)
```

## Expected output

```
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

  Audit chain: 8 hash-chained events; verify() = True
```

A `WARNING` on stderr notes that no `Authorizer` is wired, so the `operator_id`
on the chain is an unauthenticated assertion — the library being honest. A real
deployment injects an `Authorizer` to gate `clear()` and trust the recorded
operator identity. The self-clear block (`CR-12`) fires regardless.

## Where to go next

- The rung-by-rung mapping for this repo: [AUTONOMY_LADDER.md](AUTONOMY_LADDER.md)
- How these primitives would have engaged with real enforcement matters: [CASE_STUDIES.md](CASE_STUDIES.md)
- The framework + whitepaper: [autonomy-ladder.io](https://autonomy-ladder.io)
