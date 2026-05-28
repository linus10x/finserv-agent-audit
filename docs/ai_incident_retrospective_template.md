# AI Incident Retrospective Template

A Google-SRE-style postmortem template adapted for AI-incident
retrospectives in financial-services institutions. Aligned to **NIST
AI RMF GOVERN-6.2** (incident response practices), the FFIEC IT
Examination Handbook, and the 23 NYCRR Part 500 § 500.16 incident-
response expectations.

Banks have no standard format for AI-internal incident retrospectives.
The MRM second line uses SR 11-7 validation memoranda; the security
team uses cybersecurity-event incident reports; the operations team
uses Google-SRE-style postmortems. None of these is sufficient on its
own for an AI-driven failure where model behaviour, vendor change,
training-data shift, prompt change, and human override all interact.

This template closes that gap. It is a fill-in-the-blank instrument
designed to produce a single defensible artifact suitable for board
review, examiner inspection, and regulator notification.

> **Disclaimer:** Reference pattern, not legal advice. Engage qualified
> counsel for your specific regulator-notification determinations. See
> repo-root [`DISCLAIMER.md`](../DISCLAIMER.md).

---

## How to Use This Template

1. Copy the template body (everything between `--- TEMPLATE START ---`
   and `--- TEMPLATE END ---`) into a new file under a stable retrospective
   archive (e.g. `retrospectives/YYYY-MM-DD-<incident-id>.md`).
2. Fill every section. If a section is not applicable, write "Not
   applicable — [one-sentence reason]" rather than deleting it. The
   shape of the artifact is part of its evidentiary value.
3. Run the template through the second-line MRM review, the security
   incident review, and (for material incidents) the general counsel
   review before sign-off.
4. Preserve the retrospective in WORM-eligible storage
   (`src/finserv_agent_audit/governance/ledger_store_worm.py`) with an
   external `witness_anchor` so the record cannot be silently rewritten.
5. Cross-reference the retrospective from the `audit_chain` events
   that bracket the incident window.

---

## Alignment to Frameworks

| Framework | Section | Alignment |
|---|---|---|
| NIST AI RMF | GOVERN-6.2 — Incident response practices | Provides the GOVERN-6.2 incident-documentation artifact |
| 23 NYCRR Part 500 | § 500.16 (incident-response plan); § 500.17(a) (72-hour notification) | Supplies the structured root-cause and materiality determination |
| FFIEC IT Examination Handbook | Incident management module | Supplies the timeline, contributing-factors, and lessons-learned sections |
| SR 11-7 / OCC 2026-13 | Effective challenge; validation | The validation re-run section discharges the second-line re-validation expectation |
| ISO 42001 | A.6.2.7 — incident management for AI systems | Provides the AI-incident-typology section |
| Google SRE | Postmortem culture | Blameless framing; root-cause discipline; action-items with owners |

---

--- TEMPLATE START ---

# AI Incident Retrospective — `<incident-id>`

**Incident ID:** `<YYYY-MM-DD-NN>`
**Date filed:** `<YYYY-MM-DD>`
**Severity:** `<SEV-1 | SEV-2 | SEV-3 | SEV-4>`
**Author:** `<incident commander name + role>`
**Reviewers:** `<CISO · CRO · GC · MRM lead · board liaison>`
**Status:** `<DRAFT | UNDER REVIEW | FINAL | FILED>`
**Storage anchor:** `<witness_anchor hash · ledger_store URI>`

---

## 1. Incident Summary

> One paragraph (≤120 words). Describe what happened, what was
> affected, when it was detected, when it was resolved, and the
> materiality assessment in one sentence.

`<fill in>`

---

## 2. Timeline of Events

> All timestamps in UTC. Include every agent action, every human
> intervention, every governance decision, and every external
> communication. Sourced from `audit_chain` events plus reviewer notes.

| Timestamp (UTC) | Actor | Event | Source |
|---|---|---|---|
| `YYYY-MM-DDTHH:MM:SSZ` | Agent `<id>` | `<event>` | `AuditEvent <hash>` |
| `YYYY-MM-DDTHH:MM:SSZ` | Human `<role>` | `<event>` | `<source>` |
| `YYYY-MM-DDTHH:MM:SSZ` | DEFCON | `<state transition>` | `defcon` log |
| `YYYY-MM-DDTHH:MM:SSZ` | Sovereign veto | `<action>` | `sovereign_veto` event |
| ... | ... | ... | ... |

---

