# OCC Bulletin 2011-12 — Control Mapping for Autonomous AI Agents

**OCC Bulletin 2011-12, _Sound Practices for Model Risk Management: Supervisory
Guidance on Model Risk Management_** (issued April 4, 2011) is the OCC
counterpart to Federal Reserve SR 11-7. The two were drafted jointly and the
attached supervisory guidance is the **same document**, adopted under each
agency's separate supervisory authority. For OCC-supervised institutions —
national banks, federal savings associations, and federal branches of foreign
banks — Bulletin 2011-12 is the binding citation; SR 11-7 is the cross-reference.

This document is intentionally short: it cross-references the SR 11-7 mapping in
`docs/sr11_7_mapping.md` and calls out the **three places OCC 2011-12 (and
subsequent OCC issuances) diverge from or clarify the joint guidance**.

> **Disclaimer:** This mapping is provided for reference only and does not
> constitute legal or supervisory advice. Engage qualified counsel and the OCC
> Office of the Chief Counsel for any specific compliance determination.

---

## Joint-Issuance Alignment

The attached supervisory guidance text published with OCC Bulletin 2011-12 is
identical to the attachment published with Federal Reserve SR 11-7. The four
expectations are the same:

1. **Sound model development, implementation, and use.**
2. **Effective validation** (conceptual soundness, ongoing monitoring, outcomes
   analysis).
3. **Governance, policies, and controls** (board oversight, written policy,
   model inventory, role separation, internal audit).
4. **Effective challenge** as the connective discipline.

For the full pattern-to-section mapping, see
[`docs/sr11_7_mapping.md`](sr11_7_mapping.md). Every pattern in that table
applies identically under OCC 2011-12.

| Pattern | SR 11-7 Section | OCC 2011-12 Section | File |
|---|---|---|---|
| `model_inventory` | III. Overview of MRM | III. Overview of MRM | `patterns/model_inventory.py` |
| `autonomy_ladder` | IV. Development, Implementation, Use | IV. Development, Implementation, Use | `docs/autonomy_ladder.md` |
| `audit_chain` | IV. Development, Implementation, Use | IV. Development, Implementation, Use | `schemas/audit_event.py` |
| `defcon` | IV. Development, Implementation, Use | IV. Development, Implementation, Use | `examples/defcon_state_machine.py` |
| `shadow_mode` | V. Validation — Conceptual Soundness | V. Validation — Conceptual Soundness | `patterns/shadow_mode.py` |
| `mi_proxy` | V. Validation — Ongoing Monitoring | V. Validation — Ongoing Monitoring | `patterns/mi_proxy.py` |
| `sovereign_veto` | V. Validation — Effective Challenge | V. Validation — Effective Challenge | `patterns/sovereign_veto.py` |
| `vendor_score_gate` | VI. Governance — External Resources | VI. Governance — External Resources | `patterns/vendor_score_gate.py` |
| `witness_anchor` | VI. Governance — Internal Audit | VI. Governance — Internal Audit | `patterns/witness_anchor.py` |
| `ledger_store` + `timestamp_source` | Record-keeping footnote | Record-keeping footnote | `patterns/ledger_store.py`, `patterns/timestamp_source.py` |

---

## Three Places OCC 2011-12 Diverges From or Clarifies SR 11-7

### 1. Examiner Direction Is Explicit

OCC 2011-12 opens with a sentence the SR 11-7 cover letter does not: the
bulletin states the guidance applies to **OCC examining personnel and national
banks**. Practical consequence: OCC examiners cite the bulletin number in MRA
(Matters Requiring Attention) and MRIA (Matters Requiring Immediate Attention)
findings. Pattern-level effect: `audit_chain` evidence and `model_inventory`
extracts should be packaged as bulletin-keyed exhibits during an OCC exam, not
SR-letter-keyed.

### 2. Predecessor Bulletin OCC 2000-16 Is Rescinded

OCC 2011-12 expressly **replaces OCC Bulletin 2000-16, "Model Validation"**
(May 30, 2000). SR 11-7 has no equivalent predecessor statement because the
Federal Reserve did not have a standing model-validation letter prior to 2011.
Practical consequence: OCC-supervised institutions cannot fall back to
OCC 2000-16's narrower validation-only framing — the 2011 guidance covers the
full model lifecycle, and any legacy MRM policy citing OCC 2000-16 is
deprecated. The `autonomy_ladder` and `defcon` patterns supply the
lifecycle coverage the older validation-only frame did not require.

### 3. Subsequent OCC Clarifications Layer on Top

