# Audit-Pack Walkthrough — Trainee Exercise

**Status:** v1.2.0-draft · Last reviewed: 2026-05-28.
**Audience:** First-year IT audit staff at a Big-4 (or comparable assurance) firm; FSI internal-audit trainees; FSI second-line reviewers preparing for examination season.

> **Patterns are software, not legal advice.** This walkthrough uses synthetic data. Do not draw conclusions about any real bank from the contents of this pack. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

---

## Setup

The fictitious deployer is **North River Bank, N.A.**, a $42B asset US mid-size bank with operations across Texas, Oklahoma, and New Mexico. The bank is OCC-regulated, FDIC-insured, and subject to SR 11-7. It is not subject to 23 NYCRR Part 500 directly but follows its substance as institutional policy. The bank's `finserv-agent-audit` deployment covers consumer credit decisioning, fraud triage, BSA / AML alert prioritization, and a retail robo-advisor on the wealth platform.

You are a first-year IT audit associate. The engagement-team senior has handed you this pack and a 90-minute window to draft your fieldwork notes. Work through the seven exercises below, then compare your conclusions to the answers in the "Expected findings" section.

---

## Exercise 1 — Chain integrity (15 min)

Open [`sample_audit_chain.jsonl`](sample_audit_chain.jsonl). It contains 24 entries spanning May 27-28, 2026.

Tasks:
1. Count the entries by `event_type`. (Hint: use `jq` or any JSONL reader.)
2. Confirm every entry's `prev_hash` equals the prior entry's `event_hash`. (Genesis entry has `prev_hash` of 64 zeros.)
3. Identify the two `audit_chain.witness_anchor` entries. Note the `chain_head_anchored` value in each. What is the time gap between consecutive anchors?

Working-paper question: **If the bank's witness-anchor cron is configured to run every 6 hours, does the chain's anchor cadence match that policy?**

---

## Exercise 2 — Vendor scoring activity (15 min)

Open [`vendor_scores_log.csv`](vendor_scores_log.csv). It contains 60 vendor-score records for the same two-day window.

Tasks:
1. Count the records per `vendor_class`. Confirm all 5 FSI `VendorClass` values are represented.
2. Identify the 2 records where `gate_verdict` is `drift_flagged`. For each, note the prior score, the new score, and the vendor-review ticket reference.
3. Tie each drift entry in the log to the corresponding `vendor.score_drift_detected` entry in `sample_audit_chain.jsonl` (look for matching vendor + input_hash + previous_score).

Working-paper question: **For each drift entry, the bank's vendor-risk procedure says the vendor-review ticket must be opened within 24 hours. Looking at the ticket reference format (`VRR-YYYY-NNNN`), can you confirm the ticket date matches the drift event date?**

---

## Exercise 3 — Model inventory completeness (10 min)

Open [`model_inventory_export.csv`](model_inventory_export.csv). It contains 7 registered models.

Tasks:
1. Count the models by `implementation_status`.
2. For the one `in_validation` model, note the `next_validation_due` date. Is it in the past, present, or future relative to the snapshot date?
3. For the one `proposed` model (`copilot-customer-comms-v0.9`), note the `autonomy_band`. What does an A0 designation tell you about how this model is used?

Working-paper question: **The bank uses a copilot for customer-service drafting. The model is currently in `proposed` status. The bank claims the copilot is "not in production." Looking at the autonomy band and intended-use field, does this claim hold?**

---

## Exercise 4 — Adverse action tracing (10 min)

In `sample_audit_chain.jsonl`, find every entry with `event_type == "fsi.adverse_action_taken"`.

Tasks:
1. Count them.
2. For each, list the `reason_codes`. Are they generic ("credit decision," "scoring criteria") or specific (named factors like "INCOME_DTI_HIGH")?
3. Note the value of `cfpb_circular_2022_03_alignment` in each payload.

