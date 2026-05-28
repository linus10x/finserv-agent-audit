# ECOA / Regulation B — Control Mapping for Autonomous AI Agents

This document maps the governance patterns in this repository to fair-lending
obligations under the Equal Credit Opportunity Act and Regulation B
(12 C.F.R. Part 1002), with particular focus on the adverse-action notification
arm at 12 C.F.R. § 1002.9 and the protected-class non-discrimination
obligations at the heart of ECOA. The patterns that anchor this mapping are
the **EquityAudit** (Tranche 2C) and the
**ProtectedClassProxyDetector** (v1.2 MI arm per ADR-0019 § "v1.2 ship reconciliation").

> **Disclaimer:** Reference pattern, not legal advice. Regulatory characterizations
> are summaries; engage qualified counsel for your specific compliance
> determination. See repo-root [`DISCLAIMER.md`](../DISCLAIMER.md).

---

## Framework Overview

ECOA (15 U.S.C. § 1691 et seq.) makes it unlawful for any creditor to
discriminate against an applicant on the basis of a protected characteristic
in any aspect of a credit transaction. Regulation B (12 C.F.R. Part 1002) is
the CFPB's implementing rule. Two operative arms apply to an autonomous
agent stack:

1. **Non-discrimination (substantive).** A model that produces materially
   different outcomes for similarly situated applicants who differ only by a
   protected class — directly or by proxy — creates fair-lending exposure
   whether or not the model "intended" the disparity.
2. **Notification (procedural, § 1002.9).** A creditor must notify the
   applicant of action taken within **30 days** after receiving a completed
   application; on adverse action, the notice must include a statement of the
   action, the creditor's name and address, the ECOA § 701(a) notice, the
   name and address of the Federal enforcement agency, and either **specific
   reasons for the action taken** or a disclosure of the right to receive
   reasons within 30 days of a request made within 60 days.

The CFPB has been explicit that citing "internal standards or policies" or
failure to achieve a qualifying score is insufficient — reasons must relate
to the actual factors considered. CFPB Circular 2022-03 (May 26, 2022)
extended this to complex algorithms: "a creditor cannot justify noncompliance
. . . based on the mere fact that the technology . . . is too complicated or
opaque to understand."

The pattern coverage below treats every agent decision that touches the credit
surface as in-scope for both the substantive disparate-impact analysis
(EquityAudit) and the procedural notification discipline (AdverseActionGate,
mapped separately in `docs/fcra_reg_v_mapping.md`).

---

## Primary-Source Citations

| Source | Retrieved | Status |
|---|---|---|
| 12 C.F.R. § 1002.9 (Reg B notification requirements) | 2026-05-28, https://www.consumerfinance.gov/rules-policy/regulations/1002/9/ | Verified — 30-day timing, content requirements (action, creditor name/address, ECOA § 701(a) reference, enforcement-agency name/address), specific-reasons requirement, conditional-disclosure path, insufficiency of generic "internal standards" reasons confirmed |
| CFPB Circular 2022-03 (May 26, 2022) | 2026-05-28, https://www.consumerfinance.gov/compliance/circulars/circular-2022-03-adverse-action-notification-requirements-in-connection-with-credit-decisions-based-on-complex-algorithms/ | Verified — rejection of complexity defense, specific-principal-reasons requirement, ML/AI applicability confirmed verbatim |
| 15 U.S.C. § 1691 et seq. (ECOA statutory foundation) | Referenced; consult govinfo for the operative statutory text |
| 12 C.F.R. § 1002.6 (rules concerning evaluation of applications) | Referenced; verbatim section text not fetched in this pass |

---

## Protected Classes Under ECOA / Reg B

ECOA § 701(a) and Reg B § 1002.2 identify the following protected
characteristics on which a creditor may not discriminate in any aspect of a
credit transaction:

| Protected basis | Citation | Operational concern for an agent stack |
|---|---|---|
| Race | 15 U.S.C. § 1691(a)(1) | Direct use barred; proxy concern on geography (ZIP, census tract), surnames, education indicators |
| Color | 15 U.S.C. § 1691(a)(1) | Same proxy surface as race |
| Religion | 15 U.S.C. § 1691(a)(1) | Direct use barred; proxy concern on day-of-week activity, name patterns, certain merchant categories |
| National origin | 15 U.S.C. § 1691(a)(1) | Direct use barred; proxy concern on language preference, foreign-name patterns, geography |
| Sex (including gender, sexual orientation, gender identity — CFPB interpretive rule) | 15 U.S.C. § 1691(a)(1) | Direct use barred; proxy concern on first-name distribution, occupation patterns |
| Marital status | 15 U.S.C. § 1691(a)(1) | Direct use barred outside specific permitted contexts; proxy concern on co-applicant patterns |
| Age (provided the applicant has capacity to contract) | 15 U.S.C. § 1691(a)(1) | Direct use heavily restricted; proxy concern on credit-history length, account-tenure features |
| Receipt of income from public-assistance program | 15 U.S.C. § 1691(a)(2) | Direct use barred; proxy concern on income-source classification |
| Exercise in good faith of any right under the Consumer Credit Protection Act | 15 U.S.C. § 1691(a)(3) | Retaliation surface; concern on dispute-history features |