The OCC has issued two later instruments that refine 2011-12 in ways the Federal
Reserve handles through separate SR letters:

- **OCC Bulletin 2021-39, _Model Risk Management Booklet_** (Comptroller's
  Handbook, August 2021) — operationalizes the bulletin into examination
  procedures. Pattern-level effect: `mi_proxy` and `shadow_mode` outputs map
  directly to the booklet's ongoing-monitoring examination checklist.
- **OCC Bulletin 2025-26, _Model Risk Management: Clarification_** (October 6,
  2025) — addresses risk management for AI / machine-learning models and
  reaffirms that vendor and pre-trained-model components are in-scope.
  Pattern-level effect: `vendor_score_gate` and the third-party provisions of
  `model_inventory` are the technical artifacts that satisfy the 2025
  clarification.

The Federal Reserve's parallel instrument, **SR 26-2, _Revised Guidance on
Model Risk Management_** (April 17, 2026), supersedes SR 11-7 and SR 21-8 for
Federal-Reserve-supervised institutions. OCC-supervised institutions follow the
OCC 2025-26 clarification path; FDIC-supervised institutions follow FIL-22-2017
plus any FDIC-issued AI/ML supplement. The pattern stack does not change — the
citation header on the exam exhibit does.

---

## Gap Analysis — OCC-Specific Items Not Covered by the Pattern Stack

| OCC Expectation | Gap | Guidance |
|---|---|---|
| Comptroller's Handbook — Model Risk Management examination procedures | Procedural workflow, not code | Map examiner request items to `audit_chain` queries and `ledger_store` retrieval scripts in advance of any exam. |
| OCC Heightened Standards (12 CFR Part 30, Appendix D) | Applies to large banks; governance and risk-appetite framework | The bulletin's MRM expectations sit inside this broader heightened-standards regime; board reporting must roll up accordingly. |
| 12 CFR Part 30, Appendix B — Operational Resilience expectations (2024) | Resilience overlay | `defcon` autonomy degradation can be wired as a resilience control input; the wiring is institution-specific. |
| Third-party risk management — OCC Bulletin 2013-29 and the 2023 interagency final guidance | Vendor governance program | `vendor_score_gate` is one technical control; the surrounding TPRM program is contractual and procedural. |
| Fair lending model overlay (OCC supervisory expectations) | Substantive law, not MRM | See `docs/ecoa_mapping.md` and `docs/fcra_mapping.md` for the fair-lending and adverse-action control surfaces. |

---

## References

- Office of the Comptroller of the Currency. _OCC Bulletin 2011-12: Sound
  Practices for Model Risk Management — Supervisory Guidance on Model Risk
  Management._ April 4, 2011.
  <https://www.occ.gov/news-issuances/bulletins/2011/bulletin-2011-12.html>
  (canonical URL confirmed via OCC bulletin index; direct fetch returned
  403 / 404 on 2026-05-28 — content verified via FDIC FIL-22-2017 adoption
  notice and the OCC 2011 bulletin index).
- Office of the Comptroller of the Currency. _2011 Bulletins index._
  <https://www.occ.treas.gov/news-events/newsroom/news-issuances-by-year/bulletins/2011-bulletins.html>
  (retrieved 2026-05-28).
- Office of the Comptroller of the Currency. _OCC Bulletin 2025-26: Model Risk
  Management — Clarification._ October 6, 2025
  [UNVERIFIED — primary source not fetched: https://www.occ.gov/news-issuances/bulletins/2025/bulletin-2025-26.html;
  reference confirmed via cited secondary index on 2026-05-28].
- Office of the Comptroller of the Currency. _Comptroller's Handbook — Model
  Risk Management Booklet._ August 2021
  [UNVERIFIED — primary source not fetched: https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/files/model-risk-management/index-model-risk-management.html;
  reference confirmed via OCC 2021-39 issuance summary on 2026-05-28].
- FDIC. _Financial Institution Letter FIL-22-2017: Adoption of Supervisory
  Guidance on Model Risk Management._ June 7, 2017.
  <https://www.fdic.gov/news/financial-institution-letters/2017/fil17022.html>
  (retrieved 2026-05-28; primary corroboration that OCC 2011-12 and SR 11-7
  share the same attached guidance).
- Board of Governors of the Federal Reserve System. _SR 11-7: Guidance on
  Model Risk Management._ April 4, 2011.
  <https://www.federalreserve.gov/supervisionreg/srletters/sr1107.htm>
  (retrieved 2026-05-28).
