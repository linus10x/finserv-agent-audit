# NIST AI RMF 1.0 — Control Mapping for Autonomous AI Agents

The **NIST AI Risk Management Framework 1.0** (NIST AI 100-1, published
January 26, 2023) is a voluntary, sector-agnostic framework organized around
four functions — **GOVERN, MAP, MEASURE, MANAGE** — each broken into
categories and subcategories. The companion **AI RMF Playbook** provides
suggested actions per subcategory. For US financial services, the AI RMF is
not itself a binding rule, but federal banking agencies, the SEC, and the
CFPB have all referenced it as an expected reference point; AI / ML model
risk programs that map cleanly to the four functions reduce supervisory
friction and accelerate vendor due diligence.

This document maps each pattern in the repository to the AI RMF subcategories
it materially advances. The pattern stack does not satisfy every subcategory —
many subcategories require organizational process or human judgment — so the
gap-analysis section lists what remains.

> **Disclaimer:** This mapping is provided for reference only and does not
> constitute legal or regulatory advice. AI RMF 1.0 is a voluntary framework;
> binding obligations come from the underlying laws and supervisory guidance
> the framework cross-references.

---

## Control Mapping Table — Four Functions

### GOVERN — Risk culture, accountability, lifecycle policy

| Subcategory | Title (verbatim, AI RMF 1.0) | Pattern in This Repo | File |
|---|---|---|---|
| GOVERN 1.1 | Legal and regulatory requirements involving AI are understood, managed, and documented. | `model_inventory` entries carry the applicable-law tag set (SR 11-7, ECOA, FCRA, BSA, Reg BI, GLBA) | `patterns/model_inventory.py` |
| GOVERN 1.3 | Processes and procedures are in place to determine the needed level of risk management activities based on the organization's risk tolerance. | `autonomy_ladder` A-band per decision class | `docs/autonomy_ladder.md` |
| GOVERN 1.4 | The risk management process and its outcomes are established through transparent policies, procedures, and other controls. | `audit_chain` published schema makes every decision's risk-management trail inspectable | `schemas/audit_event.py` |
| GOVERN 1.5 | Ongoing monitoring and periodic review of the risk management process and its outcomes are planned. | `defcon` state transitions and `mi_proxy` rollups feed a periodic review pack | `examples/defcon_state_machine.py`, `patterns/mi_proxy.py` |
| GOVERN 1.6 | Mechanisms are in place to inventory AI systems and are resourced according to organizational risk priorities. | `model_inventory` — the inventory itself | `patterns/model_inventory.py` |
| GOVERN 1.7 | Processes and procedures are in place for decommissioning and phasing out of AI systems safely. | `model_inventory` retirement state plus `audit_chain` final-decision record | `patterns/model_inventory.py`, `schemas/audit_event.py` |
| GOVERN 2.1 | Roles and responsibilities and lines of communication related to mapping, measuring, and managing AI risks are documented. | `autonomy_ladder` names the responsible role per A-band | `docs/autonomy_ladder.md` |
| GOVERN 2.3 | Executive leadership of the organization takes responsibility for decisions about risks associated with AI system development and deployment. | Board-approved A-band ceiling per decision class; `sovereign_veto` activations escalate to named executives | `patterns/sovereign_veto.py` |
| GOVERN 3.2 | Policies and procedures are in place to define and differentiate roles and responsibilities for human-AI configurations and oversight of AI systems. | `autonomy_ladder` (A0 → A4) plus `sovereign_veto` clearance role | `docs/autonomy_ladder.md`, `patterns/sovereign_veto.py` |
| GOVERN 4.3 | Organizational practices are in place to enable AI testing, identification of incidents, and information sharing. | `shadow_mode` (testing) and `audit_chain` (incident trail) | `patterns/shadow_mode.py`, `schemas/audit_event.py` |
| GOVERN 6.1 | Policies and procedures are in place that address AI risks associated with third-party entities. | `vendor_score_gate` | `patterns/vendor_score_gate.py` |
| GOVERN 6.2 | Contingency processes are in place to handle failures or incidents in third-party data or AI systems deemed to be high-risk. | `defcon` autonomy degradation on third-party signal failure | `examples/defcon_state_machine.py` |

### MAP — Context, categorization, risk surface