## 3. Root Cause Analysis

> Use the five-whys discipline. Distinguish technical, organisational,
> and governance causes. The root cause is not the most obvious cause;
> it is the cause whose removal would have prevented the incident.

### 3.1 Technical root cause

`<fill in — model behaviour, prompt change, infrastructure, data shift>`

### 3.2 Organisational root cause

`<fill in — process gap, ownership gap, escalation gap>`

### 3.3 Governance root cause

`<fill in — A-band misclassification, missing veto, missing audit, missing
shadow-mode coverage>`

### 3.4 Five-whys trace

1. Why did the incident occur? `<fill in>`
2. Why did that happen? `<fill in>`
3. Why did that happen? `<fill in>`
4. Why did that happen? `<fill in>`
5. Why did that happen? `<fill in>`

---

## 4. Contributing Factors

> Enumerate every factor that was present and material, even if not
> the root cause. Use the standard AI-failure-mode taxonomy.

| Factor | Present? | Materiality | Evidence |
|---|---|---|---|
| Model drift | `<Y/N>` | `<H/M/L>` | `<mi_proxy signal series>` |
| Vendor model change | `<Y/N>` | `<H/M/L>` | `<vendor_score_gate event>` |
| Training-data shift | `<Y/N>` | `<H/M/L>` | `<data-quality monitoring>` |
| Prompt / policy change | `<Y/N>` | `<H/M/L>` | `<change-management record>` |
| Infrastructure | `<Y/N>` | `<H/M/L>` | `<platform incident record>` |
| Human override pattern | `<Y/N>` | `<H/M/L>` | `<sovereign_veto frequency>` |
| Adversarial input | `<Y/N>` | `<H/M/L>` | `<security incident record>` |
| Third-party dependency | `<Y/N>` | `<H/M/L>` | `<TPSP incident record>` |
| Configuration / parameter | `<Y/N>` | `<H/M/L>` | `<audit_chain config hash diff>` |

---

## 5. Detection Mechanism

> Which v1.1-v1.3 module detected the incident — or, if detection was
> human-mediated or downstream, which module *should* have caught it.

### 5.1 Detection path

| Detection layer | Module | Triggered? | Detection latency |
|---|---|---|---|
| Model-integrity drift | `mi_proxy` | `<Y/N>` | `<minutes>` |
| Population fairness drift | `equity_audit` | `<Y/N>` | `<minutes>` |
| Protected-class proxy | `protected_class_proxy_detector` | `<Y/N>` | `<minutes>` |
| Rationale quality | `adverse_action_gate` | `<Y/N>` | `<minutes>` |
| Vendor change | `vendor_score_gate` | `<Y/N>` | `<minutes>` |
| Shadow-mode delta | `shadow_mode` | `<Y/N>` | `<minutes>` |
| DEFCON transition | `defcon` | `<Y/N>` | `<minutes>` |
| Human report | (out of system) | `<Y/N>` | `<minutes>` |

### 5.2 Detection gap

`<fill in — which module should have caught it but did not; why>`

---

## 6. Customer Impact and Materiality Assessment

> Quantify the customer impact and assess materiality under each
> applicable regulator's threshold.

### 6.1 Customer impact

- Customers affected: `<count>`
- Decision class: `<adverse-action | suitability | trade | KYC | other>`
- Reversibility: `<reversible | partially reversible | irreversible>`
- Customer-facing remediation issued: `<Y/N — describe>`

### 6.2 Materiality assessment

| Regulator | Threshold | Reached? | Notes |
|---|---|---|---|
| NYDFS § 500.17(a) | "Cybersecurity event" — 72-hour notice | `<Y/N>` | `<fill in>` |
| OCC examination disclosure | Material under MRM framework | `<Y/N>` | `<fill in>` |
| SEC Item 1.05 (8-K) | Material cybersecurity incident | `<Y/N>` | `<fill in>` |
| FTC Safeguards Rule § 314.5 | 30-day notice for events affecting 500+ consumers | `<Y/N>` | `<fill in>` |
| Federal Reserve SR 11-7 / SR 26-2 successor | Material model risk event | `<Y/N>` | `<fill in>` |
| State AG (per-state) | State UDAP / civil-rights statute | `<Y/N>` | `<fill in>` |

---

## 7. Regulator-Notification Trigger

> The materiality table above flags candidate triggers. This section
> is the decision record — what was filed, with whom, when, and who
> made the call.

