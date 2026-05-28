# ISO/IEC 42001:2023 — Control Mapping for Autonomous AI Agents

This document maps the governance patterns in this repository to ISO/IEC
42001:2023, the international management-system standard for artificial
intelligence ("AI Management System" or AIMS). Any organization pursuing
a third-party-certifiable AI governance program in financial services
will benchmark against this standard.

> **Disclaimer:** This mapping is provided for reference only and does not
> constitute legal advice. Engage a qualified accredited certification body
> for a formal AIMS conformity assessment.

---

## Framework Overview

ISO/IEC 42001:2023, *Information technology — Artificial intelligence —
Management system*, was published by ISO and IEC in **December 2023**.
It is the first internationally agreed AI management-system standard and
adopts the High-Level Structure ("HLS") shared by ISO/IEC 27001 (ISMS),
ISO 9001 (QMS), and other ISO management-system standards.

The standard is **certifiable**: an accredited certification body can
audit an organization's AIMS and issue a certificate, exactly as with
ISO 27001. The seven management-system clauses (4 through 10) are
required; the Annex A reference controls are normative for organizations
declaring conformity.

**Primary source citation:** ISO/IEC 42001:2023, *Information technology —
Artificial intelligence — Management system*, first edition, December 2023.
[ABSTRACT-ONLY — full text behind paywall at iso.org/standard/81230.html;
mapping below is built from the publicly available abstract, foreword,
table of contents, and the NIST AI RMF / ISO 42001 published cross-walks.]

The standard's structure (publicly disclosed in the table of contents):

| Clause | Topic | What It Requires |
|---|---|---|
| 4 | Context of the organization | Determine internal/external issues, interested parties, AIMS scope |
| 5 | Leadership | Top-management commitment, AI policy, organizational roles |
| 6 | Planning | Risk and opportunity treatment, AI objectives, change management |
| 7 | Support | Resources, competence, awareness, communication, documented information |
| 8 | Operation | Operational planning, AI risk assessment, AI risk treatment, AI system impact assessment |
| 9 | Performance evaluation | Monitoring, internal audit, management review |
| 10 | Improvement | Nonconformity, corrective action, continual improvement |
| Annex A (normative) | Reference controls | 39 controls grouped by objective (policies, internal organization, resources, impact assessment, system life-cycle, data, information for interested parties, AI use, third-party relationships) |
| Annex B (informative) | Implementation guidance | Per-control guidance |
| Annex C (informative) | Potential AI-related organizational objectives and risk sources | |
| Annex D (informative) | Use of the AIMS across domains and sectors | |

---

## Control Mapping Table

| ISO/IEC 42001 Clause / Annex A Control | Pattern in This Repo | File |
|---|---|---|
| Clause 5.2 — AI policy | Autonomy Ladder A0–A4 documented as the operating AI policy | `docs/autonomy_ladder.md` |
| Clause 6.1.2 — AI risk assessment | DEFCON state machine — operational risk-state evaluation per cycle | `examples/defcon_state_machine.py` |
| Clause 6.1.3 — AI risk treatment | DEFCON transitions implement treatment (sizing reduction, halt) | `examples/defcon_state_machine.py` |
| Clause 6.1.4 — AI system impact assessment | Pre-deployment Shadow Mode Rollout produces side-by-side impact evidence | `patterns/shadow_mode.py` (v1.1) |
| Clause 8.2 — AI system impact assessment (operational) | Drift Monitor surfaces post-deployment impact deltas | `patterns/drift_monitor.py` (v1.1) |
| Clause 8.3 — AI risk treatment (operational) | Sovereign Veto — hard stop with documented human clearance | `patterns/sovereign_veto.py` |
| Clause 9.1 — Monitoring, measurement, analysis, evaluation | Audit Chain — every decision, input, and state transition is logged | `schemas/audit_event.py` |
| Clause 9.2 — Internal audit | Audit Chain verifier function detects tampering across the ledger | `schemas/audit_event.py` |
| Clause 9.3 — Management review | Autonomy Ladder + DEFCON state are review inputs by design | `docs/autonomy_ladder.md`, `examples/defcon_state_machine.py` |
| Clause 10.2 — Nonconformity and corrective action | DEFCON hysteresis — de-escalation requires sustained confirmation, not single-event reset | `examples/defcon_state_machine.py` |
| Annex A.6.2.2 — System life cycle | Shadow Mode → live promotion gated by Drift Monitor thresholds | `patterns/shadow_mode.py` (v1.1) |
| Annex A.6.2.6 — AI system operation and monitoring | DEFCON + Drift Monitor + Audit Chain together | multiple |
| Annex A.6.2.7 — AI system technical documentation | Explainability Stub captures per-decision rationale; AuditEvent carries the payload | `patterns/explainability_stub.py` (v1.1) |
| Annex A.6.2.8 — Recording of event logs | Hash-chained AuditEvent ledger | `schemas/audit_event.py` |
| Annex A.7 — Data for AI systems | Audit Chain captures input vectors per decision (data lineage at decision point) | `schemas/audit_event.py` |
| Annex A.9 — Use of AI systems | Autonomy Ladder classifies each decision class by required human involvement | `docs/autonomy_ladder.md` |