Working-paper question: **CFPB Circular 2022-03 (May 26, 2022) [UNVERIFIED — confirm exact title and citation] requires that adverse-action notices to consumers be specific and accurate, not generic. Based on the reason-code shape you see, does the bank's adverse-action gate satisfy this expectation?**

---

## Exercise 5 — SAR workflow (10 min)

Find every entry with `event_type == "fsi.sar_filed"`.

Tasks:
1. Count them. (Expect: 1 in the two-day window.)
2. Note the `filing_deadline`, the `filing_deadline_met` boolean, and the `safe_harbor_metadata_captured` boolean.
3. Note the `vendor_signal_ref`. Which vendor scoring event preceded this SAR filing?

Working-paper question: **The BSA's SAR-filing rule (31 U.S.C. § 5318(g)) requires filing within 30 days of detection, with a 60-day extension available if a subject of suspicious activity has not been identified. Looking at the time between the precipitating vendor signal (sequence 9) and the SAR-filed entry (sequence 10), is the deadline tracking material here? (Hint: it's not, because both events are on the same day — but the engagement team will still expect the bank to demonstrate the 30-day tracker on its own.)**

---

## Exercise 6 — Best-interest check (10 min)

Find every entry with `event_type == "fsi.best_interest_checked"`.

Tasks:
1. Count them.
2. Note the `result` field and the `care_obligation_rationale_ref`.
3. Identify the vendor signal that informed this recommendation.

Working-paper question: **SEC Reg-BI's care obligation applies when a broker-dealer or RIA makes a recommendation to a retail customer. The bank's robo-advisor sits on the wealth platform; is the bank's framework producing the recommendation-level evidence Reg-BI expects?**

---

## Exercise 7 — Verifier attestation (10 min)

Open [`audit_consumer_attestation.md`](audit_consumer_attestation.md). The sample attestation receipt covers a single `AuditChain.verify_strict()` invocation.

Tasks:
1. Identify the `issuer.backend`. What does this tell you about the bank's MIProxy posture?
2. Note `claim.canonical_source_sha256`. What would the bank do with this hash during a change-management review?
3. Note the `verifier_self_attestation.mi_proxy_result`. What does `verified` mean here? What would `verification_failed` mean?