| Regulator | Filing | Filed? | Date filed | Signatory |
|---|---|---|---|---|
| NYDFS Superintendent | § 500.17(a) cybersecurity-event notice | `<Y/N>` | `<date>` | `<role>` |
| OCC | Examination disclosure | `<Y/N>` | `<date>` | `<role>` |
| SEC | Item 1.05 (8-K) | `<Y/N>` | `<date>` | `<role>` |
| FTC | Safeguards Rule § 314.5 | `<Y/N>` | `<date>` | `<role>` |
| FRB / FDIC | Per supervisory relationship | `<Y/N>` | `<date>` | `<role>` |
| State AG(s) | Per state law | `<Y/N>` | `<date>` | `<role>` |

**Rationale for any non-filing:** `<fill in — counsel sign-off required>`

---

## 8. Remediation Actions

### 8.1 Immediate (≤24 hours)

| Action | Owner | Status | Verification |
|---|---|---|---|
| `<rollback / kill switch / sovereign veto / A-band demotion>` | `<owner>` | `<status>` | `<verification>` |

### 8.2 Short-term (≤30 days)

| Action | Owner | Due | Verification |
|---|---|---|---|
| `<patch / re-validation / re-train / vendor escalation>` | `<owner>` | `<date>` | `<verification>` |

### 8.3 Long-term (≤180 days)

| Action | Owner | Due | Verification |
|---|---|---|---|
| `<architecture change / new monitoring / new gate / policy change>` | `<owner>` | `<date>` | `<verification>` |

---

## 9. Audit-Chain Replay Verification

> Re-run `AuditChain.verify()` and confirm chain integrity covering
> the incident window. If the chain was tampered with, that fact is
> itself a SEV-1 incident.

| Check | Result | Evidence |
|---|---|---|
| `AuditChain.verify(start, end)` | `<PASS / FAIL>` | `<verification hash>` |
| External witness anchor matches | `<PASS / FAIL>` | `<witness_anchor hash>` |
| RFC 3161 timestamp present for incident bracket events | `<PASS / FAIL>` | `<timestamp_source receipts>` |
| WORM-ledger immutability confirmed | `<PASS / FAIL>` | `<ledger_store_worm verification>` |

---

## 10. Validation Re-Run

> Re-validate the model per the SR 11-7 / OCC 2026-13 second-line
> process. Required for any incident touching a regulated decision
> class.

| Validation step | Result | Validator | Evidence |
|---|---|---|---|
| Conceptual soundness review | `<PASS / FAIL / CONDITIONAL>` | `<validator>` | `<memo ref>` |
| Outcomes analysis (back-test on incident-period inputs) | `<PASS / FAIL>` | `<validator>` | `<memo ref>` |
| Sensitivity analysis (perturbation of root-cause factor) | `<PASS / FAIL>` | `<validator>` | `<memo ref>` |
| Shadow-mode rerun (`shadow_mode`) | `<PASS / FAIL>` | `<validator>` | `<memo ref>` |
| Fairness re-test (`equity_audit`) | `<PASS / FAIL>` | `<validator>` | `<memo ref>` |
| Effective-challenge attestation | `<signed / outstanding>` | `<validator>` | `<memo ref>` |

---

## 11. Lessons Learned — Changes to Governance Posture

> What changes to the audit chain, the FAILURE-MODES matrix, the
> A-band classification, the gate set, or the vendor posture follow
> from this incident? The retrospective is not complete until these
> are committed.

### 11.1 Audit-chain changes

`<fill in — new fields, new event types, new retention rules>`

### 11.2 FAILURE-MODES.md updates

`<fill in — new row, updated callable mapping, updated detection
mechanism>`

### 11.3 Autonomy-Ladder reclassification

`<fill in — A-band demotion for the affected decision class; rationale;
sunset criteria for re-promotion>`

### 11.4 New gate or new check

`<fill in — new pattern proposed, new ADR drafted, schedule>`

### 11.5 Vendor posture change

`<fill in — `vendor_score_gate` re-evaluation, contract amendment,
TPSP termination>`

### 11.6 Policy / training change

`<fill in — board-policy update, security training update, MRM policy
update>`

---

## 12. Sign-Off

| Role | Name | Date | Signature / hash |
|---|---|---|---|
| Incident commander | `<name>` | `<date>` | `<hash>` |
| Chief Risk Officer | `<name>` | `<date>` | `<hash>` |
| Chief Information Security Officer | `<name>` | `<date>` | `<hash>` |
| General Counsel | `<name>` | `<date>` | `<hash>` |
| Model Risk Management lead | `<name>` | `<date>` | `<hash>` |
| Board liaison (Audit / Risk Committee) | `<name>` | `<date>` | `<hash>` |

