# COSO Internal Control over AI — Control Mapping for Autonomous AI Agents

This document maps the governance patterns in this repository to the
Committee of Sponsoring Organizations of the Treadway Commission's
("COSO") guidance on internal control over artificial intelligence. The
relevant primary text is *Realize the Full Potential of Artificial
Intelligence* (Deloitte for COSO, 2021), which applies the five components
of the COSO *Internal Control — Integrated Framework* (2013) to AI
systems, and the November 2024 thought paper *Realize the Full Promise of
Generative AI* (PwC for COSO), which extends the same five-component
treatment to generative AI specifically.

A formal COSO standard titled "Internal Control over AI Reporting" (ICAIR)
has not been issued as of this writing; "ICAIR" is shorthand in
practitioner literature for the application of the COSO ICIF five
components to AI-driven reporting and decision systems. The mapping below
is to the COSO ICIF five components as applied in the 2021 and 2024
COSO-published AI thought papers.

> **Disclaimer:** This mapping is provided for reference only and does not
> constitute legal advice or attestation guidance. Engage qualified
> internal-audit and SOX advisors for your specific control environment.

---

## Framework Overview

COSO's *Internal Control — Integrated Framework* (2013 update of the 1992
original) defines internal control through **five components**, each
elaborated by 17 principles in total:

1. **Control Environment** — tone, structure, accountability.
2. **Risk Assessment** — identification, analysis, response to risk.
3. **Control Activities** — policies and procedures that mitigate risk.
4. **Information and Communication** — internal and external information
   flow that supports control.
5. **Monitoring Activities** — ongoing and separate evaluations.

The 2021 COSO thought paper *Realize the Full Potential of Artificial
Intelligence* applies these five components to AI systems, recommending
that organizations treat AI as a process subject to ICIF rather than a
black-box exception. The 2024 follow-on, *Realize the Full Promise of
Generative AI*, extends the same five-component analysis to LLM-based
systems and explicitly addresses the controls needed for generative
output, prompt-injection risk, and hallucination management.

**Primary source citation:**
- COSO, *Realize the Full Potential of Artificial Intelligence*, prepared
  by Deloitte, December 2021.
- COSO, *Realize the Full Promise of Generative AI*, prepared by PwC,
  November 2024.
- COSO, *Internal Control — Integrated Framework* (2013).
[VERIFIED — COSO public ERM-guidance index confirms 2021 AI paper is
publicly available; the 2024 generative-AI follow-on is published via
COSO's knowledge hub. Cross-checked with COSO ERM-guidance page index
on 2026-05-28.]

---

## Why This Applies to FSI Agent Systems

Public-company FSI organizations operate under SOX § 404 internal-control
attestation. When an AI agent influences or generates data that feeds
financial reporting (allowance-for-credit-loss models, market-data
ingestion for fair-value measurement, IFRS 9 / CECL forecasting,
operational-loss event capture, fraud-detection workflows), the agent is
a control-relevant system. The COSO ICIF five components are the standard
mental model used by external auditors when scoping SOX testing of those
systems.

The 2024 generative-AI paper is the practitioner reference cited by Big
Four audit firms when advising clients on SOX-relevant AI controls.

---

## Control Mapping Table

| COSO ICIF Component | Principle Detail | Pattern in This Repo | File |
|---|---|---|---|
| 1. Control Environment | Principle 1 — Commitment to integrity and ethical values | Autonomy Ladder A0–A4 — published, authoritative classification of decision-level human involvement | `docs/autonomy_ladder.md` |
| 1. Control Environment | Principle 3 — Management establishes structures and authorities | Sovereign Veto authority is named and documented | `patterns/sovereign_veto.py` |
| 1. Control Environment | Principle 5 — Holds individuals accountable | Audit Chain records the human override on every veto event | `patterns/sovereign_veto.py`, `schemas/audit_event.py` |
| 2. Risk Assessment | Principle 7 — Identifies and analyzes risk | DEFCON state machine — continuous risk-state evaluation | `examples/defcon_state_machine.py` |
| 2. Risk Assessment | Principle 8 — Assesses fraud risk | Audit Chain tamper-detection function | `schemas/audit_event.py` |
| 2. Risk Assessment | Principle 9 — Identifies and analyzes significant change | Drift Monitor detects statistical divergence post-deployment | `patterns/drift_monitor.py` (v1.1) |
| 3. Control Activities | Principle 10 — Selects and develops control activities | DEFCON transitions are executable control activities, not narrative policy | `examples/defcon_state_machine.py` |
| 3. Control Activities | Principle 11 — Selects and develops general controls over technology | Audit Chain hash-chain integrity; Sovereign Veto kill-switch | `schemas/audit_event.py`, `patterns/sovereign_veto.py` |
| 3. Control Activities | Principle 12 — Deploys through policies and procedures | Pattern code IS the policy; deployable, version-controlled, testable | repository-wide |
| 4. Information and Communication | Principle 13 — Uses relevant information | Explainability Stub captures decision rationale at the moment of decision | `patterns/explainability_stub.py` (v1.1) |
| 4. Information and Communication | Principle 14 — Communicates internally | DEFCON state is broadcast to dependent systems on every transition | `examples/defcon_state_machine.py` |
| 4. Information and Communication | Principle 15 — Communicates externally | BestInterestCheck and AdverseActionGate produce structured external-facing rationale payloads | `patterns/best_interest_check.py`, `patterns/adverse_action_gate.py` (v1.1) |
| 5. Monitoring Activities | Principle 16 — Ongoing and separate evaluations | Drift Monitor (ongoing) + Audit Chain verifier (separate) | `patterns/drift_monitor.py`, `schemas/audit_event.py` |
| 5. Monitoring Activities | Principle 17 — Evaluates and communicates deficiencies | DEFCON CAUTION/ALERT/DANGER/HALT state transitions are the deficiency communication channel | `examples/defcon_state_machine.py` |