Working-paper question: **The bank operates `LocalMIProxy` with an HMAC-SHA256 key. The signing key lives in their KMS. If an attacker compromises the verifier source AND the KMS, what stops them from producing a valid-looking attestation over a malicious verifier? (Hint: this is the rationale for ADR-0015's substrate-pluggable backend (SLSA / in-toto) — see [`FAILURE-MODES.md`](failure_modes_matrix_snapshot.md) row 7.)**

---

## Expected findings

After 90 minutes, your draft notes should include:

- **Exercise 1.** 24 chain entries; 11 `vendor.score_recorded`, 1 `vendor.score_drift_detected`, 2 `fsi.adverse_action_taken`, 1 `fsi.model_validated` (each day so 2 total), 1 `fsi.sar_filed`, 1 `fsi.best_interest_checked`, 3 `audit_chain.witness_anchor`, 2 `agent.started`, 1 `agent.stopped`, 1 `decision.made`, 1 `decision.vetoed`, 1 `risk.escalation`, 1 `human.approved`. Prior-hash chain intact across all 24 entries. Witness anchors at 12:00 and 18:00 on day 1 and 12:00 on day 2 — every 6 hours, matching the bank's 6-hour cron policy if that's their stated cadence.

- **Exercise 2.** Vendor records distributed across all 5 classes; vendor-credit-bureau-A and vendor-fraud-shield-B each show one drift event. Drift tickets `VRR-2026-0517` and `VRR-2026-0528` — the latter ticket date matches the drift event date; the former does not. **Working-paper note:** the bank should explain why `VRR-2026-0517` was opened 10 days before the drift event date (likely a ticket-number recycling or numbering convention; flag for client conversation).

- **Exercise 3.** 1 proposed, 1 in_validation, 1 approved_for_limited_use, 3 approved_for_production, 1 retired. Total 7. The `in_validation` model (`robo-allocator-internal-v3.0`) has `next_validation_due` of 2026-08-15 — future. The copilot at A0 is advisory-only; representatives review and edit every output. **Working-paper note:** the bank's claim that the copilot is "not in production" holds because the model is in `proposed` status (not yet deployed) and the A0 designation in the intended-use field reinforces the constraint.

- **Exercise 4.** 2 adverse-action entries. Both use specific named reason codes (`INCOME_DTI_HIGH`, `DELINQ_30_LAST_24M`, `RECENT_INQUIRY_COUNT_HIGH`, `UTILIZATION_PCT_OVER_THRESHOLD`, `OPEN_DELINQ_60_PLUS_PRESENT`). Both flag `cfpb_circular_2022_03_alignment: true`. The reason codes appear specific and traceable — but the engagement team should still pull the actual consumer notices to confirm specificity at the customer-facing level, not just at the chain-payload level.

- **Exercise 5.** 1 SAR-filed entry, deadline met, safe-harbor metadata captured, vendor signal was `vendor-aml-monitor-D`. Deadline tracking is not material in this two-day window because both events are same-day; the engagement team needs the bank's longer-period tracker to assess deadline compliance.

- **Exercise 6.** 1 best-interest-checked entry, result `pass`, rationale doc reference present, vendor signal was `vendor-robo-allocator-E`. The framework produces the recommendation-level evidence Reg-BI expects; the engagement team should pull the rationale document referenced to confirm depth.

- **Exercise 7.** The `LocalMIProxy` backend tells you the bank is on the stdlib HMAC-SHA256 path. The `canonical_source_sha256` would be tied to the source committed under change-management; the auditor confirms the hash matches the committed source. `verified` means the verifier source has not been tampered with as of attestation time; `verification_failed` would raise `IntegrityVerificationError` and block the verify result from being trusted. The dual-compromise (verifier + KMS) is exactly the threat that motivates moving to a substrate-pluggable backend (SLSA / in-toto) — flag this as a recommendation for the bank's MRM roadmap.

---

## Trainee debrief — what to take into a real engagement

1. **The chain entries are the evidence — but the rationale documents are the substance.** The chain tells you what happened; the rationale doc reference tells you why. Always pull the rationale doc, not just the chain entry.

2. **Sample sizes are calibrated to inherent risk.** A2 / A3 / A4 autonomy bands and high-volume vendor classes get expanded samples; A0 advisory-only and low-volume vendors get abbreviated samples. The engagement-team senior sets the sample plan; you execute it.

3. **Test the failure mode, not just the success case.** Every named control should have a sandbox demonstration of the failure path. If the bank cannot demonstrate the failure, the control is not yet operational from the auditor's perspective.

4. **Vendor drift is a 30-second client conversation, not a one-line working paper.** Every `VENDOR_SCORE_DRIFT_DETECTED` chain entry deserves a vendor-disposition memo. If there's no memo, the chain is operating but the operational response is not.

5. **The chain is portable.** Any audit-firm reviewer with the framework installed can re-execute `AuditChain.verify_strict()` against a chain export. If a chain ever moves from one auditor to another, the second auditor's first action is to re-verify.

---

## Cross-references

- [`README.md`](README.md) — pack contents overview
- [`ASSURANCE-GUIDE.md`](../../ASSURANCE-GUIDE.md) — engagement-team's full walk-through guide
- [`docs/big4_engagement_letter_exhibit.md`](../../docs/big4_engagement_letter_exhibit.md) — SOW exhibit
- [`docs/pre_examination_ai_self_assessment.md`](../../docs/pre_examination_ai_self_assessment.md) — client-side self-assessment

---

*Patterns are software, not legal advice. The training scenario above is invented; do not extrapolate from any one detail to a real institution.*