---

## Walkthrough — AIMS Adoption Using This Repository

A regulated FSI organization adopting ISO/IEC 42001 typically follows
this sequence:

1. **Clause 4 — Scope.** Define the AIMS scope: which agent systems,
   which decision classes, which customer populations. This repository
   does not produce the scope document; the Autonomy Ladder is the
   vocabulary that makes the scope unambiguous.
2. **Clause 5 — Policy.** Adopt the Autonomy Ladder A0–A4 as the
   organization's published AI policy. The classification table is the
   policy artifact.
3. **Clause 6 — Planning.** Run AI impact assessments per decision class
   using Shadow Mode Rollout (v1.1) outputs as primary evidence.
4. **Clause 7 — Support.** The repository provides documented patterns
   that satisfy the documented-information requirement for the AIMS
   technical layer.
5. **Clause 8 — Operation.** DEFCON, Sovereign Veto, Drift Monitor, and
   Explainability Stub together provide operational control.
6. **Clause 9 — Performance evaluation.** The Audit Chain plus the
   chain verifier provide the evidence base for internal audit and
   management review.
7. **Clause 10 — Improvement.** DEFCON hysteresis enforces that
   corrective actions are confirmed before they are accepted, preventing
   the common audit finding of "ineffective corrective action."

---

## Gap Analysis — What This Repo Does NOT Cover

| ISO/IEC 42001 Requirement | Gap | Guidance |
|---|---|---|
| Clause 5.3 — Organizational roles, responsibilities, authorities | RACI / RAPID at the org level | Document via organizational policy |
| Clause 7.2 — Competence | AI workforce training program | Pair with internal training and certification |
| Clause 7.3 — Awareness | Organization-wide communication | Internal comms program |
| Annex A.4 — Internal organization | AI ethics committee, reporting lines | Org-design exercise |
| Annex A.10 — Third-party and customer relationships | Vendor AIMS due diligence | Supplier-risk-management program |
| Conformity assessment by accredited body | Third-party certification audit | Engage ISO 42001-accredited certification body |

---

## NIST AI RMF Cross-Walk Note

ISO/IEC 42001 and the NIST AI Risk Management Framework (NIST AI 100-1,
January 2023) are complementary. NIST AI RMF organizes around four
functions — Govern, Map, Measure, Manage — and 19 categories. The patterns
in this repository map naturally to both: Autonomy Ladder and DEFCON
correspond to NIST RMF Govern and Manage; Audit Chain corresponds to
Measure; Shadow Mode and Drift Monitor correspond to Map and Measure;
Sovereign Veto corresponds to Manage. Organizations pursuing ISO 42001
certification typically use NIST AI RMF as the implementation playbook
under the ISO clauses, since NIST is freely available and ISO is paywalled.

---

## References

- ISO/IEC 42001:2023, *Information technology — Artificial intelligence —
  Management system*, first edition, December 2023.
  [Public abstract: https://www.iso.org/standard/81230.html]
- NIST AI Risk Management Framework (NIST AI 100-1), version 1.0,
  January 2023.
- BSI public guidance on ISO/IEC 42001 implementation.
- Patterns in this repo: `docs/autonomy_ladder.md`,
  `examples/defcon_state_machine.py`, `patterns/sovereign_veto.py`,
  `patterns/shadow_mode.py` (v1.1), `patterns/drift_monitor.py` (v1.1),
  `patterns/explainability_stub.py` (v1.1), `schemas/audit_event.py`.