| Subcategory | Title (verbatim, AI RMF 1.0) | Pattern in This Repo | File |
|---|---|---|---|
| MAP 1.1 | Intended purpose, potentially beneficial uses, context-specific laws, norms and expectations, and prospective settings in which the AI system will be deployed are understood and documented. | `model_inventory` purpose field + applicable-law tags | `patterns/model_inventory.py` |
| MAP 1.5 | Organizational risk tolerances are determined and documented. | `autonomy_ladder` A-band assignment per decision class | `docs/autonomy_ladder.md` |
| MAP 2.1 | The specific task, and methods used to implement the task, that the AI system will support is defined. | `model_inventory` task definition; `audit_chain` carries the per-decision task tag | `patterns/model_inventory.py`, `schemas/audit_event.py` |
| MAP 2.2 | Information about the AI system's knowledge limits and how system output may be utilized and overseen by humans is documented. | `autonomy_ladder` documents the human-clearance and override mechanism per band | `docs/autonomy_ladder.md` |
| MAP 3.5 | Processes for human oversight are defined, assessed, and documented in accordance with organizational policies from GOVERN function. | `sovereign_veto` is the oversight gate; activations are documented | `patterns/sovereign_veto.py` |
| MAP 4.1 | Approaches for mapping AI technology and legal risks of its components – including the use of third-party data or software – are in place. | `vendor_score_gate` plus `model_inventory` third-party tags | `patterns/vendor_score_gate.py`, `patterns/model_inventory.py` |
| MAP 4.2 | Internal risk controls for components of the AI system including third-party AI technologies are identified and documented. | `vendor_score_gate` enforcement record written to `audit_chain` | `patterns/vendor_score_gate.py` |

### MEASURE — Metrics, evaluation, monitoring

| Subcategory | Title (verbatim, AI RMF 1.0) | Pattern in This Repo | File |
|---|---|---|---|
| MEASURE 1.1 | Approaches and metrics for measurement of AI risks enumerated during the Map function are selected for implementation starting with the most significant AI risks. | `mi_proxy` metric set is prioritized by A-band | `patterns/mi_proxy.py` |
| MEASURE 1.3 | Internal experts who did not serve as front-line developers for the system and/or independent assessors are involved in regular assessments. | `shadow_mode` is run by the second line; results are independent | `patterns/shadow_mode.py` |
| MEASURE 2.1 | Test sets, metrics, and details about the tools used during test, evaluation, validation, and verification (TEVV) are documented. | `audit_chain` records the TEVV run, dataset hash, and tool version | `schemas/audit_event.py` |
| MEASURE 2.3 | AI system performance or assurance criteria are measured qualitatively or quantitatively and demonstrated for conditions similar to deployment setting(s). | `shadow_mode` runs the candidate against live inputs without binding effect | `patterns/shadow_mode.py` |
| MEASURE 2.4 | The functionality and behavior of the AI system and its components are monitored when in production. | `mi_proxy` plus `defcon` state machine | `patterns/mi_proxy.py`, `examples/defcon_state_machine.py` |
| MEASURE 2.5 | The AI system to be deployed is demonstrated to be valid and reliable. | `shadow_mode` agreement / divergence record gated against an A-band ceiling | `patterns/shadow_mode.py` |
| MEASURE 2.7 | AI system security and resilience are evaluated and documented. | `witness_anchor` provides tamper-evidence; `defcon` degrades autonomy on resilience signals | `patterns/witness_anchor.py`, `examples/defcon_state_machine.py` |
| MEASURE 2.8 | Risks associated with transparency and accountability are examined and documented. | `audit_chain` rationale field per decision; `autonomy_ladder` publication | `schemas/audit_event.py`, `docs/autonomy_ladder.md` |
| MEASURE 2.11 | Fairness and bias are evaluated and results are documented. | `equity_audit` runs the fair-lending / disparate-impact battery and writes results to `audit_chain` | `patterns/equity_audit.py` |

### MANAGE — Response, mitigation, escalation

| Subcategory | Title (verbatim, AI RMF 1.0) | Pattern in This Repo | File |
|---|---|---|---|
| MANAGE 1.2 | Treatment of documented AI risks is prioritized based on impact, likelihood, or available resources or methods. | `defcon` thresholds are tuned by A-band blast radius | `examples/defcon_state_machine.py` |
| MANAGE 1.3 | Responses to the AI risks deemed high priority as identified by the Map function, are developed, planned, and documented. | `sovereign_veto` is the documented high-priority response path | `patterns/sovereign_veto.py` |
| MANAGE 2.3 | Procedures are followed to respond to and recover from a previously unknown risk when it is identified. | `defcon` degradation plus `sovereign_veto` activation; recovery is gated by a documented re-promotion path | `examples/defcon_state_machine.py`, `patterns/sovereign_veto.py` |
| MANAGE 2.4 | Mechanisms are in place and applied to supersede, disengage, or deactivate AI systems demonstrating performance inconsistent with intended use. | `sovereign_veto` is the hard stop; `defcon` is the graduated stop | `patterns/sovereign_veto.py`, `examples/defcon_state_machine.py` |
| MANAGE 3.1 | AI risks and benefits from third-party resources are regularly monitored, and risk controls are applied and documented. | `vendor_score_gate` continuous re-scoring; results written to `audit_chain` | `patterns/vendor_score_gate.py` |
| MANAGE 3.2 | Pre-trained models used for development are monitored as part of AI system regular monitoring and maintenance. | `vendor_score_gate` covers foundation models; `mi_proxy` covers drift | `patterns/vendor_score_gate.py`, `patterns/mi_proxy.py` |
| MANAGE 4.1 | Post-deployment AI system monitoring plans are implemented, including mechanisms for capturing input from users and other relevant AI actors. | `audit_chain` ingests user override events and adverse-action feedback (`adverse_action_gate`) | `schemas/audit_event.py`, `patterns/adverse_action_gate.py` |
| MANAGE 4.3 | Incidents and errors are communicated to relevant AI actors including affected communities. | `adverse_action_gate` triggers the FCRA / ECOA notification path; `audit_chain` carries the notification record | `patterns/adverse_action_gate.py`, `schemas/audit_event.py` |

