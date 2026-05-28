# Treasury Financial Services Sector AI Risk Management Framework — Module Cross-Walk

**Source: Cyber Risk Institute (CRI) — _Financial Services AI Risk Management Framework_ (FS AI RMF), published February 12, 2026, in coordination with the Financial Services Sector Coordinating Council (FSSCC). 230 control objectives. 100+ contributing financial institutions globally.**

**Status:** Primary-source verified via the CRI press release ("Financial Services Industry Unites to Launch Comprehensive AI Risk Management Framework," fetched 2026-05-28). The full framework text (230 control objectives, mapped risk statements, trustworthy-AI principle alignment) is published through CRI member-access channels; this mapping treats the public press release as the authoritative summary and marks every control-objective-level detail as ABSTRACT-ONLY where the full text is not in public hand.

> **Disclaimer.** This mapping is provided for reference only and does not constitute legal or supervisory advice. Banks should procure or access the full FS AI RMF text through CRI / FSSCC channels for production use.

---

## 1. Context — why this framework matters in the agentic-AI gap

The FS AI RMF, launched February 12, 2026, is **the most-mature operational AI-governance framework available to the US financial services industry as of this writing**. Three structural facts make it the reference of choice for second-line MRM functions building their post-OCC-2026-13 posture:

1. **Sector-led, not vendor-led.** CRI is the industry coordinating body; 100+ financial institutions contributed. The framework is consensus prudential industry practice, not a single-vendor narrative.
2. **230 control objectives.** The control surface is granular enough to function as a checklist for second-line model-validation walkthroughs.
3. **FSSCC coordination.** The FSSCC is the sector's formal liaison with US Treasury and the financial regulators. The framework's posture is therefore the one most likely to be cited approvingly by examiners during the interval before the joint OCC / FRB / FDIC RFI on agentic-AI MRM completes.

For the framework's positioning relative to the April 17, 2026 OCC Bulletin 2026-13, see `docs/interagency_mrm_2026_overlay.md`.

---

## 2. Risk categories — public abstract

The CRI press release names the following risk areas the framework addresses:

| FS AI RMF risk area | Public abstract | Verification status |
|---|---|---|
| **Fairness** | AI outcomes that produce disparate effects across protected classes; fair-lending overlay | ABSTRACT-ONLY (public press release) |
| **Transparency** | Explainability of model behaviour to consumers, regulators, and internal validators | ABSTRACT-ONLY |
| **Data Privacy** | Protection of consumer financial information used to train and operate AI models | ABSTRACT-ONLY |
| **Security** | Adversarial-robustness, prompt-injection, model-extraction, supply-chain integrity | ABSTRACT-ONLY |
| **Operational Resilience** | AI-workload availability, degradation modes, recovery posture | ABSTRACT-ONLY |

Six additional risk categories Treasury named in its prior 2024 financial-services-AI report (_Managing Artificial Intelligence-Specific Cybersecurity Risks in the Financial Services Sector_, March 2024) recur in the same conceptual space and should be treated as in-scope for any second-line walkthrough:

