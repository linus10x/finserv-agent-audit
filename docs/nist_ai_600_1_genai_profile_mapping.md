# NIST AI 600-1 Generative AI Profile — Module Cross-Walk

**Source: NIST AI 600-1, _Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile_, published July 26, 2024 (finalized; draft released April 29, 2024). Companion to NIST AI 100-1 (the AI RMF 1.0) and structured around the AI RMF's four core functions: Govern, Map, Measure, Manage.**

**Status:** Primary-source verified via the NIST AI RMF resource landing page (fetched 2026-05-28). The full 12-category risk taxonomy is summarized below from the published profile and corroborating sources.

> **Disclaimer.** This mapping is provided for reference only and does not constitute legal or supervisory advice. Banks should consult the full NIST AI 600-1 text for production use.

---

## 1. Context — why the GenAI Profile is the framework's de facto operational reference

NIST AI 600-1 is the operational complement to the AI RMF 1.0 for generative-AI workloads. It enumerates 12 risk categories that are unique to or exacerbated by generative AI, and for each category provides an action matrix indexed against the Govern / Map / Measure / Manage functions of the AI RMF. Two reasons make the GenAI Profile the framework's de facto operational reference:

1. **It is the most-cited US-government GenAI risk taxonomy.** Cross-references appear in the Treasury FS AI RMF (`docs/treasury_fs_ai_rmf_mapping.md`), the EU AI Act implementing acts, and state-level AI statutes.
2. **Its action-matrix structure matches how the framework's modules slot in.** Each risk category maps cleanly to Govern (board / policy / inventory), Map (context-of-use), Measure (validation / monitoring), Manage (response / incident) — the same four-axis vocabulary that ASSURANCE-GUIDE.md and DEPLOY-CHECKLIST.md follow.

For the framework's positioning relative to the post-OCC-2026-13 agentic-AI gap, see `docs/interagency_mrm_2026_overlay.md`.

---

## 2. The 12 risk categories — one section per category

For each category: (a) the NIST AI 600-1 definition (summarized), (b) the framework modules that apply, (c) the Govern / Map / Measure / Manage assignment, (d) gap notes.

### 2.1 CBRN Information or Capabilities

**Definition (summarized).** Generative AI lowering the barrier to chemical, biological, radiological, or nuclear weapons information or capabilities.

**Framework modules.** Out of scope for FSI applications by sectoral fit; the framework's relevance is limited to **negative-use-case** documentation and policy gating.

**Govern.** `vendor_score_gate` for any upstream model whose training data may include CBRN-relevant material; institutional policy gate referencing this risk in the model-risk policy.
**Map.** Workload classification — banks running customer-service or operations workloads have low intrinsic CBRN exposure, but pre-trained model components may carry latent capability.
**Measure.** Not a primary framework measurement surface.
**Manage.** `sovereign_veto` and `defcon` for any incident detection where a workload produces CBRN-adjacent output.

**Gap.** No FSI-specific CBRN detector in the framework; treated as an institution-policy gate, not a runtime control. **Out of scope by design for v2.0** — banks should rely on the upstream model provider's safety filters and the institution's content-moderation policy.

### 2.2 Confabulation

**Definition (summarized).** The production of confidently stated content that has no basis in input data or factual reality — "hallucination."

**Framework modules.** `audit_chain`, `model_inventory`, `shadow_mode`, `defcon`, `sovereign_veto`.

**Govern.** `model_inventory` lifecycle state must include a documented confabulation-tolerance posture per workload.
**Map.** Workload classification — retrieval-augmented vs. open-generative; the higher the open-generative surface, the higher the confabulation residual.
**Measure.** `shadow_mode` promotion criteria must include confabulation-rate measurement; `audit_chain` per-decision rationale entries support post-hoc confabulation review.
**Manage.** `sovereign_veto` and `defcon` for runtime confabulation-rate exceedances.

**Gap.** No runtime confabulation detector ships in v1.x. **Candidate for v2.0** — a confabulation-flag hook in `audit_event`, with workload-specific detection logic supplied by adopters.

### 2.3 Dangerous, Violent, or Hateful Content

**Definition (summarized).** Generative-AI production of content that incites or describes violence, harassment, or hateful expression.

**Framework modules.** `audit_chain`, `sovereign_veto`, `defcon`, `vendor_score_gate`.

