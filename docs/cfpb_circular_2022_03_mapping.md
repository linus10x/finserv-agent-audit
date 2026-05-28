# CFPB Circular 2022-03 — Control Mapping for Autonomous AI Agents

This document maps the governance patterns in this repository to CFPB
Circular 2022-03, *Adverse Action Notification Requirements in Connection
with Credit Decisions Based on Complex Algorithms* (May 26, 2022). Any
AI agent that produces or materially influences an adverse credit decision
falls inside the scope of this Circular and the underlying Equal Credit
Opportunity Act ("ECOA") and Regulation B regime.

> **Disclaimer:** This mapping is provided for reference only and does not
> constitute legal advice. Engage qualified legal counsel for your specific
> compliance determination.

---

## Framework Overview

The Bureau issued Circular 2022-03 on **May 26, 2022**, answering a single
question with a single answer:

> **Question.** When creditors make credit decisions based on complex
> algorithms that may preclude a straightforward explanation of the reasons
> for an adverse action, do ECOA and Regulation B still require the creditor
> to provide a statement of specific reasons to the applicant?
>
> **Answer.** Yes. Creditors cannot justify non-compliance with ECOA's
> requirement to provide adverse-action reasons on the basis that the
> technology used to make credit decisions is too complicated, too opaque
> in its decision-making, or too new.

The Circular invokes 15 U.S.C. § 1691(d)(2)(A)-(B) and 12 C.F.R. § 1002.9(b)(2),
which require that adverse-action notices include "the specific reasons for
the adverse action" or disclose the applicant's right to request them. A
generic statement of internal standards or model output does not satisfy
this requirement.

The Bureau's reasoning is direct: ECOA's notice requirement serves two
purposes — preventing discrimination by forcing transparent decision logic,
and educating consumers so they can correct errors or improve standing. The
Bureau states explicitly that "a creditor's lack of understanding of its
own methods is therefore not a cognizable defense" under ECOA.

**Primary source citation:** CFPB Circular 2022-03 (May 26, 2022); ECOA
15 U.S.C. § 1691(d); 12 C.F.R. § 1002.9(b)(2); Official Interpretation
to § 1002.9 — Comment 9(b)(2)-3.
[VERIFIED — fetched from consumerfinance.gov on 2026-05-28.]

The position was reinforced in **Circular 2023-03** (September 19, 2023),
which extended the rule by requiring that any of the model-form reason
codes (Form C-1 through C-5 in Appendix C of Regulation B) actually relate
to and accurately describe the factors considered. A creditor cannot pick
a checkbox reason because it is the closest pre-printed option.

---

## Why This Applies to Every AI Credit-Decision Surface

The Circular reaches any creditor that uses "complex algorithms" — explicitly
including machine-learning models, ensemble methods, and any model whose
internal weighting cannot be human-narrated by the lender. This covers:

- Automated underwriting engines that surface accept/decline.
- Pre-approval scoring agents that gate inbound applications.
- Risk-based pricing models that produce counteroffers materially less
  favorable than what the applicant sought.
- Account-management actions (line reductions, account closures) where ECOA
  also requires adverse-action notice under § 1002.9(a)(1)(ii).

If the agent makes or materially shapes any of the above, the agent
pipeline must produce a specific, accurate, principal-reason rationale per
decision — produced before the decision is communicated to the applicant.

---

## Control Mapping Table

| Circular 2022-03 / ECOA Requirement | Citation | Pattern in This Repo | File |
|---|---|---|---|
| Specific principal reasons in adverse-action notice | 12 C.F.R. § 1002.9(b)(2) | AdverseActionGate pattern produces a structured principal-reason rationale; recommendation is blocked if rationale is missing or generic | `patterns/adverse_action_gate.py` (v1.1) |
| Reasons must accurately reflect factors actually considered | Circular 2022-03 § II; Circular 2023-03 | Explainability Stub captures the actual top-K input contributions to the model output | `patterns/explainability_stub.py` (v1.1) |
| 30-day notification window | 12 C.F.R. § 1002.9(a)(1)(i) | Rate Limiter tracks decision-to-notice latency; DEFCON CAUTION on breach | `patterns/rate_limiter.py` (v1.1) |
| Decision auditability for fair-lending exam | ECOA § 706; 12 C.F.R. § 1002.12 (record retention) | Audit Chain — hash-chained decision ledger with 25-month retention path | `schemas/audit_event.py` |
| Human override on edge cases | Implicit in Circular's "lack of understanding is not a defense" | Sovereign Veto — human can halt the agent's adverse-action pipeline | `patterns/sovereign_veto.py` |
| Governance posture under model failure | ECOA fair-lending supervisory expectations | DEFCON state machine — halts new adverse-action issuance when drift or error rate breaches threshold | `examples/defcon_state_machine.py` |
| Classification of decision autonomy | Supervisory expectation under fair-lending | Autonomy Ladder A0–A4 — typically A1 or A2 for adverse-action surfaces | `docs/autonomy_ladder.md` |

