# ADR-0004: Autonomy Ladder A0 to A4

**Status:** Accepted
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel. No attorney-client relationship is formed by use of this ADR. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

---

## Context

Three case-of-record regulatory matters in financial services illustrate the cost of AI operating above the autonomy level its **assurance case** (Kelly & Weaver 2004; Bloomfield et al. 2021) could defend:

- **Apple Card / Goldman Sachs DFS consent order (October 2023)** — NYDFS settlement with Goldman Sachs Bank USA for credit-decisioning practices on the Apple Card; the underlying issue was an automated decision system operating at an autonomy tier the supporting assurance case could not defend against a fair-lending challenge. [UNVERIFIED — primary source not fetched]
- **Knight Capital (August 1, 2012)** — $440M loss in 45 minutes from an algorithmic-trading deployment that was operationally at full autonomy without a working circuit-breaker; the post-incident analysis is now the standard reference for "autonomy without runtime kill is settlement-class risk." [UNVERIFIED — primary source not fetched]
- **CFPB enforcement actions on adverse-action notice quality for AI-driven credit decisions (multiple matters, 2023–2025)** — pattern of enforcement around the explainability gap when an automated decisioning system operates at full autonomy and the firm cannot produce a regulator-defensible explanation of any individual decision. [UNVERIFIED — primary source not fetched]

"Is this AI program ready for production?" is the wrong question. The question is "at what level of autonomy is this program ready, and what is the next promotable tier?" A program at full autonomy on a low-risk read-only task is shipping. A program at full autonomy on a model whose SR 11-7 validation report flags material limitations is a settlement waiting to happen.

The conventional answer is a binary "human-in-loop" / "fully autonomous." The binary is wrong. Regulators (EU AI Act Article 14, NIST AI RMF Govern), institutional investors, and internal risk committees all distinguish between tiers of autonomy with different controls at each tier.

## Decision

Adopt the **Autonomy Ladder A0 to A4**, five named maturity tiers with a documented compose pattern at each tier and an explicit promotion gate between tiers.

```
A0 INFORMATIONAL
   Agent reads. Agent recommends. No write authority.
   Use case: model-flagged exception flagging for credit officer review;
             trade-idea surfacing to a portfolio manager.

A1 ASSISTED
   Agent reads. Agent drafts. Human approves every write.
   Use case: KYC/AML adjudication drafts presented for analyst signature;
             pre-trade order suggestions presented to a trader.

A2 DELEGATED
   Agent reads and writes for low-risk decisions inside a hard envelope.
   Human approves a sampled subset and all out-of-envelope decisions.
   Use case: routine alert disposition in transaction monitoring; rebalancing
             execution within a pre-approved drift band on a model portfolio.

   --- A2 to A3 promotion is the regulator-visible boundary. ---
   --- Runtime circuit-breaker MUST exist AND be tested.    ---

A3 SUPERVISED AUTONOMOUS
   Agent reads and writes for in-scope decision class autonomously.
   Sovereign-veto layer is non-overridable. Audit ledger is live.
   Human supervises by exception, not by approval.
   Use case: pre-trade risk envelope enforcement on agent-generated orders
             under SR 11-7 second-line oversight; sanctions screening with
             EDD-band veto.

A4 PRODUCTION AUTONOMOUS
   A3 plus inter-agent orchestration, monitor-led promotion of new
   capabilities, and operator-validated escalation paths.
   Use case: portfolio-wide rebalancing across strategies with sovereign veto
             on concentration, borrowing-exposure, and ECOA-style constraint
             surfaces.
```

The A2 to A3 promotion gate is the regulator-visible boundary. Under the SR 11-7 three-lines-of-defense model, A3 promotion is the point at which the second line (risk and compliance) and third line (internal audit) sign on to the agent operating with non-overridable runtime controls in place. Promotion requires:

1. **Sovereign-veto layer (ADR-0002) live and load-tested** under representative traffic, with the veto-reason-code distribution reviewed by second-line risk.
2. **Audit ledger (ADR-0003) running for at least 90 days** with a regulator-replayable subset; ledger backend is on durable persistence with an external witness anchor schedule documented per ADR-0014.
3. **Shadow Mode (ADR-0006) ran for at least 30 days** with no material divergence between shadow and production decisions.
4. **Circuit-breaker tested** at least quarterly, with the test recorded on the audit ledger.
5. **Model-validation report under SR 11-7** explicitly authorizes the proposed autonomy tier; the validation report's "limitations and assumptions" section is mapped to specific reason codes in the Sovereign Veto layer.

The promotion gate is the work, not the framework.

## Alternatives Considered