**Govern.** Institutional content-policy referenced in `model_inventory`; vendor governance via `vendor_score_gate` to ensure upstream safety filters are documented and tested.
**Map.** Workload exposure — customer-facing surfaces have higher exposure than internal-operations workloads.
**Measure.** `audit_chain` retention of flagged outputs for post-hoc review; institution-specific content-moderation classifier supplies the runtime signal.
**Manage.** `sovereign_veto` and `defcon` for runtime exceedance; institution-specific user-notification and remediation workflow.

**Gap.** No runtime content classifier in the framework. Out of scope by design — content-moderation is a substantive product layer separate from governance.

### 2.4 Data Privacy

**Definition (summarized).** Risks to personal-data confidentiality from training-set leakage, inversion attacks, or unintended memorization.

**Framework modules.** `audit_chain`, `mi_proxy`, `vendor_score_gate`, `model_inventory`, `ledger_store_worm`.

**Govern.** `model_inventory` records the data-classification of training and inference inputs; `vendor_score_gate` records the upstream model provider's privacy posture.
**Map.** Workload data-handling map — what consumer financial information enters the prompt or fine-tuning corpus.
**Measure.** `mi_proxy` verifier-integrity attestation guards against silent data-handling-logic modification; `audit_chain` records per-decision data-touch events.
**Manage.** `sovereign_veto` for privacy-incident response; `ledger_store_worm` for forensic retention.

**Gap.** No differential-privacy or membership-inference detection in v1.x. Out of scope by design — these are model-training-stage controls; framework operates at the agent-governance stage. Cross-references: `docs/glba_safeguards_mapping.md`.

### 2.5 Environmental Impacts

**Definition (summarized).** Energy, water, and carbon footprint of training and inference at scale.

**Framework modules.** `model_inventory` (lifecycle disposition), `vendor_score_gate` (upstream provider disclosure).

**Govern.** `model_inventory` may carry an environmental-footprint field per institution policy; `vendor_score_gate` records upstream provider disclosures where available.
**Map.** Workload footprint — high-throughput inference workloads vs. low-throughput.
**Measure.** Not a primary framework measurement surface.
**Manage.** Out of scope for the framework's runtime control surface.

**Gap.** Substantively out of scope for v2.0; framework's contribution is metadata-only via `model_inventory`.

### 2.6 Harmful Bias and Homogenization

**Definition (summarized).** Generative-AI amplification of statistical bias against protected classes; homogenization of outputs across users.

**Framework modules.** `equity_audit`, `adverse_action_gate`, `protected_class_proxy_detector` (deferred), `audit_chain`, `model_inventory`, `shadow_mode`.

**Govern.** `model_inventory` records fair-lending posture; institution-specific fair-lending policy gates the workload.
**Map.** Workload classification — credit-decisioning, marketing-segmentation, customer-treatment-differentiation surfaces are higher-exposure.
**Measure.** `equity_audit` per-cohort outcome tracking; `shadow_mode` promotion criteria include disparate-impact thresholds.
**Manage.** `adverse_action_gate` for FCRA / Reg B notification; `sovereign_veto` for runtime disparate-impact exceedance.

**Gap.** `protected_class_proxy_detector` is deferred per ADR-0019. **Candidate for v2.0** — full implementation with stable cohort-baseline calibration. Cross-references: `docs/ecoa_reg_b_mapping.md`, `docs/fcra_reg_v_mapping.md`, `docs/cfpb_circular_2022_03_mapping.md`.

### 2.7 Human-AI Configuration

**Definition (summarized).** Risks from how humans and AI systems are configured to interact — over-reliance, under-reliance, role-ambiguity, automation surprise.

**Framework modules.** `autonomy_ladder`, `sovereign_veto`, `defcon`, `shadow_mode`, `audit_chain`.

**Govern.** `autonomy_ladder` A0→A4 progression defines the explicit configuration; `model_inventory` records the current autonomy level per workload.
**Map.** Workload classification — the higher the autonomy level, the higher the human-AI-configuration risk surface.
**Measure.** `shadow_mode` promotion criteria require operator-effectiveness measurement; `audit_chain` records every operator-override event.
**Manage.** `sovereign_veto` for emergency human-override; `defcon` for graceful autonomy-degradation when human-AI-configuration trust degrades.

**Gap.** This is the framework's primary native risk surface; the v1.0 patterns are designed at this exact shape. No gap.

### 2.8 Information Integrity

