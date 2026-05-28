# ADR-0006 · Shadow Mode Rollout for FSI Agent Capabilities

**Status:** Accepted
**Date:** 2026-05-28
**Decider:** Kunjar Bhaduri
**Repo:** finserv-agent-audit v1.1

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel. No attorney-client relationship is formed by use of this ADR. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

## Context

A new agent capability — an updated credit-decision model, a revised order-routing rule, a new AML alert classifier, a refreshed market-surveillance signal — must move from development into production without becoming the cause of the next consent order. The conventional canary approach (ship to a small slice of live traffic) is the wrong default for FSI decisions because even one percent of regulated traffic crosses an OCC, FRB, SEC, FINRA, or CFPB-examinable surface. A single mispriced credit decision is a Reg B (ECOA) finding; a single mistimed order is a Reg NMS or Reg SHO problem; a single missed SAR is a BSA matter.

The correct default is to run the new capability **in parallel with the current production path on the same input**, observe divergence, and promote only when divergence is understood and below a calibrated band. This is shadow mode, and SR 11-7 already names it as expected practice for material model changes (Section V — "Model Implementation, Use, and Change").

## Decision

Adopt **Shadow Mode Rollout** as the mandatory promotion path for any agent capability whose output crosses a Sovereign Veto surface (ADR-0002). The implementation lives at `src/finserv_agent_audit/governance/shadow_mode.py` and is composed into the runtime pipeline ahead of the production action.

```
Live input
   │
   ├──► Production agent ──► Sovereign Veto ──► Audit ledger ──► Action executes
   │
   └──► Shadow agent     ──► Sovereign Veto ──► Audit ledger (shadow) ──► Silent
```

Both paths run on identical input. Both write to the hash-chain audit ledger (ADR-0003); shadow entries carry `shadow=true` and are excluded from action dispatch. A divergence monitor compares outputs on every decision and emits:

- **Aggregate divergence rate** — share of decisions where the two paths disagreed on outcome
- **Veto-direction divergence** — share where one path vetoed and the other did not, with sign (shadow more conservative vs. shadow more aggressive)
- **Cohort-stratified divergence** — disparate-impact analysis on the divergence itself, segmented by ECOA-protected classes for credit decisions and by FINRA-defined customer categories for trading
- **Materiality-weighted divergence** — dollar-weighted for trading and lending decisions, alert-count-weighted for AML

### Promotion gate to live

| Decision class | Minimum shadow duration | Maximum divergence | Sign-offs |
|---|---|---|---|
| Informational / classification (no client impact) | 7 days | < 5% aggregate; no worse-direction veto | First-line owner |
| Trade execution / order routing | 30 days | < 1% aggregate; zero worse-direction veto on customer-protection rules | First-line + second-line model validation |
| Credit decisioning, scoring, line management | 60 days | < 1% aggregate; zero worse-direction veto on any ECOA-protected cohort | First-line + second-line + Fair Lending counsel |
| AML / surveillance alert disposition | 60 days | < 0.5% aggregate on suppression direction; alert-recall non-inferiority | First-line + BSA Officer |
| Capital, liquidity, or stress-test inputs | 90 days | < 0.5% aggregate; second-line validation report on file | First-line + second-line + Chief Risk Officer |

Promotion writes an audit-ledger entry recording the shadow-period summary statistics, the operator who promoted, the second-line validator, and the rationale. The entry is hash-chained and replayable.

## Alternatives Considered

- **Canary rollout (1% live traffic).** Rejected as the default for regulated surfaces: even one percent is a settled-liability surface and a regulator-reportable population.
- **Backtest-only validation.** Rejected: backtests do not capture production data drift, vendor-feed latency, or operator-intervention patterns. SR 11-7 Section V.2 explicitly calls out testing under production conditions.
- **Champion-challenger in production with random arm assignment.** Acceptable for non-customer-facing optimization, but rejected as the default for credit and trading surfaces because random assignment creates a deliberate disparate-treatment exposure under ECOA and Reg B.

## Consequences

**Positive.** A new capability never reaches an examinable decision surface without production-condition observation. Divergence is a structured signal, not a post-incident reconstruction. The promotion record is examination-ready: who approved, what they saw, when they signed.

**Negative.** Cost roughly doubles during shadow periods because two model paths consume compute and (where applicable) two vendor-score lookups. The cost is small relative to a single Reg B finding. Mitigation: shadow periods are time-boxed by decision class, vendor-score caching de-duplicates lookups, and only capabilities passing the gate consume the full window.

**Operational.** A capability stuck in shadow indefinitely is a signal in itself — either divergence is not converging (the capability is wrong) or the operator is unwilling to promote (the program is stuck). The monitor agent flags time-in-shadow as a board-reportable metric.

## Regulatory Mapping

- **SR 11-7 Section V — Model Implementation, Use, and Change** — expects parallel-run testing for material model changes
- **OCC Bulletin 2011-12** — adopts SR 11-7 standards for OCC-regulated institutions `[UNVERIFIED — primary source not fetched]`
- **EU AI Act Art. 15** — statutory title "Accuracy, robustness and cybersecurity"; testing under representative conditions
- **NIST AI RMF MEASURE 2.1** — testing under representative conditions
- **FINRA Rule 3110(b)** — supervisory procedures expected to include pre-deployment testing of algorithmic changes
- **Reg B / ECOA — 12 CFR § 1002** — adverse-action and disparate-impact obligations attach the moment a new model touches a credit decision

## Pre-mortem

What fails:

1. **Shadow path silently degrades** (e.g., stale vendor scores fed only to shadow). Detection: divergence monitor reports input-feed mismatch as a first-class signal, not a noise floor.
2. **Promotion happens on a Friday afternoon** with no second-line on call. Detection: the promotion gate refuses if any required signer is not authenticated within a 24-hour window.
3. **Cohort divergence is hidden by aggregate threshold.** Detection: cohort-stratified report is the gate, not the aggregate; aggregate is informational only.
4. **Capability sits in shadow for 200 days without decision.** Detection: time-in-shadow over 2x the class minimum auto-escalates to DEFCON-3 for the affected capability per ADR-0001.

## Reversibility

Very high. A promoted capability can be demoted to shadow with a single operator action; the prior production path is retained for the duration of the shadow period and is re-promotable. The hash-chain audit ledger preserves the entire decision history, so any post-incident reconstruction is exact.

## Cross-references

- ADR-0001 (DEFCON) — DEFCON-3 forces any new capability into indefinite shadow
- ADR-0002 (Sovereign Veto) — shadow path executes the same veto gate; divergence on veto outcomes is the primary safety signal
- ADR-0003 (Hash-chain audit) — shadow entries are first-class ledger entries
- ADR-0004 (Autonomy Ladder) — shadow-period summary is a required input for A2 → A3 promotion
- ADR-0007 (SR 11-7 overlay) — Shadow Mode is the second-line validation surface for new and changed models
- Code: `src/finserv_agent_audit/governance/shadow_mode.py` (lands in Tranche 2D)