---

## Risk-Tiering Walkthrough

AI RMF 1.0 does not impose a fixed tier scheme; it requires the organization to
set its own per the GOVERN 1.3 and MAP 1.5 subcategories. The
`autonomy_ladder` A-band scheme is the repository's recommended tiering and
maps as follows:

| A-band | Decision character | AI RMF MAP categorization | AI RMF MANAGE response posture |
|---|---|---|---|
| A0 | Advisory only — no binding effect | Low impact | Monitor (`mi_proxy`) |
| A1 | Bounded action with human sign-off | Low-medium | `sovereign_veto` available, `shadow_mode` parallel run |
| A2 | Bounded action, post-hoc review | Medium | Active `defcon` thresholds, sampled human review |
| A3 | Production action, exception-only review | Medium-high | Full `defcon` + `mi_proxy`; second-line `shadow_mode` continuous |
| A4 | Sovereign-only — irreversible / fiduciary | High | `sovereign_veto` mandatory pre-commit; `witness_anchor` on every record |

---

## Gap Analysis — What This Repo Does NOT Cover

The pattern stack is a technical control layer. The following AI RMF
subcategories require organizational, workforce, or stakeholder work the code
cannot supply.

| AI RMF Subcategory | Gap | Guidance |
|---|---|---|
| GOVERN 2.2 — AI risk management training | Workforce program | Build a role-keyed training curriculum keyed to the A-band a person can authorize. |
| GOVERN 3.1 — Diverse decision-making team | Hiring and team design | Outside the repository scope. |
| GOVERN 4.1 — Critical-thinking, safety-first culture | Cultural program | Pair the pattern stack with a published incident-review cadence. |
| GOVERN 5.1, 5.2 — External stakeholder feedback | External engagement | Stand up an external feedback channel and route inputs into the `audit_chain` for traceability. |
| MAP 1.2 — Diverse inter-disciplinary AI actors | Team composition | Outside the repository scope. |
| MAP 1.3 — Mission alignment | Strategy artifact | Document mission alignment in the `model_inventory` purpose field. |
| MAP 3.1, 3.2 — Benefit / cost examination | Business-case work | Capture in the model-inventory entry; not a code artifact. |
| MEASURE 2.2 — Human-subject evaluation requirements | Research-ethics process | Engage IRB / privacy office where applicable. |
| MEASURE 2.6 — Safety risk evaluation | Safety case | Safety-case authoring is outside the code surface; the patterns supply the run-time controls. |
| MEASURE 2.10 — Privacy risk | Privacy program | See `docs/glba_mapping.md` for the GLBA-keyed privacy control surface. |
| MANAGE 1.4 — Residual risk documented to downstream parties | Disclosure workflow | Build a downstream-disclosure pack from the `audit_chain` for any model whose output is shared. |
| MANAGE 4.2 — Continual improvement engagement | Cadence | Stand up a quarterly review keyed off `audit_chain` and `mi_proxy` rollups. |

---

## References

- National Institute of Standards and Technology. _AI Risk Management Framework
  1.0_ (NIST AI 100-1). January 26, 2023.
  <https://www.nist.gov/itl/ai-risk-management-framework>
  (retrieved 2026-05-28).
- NIST. _AI RMF Playbook — GOVERN._
  <https://airc.nist.gov/airmf-resources/playbook/govern/>
  (retrieved 2026-05-28; subcategory titles for GOVERN verified verbatim).
- NIST. _AI RMF Playbook — MAP._
  <https://airc.nist.gov/airmf-resources/playbook/map/>
  (retrieved 2026-05-28; subcategory titles for MAP verified verbatim).
- NIST. _AI RMF Playbook — MEASURE._
  <https://airc.nist.gov/airmf-resources/playbook/measure/>
  (retrieved 2026-05-28; subcategory titles for MEASURE verified verbatim).
- NIST. _AI RMF Playbook — MANAGE._
  <https://airc.nist.gov/airmf-resources/playbook/manage/>
  (retrieved 2026-05-28; subcategory titles for MANAGE verified verbatim).
- NIST. _AI RMF Generative AI Profile_ (NIST-AI-600-1). July 26, 2024
  [UNVERIFIED — primary source not fetched: https://airc.nist.gov/AI_RMF_Knowledge_Base/Roadmap/Generative_AI_Profile;
  reference confirmed via the AI RMF landing page on 2026-05-28].