**Definition (summarized).** Generative-AI undermining the integrity of public discourse via deepfakes, synthetic-content manipulation, or coordinated inauthentic behaviour.

**Framework modules.** `witness_anchor`, `audit_chain`, `ledger_store_worm`, `timestamp_source`.

**Govern.** Institutional policy on AI-generated content publication; `model_inventory` records workload-output classification (e.g. customer-facing communication).
**Map.** Workload classification — workloads producing public-facing content have higher exposure than internal-operations workloads.
**Measure.** `witness_anchor` + `timestamp_source` together provide cryptographic evidence of when a piece of AI-generated content was produced and that it has not been retroactively altered.
**Manage.** `sovereign_veto` for emergency takedown; `audit_chain` for forensic reconstruction.

**Gap.** No watermarking or content-provenance signing in v1.x. **Candidate for v2.0** — content-provenance signing hook integrated with `witness_anchor`.

### 2.9 Information Security

**Definition (summarized).** Generative-AI as attacker tool (phishing, malware generation, vulnerability discovery) or as attack target (prompt injection, model extraction, jailbreak).

**Framework modules.** `mi_proxy`, `sovereign_veto`, `defcon`, `audit_chain`, `vendor_score_gate`, `ledger_store_worm`, adversarial-agent threat model (ADR-0018).

**Govern.** `model_inventory` records the workload's threat-model classification; `vendor_score_gate` records upstream security posture.
**Map.** Workload classification — internet-exposed workloads have higher exposure than internal workloads.
**Measure.** `mi_proxy` verifier-integrity attestation; `audit_chain` per-decision evidence; `witness_anchor` cross-verification.
**Manage.** `sovereign_veto` for emergency degradation; `defcon` for graceful resilience response; `ledger_store_worm` for forensic retention.

**Gap.** No runtime prompt-injection or jailbreak detector in v1.x. **Candidate for v2.0** — runtime adversarial-input detection layer per ADR-0018. Cross-references: `docs/glba_safeguards_mapping.md`.

### 2.10 Intellectual Property

**Definition (summarized).** Generative-AI reproduction of copyrighted material, trademark infringement, or trade-secret leakage in outputs.

**Framework modules.** `model_inventory`, `vendor_score_gate`, `audit_chain`.

**Govern.** `model_inventory` records the workload's IP posture; `vendor_score_gate` records upstream provider IP-indemnification posture.
**Map.** Workload classification — content-generation workloads have higher IP exposure than decisioning workloads.
**Measure.** `audit_chain` retention of outputs for post-hoc IP-claim defence.
**Manage.** Out of scope for the framework's runtime control surface; institution-specific IP-defence workflow.

**Gap.** No content-similarity or IP-detection in v1.x. Out of scope by design — substantively a product-layer or legal-review concern.

### 2.11 Obscene, Degrading, and/or Abusive Content

**Definition (summarized).** Generative-AI production of obscene, degrading, or abusive content, including CSAM.

**Framework modules.** `vendor_score_gate`, `sovereign_veto`, `defcon`, `audit_chain`.

**Govern.** Institutional content-policy referenced in `model_inventory`; `vendor_score_gate` records upstream safety-filter posture.
**Map.** Workload exposure — customer-facing surfaces have higher exposure.
**Measure.** Institution-specific content classifier supplies the runtime signal; `audit_chain` retains flagged outputs.
**Manage.** `sovereign_veto` for emergency takedown; `defcon` for systemic response.

**Gap.** No runtime content classifier in the framework. Out of scope by design — content-moderation is a substantive product layer.

### 2.12 Value Chain and Component Integration

**Definition (summarized).** Risks from integrating third-party components — pre-trained models, fine-tuning datasets, embedding stores, retrieval pipelines — into the overall AI system.

**Framework modules.** `vendor_score_gate`, `mi_proxy`, `model_inventory`, `witness_anchor`, adversarial-agent threat model (ADR-0018).

**Govern.** `vendor_score_gate` records per-vendor governance evidence; `model_inventory` records every third-party component in the workload's value chain.
**Map.** Workload supply-chain map — pre-trained model lineage, fine-tuning corpus provenance, embedding-store provider, retrieval pipeline.
**Measure.** `mi_proxy` verifier-integrity attestation across the supply chain; `witness_anchor` cross-verification of component versions in use.
**Manage.** `sovereign_veto` for supply-chain compromise incident; `vendor_score_gate` for ongoing-monitoring of vendor posture changes.