1. **Binary autonomous / human-in-loop.** Rejected. The binary forces a choice between unscalable (HITL on every decision at FSI scale) and indefensible (full autonomy without the runtime controls regulators now expect). The five-tier ladder maps to the actual control postures firms run.
2. **Continuous numerical autonomy score (0–100).** Rejected. A continuous score is not enumerable to a regulator ("what is your autonomy posture on this workflow?") and produces false precision. Named tiers map to named compose patterns.
3. **Per-decision autonomy negotiation by the agent.** Rejected. The agent cannot be the arbiter of its own autonomy tier. The tier is a property of the workflow plus the assurance case, set by the operator and the second line, not by the agent at runtime.

## Consequences

**Positive.** Programs have a documented promotion path with regulator-defensible criteria. Board risk committees have a tier to point to when explaining their AI program. LP and counterparty letters can specify "operating at A3 with audited circuit-breaker" — a more meaningful claim than "AI-enabled."

**Negative.** Adds vocabulary the organization must learn. Mitigated by the fact that the alternative — implicit, unstated, inconsistent autonomy levels per workflow — costs more in regulatory exposure than the vocabulary investment costs in training.

## Regulatory Mapping

- **SR 11-7** (Federal Reserve / OCC Supervisory Guidance on Model Risk Management, April 4, 2011) — the three-lines-of-defense framing and the model-validation discipline that the A2 to A3 promotion gate operationalizes.
- **OCC 2011-12** (OCC Bulletin 2011-12, companion to SR 11-7) — same substance, OCC-issued. [UNVERIFIED — primary source not fetched]
- **EU AI Act Article 14** (Regulation (EU) 2024/1689) — human oversight requirements scale by risk classification; the autonomy tier of the deployment must match the oversight design. [UNVERIFIED — primary source not fetched]
- **NIST AI RMF** MANAGE 2.3 — risk decisions documented; tiered oversight scaling with risk.
- **FFIEC IT Examination Handbook, Audit booklet** — examiner expectations for evidence of control effectiveness at the autonomy tier the firm represents. [UNVERIFIED — primary source not fetched]

## Pre-mortem

- **Tier inflation.** Pressure to promote to A3 before the four-condition gate is met. Mitigation — promotion evidence pack is an artifact reviewed by second-line risk and signed; reviewer signature is on the audit ledger.
- **Tier regression (A4 to A3 mid-incident).** Operationally messy. Mitigation — documented in the operator's runbook; the DEFCON ladder (ADR-0001) provides the runtime mechanism (DEFCON-3 effectively regresses A4 to A3-equivalent posture).
- **Cross-system tier transferability assumption.** An A3 in one firm's stack is not necessarily A3 in another's; the tier is local to the assurance case. Mitigation — public-facing claims of A3/A4 must cite the workflow scope and the assurance case.
- **Tier set on the wrong granularity.** A firm declares "the AI program is at A3" when in fact the trading agent is at A2 and the KYC agent is at A3. Mitigation — autonomy tier is a property of the *workflow plus model plus decision-class*, never of "the program" as a monolith.

## Reversibility

Tier demotion is supported and tested (an A3 program can be demoted to A2 with documented justification and the demotion entry on the audit ledger). The ladder structure itself is reversible: a deployer can drop to a binary HITL / autonomous posture, with the cost being loss of regulator-defensible promotion-gate evidence. Individual tiers can be reordered or renamed without disturbing the compose-pattern structure, though doing so breaks cross-deployer comparability.

## Cross-references

- **Implementation:** Autonomy tier is metadata on every audit entry (`schemas/audit_event.py`); the tier-to-compose-pattern mapping is enforced at agent-boundary wiring time (caller wiring layer, not enforced inside `src/finserv_agent_audit/governance/`).
- **Prior art and lineage:** SAE J3016 (driving-automation 0–5 ladder); OECD AI Principles (2019); NIST AI RMF 1.0 (2023) MANAGE 2.3; Shavit et al. (2023) *Practices for Governing Agentic AI Systems*; Anderljung et al. (2023) *Frontier AI Regulation*; Kelly & Weaver (2004), Bloomfield et al. (2021) on assurance cases.
- **Related ADRs:** ADR-0001 (DEFCON, runtime risk-state) · ADR-0002 (Sovereign Veto, required for A3 and above) · ADR-0003 (Hash-chain Audit, 90-day history required for A3 promotion) · ADR-0006 (Shadow Mode, 30-day clean run required for A3 promotion) · ADR-0014 (External-Witness Anchoring, named on the A3 promotion evidence pack)
- **Web:** [autonomy-ladder.io](https://autonomy-ladder.io) — self-score demo for the framework.
