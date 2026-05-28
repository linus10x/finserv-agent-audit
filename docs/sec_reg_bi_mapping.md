# SEC Regulation Best Interest — Control Mapping for Autonomous AI Agents

This document maps the governance patterns in this repository to specific
obligations under SEC Regulation Best Interest, 17 C.F.R. § 240.15l-1 ("Reg BI").
Any broker-dealer that uses an AI agent to generate, surface, or systematically
influence a securities recommendation to a retail customer is squarely inside
Reg BI's recommendation perimeter.

> **Disclaimer:** This mapping is provided for reference only and does not
> constitute legal advice. Engage qualified legal counsel for your specific
> compliance determination.

---

## Framework Overview

The SEC adopted Reg BI on June 5, 2019 (Release No. 34-86031), with a
compliance date of **June 30, 2020**. The rule establishes a best-interest
standard of conduct that applies when a broker-dealer or associated person
makes a recommendation of any securities transaction or investment strategy
involving securities to a "retail customer."

A natural-language definition will not survive an enforcement letter; the rule
imposes four discrete component obligations that must all be satisfied:

1. **Disclosure Obligation** — § 240.15l-1(a)(2)(i): full and fair written
   disclosure of all material facts relating to the scope and terms of the
   relationship and all material facts relating to conflicts of interest.
2. **Care Obligation** — § 240.15l-1(a)(2)(ii): the broker-dealer must
   exercise reasonable diligence, care, and skill to (A) understand the risks,
   rewards, and costs of the recommendation, (B) have a reasonable basis to
   believe the recommendation is in the retail customer's best interest, and
   (C) have a reasonable basis to believe a series of recommended transactions
   is not excessive.
3. **Conflict of Interest Obligation** — § 240.15l-1(a)(2)(iii): written
   policies and procedures reasonably designed to identify, disclose, mitigate,
   or eliminate conflicts of interest associated with the recommendation.
4. **Compliance Obligation** — § 240.15l-1(a)(2)(iv): written policies and
   procedures reasonably designed to achieve compliance with Reg BI as a whole.

A "retail customer" under § 240.15l-1(b)(1) is a natural person (or the legal
representative of a natural person) who receives and uses a recommendation
primarily for personal, family, or household purposes.

**Primary source citation:** 17 C.F.R. § 240.15l-1; SEC Release No. 34-86031
(June 5, 2019); compliance date June 30, 2020.
[VERIFIED — corroborated via FINRA Reg BI key-topics page and SEC release record.]

---

## Why Reg BI Applies to AI Agent Pipelines

Reg BI does not exempt algorithmically generated recommendations. The SEC's
April 26, 2023 risk alert from the Division of Examinations
(*Observations from Broker-Dealer Examinations Related to Reg BI*) confirmed
that any system that selects, ranks, or surfaces securities to a retail
customer is subject to the same four obligations as a human registered
representative. A "robo-advisor" wrapper does not move the agent outside the
recommendation perimeter; if anything, automation increases the surface area
of the Care and Conflict obligations because the agent operates at scale.

The July 2023 SEC proposed rule on predictive data analytics (Release No.
34-97990) further signaled that the Commission treats AI-driven nudges,
prompts, and personalization as recommendations whenever they materially
influence a retail decision.

---

## Control Mapping Table

| Reg BI Obligation | Citation | Pattern in This Repo | File |
|---|---|---|---|
| Disclosure Obligation — material facts on relationship | § 240.15l-1(a)(2)(i) | BestInterestCheck pattern emits a structured disclosure payload per recommendation | `patterns/best_interest_check.py` (v1.1) |
| Care Obligation — reasonable basis to believe in best interest | § 240.15l-1(a)(2)(ii)(B) | BestInterestCheck enforces a pre-recommendation gate; rejected recommendations never reach the customer | `patterns/best_interest_check.py` (v1.1) |
| Care Obligation — series-of-transactions test | § 240.15l-1(a)(2)(ii)(C) | Rate Limiter caps recommendation frequency per customer; flags excessive activity | `patterns/rate_limiter.py` (v1.1) |
| Conflict of Interest Obligation — identify and mitigate | § 240.15l-1(a)(2)(iii) | Audit Chain records every input that fed the recommendation, enabling conflict review | `schemas/audit_event.py` |
| Conflict of Interest Obligation — eliminate sales-contest incentives | § 240.15l-1(a)(2)(iii)(D) | Sovereign Veto blocks any recommendation flagged as incentive-driven | `patterns/sovereign_veto.py` |
| Compliance Obligation — written policies and procedures | § 240.15l-1(a)(2)(iv) | DEFCON state machine documents escalation and de-escalation as executable policy | `examples/defcon_state_machine.py` |
| Compliance Obligation — supervisory review | § 240.15l-1(a)(2)(iv) | Autonomy Ladder A0–A4 fixes the human-review level per recommendation class | `docs/autonomy_ladder.md` |