---

## Walkthrough — Single Adverse-Action Lifecycle

A consumer-lending agent scores an unsecured-personal-loan application.

1. **Model scoring.** The underlying ML model produces a score and a
   decision (decline).
2. **Explainability capture.** The Explainability Stub (v1.1) captures the
   top contributing features and their directional contributions
   (e.g., revolving utilization +0.42, recent inquiries +0.31, length of
   credit history -0.18). This satisfies the Circular's "accurately
   describe the factors actually considered" requirement.
3. **AdverseActionGate.** The gate (Tranche 2C, v1.1) verifies the
   rationale is non-empty, names specific principal reasons, and maps to
   the model-form codes in Appendix C of Regulation B. If the rationale is
   generic ("internal standards") or refers to model opacity, the decline
   is blocked and routed to human review.
4. **30-day clock.** A timer fires on decision entry. If the notice has
   not been issued within 30 days, the Rate Limiter raises an event and
   the AuditEvent is flagged.
5. **Audit Chain.** Every input, the model output, the explainability
   payload, and the principal-reason rationale are hash-chained into the
   ledger. Any tampering between the decision moment and a later
   fair-lending exam is detectable by the chain verifier.
6. **Sovereign Veto.** A compliance officer can halt the entire automated
   adverse-action pipeline if drift or fair-lending disparate-impact
   thresholds are breached. The veto state is itself audited.
7. **Autonomy classification.** For adverse-action surfaces in regulated
   consumer credit, the Autonomy Ladder default is A1 (human in the loop)
   or A2 (human on the loop) — A3/A4 are not appropriate because the
   regulatory consequences of a wrong, opaque decline are immediate.

---

## Gap Analysis — What This Repo Does NOT Cover

| Requirement | Gap | Guidance |
|---|---|---|
| Form-letter generation (Reg B Appendix C model forms) | Customer-facing document generation, not agent decision logic | Generate via consumer-communications system using the rationale payload as input |
| Disparate-impact testing | Statistical fairness testing of model outputs | Pair this repo with a fairness-testing library (e.g., Aequitas) plus periodic fair-lending audit |
| Demographic-data segregation under Reg B § 1002.5(b) | Lawful collection and segregation of monitoring information | Handle in data-architecture layer |
| ECOA right to receive a copy of the appraisal (for secured credit) | Real-property-secured credit specific obligation | Out of scope for unsecured-credit agent patterns |
| State-level UDAAP overlays | State attorneys general may impose additional explanation requirements | Engage state-by-state counsel |

---

## References

- CFPB Circular 2022-03, *Adverse Action Notification Requirements in
  Connection with Credit Decisions Based on Complex Algorithms*
  (May 26, 2022).
- CFPB Circular 2023-03, *Adverse Action Notification Requirements and the
  Proper Use of the CFPB's Sample Forms Provided in Regulation B*
  (September 19, 2023).
- 15 U.S.C. § 1691 et seq. — Equal Credit Opportunity Act.
- 12 C.F.R. Part 1002 — Regulation B; Appendix C model forms; Comment
  9(b)(2)-3.
- Patterns in this repo: `patterns/adverse_action_gate.py` (Tranche 2C,
  v1.1), `patterns/explainability_stub.py` (v1.1),
  `patterns/rate_limiter.py` (v1.1), `patterns/sovereign_veto.py`,
  `schemas/audit_event.py`, `examples/defcon_state_machine.py`,
  `docs/autonomy_ladder.md`.
