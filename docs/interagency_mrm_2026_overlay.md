# Interagency Model Risk Management — 2026 Overlay

**OCC Bulletin 2026-13 · _Model Risk Management: Revised Guidance_ · April 17, 2026**
**Joint issuance: OCC, Federal Reserve Board, FDIC**
**Status: primary-source verified (OCC site, fetched 2026-05-28)**

---

> **Disclaimer.** This document interprets a supervisory issuance for engineering and second-line model-risk-management audiences. It is not legal advice. Every institution must reconcile this overlay with its own General Counsel, second-line model-validation function, and prudential examiner.

---

## 1. The April 17, 2026 issuance — what changed

On April 17, 2026 the OCC, Federal Reserve Board, and FDIC jointly issued revised guidance on model risk management. The OCC promulgated it as **OCC Bulletin 2026-13, _Model Risk Management: Revised Guidance_**, signed by James M. Gallagher (Senior Deputy Comptroller and Chief National Bank Examiner), addressed to "Chief Executive Officers of all national banks, federal savings associations, and federal branches and agencies of foreign banking organizations."

The bulletin **rescinds four prior instruments**:

1. **OCC Bulletin 2011-12** — _Sound Practices for Model Risk Management_ (April 4, 2011), the OCC counterpart to Federal Reserve SR 11-7.
2. **OCC Bulletin 1997-24** — _Credit Scoring Models_.
3. **OCC Bulletin 2021-19** — _BSA/AML Model Risk Management_.
4. **The _Model Risk Management_ booklet of the Comptroller's Handbook**.

For OCC-supervised institutions, the binding instrument is now Bulletin 2026-13. Federal Reserve-supervised institutions follow the parallel SR letter issued the same day. FDIC-supervised institutions follow the corresponding FIL.

For the framework's purposes, every reference to "OCC Bulletin 2011-12" or "SR 11-7" in v1.1 documentation now reads as **legacy citation — superseded for new examination cycles, retained for historical evidence (in-flight validations, prior-period audit chains, examiner exhibits filed under the prior guidance).** The four expectations of the 2011 attachment (sound development; effective validation; governance and controls; effective challenge) survive the rescission as **conceptual ancestry** but no longer as binding citation.

## 2. The agentic-AI carve-out — verbatim

Two passages in OCC Bulletin 2026-13 contain identical language regarding generative and agentic AI:

> "Generative AI and agentic AI models are novel and rapidly evolving. As such, they are not within the scope of this guidance."

The agencies further committed to issuing, in the near future, "a request for information that addresses model risk management generally and considers, in particular, banks' use of AI, including generative AI and agentic AI and AI-based models."

This is the operative regulatory white-space the framework occupies. The agencies explicitly removed agentic AI from the new MRM guidance, did not replace it with a new agentic-AI-specific instrument, and signalled that the replacement will arrive via RFI process. Until that RFI completes — comment period, agency synthesis, final guidance — every US national bank, federal savings association, federal branch, and (by parallel issuance) every state-member bank and FDIC-supervised institution that runs agentic AI is operating without a binding supervisory framework for those systems.

The framework's positioning: **provide the operational reference banks use while waiting for the joint RFI.**

## 3. Module-by-module overlay

The 15 governance modules shipped in v1.1 fall into three tranches under the post-2026-13 landscape: (a) modules whose binding citation lineage shifts (the ancestral MRM modules), (b) modules whose binding citation lineage is unchanged (those grounded in other regimes — GLBA, FCRA, ECOA, BSA/AML, SOX, SEC 17a-4), and (c) modules that occupy the agentic-AI gap directly.

### Tranche A — Ancestral MRM lineage (citation updates)