---

## Walkthrough — Single Recommendation Lifecycle

Consider an autonomous agent surfacing a leveraged-ETF rebalance to a retail
customer.

1. **Pre-recommendation gate.** BestInterestCheck (v1.1) evaluates the
   prospective recommendation against the customer's investment profile,
   liquidity needs, risk tolerance, and cost profile. A failed check produces
   an AuditEvent with a structured rationale and the recommendation is
   suppressed. This satisfies the Care Obligation's reasonable-basis test.
2. **Frequency gate.** The Rate Limiter checks whether the recommendation
   would push the customer past a series-of-transactions threshold. A
   threshold breach triggers a DEFCON CAUTION transition for that account.
3. **Disclosure payload.** On pass, BestInterestCheck emits a disclosure
   payload covering the material facts of the recommendation and any
   identified conflicts.
4. **Conflict review.** The recommendation, the disclosure payload, and the
   full input vector are written to the Audit Chain. The hash-chained ledger
   means a later compliance review can reconstruct the exact state at the
   moment of recommendation.
5. **Sovereign Veto path.** A compliance officer can revoke the recommendation
   class at any time. The veto is a hard stop and is itself audited.
6. **Supervisory record.** The Autonomy Ladder classification for this
   recommendation type (A2 — human on the loop, in this example) is recorded
   on the AuditEvent so the supervisory review is traceable.

The repository does not generate the Form CRS relationship summary or the
account-opening disclosures; those are produced upstream by the broker-dealer
and are out of scope for an agent-decision-layer pattern library.

---

## Gap Analysis — What This Repo Does NOT Cover

| Reg BI Requirement | Gap | Guidance |
|---|---|---|
| Form CRS relationship summary | Customer-facing document; not an agent-decision artifact | Generate via firm's customer onboarding system |
| Pre-trade and post-trade trade reporting (Rule 605/606) | Execution-quality reporting, not recommendation governance | Handle in OMS/EMS layer |
| Suitability rule legacy (FINRA Rule 2111) — held to the extent it applies to non-retail customers | Reg BI does not displace FINRA 2111 for institutional accounts | Engage FINRA-licensed compliance counsel |
| Books-and-records retention (Rule 17a-4) | Six-year retention obligation for recommendation records | Use Audit Chain plus WORM-compliant storage downstream |
| Annual CEO certification of compliance | Organizational signoff, not an agent control | Map to firm's compliance attestation program |

---

## References

- 17 C.F.R. § 240.15l-1 — Regulation Best Interest (current).
- SEC Release No. 34-86031 (June 5, 2019) — adopting release for Reg BI.
- SEC Division of Examinations Risk Alert, *Observations from Broker-Dealer
  Examinations Related to Reg BI* (April 26, 2023).
- SEC Release No. 34-97990 (July 26, 2023) — proposed rule on predictive
  data analytics (PDA), conflicts of interest associated with broker-dealer
  and investment-adviser use of PDA.
- FINRA, *Regulation Best Interest (Reg BI)* — key-topics page (current).
- Patterns in this repo: `patterns/best_interest_check.py` (Tranche 2C),
  `patterns/rate_limiter.py` (v1.1), `patterns/sovereign_veto.py`,
  `schemas/audit_event.py`, `examples/defcon_state_machine.py`,
  `docs/autonomy_ladder.md`.