| Treasury 2024 risk category | Bridges to FS AI RMF area |
|---|---|
| Data privacy / security / quality | Data Privacy + Security |
| Bias / explainability / hallucinations | Fairness + Transparency |
| Consumer protection / fair lending / financial inclusion | Fairness |
| Concentration | Operational Resilience + Security (third-party / supply chain) |
| Third-party risk | Security + Operational Resilience |
| Illicit finance | (orthogonal — flows to the institution's BSA/AML AI workload governance) |

The full 230 control objectives, the per-objective risk-statement linkage, and the trustworthy-AI-principle alignment are documented in the CRI / FSSCC publication and are not reproduced here.

---

## 3. Module cross-walk — `finserv-agent-audit` v1.x against the public risk areas

Each row maps a v1.1 governance module to the FS AI RMF public risk areas that module addresses, plus the relevant ADR for the design rationale.

### 3.1 Fairness

| Module | Canonical path | How it addresses Fairness | ADR |
|---|---|---|---|
| `adverse_action_gate` | `finserv_agent_audit.governance.adverse_action_gate` | FCRA § 615 / Reg B § 1002.9 adverse-action notices; specific reasons must be recorded and disclosed | ADR-0009 |
| `equity_audit` | `finserv_agent_audit.governance.equity_audit` | ECOA / Reg B § 1002.4 disparate-impact monitoring; per-cohort outcome tracking | ADR-0010 |
| `protected_class_proxy_detector` | `finserv_agent_audit.governance.protected_class_proxy_detector` (deferred per ADR-0019) | ECOA proxy doctrine; flags features that proxy for protected-class status | ADR-0019 |

### 3.2 Transparency

| Module | Canonical path | How it addresses Transparency | ADR |
|---|---|---|---|
| `audit_chain` | `finserv_agent_audit.governance.audit_chain` | Per-decision rationale entry recorded in SHA-256 hash-chain; reconstructable post-hoc | ADR-0003 |
| `model_inventory` | `finserv_agent_audit.governance.model_inventory` | Per-model lifecycle state, validation date, owning second-line MRM function | ADR-0007 derivative |
| `autonomy_ladder` | `finserv_agent_audit.governance.autonomy_ladder` | A0→A4 progression makes the agent's scope of action explicit and inspectable | ADR-0004 |
| `shadow_mode` | `finserv_agent_audit.governance.shadow_mode` | Promotion decisions documented; conceptual-soundness evidence packet generated | ADR-0006 |

### 3.3 Data Privacy

| Module | Canonical path | How it addresses Data Privacy | ADR |
|---|---|---|---|
| `audit_chain` | `finserv_agent_audit.governance.audit_chain` | Per-decision evidence supports GLBA Safeguards § 314 incident-response and access-audit obligations | ADR-0003 |
| `mi_proxy` | `finserv_agent_audit.governance.mi_proxy` | Verifier-integrity control prevents silent data-handling-logic modification | ADR-0015 |
| `vendor_score_gate` | `finserv_agent_audit.governance.vendor_score_gate` | Third-party / pre-trained model data-handling governance | ADR-0016 |

See `docs/glba_safeguards_mapping.md` for the GLBA-specific surface.

### 3.4 Security

| Module | Canonical path | How it addresses Security | ADR |
|---|---|---|---|
| `mi_proxy` | `finserv_agent_audit.governance.mi_proxy` | Model-implementation integrity; verifier root-of-trust attestation | ADR-0015 |
| `witness_anchor` | `finserv_agent_audit.governance.witness_anchor` | External anchor to detect tamper attempts against the audit chain | ADR-0014 |
| `ledger_store_worm` | `finserv_agent_audit.governance.ledger_store_worm` | WORM record-keeping prevents post-hoc audit-log modification | ADR-0013 derivative |
| `sovereign_veto` | `finserv_agent_audit.governance.sovereign_veto` | Out-of-band kill switch independent of the agent's own decision surface | ADR-0002 |
| `vendor_score_gate` | `finserv_agent_audit.governance.vendor_score_gate` | Supply-chain governance for third-party / pre-trained model components | ADR-0016 |
| (deferred) Adversarial-agent threat model | (design pattern, no module yet) | Threat-model document for prompt-injection, model-extraction, jailbreak | ADR-0018 |

### 3.5 Operational Resilience

| Module | Canonical path | How it addresses Operational Resilience | ADR |
|---|---|---|---|
| `defcon` | `finserv_agent_audit.governance.defcon` | Autonomy-degradation state machine: NORMAL → CAUTION → ALERT → DANGER with hysteresis | ADR-0001 |
| `sovereign_veto` | `finserv_agent_audit.governance.sovereign_veto` | Operator-initiated emergency degradation independent of model state | ADR-0002 |
| `autonomy_ladder` | `finserv_agent_audit.governance.autonomy_ladder` | Graceful fallback from A4 → A3 → … → A0 when trust degrades | ADR-0004 |
| `shadow_mode` | `finserv_agent_audit.governance.shadow_mode` | Pre-promotion validation prevents resilience-degrading deployments | ADR-0006 |
| `timestamp_source` | `finserv_agent_audit.governance.timestamp_source` | Trusted-time backbone for resilience-event timeline reconstruction | ADR-0014 derivative |

---

## 4. Cross-mapping at the Treasury 2024 risk-category level

For the 2024 risk-category vocabulary banks may still encounter in older policy documents:

| Treasury 2024 risk category | Primary v1.x modules | Mapping doc |
|---|---|---|
| Data privacy / security / quality | `audit_chain`, `mi_proxy`, `vendor_score_gate`, `witness_anchor`, `ledger_store_worm` | `docs/glba_safeguards_mapping.md` |
| Bias / explainability / hallucinations | `adverse_action_gate`, `equity_audit`, `audit_chain`, `model_inventory`, `autonomy_ladder`, `shadow_mode` | `docs/ecoa_reg_b_mapping.md`, `docs/fcra_reg_v_mapping.md`, `docs/cfpb_circular_2022_03_mapping.md` |
| Consumer protection / fair lending / financial inclusion | `adverse_action_gate`, `equity_audit`, `best_interest_check` | `docs/ecoa_reg_b_mapping.md`, `docs/fcra_reg_v_mapping.md`, `docs/sec_reg_bi_mapping.md` |
| Concentration | `vendor_score_gate`, `model_inventory` | (Concentration risk is institution-specific; the modules supply the inventory and vendor-score evidence that feeds concentration analysis.) |
| Third-party risk | `vendor_score_gate`, `mi_proxy`, `model_inventory` | (Interagency TPRM final guidance, June 6, 2023; OCC Bulletin 2013-29 historical lineage.) |
| Illicit finance | `sar_workflow_audit`, `audit_chain`, `witness_anchor` | `docs/bsa_aml_mapping.md` |

---

## 5. Gap analysis — what Treasury / FS AI RMF covers that the framework does not yet

The framework's v1.x module set covers the operational-governance surface — the runtime patterns an agentic-AI workload needs to ship under prudential oversight. The FS AI RMF (and the broader Treasury / FSSCC corpus) covers additional surfaces that the framework either defers or addresses only through references to companion regimes.

### 5.1 Gaps the framework defers

| Gap | Why deferred | v2.0 disposition |
|---|---|---|
| **Adversarial-agent threat-model module** | Threat-model documentation exists as ADR-0018 but no runtime module yet | Candidate for v2.0 — runtime adversarial-input detection layer |
| **Protected-class proxy detection** | Deferred per ADR-0019 pending stable statistical baseline | Candidate for v2.0 — full implementation with cohort-baseline calibration |
| **AI-specific concentration-risk monitor** | Concentration analysis is institution-portfolio-level, not module-level | Candidate for v2.0 — inventory aggregation feeding concentration dashboard |
| **Explainability surface (SHAP / counterfactual)** | Substantive explainability requires per-model implementation; framework records the rationale, not the explainability artefact itself | Candidate for v2.0 — explainability evidence schema in `audit_event` |
| **Consumer-facing AI-decision disclosure templates** | Substantive law (FCRA § 615, ECOA § 1002.9) plus institution-specific brand voice; framework supplies the trigger and audit hook, not the consumer letter | Out of scope — institution-specific |
| **Hallucination / confabulation runtime detector** | Detection is workload-specific (retrieval-augmented, citation-required, etc.); framework records the event when flagged but does not detect | Candidate for v2.0 — confabulation-flag hook in `audit_event` |

### 5.2 Gaps the framework addresses by reference

| Gap | Reference |
|---|---|
| **GLBA Safeguards § 314 program** | `docs/glba_safeguards_mapping.md` |
| **SOX § 404 ITGC** | `docs/sox_404_itgc_mapping.md` |
| **SEC 17a-4 record-keeping** | `docs/sec_17a_4_mapping.md` + `ledger_store_worm` |
| **EU AI Act high-risk obligations** | `docs/eu_ai_act_mapping.md` |
| **ISO/IEC 42001 AI management system** | `docs/iso_42001_mapping.md` |
| **NIST AI RMF 1.0 + Generative AI Profile** | `docs/nist_ai_rmf_mapping.md`, `docs/nist_ai_600_1_genai_profile_mapping.md` |
| **Interagency TPRM final guidance (2023)** | `docs/occ_2011_12_mapping.md` § Gap Analysis (vendor section) |

### 5.3 Gaps that are out of scope by design

| Gap | Why out of scope |
|---|---|
| **Insurance regulation (NAIC Model Bulletin on AI)** | State-by-state insurance posture; framework is bank-and-broker-dealer focused. Banks with insurance subsidiaries must layer NAIC overlay separately. |
| **CFPB UDAAP enforcement specifics** | Enforcement posture, not control surface. Framework supports evidence retention; the substantive UDAAP analysis is legal. |
| **State-level AI statutes (Colorado SB 24-205 / SB 189, Texas TRAIGA, NYC Local Law 144, etc.)** | State-by-state posture diverges; institution must reconcile by jurisdiction. |

---

## 6. Operational use — how a second-line MRM function uses this mapping

A second-line model-risk-management function uses this mapping in three operational contexts:

1. **Pre-deployment review.** Before any agentic-AI workload enters production, the second line walks each of the FS AI RMF public risk areas (Section 3) and confirms the relevant v1.x modules are wired, configured, and emitting evidence.
2. **Examiner walkthrough.** During a prudential examination, the second line presents the FS AI RMF risk-area table (Section 3) as the bridge between the examiner's regulatory frame and the institution's technical controls.
3. **Internal-audit cycle.** During the internal-audit cycle, the audit function uses Section 5 (gap analysis) to assess residual risk that the framework does not yet address; gaps marked "Candidate for v2.0" flag the institution's roadmap for compensating controls.

---

## 7. References

- Cyber Risk Institute. _Financial Services Industry Unites to Launch Comprehensive AI Risk Management Framework._ February 12, 2026. <https://www.cyberriskinstitute.org/press/financial-services-industry-unites-to-launch-comprehensive-ai-risk-management-framework>. **(Primary-source verified via WebFetch 2026-05-28; date, 230 control objectives, 100+ contributing institutions, FSSCC coordination, and risk-area list confirmed.)**
- Cyber Risk Institute. _Financial Services AI Risk Management Framework_ (full document). [ABSTRACT-ONLY — full text published through CRI member-access channels; not fetched in this session.]
- U.S. Department of the Treasury. _Managing Artificial Intelligence-Specific Cybersecurity Risks in the Financial Services Sector._ March 2024. [UNVERIFIED — primary source not fetched in this session; six-category vocabulary cited from public summaries on 2026-05-28.]
- Financial Services Sector Coordinating Council. _FSSCC AI Working Group._ [UNVERIFIED — primary source not fetched in this session.]
- Office of the Comptroller of the Currency. _OCC Bulletin 2026-13: Model Risk Management — Revised Guidance._ April 17, 2026. (Primary-source verified; see `docs/interagency_mrm_2026_overlay.md`.)
- `finserv-agent-audit` v1.x — `docs/interagency_mrm_2026_overlay.md`, `docs/nist_ai_600_1_genai_profile_mapping.md`, `ASSURANCE-GUIDE.md`, per-regime mapping documents under `docs/`.
