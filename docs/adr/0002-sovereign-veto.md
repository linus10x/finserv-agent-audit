# ADR-0002: Sovereign Veto

**Status:** Accepted
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel. No attorney-client relationship is formed by use of this ADR. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

---

## Context

An AI agent operating inside a regulated financial-services workflow will, given enough time and enough decisions, propose an action it does not have authority to take. The failure mode is not random — it is concentrated in decisions where the agent's training distribution misaligns with regulatory or fiduciary constraint surfaces.

FSI-specific examples:

- A trading agent placing an order that violates the firm's pre-trade risk envelope (SEC Rule 15c3-5 market-access controls).
- A credit-decisioning agent inferring on a proxy variable that drives a disparate-impact outcome under ECOA (Regulation B, 12 CFR Part 1002).
- A KYC/AML triage agent clearing a customer whose risk score is in the band that requires Enhanced Due Diligence under FinCEN's Customer Due Diligence Rule (31 CFR § 1010.230).
- A model-output adapter pushing a recommendation that exceeds the autonomy band documented in the SR 11-7 model-validation report.

The standard fix is "human in the loop." At realistic FSI scale (a single broker-dealer can produce hundreds of thousands of agent-evaluable decisions per trading day; a top-10 carrier's commercial-lines underwriting workflow generates tens of thousands of automated risk-tier assignments per week), human review on every decision is theatre, a bottleneck, or both.

The agent itself cannot be the arbiter of its own authority. The check must come from outside the agent and must be non-overridable by the agent.

## Decision

Implement a **Sovereign Veto** — a non-overridable check that runs at the agent boundary before any action that crosses a constraint surface the agent does not have authority to clear. Reference implementation: `src/finserv_agent_audit/governance/sovereign_veto.py`.

Properties:

1. **Non-overridable by the agent.** No prompt, no chain-of-thought, no reasoning step can bypass the veto. The veto sits outside the agent's reachable code path.
2. **Bypass-able by a human only with logged exception.** A human can override the veto for a single decision, but the override generates a logged exception that carries a named owner, a regulatory basis, and a timestamp. The exception is durable; it cannot be edited or deleted.
3. **Constraint-surface-specific.** The veto runs different checks for different action classes. Trading runs the Pre-Trade Risk Envelope check (Rule 15c3-5). Credit decisions run the ECOA proxy-variable check. KYC/AML runs the EDD-band check. Model-mediated decisions run the SR 11-7 autonomy-band check.
4. **Returns a structured reason code.** Vetoes are not "no." Vetoes are `RULE-15C3-5-PRETRADE-BREACH`, `ECOA-PROXY-DISPARATE-IMPACT`, `BSA-EDD-BAND-UNCLEARED`, `SR11-7-AUTONOMY-BAND-EXCEEDED`. The code is logged. The code is the regulator-readable explanation.

```python
class SovereignVeto:
    def check(self, action: AgentAction, context: AuditContext) -> VetoResult:
        # Returns VetoResult.PASS, or VetoResult.VETO(reason_code, owner_required)
        ...
```

A vetoed action is written to the audit ledger (ADR-0003) with full context. The agent receives the veto and either proposes a corrected action or escalates to a human in the workflow.

## Alternatives Considered

1. **Prompt-engineered self-restraint.** Rejected. The agent cannot be the arbiter of its own authority; prompt-level guardrails are bypassable by the agent's own reasoning and by adversarial input. The check must be outside the agent.
2. **Post-hoc audit only.** Rejected. Post-hoc audit catches the violation after the order is filled, the credit decision is sent, or the customer is cleared. The settlement, the disparate-impact harm, and the SAR are already in motion.
3. **Hard rule-coded if-statements scattered in agent code.** Rejected. Scattered checks are not enumerable to a regulator. The veto layer must be a single inspectable surface ("show me every constraint the agent is checked against, and the reason code each one emits").

## Consequences

**Positive.** Regulator-defensible architecture. Every decision the agent did not take is as recoverable as every decision it did. The bypass log becomes the board-level governance artifact — a thing regulators, LPs, and chief risk officers ask for by name ("show me the exception log for Q3").

**Negative.** Decisions take longer. The compose-order placement means the veto runs only if upstream checks passed, which keeps the cost off the hot path for unsafe-state cases. Calibration risk: an over-tight veto produces a flood of bypass exceptions; an under-tight veto produces settled liability. Calibration is the work of the program, not the framework.

**Architectural.** The veto layer must be outside the agent's process or, at minimum, outside the agent's reasoning context. In this reference repo it is a separate Python module the agent code cannot mutate. In a production deployment it is a separate service.

## Regulatory Mapping

- **SEC Rule 15c3-5** (17 CFR § 240.15c3-5) — pre-trade risk-management controls for broker-dealers with market access; the veto is the runtime enforcement point. [UNVERIFIED — primary source not fetched]
- **MiFID II Article 17** (Directive 2014/65/EU) — algorithmic-trading firms must have a kill-switch and pre-trade controls. The Sovereign Veto is the named kill-the-bad-order mechanism. [UNVERIFIED — primary source not fetched]
- **NYDFS Part 200.16** (algorithmic-trading-rules style requirement for supervisory architecture in firms operating algorithmic execution). [UNVERIFIED — primary source not fetched]
- **ECOA Regulation B** (12 CFR Part 1002) — credit decisioning fair-lending controls; the veto enforces disparate-impact proxy-variable checks at runtime. [UNVERIFIED — primary source not fetched]
- **SR 11-7** (2011) — model-validation findings translate into an autonomy band; the veto enforces the band at runtime.
- **Three-lines-of-defense model** — the veto is a second-line control implemented at runtime.
- **NIST AI RMF** MANAGE 2.3 — risk decisions and trade-offs documented.

## Pre-mortem

- **Over-tight calibration produces exception fatigue.** A flood of bypass requests trains the human approver to rubber-stamp. Mitigation — every bypass requires a typed reason code and a regulatory basis; a quarterly review of bypass-rate-per-reason-code is on the risk-committee agenda.
- **Vendor-side veto authority is unclear.** When a third-party vendor model is in the decision path (Bloomberg AIM, FactSet, ZestFinance, a sanctions-screening vendor), the operator's sovereign veto fires on the operator's *use* of the vendor output — not on the vendor's model itself. Document the vendor-output adapter pattern (see ADR-0011).
- **Adversarial bypass via IdP impersonation.** Sovereign veto is non-overridable *by the agent*; it does NOT defend against an attacker with privileged access to the IdP impersonating an authorized human bypass owner. Identity-and-access controls are out of scope.
- **Single-authority bypass becomes a single point of failure.** Mitigation — two-person rule (one Chief Risk Officer + one General Counsel must both approve) for the highest-severity reason codes. The reference enum is single-authority; quorum is a deployer extension.

## Reversibility

The veto layer is a separate module; a deployer can remove it. Doing so removes the regulator-defensible architecture and exposes the firm to the failure modes above. Individual reason codes can be tuned, disabled (with logged justification), or added without disturbing the framework. The bypass log is append-only and not reversible — an issued bypass cannot be redacted.

## Cross-references

- **Implementation:** `src/finserv_agent_audit/governance/sovereign_veto.py`
- **Tests:** `tests/test_sovereign_veto.py`
- **Related ADRs:** ADR-0001 (DEFCON, filters which veto checks load) · ADR-0003 (Hash-chain Audit, records every veto) · ADR-0004 (Autonomy Ladder, A3 requires veto live and load-tested)