---

## Walkthrough — SOX-Relevant AI Agent Lifecycle

Consider an AI agent that produces CECL forecast inputs for a regional
bank's allowance-for-credit-loss calculation.

1. **Control Environment.** The Autonomy Ladder classifies the CECL-input
   agent as A1 (human in the loop) — the model controller approves each
   forecast batch before it is consumed by accounting. The Sovereign
   Veto authority is named in the model-risk-management policy.
2. **Risk Assessment.** The DEFCON state machine evaluates the agent's
   input-data freshness, macro-variable plausibility, and back-test error
   on each cycle. The Drift Monitor (v1.1) compares the current batch's
   distribution against the validated baseline.
3. **Control Activities.** A DEFCON transition into ALERT automatically
   reduces the agent's autonomy from A1 to A0 — requiring full human
   decision authority on the next forecast run. The Audit Chain records
   every input feature, the model output, and the human approval.
4. **Information and Communication.** The Explainability Stub captures
   the top contributing macro-economic features and their directional
   impact on the forecast. This rationale becomes part of the
   management-review package supporting the allowance posting.
5. **Monitoring Activities.** Internal audit runs the Audit Chain
   verifier quarterly. The verifier produces a tamper-evident attestation
   that no entry between forecast batches has been altered. The external
   SOX auditor uses this attestation as part of their controls-reliance
   testing.

---

## Gap Analysis — What This Repo Does NOT Cover

| COSO ICIF Requirement | Gap | Guidance |
|---|---|---|
| Entity-level controls (tone at the top, governance committees) | Organizational, not technical | Document via board and audit-committee charters |
| Three-Lines-of-Defense organizational design | Org-design exercise | Pair with model-risk-management policy under SR 11-7 |
| Materiality determination for SOX scoping | Auditor-judgment exercise | Engage external auditors |
| Walkthrough documentation in audit work papers | Audit-firm artifact | Generate via audit firm's documentation tools |
| Deficiency aggregation and severity rating | SOX management-process exercise | Use the firm's existing deficiency-tracking system |

---

## References

- COSO, *Internal Control — Integrated Framework* (2013), Committee of
  Sponsoring Organizations of the Treadway Commission.
- COSO, *Realize the Full Potential of Artificial Intelligence*, prepared
  by Deloitte & Touche LLP, December 2021. [https://www.coso.org/]
- COSO, *Realize the Full Promise of Generative AI*, prepared by PwC,
  November 2024.
- COSO, *Enterprise Risk Management — Integrating with Strategy and
  Performance* (2017) — companion ERM framework.
- PCAOB Auditing Standard AS 2201 — *An Audit of Internal Control Over
  Financial Reporting That Is Integrated with an Audit of Financial
  Statements*.
- SR 11-7 — Federal Reserve / OCC *Supervisory Guidance on Model Risk
  Management* (April 4, 2011); applies to model risk and is commonly
  read alongside COSO ICIF for AI in regulated banks.
- Patterns in this repo: `docs/autonomy_ladder.md`,
  `patterns/sovereign_veto.py`, `examples/defcon_state_machine.py`,
  `patterns/drift_monitor.py` (v1.1),
  `patterns/explainability_stub.py` (v1.1),
  `patterns/best_interest_check.py` (Tranche 2C, v1.1),
  `patterns/adverse_action_gate.py` (Tranche 2C, v1.1),
  `schemas/audit_event.py`.
