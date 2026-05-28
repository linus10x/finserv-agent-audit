# ADR-0001: DEFCON State Machine

**Status:** Accepted
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel. No attorney-client relationship is formed by use of this ADR. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

---

## Context

An autonomous AI agent operating inside a regulated financial-services workflow will encounter system-wide unsafe states whose cost is asymmetric: a single hour of agent autonomy during a market-data outage, a model-validation failure, an SEC inquiry-in-flight, or an exchange-side trading halt can produce hundreds of decisions that later require manual unwind. Per-decision risk checks are necessary but insufficient. Some risk conditions are system-wide and need a system-wide brake.

FSI-specific motivating cases:

- A trading agent continues to size positions while the firm's net-capital ratio is approaching the SEC Rule 15c3-1 minimum (broker-dealer net-capital deficiency).
- A KYC/AML triage agent continues to clear customers during a known sanctions-list data-feed outage, producing un-screened approvals that later require BSA/AML SAR (Suspicious Activity Report) filings.
- A market-making agent continues quoting after an intraday drawdown threshold (e.g., 4% on a 1-day window) is breached and risk management has not yet signed off on continued operation.

The conventional "feature flag" approach is too granular and too distributed. A flag-per-capability creates a combinatorial blast radius when the operator needs to roll back fast under regulator or risk-committee scrutiny.

## Decision

Adopt a **DEFCON state machine** with discrete named states, named transition conditions, and a per-state allowlist of agent capabilities. State is global, owned by a single `DefconController` actor. The reference implementation lives at `src/finserv_agent_audit/governance/defcon.py`.

```
DEFCON-5 (NORMAL)      All capabilities active. Standard audit.
DEFCON-4 (HEIGHTENED)  Material orders (size > calibrated band) require
                       human co-sign. Other capabilities active.
DEFCON-3 (RESTRICTED)  New-position sizing paused. Risk-reducing trades
                       (close-only) continue. KYC/AML triage continues with
                       mandatory reviewer signature on every clear.
DEFCON-2 (CONTAINMENT) All writes paused. Agents read-only. Audit ledger
                       continues writing. Open positions held; no new orders.
DEFCON-1 (HALT)        Agents offline. Audit ledger continues writing.
                       Operator-only mode. Manual override required to exit.
```

Transitions are triggered by:

- **Operator command** — explicit escalation or de-escalation (logged with named owner).
- **Monitor alerts** — anomaly thresholds breached on the audit ledger (veto-rate band, drawdown band, model-confidence collapse).
- **External signal** — regulator notice, exchange-side halt, vendor incident on a third-party model in the decision path.
- **Scheduled** — pre-announced regulatory window (FINRA TRACE reporting cutover, Fed FOMC blackout, quarter-end risk-system freeze).

De-escalation requires more consecutive confirmations than escalation (hysteresis) so the controller does not flap. Every state transition writes an immutable entry to the audit ledger (ADR-0003) with reason, actor, prior state, new state, and an estimated duration.

## Alternatives Considered

1. **Feature-flag-per-capability.** Rejected. At realistic FSI scale (dozens of capabilities, hundreds of strategy variants) the cross-product is unmanageable in an incident. An operator under regulator-watch pressure cannot reason about 200 flags.
2. **Single binary kill-switch.** Rejected. A binary "on/off" forces a choice between full autonomy and full halt; most real incidents call for a partial restriction (close-only mode, mandatory co-sign on material orders) that preserves the ability to reduce risk while pausing risk-taking.
3. **Per-agent local state.** Rejected. System-wide risk conditions (market-data outage, firm-level net-capital pressure) require system-wide response. Per-agent state produces inconsistent behavior across agents on the same firm-level event.

## Consequences

**Positive.** A single switch can stop the bleed. Operators have a calibrated, well-documented escalation ladder rather than ad-hoc flag flipping. Regulators see a structured response to incidents. DEFCON state is the first check in the compose order, so unsafe-state actions are killed before downstream cost.

**Negative.** Adds latency to every agent action (one state read). Mitigated by caching state in-process with a 1-second TTL and a force-invalidate hook on transition events.

**Operational.** DEFCON-3 and below are not normal operating modes. Time-in-state metrics are reported to the risk committee. A program that spends more than 5% of operating hours below DEFCON-5 is showing a structural issue.

## Regulatory Mapping

- **SEC Rule 15c3-5** (Market Access Rule, 17 CFR § 240.15c3-5) — pre-trade risk-management controls and supervisory procedures for broker-dealers with direct market access. The DEFCON state is one element of the supervisory architecture. [UNVERIFIED — primary source not fetched]
- **MiFID II Article 17** (Directive 2014/65/EU) — algorithmic-trading firms must have "effective business continuity arrangements" and risk controls including the ability to halt trading. DEFCON-1 (HALT) implements the firm-level kill. [UNVERIFIED — primary source not fetched]
- **NYDFS Part 504** (23 NYCRR 504) — transaction-monitoring and OFAC-screening program governance; DEFCON ladder supports the "model-validation deficiency" response posture. [UNVERIFIED — primary source not fetched]
- **NIST AI RMF** GOVERN 1.6 — incident-response procedures documented.
- **SR 11-7** (Federal Reserve Guidance on Model Risk Management, 2011) — model-governance posture for sudden model-performance degradation.

## Pre-mortem

- **Operator misuse: de-escalating too fast.** Mitigation — hysteresis (N consecutive confirmations) plus a logged exception requiring a named risk-committee approver for any de-escalation under the prescribed window.
- **State-read becomes a hot-path bottleneck.** Mitigation — 1-second TTL cache; invalidation on transition event broadcast.
- **Operator escalates manually, controller never sees the external signal.** Mitigation — external-signal adapter pattern; every supported external feed has a documented integration test and an alerting fallback if the feed stops emitting heartbeat.
- **Audit ledger goes down while DEFCON is mid-transition.** Mitigation — the transition is the atomic unit; the controller does not commit the new state until the ledger write has acknowledged.

## Reversibility

State transitions are themselves reversible (de-escalation is supported and tested). The reference implementation persists last-confirmed state to disk; on restart, the controller loads the last confirmed state, not a recomputed live evaluation (intentionally conservative). The pattern itself is reversible: a deployer can replace the controller with a simpler kill-switch, but loses the partial-restriction states; the lost capability is the cost of the simplification.

## Cross-references

- **Implementation:** `src/finserv_agent_audit/governance/defcon.py`
- **Tests:** `tests/test_defcon_controller.py`
- **Architecture notes:** `docs/DEFCON_ARCHITECTURE.md`
- **Related ADRs:** ADR-0002 (Sovereign Veto, runs after DEFCON check) · ADR-0003 (Hash-chain Audit, records every transition) · ADR-0004 (Autonomy Ladder, A2→A3 promotion requires DEFCON ladder live)
