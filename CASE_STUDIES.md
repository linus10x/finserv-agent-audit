# Case studies — how these patterns would have engaged with public FSI matters

Three narratives, each built on a **named, on-record** U.S. financial-services
enforcement or guidance matter, showing how a specific primitive in this library
would have engaged with the failure mode and what audit artifact a regulator
would have been handed.

> **Honest framing — read this first.** These are *illustrative* reference
> studies, not deployment claims. This library was **not** deployed in any of the
> matters below, and adopting it would **not** have substituted for fair-lending
> judgment, model validation, or counsel review. The framework is governance
> scaffolding: where it engages, it produces a defensible audit trail, an earlier
> escalation, or a sovereign-veto hold — nothing more. Matter summaries paraphrase
> the public record; full citations and verification notes live in
> [`docs/fsi_settled_matters.md`](docs/fsi_settled_matters.md). This is a
> reference document, not legal advice — see [`DISCLAIMER.md`](DISCLAIMER.md).

---

## Case 1 · The reason-code that did not exist — CFPB v. Wells Fargo ($3.7B, Dec 20, 2022)

**The matter (public).** The CFPB's December 20, 2022 consent order found
systemic failures across auto loans, mortgages, and deposit accounts —
$3.7 billion aggregate ($2.0B consumer redress + $1.7B civil money penalty), the
largest CFPB penalty at the time. Among the findings: improper denials of
mortgage-loan modifications the bank's own systems should have approved. The order
does not label the systems "AI", but the modification-denial findings describe a
workflow where automated scoring produced denials the bank **could not
reconstruct or defend per-decision** when challenged. The remediation requires
controls — model validation and decision traceability — not just checks.

**The failure mode.** An automated decision surface issued an adverse outcome and
the operator could not, on demand, produce what inputs were used, what the system
computed, what reason codes attached, and how the action was approved or vetoed.
The defensibility gap *was* the liability.

**Which primitive / rung would have caught it.** The `AdverseActionGate`
(ADR-0009) fails closed: a denial or "unfavorable change" cannot emit unless a
`ReasonCode` mapping is present, defensible, and recorded on the hash-chain
*first*. A denial of a loan modification is an adverse action under ECOA and an
"unfavorable change" under FCRA §615, so it routes through the gate. With no
defensible reason-code mapping, the action is held under the **sovereign veto**
(ADR-0002) and escalated to a human at rung A0/A1 rather than emitted
autonomously. The `SR 11-7 model-validation overlay` (ADR-0007) would have
engaged the missing-validation discipline behind the scoring engine: a stale or
absent `MODEL_VALIDATED` event trips the same veto path.

**The audit artifact a regulator would get.** A per-decision reconstruction from
the WORM-persisted hash-chain ledger (ADR-0003 + ADR-0013, SEC 17a-4-style
retention adapted for consumer-finance discovery): for each modification denial,
the inputs used, the computed result, the attached `ReasonCode` decomposition
with `upstream_feature_ids`, and the human or documented-automated escalation
that approved or vetoed it — produced on demand, not from product-team memory.

---

## Case 2 · The conflict baked into the allocation — SEC v. Schwab Intelligent Portfolios ($187M, Jun 13, 2022)

**The matter (public).** The SEC's June 13, 2022 order ($187M aggregate — $52M
penalty + $135M disgorgement and prejudgment interest) found that from March 2015
to November 2018, Schwab's robo-advisor marketed "no advisory fees" while its
allocation logic systematically held a higher cash allocation than an
equivalent-risk portfolio would, with the cash swept to an affiliate bank earning
a spread. Settled on Investment Advisers Act §206(2) (negligent breach of
fiduciary duty) and §206(4). The SEC computed disgorgement on the **spread the
operator earned**, not just customer harm.

**The failure mode.** A conflict of interest was embedded in the recommendation
*logic* itself — not disclosed at the decision surface — and the regulated
artifact was the allocation engine's output, not the disclaimer wrapped around
it.

**Which primitive / rung would have caught it.** The `BestInterestCheck`
(`best_interest_check.py`) is a pre-emit gate on every recommendation to a
retail customer or internal allocation engine. It records a
`BEST_INTEREST_CHECKED` event with the customer-profile inputs, the universe
considered, the chosen recommendation, and — as a **first-class field, not a
prospectus footnote** — the conflict-of-interest declarations attached to each
option (cash-sweep spread, affiliated-fund preference, revenue share). An
allocation model whose validation file did not document the cash-spread conflict
as a tested-and-disclosed feature would not clear the gate; the
`SR 11-7 overlay` (ADR-0007) holds it under the veto until validation is current.

**The audit artifact a regulator would get.** The four-year cash-spread economics
made reconstructable on demand from the hash-chain ledger: every recommendation
with its conflict declarations recorded at emission time, so a §206 conflict
inquiry reads the conflict field across the violation period directly — rather
than reverse-engineering it from internal memory or a product dashboard that
could be modified or lost.

---

## Case 3 · "We don't know why the model said no" is not a defense — CFPB Circular 2022-03 (May 26, 2022)

**The matter (public).** CFPB Consumer Financial Protection Circular 2022-03
answers one question: must a creditor using a complex algorithm (including ML
models whose internal logic is not readily interpretable) still meet the
adverse-action notification requirements of ECOA and Regulation B? The answer is
yes, without exception. The text rejects the opacity defense explicitly — "a
creditor's lack of understanding of its own methods is therefore not a cognizable
defense" — and permits post-hoc explanations (SHAP, LIME, surrogate models) only
if **validated for accuracy** against the underlying decision.

**The failure mode.** An autonomous-agent stack that issues or materially
influences a credit decision inherits the full ECOA / Reg B adverse-action
burden, and the burden of validating any post-hoc explanation sits on the
creditor — not the model vendor. Opacity becomes a notice-content compliance
failure, not merely a model-quality concern.

**Which primitive / rung would have caught it.** This Circular is the regulatory
anchor for the `AdverseActionGate` (ADR-0009). The gate fails closed: if a
reason-code mapping is not present, defensible, and recorded on the hash-chain
before emission, the decision is vetoed (ADR-0002) and escalates to a
human-in-the-loop reviewer at rung A0/A1 — or is dropped. The recorded
`ADVERSE_ACTION_TAKEN` event carries the `ReasonCode` decomposition with
`upstream_feature_ids`, so the post-hoc-explanation accuracy claim the Circular
requires is reproducible **from the ledger**, not from a vendor dashboard.

**The audit artifact a regulator would get.** For any adverse credit decision: an
immutable `ADVERSE_ACTION_TAKEN` event with the institution reason code, the
plain-language wording, the factor contribution, and the upstream feature IDs —
the exact decomposition an examiner needs to test whether the disclosed reasons
"accurately describe the factors actually considered or scored," reproducible
on demand from the hash-chain.

---

## How to use these

For a first internal audit-committee briefing, open with **Case 3** (the cleanest
articulation of the operator-side rule), move to **Case 1** (the dollar anchor and
the controls-as-remediation template), and close with **Case 2** (the
recommendation surface as the regulated artifact). For a first counsel review,
walk the cited ADRs (0002 / 0003 / 0007 / 0009 / 0013) against your institution's
existing reason-code taxonomy and model-validation file format using the
hash-chain ledger schema in
[`schemas/audit_event.py`](schemas/audit_event.py). The full matter record —
agencies, dates, dollar amounts, statutory bases, and source-URL verification
notes (including where a primary-source PDF was not directly fetchable at
retrieval time) — is in [`docs/fsi_settled_matters.md`](docs/fsi_settled_matters.md).