**Final storage:**
- `ledger_store_worm` URI: `<uri>`
- `witness_anchor` external anchor: `<hash + anchor system>`
- Cross-reference to `audit_chain` event bracket: `<start hash> → <end
  hash>`

--- TEMPLATE END ---

---

## Worked Example — Sketch

A consumer-lending agent began producing decline rationales that mapped
disproportionately to a generic Form C-1 checkbox after a vendor model
upgrade. The `equity_audit` population-fairness signal tripped at
T+22 hours. The `mi_proxy` signal had been stable. The DEFCON state
machine had not transitioned. The first detection was the population
fairness check, not the model-integrity check — which itself becomes
a lesson learned.

In this case the retrospective would record:

- **Detection mechanism:** `equity_audit` (population fairness) — not
  `mi_proxy` (model integrity). The model output distribution looked
  stable; only the rationale-to-protected-class joint distribution
  shifted.
- **Detection gap:** `mi_proxy` did not trip because the vendor model
  upgrade preserved aggregate calibration while shifting the rationale
  surface.
- **Root cause:** The upgraded vendor model emitted a different top-K
  feature set whose nearest-checkbox mapping concentrated on C-1 even
  for cases whose actual principal reason was novel — which itself is
  a Circular 2023-03 accuracy-prong violation.
- **Materiality:** Above the NYDFS § 500.17(a) threshold for the
  affected customer count; SEC Item 1.05 review required; state AG
  notification under MA chapter 93A considered.
- **Remediation:** Immediate sovereign-veto on the affected decision
  class; short-term re-deployment of the prior vendor model under
  shadow mode; long-term `vendor_score_gate` policy change requiring
  rationale-distribution-stability evidence as a pre-promotion gate.
- **Lessons learned:** New `audit_chain` event type for rationale-to-
  checkbox distribution; FAILURE-MODES.md updated with the rationale-
  distribution-drift row; vendor contract amendment to require
  rationale-surface-stability attestation pre-upgrade.

---

## References

- Google SRE Book — *Postmortem Culture: Learning from Failure.*
  <https://sre.google/sre-book/postmortem-culture/>
- NIST AI RMF — GOVERN-6 function (incident response practices).
- FFIEC IT Examination Handbook — incident-management module.
- 23 NYCRR Part 500 § 500.16 (incident-response plan) and § 500.17(a)
  (72-hour cybersecurity-event notice).
- SR 11-7 / OCC 2026-13 — second-line validation process; see
  [`docs/sr11_7_mapping.md`](sr11_7_mapping.md) and
  [`docs/interagency_mrm_2026_overlay.md`](interagency_mrm_2026_overlay.md).
- ISO 42001 A.6.2.7 — incident management for AI systems; see
  [`docs/iso_42001_mapping.md`](iso_42001_mapping.md).
- Patterns in this repo:
  `src/finserv_agent_audit/governance/audit_chain.py`,
  `src/finserv_agent_audit/governance/mi_proxy.py`,
  `src/finserv_agent_audit/governance/equity_audit.py`,
  `src/finserv_agent_audit/governance/protected_class_proxy_detector.py`,
  `src/finserv_agent_audit/governance/adverse_action_gate.py`,
  `src/finserv_agent_audit/governance/vendor_score_gate.py`,
  `src/finserv_agent_audit/governance/shadow_mode.py`,
  `src/finserv_agent_audit/governance/defcon.py`,
  `src/finserv_agent_audit/governance/sovereign_veto.py`,
  `src/finserv_agent_audit/governance/witness_anchor.py`,
  `src/finserv_agent_audit/governance/timestamp_source.py`,
  `src/finserv_agent_audit/governance/ledger_store_worm.py`,
  `docs/autonomy_ladder.md`,
  `FAILURE-MODES.md`.
- Related mappings:
  [`docs/nydfs_part500_ai_mapping.md`](nydfs_part500_ai_mapping.md),
  [`docs/sr11_7_mapping.md`](sr11_7_mapping.md),
  [`docs/interagency_mrm_2026_overlay.md`](interagency_mrm_2026_overlay.md),
  [`docs/nist_ai_rmf_mapping.md`](nist_ai_rmf_mapping.md),
  [`docs/iso_42001_mapping.md`](iso_42001_mapping.md).
