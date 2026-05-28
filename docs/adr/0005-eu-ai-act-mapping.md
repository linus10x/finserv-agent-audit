# ADR-0005 · EU AI Act Mapping for Autonomous FSI Agents

**Status:** Accepted
**Date:** 2026-05-28
**Decider:** Kunjar Bhaduri
**Repo:** finserv-agent-audit v1.1

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel. No attorney-client relationship is formed by use of this ADR. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

## Context

An autonomous AI agent operating inside a regulated financial-services institution — credit decisioning, market-making, surveillance, fraud triage, KYC/AML adjudication, wealth-platform allocation — falls under EU AI Act Annex III (high-risk) when the EU is a deployer jurisdiction. The Act is not optional for a US-headquartered firm with EU clients or EU-resident data subjects; the extraterritorial reach in Art. 2(1)(c) attaches when output is used in the Union.

A buyer-side risk officer asks a single question: "For each Article 9 through 15 requirement, which named pattern in this repository is the architectural answer, and where is the code?" An informal mapping in a README does not survive a regulator examination. A YAML buried in a config tree is not discoverable by counsel. The mapping needs to be an ADR — versioned, dated, citable.

The pre-existing `docs/eu_ai_act_mapping.md` table was a starting point but lacked: ADR status, decision rationale, alternatives considered, pre-mortem, reversibility, and the cross-link to the SR 11-7 overlay (ADR-0007) that US bank examiners will ask for in parallel.

## Decision

Adopt this ADR as the authoritative mapping of each governance pattern in this repository to the corresponding EU AI Act high-risk obligation. The table below is the source of truth; `docs/eu_ai_act_mapping.md` is retained as the reader-friendly summary and links here for normative content.

### Mapping table

| EU AI Act Article | Obligation | Pattern in this repo | Code reference |
|---|---|---|---|
| Art. 9 | Risk management system across the lifecycle | DEFCON state machine — system-wide risk posture with named transitions | `examples/defcon_state_machine.py` (ADR-0001) |
| Art. 10 | Data and data governance — training, validation, testing sets | Vendor Score Gate + Model Inventory entries record dataset provenance | ADR-0010 (Vendor Score Gate), ADR-0011 (Model Inventory) |
| Art. 11 | Technical documentation maintained and current | Per-decision rationale field on every `AuditEvent`; ADRs versioned in-repo | `src/finserv_agent_audit/schemas/audit_event.py` |
| Art. 12 | Automatic recording of events (logs) over lifetime | Tamper-evident hash-chain audit log | `src/finserv_agent_audit/governance/audit_chain.py` (ADR-0003) |
| Art. 13 | Transparency and information to deployers | Autonomy Ladder published per decision class with rationale | `docs/autonomy_ladder.md` (ADR-0004) |
| Art. 14 | Human oversight — effective oversight by natural persons | Sovereign Veto — operator-clearance gate with documented override | `src/finserv_agent_audit/governance/sovereign_veto.py` (ADR-0002) |
| Art. 15 | "Accuracy, robustness and cybersecurity" (statutory title) | DEFCON hysteresis + Shadow Mode pre-promotion testing | `examples/defcon_state_machine.py` + `src/finserv_agent_audit/governance/shadow_mode.py` (ADR-0006) |
| Art. 17 | Quality management system | SR 11-7 three-lines-of-defense overlay applied across all patterns | ADR-0007 |
| Art. 26 | Deployer obligations — monitor operation, suspend on incident | DEFCON-2 (CONTAINMENT) and DEFCON-1 (SHUTDOWN) states | ADR-0001 |
| Art. 72 | Post-market monitoring plan | Audit-chain replay + divergence monitoring on Shadow Mode | ADR-0003 + ADR-0006 |

### High-risk classification under Annex III

An FSI deployment is presumptively high-risk when the agent:

1. Makes or materially influences credit-worthiness or credit-scoring decisions on natural persons (Annex III §5(b))
2. Evaluates risk and pricing for life or health insurance products (Annex III §5(c))
3. Is used for emergency-response triage on financial-stability events (operational analog)
4. Is the determining factor in employment-related decisions inside the institution (Annex III §4)

The full Article 9 through 15 control set attaches when any condition holds. The repository assumes high-risk by default; deployers may downgrade after written assessment.

## Alternatives Considered

- **Keep the mapping as a free-standing markdown table only.** Rejected: not versioned as a decision; no rationale captured; readers cannot tell when the mapping was last reviewed against the published Act text.
- **Embed the mapping inside each per-pattern ADR.** Rejected: produces duplication and drift; a regulator wants one document, not seven.
- **Defer EU AI Act mapping until a deployer requests it.** Rejected: the deployer is the bank, and the bank's procurement gate already requires this artifact at vendor onboarding.

## Consequences

**Positive.** A risk officer maps a regulator question to a code path in one read. The audit ledger can label each entry with the Article numbers satisfied by the gates that passed, producing examination-ready evidence with no extraction step. The ADR is dated, so drift is visible.

**Negative.** EU AI Act delegated acts and harmonized standards are still settling through 2026 and into 2027. Some characterizations here will need refresh. Mitigation: every row carries a code reference; when a row goes stale, the failing test on the code reference is the canary, and the next ADR version supersedes this one with a `Supersedes` header.

**Operational.** The pattern of mapping reg → article → code reference becomes the template for further jurisdictional ADRs (UK FCA, MAS, FINMA, OSFI) without re-architecting the artifact.

## Regulatory Mapping

- EU AI Act — Regulation (EU) 2024/1689, in force August 1, 2024; high-risk obligations apply from August 2, 2026 with phased provisions through August 2, 2027. `[UNVERIFIED — primary OJ text not fetched in this session; dates per published Commission summary]`
- Annex III — high-risk use cases, including credit-worthiness and insurance risk
- Art. 99 — penalties up to EUR 35M or 7% of worldwide turnover for prohibited-practice violations
- Cross-walks to NIST AI RMF (Govern, Map, Measure, Manage) and to SR 11-7 are documented in ADR-0007

## Pre-mortem

What fails:

1. **Article numbering changes** in a recital-driven amendment. Detection: annual review by maintainers cross-checks Article numbers against the consolidated Act text on EUR-Lex; failing checks open a tracked issue.
2. **Pattern code is renamed** without updating the table. Detection: a doc-linter test asserts every code reference in the table resolves to a real file; CI fails on drift.
3. **A deployer treats this ADR as legal sufficiency.** Detection: the disclaimer at the top is repeated in the README compliance section; deployer ackowledges on first install.

## Reversibility

High. Withdrawing the ADR is a single-PR change that removes the table; runtime patterns are unaffected because the mapping is documentary, not executable. The cost of reversal is loss of buyer-side artifact, not loss of safety.

## Cross-references

- ADR-0001 (DEFCON state machine) — Art. 9, Art. 26
- ADR-0002 (Sovereign Veto) — Art. 14
- ADR-0003 (Hash-chain audit) — Art. 12, Art. 72
- ADR-0004 (Autonomy Ladder) — Art. 13
- ADR-0006 (Shadow Mode) — Art. 15, Art. 72
- ADR-0007 (SR 11-7 overlay) — Art. 17 quality-management mapping for US bank examiners
- `docs/eu_ai_act_mapping.md` — reader-friendly summary, normative content lives here