| Module | Canonical path | v1.1 framing | v1.2 framing |
|---|---|---|---|
| `defcon` | `finserv_agent_audit.governance.defcon` | Operationalizes "sound development, implementation, use" (OCC 2011-12 § IV) | Conceptual ancestry preserved; binding citation deferred pending RFI. Operational reference for the autonomy-degradation control surface the RFI is expected to address. |
| `sovereign_veto` | `finserv_agent_audit.governance.sovereign_veto` | Effective challenge (OCC 2011-12 § V) | Effective challenge is preserved as a discipline; the framework provides the technical control that satisfies whatever the RFI lands on. |
| `audit_chain` | `finserv_agent_audit.governance.audit_chain` | Model documentation + life-of-model evidence (OCC 2011-12 § IV) | The hash-chain audit log is the evidence pipeline second-line MRM uses regardless of binding-citation drift. SR 11-7 § IV remains the analytical ancestry. |
| `autonomy_ladder` | `finserv_agent_audit.governance.autonomy_ladder` | A0→A4 progression as the model-development overlay (OCC 2011-12 § IV) | The progression doctrine is the framework-native answer to the agentic-AI scope-of-action question the RFI will have to address. |
| `shadow_mode` | `finserv_agent_audit.governance.shadow_mode` | Conceptual-soundness validation (OCC 2011-12 § V) | Validation discipline preserved; the shadow-mode pattern is the technical evidence path. |
| `ledger_store` (jsonl / sqlite / WORM) | `finserv_agent_audit.governance.ledger_store_*` | Record-keeping (OCC 2011-12 record-keeping footnote) | Record-keeping discipline preserved; WORM variant is the SEC 17a-4(f) technical control independent of MRM citation drift. |
| `timestamp_source` | `finserv_agent_audit.governance.timestamp_source` | Trusted-time backbone for audit chain | Preserved; underpins the witness-anchor pattern. |
| `witness_anchor` | `finserv_agent_audit.governance.witness_anchor` | Internal-audit cross-verification (OCC 2011-12 § VI) | Preserved as the technical answer to "evidence the second line cannot quietly mutate." |
| `mi_proxy` | `finserv_agent_audit.governance.mi_proxy` | Model-implementation soundness control (OCC 2011-12 § V) | Verifier-integrity discipline preserved; the asymmetric-attestation upgrade path is the RFI-ready posture. |
| `vendor_score_gate` | `finserv_agent_audit.governance.vendor_score_gate` | Third-party / external-resources governance (OCC 2011-12 § VI; OCC 2013-29; 2023 interagency final TPRM guidance) | TPRM lineage is unchanged. Vendor governance survives the MRM rescission because its binding citation lives in the interagency TPRM final guidance, not in 2011-12. |
| `model_inventory` | `finserv_agent_audit.governance.model_inventory` | Model inventory + lifecycle states (OCC 2011-12 § III) | Inventory discipline preserved; the lifecycle state machine is the RFI-ready inventory surface. |

### Tranche B — Non-MRM-anchored modules (citation lineage unchanged)

| Module | Canonical path | Binding citation (unchanged) |
|---|---|---|
| `adverse_action_gate` | `finserv_agent_audit.governance.adverse_action_gate` | FCRA § 615 / Regulation V; ECOA / Regulation B § 1002.9 |
| `sar_workflow_audit` | `finserv_agent_audit.governance.sar_workflow_audit` | BSA / 31 CFR § 1020.320; FinCEN SAR-confidentiality regime |
| `equity_audit` | `finserv_agent_audit.governance.equity_audit` | ECOA / Regulation B § 1002.4; HMDA; CFPB Circular 2022-03 |
| `best_interest_check` | `finserv_agent_audit.governance.best_interest_check` | SEC Regulation Best Interest (17 CFR § 240.15l-1) |
| `protected_class_proxy_detector` | `finserv_agent_audit.governance.protected_class_proxy_detector` (deferred per ADR-0019) | ECOA proxy doctrine; FHA; CFPB UDAAP authority |

None of these is touched by the 2026-13 rescission. The relevant mapping docs (`docs/fcra_reg_v_mapping.md`, `docs/ecoa_reg_b_mapping.md`, `docs/bsa_aml_mapping.md`, `docs/sec_reg_bi_mapping.md`) remain authoritative on their respective surfaces.

### Tranche C — Modules that occupy the agentic-AI gap directly

The four-module subset that the framework presents as the **operational reference for agentic AI pre-RFI**:

1. **`autonomy_ladder`** — formalizes A0 (recommend only) → A4 (fully autonomous within sovereign-veto envelope). The RFI will have to address scope of action; the ladder is one prior-art answer.
2. **`sovereign_veto`** — the human-in-the-loop control that survives every plausible RFI outcome. If the joint guidance lands on "humans must retain effective challenge over agentic AI," `sovereign_veto` is the engineering pattern that operationalizes that.
3. **`defcon`** — autonomy-degradation state machine. The framework's answer to "what does the agent do when it loses trust in itself?" — directly relevant to whatever circuit-breaker requirement the RFI lands on.
4. **`audit_chain` + `witness_anchor` + `ledger_store_worm`** — the evidence stack. Whatever the RFI requires for agentic-AI model documentation, life-of-model evidence, or second-line review, the SHA-256 hash-chain + external witness anchor + WORM ledger combination satisfies the technical control surface.

## 4. Why this framework is the operational reference banks use while waiting for the joint RFI

Three structural reasons.

### 4.1 The agencies have not paused the production deployment of agentic AI

Banks have agentic AI in production today — customer-service triage, internal operations automation, fraud-detection cascade orchestration, treasury-operations co-pilots. The agencies' April 2026 carve-out did not pause those deployments; it simply removed the binding MRM citation. Every second-line MRM team running these systems needs a **defensible operational framework** to point examiners and the audit committee at while the RFI process unfolds. Pointing at "we are waiting for guidance" is not a defensible posture; pointing at "we are governed by `finserv-agent-audit` v1.x, MIT-licensed, primary-source-mapped, and we will reconcile with the RFI when finalized" is.

### 4.2 The framework's binding-citation lineage is multi-regime, not 2011-12-dependent

The MRM rescission does not eliminate the model-validation, governance, or audit-evidence obligations facing a bank running agentic AI. Those obligations are also expressed in **GLBA Safeguards Rule**, **SOX § 404 ITGC**, **SEC 17a-4(f)** record-keeping, the **OCC Heightened Standards** (12 CFR Part 30, Appendix D), the **interagency third-party risk management final guidance** (2023), and the **Treasury Financial Services Sector AI Risk Management Framework** (February 12, 2026, 230 control objectives, 100+ contributing institutions). The framework's mapping documentation already references each of those regimes. The 2026-13 rescission shifts the binding citation; it does not unwind the control surface.