**Gap.** No SBOM-style AI-bill-of-materials in v1.x. **Candidate for v2.0** — AIBOM schema integrated with `model_inventory` and `vendor_score_gate`. Cross-references: interagency TPRM final guidance (June 6, 2023).

---

## 3. Govern / Map / Measure / Manage — module assignment summary

The cross-walk in section 2 distributes the framework's modules across the AI RMF's four functions. The summary table:

| Function | Primary modules | Secondary modules |
|---|---|---|
| **Govern** | `model_inventory`, `vendor_score_gate` | `autonomy_ladder` (policy surface) |
| **Map** | `autonomy_ladder`, `model_inventory` | `vendor_score_gate` |
| **Measure** | `audit_chain`, `shadow_mode`, `mi_proxy`, `equity_audit`, `witness_anchor`, `timestamp_source` | `defcon` (state observability) |
| **Manage** | `sovereign_veto`, `defcon`, `adverse_action_gate`, `ledger_store_worm`, `sar_workflow_audit` | `audit_chain` (forensic), `best_interest_check` |

The framework's evidence stack (`audit_chain` + `witness_anchor` + `timestamp_source` + `ledger_store_worm`) crosses the Measure / Manage boundary; it is the common substrate every other module's evidence flows through.

---

## 4. Gap summary

Categories where v1.x has **no gap**:

- 2.7 Human-AI Configuration (native design surface)

Categories with **deferred-module gaps** (candidates for v2.0):

- 2.2 Confabulation — confabulation-flag hook in `audit_event`
- 2.6 Harmful Bias and Homogenization — `protected_class_proxy_detector` full implementation
- 2.8 Information Integrity — content-provenance signing
- 2.9 Information Security — runtime adversarial-input detection layer
- 2.12 Value Chain and Component Integration — AIBOM schema

Categories that are **out of scope by design**:

- 2.1 CBRN
- 2.3 Dangerous, Violent, or Hateful Content (runtime classifier)
- 2.5 Environmental Impacts
- 2.10 Intellectual Property (similarity / IP detection)
- 2.11 Obscene, Degrading, and/or Abusive Content (runtime classifier)

Categories where v1.x **covers operationally but defers substantive law** to companion regimes:

- 2.4 Data Privacy (GLBA Safeguards — `docs/glba_safeguards_mapping.md`)
- 2.6 Harmful Bias and Homogenization (ECOA / Reg B, FCRA / Reg V, CFPB Circular 2022-03)
- 2.9 Information Security (GLBA Safeguards)

---

## 5. Operational use

A second-line MRM function uses this mapping in two operational contexts:

1. **Pre-deployment GenAI workload review.** For any workload incorporating a generative-AI model, walk each of the 12 categories in Section 2 and confirm: (a) which categories apply at non-trivial exposure, (b) which modules are wired and emitting evidence, (c) which gaps require compensating controls.
2. **Audit-committee / examiner walkthrough.** Present the Govern / Map / Measure / Manage summary table (Section 3) as the bridge between the AI RMF vocabulary and the institution's technical controls.

---

## 6. References

- NIST. _NIST AI 600-1: AI Risk Management Framework — Generative AI Profile._ July 26, 2024 (finalized; draft April 29, 2024). <https://airc.nist.gov/airmf-resources/ai-rmf-generative-ai-profile/>. PDF: <https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf>. **(Verified via WebFetch 2026-05-28; title, publication date, NIST publisher, and AI RMF companion status confirmed. The 12-category list and per-category summaries are drawn from the published profile and corroborating sources; full per-category action-matrix detail should be read against the source PDF for production use.)**
- NIST. _NIST AI 100-1: Artificial Intelligence Risk Management Framework 1.0._ January 26, 2023. <https://www.nist.gov/itl/ai-risk-management-framework>.
- Office of the Comptroller of the Currency. _OCC Bulletin 2026-13: Model Risk Management — Revised Guidance._ April 17, 2026. (Primary-source verified; see `docs/interagency_mrm_2026_overlay.md`.)
- Cyber Risk Institute. _Financial Services AI Risk Management Framework._ February 12, 2026. (See `docs/treasury_fs_ai_rmf_mapping.md`.)
- `finserv-agent-audit` v1.x — `docs/interagency_mrm_2026_overlay.md`, `docs/treasury_fs_ai_rmf_mapping.md`, `docs/nist_ai_rmf_mapping.md`, per-regime mapping documents under `docs/`.