The pattern stance is **prohibited features are not present in the training
data, the inference inputs, or the explanation surface**, and a proxy-detection
discipline runs on every model promotion to surface features that correlate
with a protected basis above a configured threshold.

---

## Control Mapping Table

| ECOA / Reg B Requirement | Citation | Pattern in This Repo | File |
|---|---|---|---|
| Non-discrimination — substantive obligation | 15 U.S.C. § 1691(a); 12 C.F.R. § 1002.4(a) | `EquityAudit` — disparate-impact analysis on every model promotion gate; outcomes binned by inferred class proxy and compared against benchmark | `src/finserv_agent_audit/governance/equity_audit.py` (Tranche 2C) |
| Proxy-feature concern on protected bases | 15 U.S.C. § 1691(a); supervisory guidance | `ProtectedClassProxyDetector` — mutual-information arm shipped v1.2 (per-feature MI against the inferred-class panel AND against the decisions; both must clear threshold to flag) | `src/finserv_agent_audit/governance/protected_class_proxy_detector.py` (ADR-0019 § "v1.2 ship reconciliation") |
| Evaluation rules (no use of prohibited basis as predictor) | 12 C.F.R. § 1002.6(b) | Feature-allowlist on the model-promotion gate; explicit-class features blocked at the feature registry | (Tranche 2C, composed with `vendor_score_gate`) |
| Notification within 30 days of completed application | 12 C.F.R. § 1002.9(a)(1) | Audit-chain timestamp on the decision packet; SLA monitored against the chain | `src/finserv_agent_audit/schemas/audit_event.py` |
| Statement of action taken | 12 C.F.R. § 1002.9(a)(2) | `AdverseActionPacket.action_kind` (see FCRA mapping); enumerated kinds |  `src/finserv_agent_audit/governance/adverse_action_gate.py` (ADR-0009) |
| Creditor name and address; ECOA § 701(a) reference; enforcement-agency name and address | 12 C.F.R. § 1002.9(a)(2) | Notice-template registry pinned at decision time, version recorded on the chain | `src/finserv_agent_audit/schemas/audit_event.py` |
| Specific reasons for the action taken (or conditional-disclosure path) | 12 C.F.R. § 1002.9(a)(2)(i) | `FCRA-REASONS-MISSING` veto (ADR-0009) — generic placeholders rejected; reason codes must trace to upstream features | ADR-0009 |
| Specific reasons must be substantive; "internal standards" or "score-below-threshold" alone insufficient | 12 C.F.R. § 1002.9(b)(2) | Reason-code taxonomy reviewed annually with Fair-Lending function; audit chain logs reason-code frequency; a code on >25% of decisions is treated as evidence the taxonomy needs refinement | ADR-0009 pre-mortem |
| Algorithmic complexity is not a defense for missing specific reasons | CFPB Circular 2022-03 | `FCRA-FACTOR-TRACE-MISSING` veto — post-hoc SHAP/LIME on a black-box score is rejected; reasons must trace to features actually scored | ADR-0009 |
| Incomplete application — notice of incompleteness or adverse action on incomplete | 12 C.F.R. § 1002.9(c) | Application-completeness signal carried on the decision packet; incomplete-application path is a distinct `AdverseActionKind` | ADR-0009 |
| Record retention for compliance review | 12 C.F.R. § 1002.12 | Hash-chain audit ledger with WORM storage option; tamper-evident; queryable per consumer | `src/finserv_agent_audit/governance/ledger_store_worm.py`, `src/finserv_agent_audit/governance/witness_anchor.py` |
| Model-risk discipline (model validation, ongoing monitoring) | SR 11-7 / OCC 2011-12 | `model_validation_id` field on the decision packet; bridge to the institution's model-risk artifact set | ADR-0009 |
| Sovereign-veto authority on substantive non-compliance | 12 C.F.R. § 1002.16 (penalties) | Sovereign-veto pattern — emission-blocked on any fail-closed veto; gate-disable drops the program to DEFCON-3 | `patterns/sovereign_veto.py`, `src/finserv_agent_audit/governance/defcon.py` |

---

## EquityAudit — How the Substantive Arm Operates

The EquityAudit pattern runs on every model-promotion gate and on a scheduled
cadence against production decisions. The minimum-viable audit produces, for
each protected-basis dimension:

1. **Outcome rate by inferred class.** Approval rate, average APR offered,
   average credit-line amount, denial rate by decision kind.
2. **Adverse-impact ratio (AIR).** The four-fifths rule benchmark (rate for
   the comparison group divided by the rate for the highest-rate group);
   readings below 0.80 trigger an investigative review.
3. **Standardized mean difference (SMD).** A statistical complement to AIR
   for continuous outcomes (e.g., APR offered).
4. **Reason-code distribution by inferred class.** A reason that appears
   disproportionately in adverse decisions against a protected group is a
   red flag whether or not the AIR threshold is breached.
5. **Feature-importance distribution by inferred class.** A model that ranks
   different features as primary drivers for similarly situated applicants
   who differ by protected basis is a candidate for proxy investigation.

Inferred-class panels use the Bayesian Improved Surname Geocoding (BISG)
method or equivalent; the audit operates on inferred class because direct
class data is not collected. The audit output is itself an audit-chain entry
and the model-promotion gate fails closed on any threshold breach.

---

## ProtectedClassProxyDetector — v1.2 Mutual-Information Arm (ADR-0019)

The proxy-detector pattern shipped its mutual-information arm in v1.2,
closing the v1.1 API-reservation deferral per ADR-0019. The detector
runs on a recent decision window: for each candidate feature it computes
the mutual information against the protected attribute AND against the
decisions, and flags features that clear the configured threshold on
both axes. The default threshold is 0.1 nats; calibrate per program.

Operational integration still requires (a) an institutional BISG or
equivalent class-inference capability to supply the `protected_class`
input, (b) a Fair-Lending workflow for the review queue that consumes
the flagged features, and (c) a feature-registry hook into the model-
promotion gate. The detector also reports the 4/5ths-rule-style direct
disparate-impact ratio independently from the per-feature MI sweep —
useful when the decision is disparate without any single feature
carrying the signal.

The SHAP attribution audit and conditional-demographic-disparity arms
named in ADR-0019 remain on the v1.3 roadmap; see ADR-0019 § "v1.2 ship
reconciliation" for the detailed scope and reversibility framing.

---

## Gap Analysis — What This Repo Does NOT Cover

| Requirement | Gap | Guidance |
|---|---|---|
| Self-test privilege framework (12 C.F.R. § 1002.15) | Self-test design and privilege strategy are institutional / counsel-led | Coordinate with Fair-Lending counsel; the EquityAudit output can serve as evidence in a self-test program if structured under § 1002.15 |
| Spousal-signature rules (12 C.F.R. § 1002.7) | Application-form / underwriting-process discipline | Out of scope for an agent-governance repository |
| HMDA data collection and reporting overlay | Distinct statutory regime with its own reporting cadence | Map separately; the audit chain is the common evidentiary substrate |
| State fair-lending overlays | Substantive overlap with ECOA but distinct enforcement | Map separately |
| Inferred-class methodology and panel maintenance | The EquityAudit consumes an inferred-class panel; it does not produce one | Institution maintains BISG or equivalent panel; the audit is a consumer of that artifact |
| Disparate-treatment investigation workflow | The audit produces signals; the investigation discipline is institutional | Fair-Lending function owns the investigative protocol; the audit chain supplies the evidentiary record |
| Notice-template language drafting | The gate guarantees the input is well-formed; template drafting is counsel-led | Notice-template registry pins the version at decision time; drafting is out of scope |

---

## References

- 12 C.F.R. § 1002.9 (Regulation B — Notifications). Retrieved 2026-05-28,
  CFPB eRegulations.
- 15 U.S.C. § 1691 et seq. (Equal Credit Opportunity Act).
- 12 C.F.R. § 1002.4, § 1002.6, § 1002.7, § 1002.12, § 1002.15, § 1002.16
  (Regulation B operative sections referenced above).
- CFPB Circular 2022-03 (May 26, 2022). "Adverse action notification
  requirements in connection with credit decisions based on credit decisions
  based on complex algorithms." Retrieved 2026-05-28, consumerfinance.gov.
- SR 11-7 / OCC 2011-12 — Supervisory guidance on model risk management.
- ADR-0010 · ECOA / Reg B Fair Lending (cross-referenced in ADR-0009; module
  lands in Tranche 2C).
- ADR-0019 · Protected-Class Proxy Detector (deferred; tracked).
- ADR-0009 · FCRA § 615 / Reg V — AdverseActionGate
  (`docs/adr/0009-fcra-reg-v-adverse-action.md`).
- ADR-0008 · GLBA Safeguards Rule — Customer NPI Partitioning
  (`docs/adr/0008-glba-safeguards.md`).
- Cross-mapping: `docs/fcra_reg_v_mapping.md` (procedural arm of the same
  decision surface); `docs/glba_safeguards_mapping.md` (customer NPI used in
  the decision packet).