### 4.3 The framework is the only public reference designed for agentic AI, not for traditional statistical models

SR 11-7 / OCC 2011-12 were drafted for credit-risk and market-risk statistical models — instruments where inputs, outputs, and the validation surface are stable. Agentic AI does not match that shape: it acts, the action affects state, the state affects subsequent action, and the trust boundary moves at machine speed. The framework's six v1.0 patterns (DEFCON, Sovereign Veto, Autonomy Ladder, Audit Chain, Shadow Mode, Vendor Score Gate) plus the nine v1.1 hardening modules (MI Proxy, Witness Anchor, Timestamp Source, Ledger Store variants, Model Inventory, Adverse Action Gate, SAR Workflow Audit, Equity Audit, Best Interest Check) are designed at the shape of agentic AI, not retrofitted from a credit-scorecard frame. That design fit is the reason the framework is the public reference banks consult while the RFI clock runs.

## 5. The validation packet a second-line MRM team can put on file today

The framework ships with companion documents intended to land on a Chief Risk Officer's desk as a defensible pre-RFI posture:

- **`ASSURANCE-GUIDE.md`** — second-line walkthrough for using `model_inventory`, `audit_chain`, `witness_anchor`, and `mi_proxy` as model-risk-management evidence.
- **`DEPLOY-CHECKLIST.md`** — pre-production deployment checklist for any agentic-AI workload running on the framework.
- **`docs/MRM_BRIDGE_TEMPLATE.md`** — a forkable internal whitepaper template a bank's second line can submit to its model-risk committee to document the rationale for adopting `finserv-agent-audit` v1.x pre-RFI.
- **`docs/treasury_fs_ai_rmf_mapping.md`** — module-to-control-objective cross-walk against the Treasury / Cyber Risk Institute FS AI RMF (the most-mature operational framework available as of this writing).
- **`docs/nist_ai_600_1_genai_profile_mapping.md`** — module mapping against the 12 NIST AI 600-1 generative-AI risk categories.

Combined, these supply the second-line model-risk-management function with the evidence package to defend "we are not running ungoverned agentic AI; we are running governed agentic AI under a documented framework selected on first-principles grounds." That defence holds whether the joint RFI lands in late 2026 or 2028.

## 6. Sunset clause

This overlay document, the modules cited herein, the bridge template, and the citation refresh across v1.1 documentation are all bounded by the same sunset condition: **when the joint OCC/FRB/FDIC RFI on agentic-AI MRM is finalized**, the framework's binding-citation references update accordingly. The architecture does not change; the citation header on the exam exhibit does. The framework's commitment is to ship the citation refresh within one minor release of RFI finalization.

## 7. References

- Office of the Comptroller of the Currency. _OCC Bulletin 2026-13: Model Risk Management — Revised Guidance._ April 17, 2026. <https://www.occ.treas.gov/news-issuances/bulletins/2026/bulletin-2026-13.html>. PDF: <https://www.occ.gov/news-issuances/bulletins/2026/bulletin-2026-13a.pdf>. **(Primary source verified via WebFetch on 2026-05-28; bulletin number, date, joint issuance, four rescissions, agentic-AI scope-exclusion language, RFI commitment, and signatory all confirmed verbatim.)**
- Federal Reserve Board. _SR Letter parallel to OCC Bulletin 2026-13._ April 17, 2026. [UNVERIFIED — primary source not fetched in this session; parallel issuance referenced in OCC 2026-13 text.]
- Federal Deposit Insurance Corporation. _Financial Institution Letter parallel to OCC Bulletin 2026-13._ April 17, 2026. [UNVERIFIED — primary source not fetched in this session; parallel issuance referenced in OCC 2026-13 text.]
- Cyber Risk Institute. _Financial Services Industry Unites to Launch Comprehensive AI Risk Management Framework._ February 12, 2026. <https://www.cyberriskinstitute.org/press/financial-services-industry-unites-to-launch-comprehensive-ai-risk-management-framework>. (Verified via WebFetch 2026-05-28; 230 control objectives, 100+ contributing institutions, FSSCC coordination.)
- NIST. _NIST AI 600-1: AI Risk Management Framework — Generative AI Profile._ July 26, 2024. <https://airc.nist.gov/airmf-resources/ai-rmf-generative-ai-profile/>. (Verified via WebFetch 2026-05-28.)
- Office of the Comptroller of the Currency. _OCC Bulletin 2011-12: Sound Practices for Model Risk Management._ April 4, 2011 — **rescinded by OCC Bulletin 2026-13.** Retained in framework documentation as conceptual ancestry only.
- Board of Governors of the Federal Reserve System. _SR 11-7: Guidance on Model Risk Management._ April 4, 2011 — **superseded for new examinations by the April 17, 2026 SR letter parallel to OCC 2026-13.** Retained in framework documentation as conceptual ancestry only.
