# NYDFS 23 NYCRR Part 500 — AI Control Mapping for Autonomous Agents

This document maps the governance patterns in this repository to the New York
State Department of Financial Services (NYDFS) cybersecurity regulation,
**23 NYCRR Part 500**, as amplified by two AI-specific industry letters:
the **October 16, 2024 letter** on cybersecurity risks arising from
artificial intelligence, and the **May 21, 2026 letter** on heightened
cybersecurity risks associated with frontier AI models.

NYDFS is the most aggressive US state financial-services regulator on AI
cybersecurity. Part 500 is the only state-level cybersecurity rule with
direct examination authority over banks, insurers, money transmitters,
mortgage bankers, and virtual-currency businesses operating in New York —
and the two industry letters bring autonomous AI agents squarely inside
the existing Part 500 examination program rather than waiting on a new
rule.

> **Disclaimer:** Reference pattern, not legal advice. Regulatory
> characterizations are summaries; engage qualified counsel for your
> specific compliance determination. See repo-root
> [`DISCLAIMER.md`](../DISCLAIMER.md).

---

## Framework Overview

23 NYCRR Part 500 was adopted in 2017 and amended November 1, 2023 (the
"Second Amendment") with a phased compliance schedule running through
November 2025. The Second Amendment introduced a senior-governing-body
oversight standard (§ 500.4(d)), expanded multi-factor-authentication
expectations (§ 500.12), required tightened third-party-service-provider
controls (§ 500.11), and obligated a written incident-response and
business-continuity program (§ 500.16) with a 72-hour cybersecurity-event
notification clock (§ 500.17(a)).

The October 16, 2024 industry letter does not create new requirements —
it tells covered entities that AI-specific risks fall inside the
existing Part 500 framework and identifies four categories of AI-driven
threat: AI-enabled social engineering (deepfakes), AI-enhanced cyber
attacks (rapid vulnerability discovery), exposure or theft of large
volumes of nonpublic personal information ("NPI") used in AI training,
and AI supply-chain vulnerabilities. The letter cites a specific case
in which a Hong Kong finance worker transferred USD 25 million after
deepfakes mimicked executives in a video call.

The May 21, 2026 letter goes further. It defines "frontier AI models"
as those that "amplify the potency, scale, and speed of identifying
vulnerabilities and exploits in information systems," and urges covered
entities to **improve security posture before broader model
availability** — language that establishes an anticipatory examination
standard. The letter directs entities to expedite vulnerability
management, secure third-party dependencies, strengthen secure
programming practices with human oversight for AI-generated code, and
enhance monitoring and threat reporting.

For autonomous AI agents operating inside a Part 500 covered entity, the
combined effect is unambiguous: the agent's NPI reads, its model
provenance, its third-party dependencies, its code-generation outputs,
and its incident posture are all in scope today.

---

## Primary-Source Citations

| Source | Retrieved | Status |
|---|---|---|
| NYDFS Industry Letter — "Cybersecurity Risks Arising from Artificial Intelligence and Strategies to Combat Related Risks" (October 16, 2024) | 2026-05-28, https://www.dfs.ny.gov/industry-guidance/industry-letters/il20241016-cyber-risks-ai-and-strategies-combat-related-risks | Verified — four risk categories, MFA / training / TPSP / data-minimization / monitoring expectations confirmed verbatim |
| NYDFS Industry Letter — "Heightened Cybersecurity Risks Associated with Frontier AI Models" (May 21, 2026) | 2026-05-28, https://www.dfs.ny.gov/industry-guidance/industry-letters/20260521-heightened-cybersecurity-risks-assoc-with-frontier-ai-models | Verified — frontier-model definition, anticipatory-posture language, secure-programming and human-oversight expectations confirmed |
| 23 NYCRR Part 500 (Second Amendment effective November 1, 2023) | Referenced; consult NYDFS published rule text for operative section language | `[UNVERIFIED — primary-source PDF not fetched this pass]` |

---

## Control Mapping Table — 23 NYCRR Part 500 (with AI letters)

| Part 500 Section | Requirement | AI-Letter Amplification | Pattern in This Repo | File |
|---|---|---|---|---|
| § 500.2 — Cybersecurity program | Maintain a documented program addressing identification, protection, detection, response, recovery | Oct 2024: program scope includes the entity's own AI use plus vendor/TPSP AI systems | `model_inventory` enumerates every AI agent and its NPI surface | `src/finserv_agent_audit/governance/model_inventory.py` |
| § 500.3 — Cybersecurity policy | Board-approved written policy | May 2026: policy must reflect frontier-AI risk awareness and anticipatory posture | `autonomy_ladder` published A0→A4 classification, board-approved ceiling per decision class | `docs/autonomy_ladder.md` |
| § 500.4(d) — Senior governing body oversight | Senior governing body must "exercise oversight" of cybersecurity risk management | Both letters: AI-risk reporting must reach the senior governing body | `audit_chain` produces a board-reportable evidence trail; DEFCON state transitions are board-visible signals | `src/finserv_agent_audit/governance/audit_chain.py`, `src/finserv_agent_audit/governance/defcon.py` |
| § 500.5(b) — Vulnerability management | Continuous monitoring for vulnerabilities | May 2026: expedited vulnerability management; human oversight for AI-generated code | `mi_proxy` model-integrity proxy signals feed DEFCON state transitions on drift / anomaly | `src/finserv_agent_audit/governance/mi_proxy.py` |
| § 500.7 — Access privileges and management | Least-privilege access; periodic review | Oct 2024: agents are first-class authorized users; their NPI reads must be gated and purpose-tagged | `adverse_action_gate` and `sovereign_veto` enforce per-decision human-clearance and second-line gating | `src/finserv_agent_audit/governance/adverse_action_gate.py`, `src/finserv_agent_audit/governance/sovereign_veto.py` |
| § 500.10(a)(2) — Cybersecurity personnel and training | Provide cybersecurity training | Oct 2024: training expanded to cover deepfakes, AI threat recognition, secure AI query drafting | Out-of-scope for code; cross-reference `docs/caio_first_90_days_playbook.md` for the program-level training agenda |  |
| § 500.11 — Third-party service provider security policy | Written TPSP policy; due diligence; contractual provisions | Oct 2024: enhanced due diligence on TPSPs using AI; breach-notification clauses; secure NPI handling in contracts | `vendor_score_gate` blocks promotion of any third-party model lacking documented evidence; `vendor-clauses/` ships contract language | `src/finserv_agent_audit/governance/vendor_score_gate.py`, `vendor-clauses/` |
| § 500.12 — Multi-factor authentication | MFA for all authorized users (deadline November 1, 2025) | Oct 2024: prefer deepfake-resistant factors (digital certificates, physical security keys) over SMS / voice / video | Out-of-scope for agent-decision code; cross-reference the entity IAM stack |  |
| § 500.13 — Asset management and data retention | Maintain a current asset inventory; minimize data; document disposal | Oct 2024: AI-system inventory; dispose of unnecessary NPI used for AI purposes | `model_inventory` lifecycle field captures `retired`; `ledger_store` retention window with WORM-eligible storage | `src/finserv_agent_audit/governance/model_inventory.py`, `src/finserv_agent_audit/governance/ledger_store.py`, `src/finserv_agent_audit/governance/ledger_store_worm.py` |
| § 500.14 — Training and monitoring | Audit logs sufficient to detect and respond | Oct 2024: monitor for unusual query behaviour in AI applications; block queries that expose NPI | `audit_chain` records every agent decision input, model output, rationale, and downstream effect; `shadow_mode` captures candidate-vs-production deltas | `src/finserv_agent_audit/governance/audit_chain.py`, `src/finserv_agent_audit/governance/shadow_mode.py` |
| § 500.16 — Incident response and business continuity | Written incident-response plan; BCP/DR plan | Both letters: AI-incident scenarios must be in the plan | `docs/ai_incident_retrospective_template.md` (v1.3) provides the post-incident learning template; sovereign-veto state is itself audited | `docs/ai_incident_retrospective_template.md` |
| § 500.17(a) — Cybersecurity event notice (72 hours) | Notify the Superintendent within 72 hours of a reportable cybersecurity event | Both letters: AI-vector events count (deepfake-driven fraud, AI-discovered exploit, NPI exposure via AI query) | `audit_chain` walk-back replay supports the materiality determination; `witness_anchor` provides external anchoring for evidence preservation | `src/finserv_agent_audit/governance/audit_chain.py`, `src/finserv_agent_audit/governance/witness_anchor.py` |
| § 500.17(b) — Annual certification of compliance | CISO certification with documented exceptions | Both letters: certification must reflect AI-specific risk treatment | `pre_examination_ai_self_assessment.md` provides the structured pre-cert walk; evidence pack assembled from `audit_chain` | `docs/pre_examination_ai_self_assessment.md` |

---

## AI-Specific Module Coverage Detail

### Detection and monitoring (§ 500.5(b), § 500.14)

NYDFS's October 2024 letter explicitly calls for monitoring of "unusual
query behaviour in AI applications" and blocking queries that expose
NPI. The repository's `audit_chain` records every agent decision —
input hash, model version, prompt / policy version, rationale string,
and downstream effect — providing the substrate against which anomaly
detection runs. `shadow_mode` provides a parallel non-binding evaluation
path so candidate model behaviour can be examined before binding effect,
matching the May 2026 expectation that entities "improve security
posture before broader model availability."

### Third-party service provider (§ 500.11)

The October 2024 letter is explicit: enhanced due diligence on TPSPs
that use AI, contractual breach-notification, and contractual
NPI-handling provisions. `vendor_score_gate` provides the pre-promotion
gate that blocks any third-party model lacking documented evidence,
license attestation, and red-team artifacts. The `vendor-clauses/`
companion ships reusable contract language for examination defensibility.

### Human oversight for AI-generated code (May 2026)

The May 2026 letter is the first NYDFS surface to explicitly require
"human oversight for AI-generated code." The Autonomy Ladder framework
(`docs/autonomy_ladder.md`) provides the published A0→A4 classification
that codifies which decision classes are eligible for autonomous code
deployment (typically A0 or A1 for production-touching code-generation
agents, never A3 or A4) and `sovereign_veto` provides the hard-stop
control.

### Incident response (§ 500.16, § 500.17(a))

The repository's `docs/ai_incident_retrospective_template.md` (v1.3)
provides a Google-SRE-style postmortem template adapted for AI-specific
failure modes (model drift, vendor change, training-data shift, prompt
change). The template includes a regulator-notification-trigger
section that explicitly evaluates Part 500 § 500.17(a) reportability
alongside SEC 8-K, OCC examination disclosure, and FFIEC IT-examination
expectations.

---

## Annual Certification Walkthrough (§ 500.17(b))

The April 15 annual certification of compliance is the operational
forcing function for the AI letters. A covered entity's CISO must
either certify materially compliant or file an acknowledgement of
non-compliance with a remediation plan. For each AI agent in production,
the certification walk should produce:

1. **Inventory entry.** `model_inventory` record with current lifecycle
   state, A-band classification, and NPI-exposure summary.
2. **Risk assessment.** Documented Part 500 § 500.2 risk-assessment
   update covering the four October 2024 risk categories.
3. **TPSP evidence.** `vendor_score_gate` artifacts for every third-party
   model dependency.
4. **Audit-chain integrity.** A current `AuditChain.verify()` result
   confirming chain integrity, plus the most recent `witness_anchor`
   external anchor.
5. **Incident posture.** Evidence that the incident-response plan
   covers AI failure modes (cross-reference
   `docs/ai_incident_retrospective_template.md`) and that any
   reportable events in the certification period were filed within
   the § 500.17(a) 72-hour window.
6. **Frontier-model posture.** May 2026 anticipatory-posture evidence:
   secure-programming controls for AI-generated code, expedited
   vulnerability management, third-party dependency review.

---

## Gap Analysis — What This Repo Does NOT Cover

| Requirement | Gap | Guidance |
|---|---|---|
| MFA implementation (§ 500.12) | Identity infrastructure, not agent code | Use the entity IAM stack; prefer deepfake-resistant factors per Oct 2024 letter |
| BCP / DR plan (§ 500.16) | Program-level, not agent code | Cross-reference enterprise BCP; AI-specific scenarios must be enumerated |
| Annual penetration testing (§ 500.5(a)(1)) | Out-of-scope for agent governance | Engage qualified offensive-security firm |
| Cybersecurity training program (§ 500.10) | Program-level, not agent code | Incorporate AI threat content per Oct 2024 letter |
| Encryption of NPI in transit and at rest (§ 500.15) | Infrastructure, not agent code | Cross-reference data-layer controls |
| April 15 certification filing (§ 500.17(b)) | Administrative filing, not agent code | Use `docs/pre_examination_ai_self_assessment.md` as the structured pre-cert walk |

---

## References

- New York State Department of Financial Services. *Industry Letter —
  Cybersecurity Risks Arising from Artificial Intelligence and Strategies
  to Combat Related Risks.* October 16, 2024.
  <https://www.dfs.ny.gov/industry-guidance/industry-letters/il20241016-cyber-risks-ai-and-strategies-combat-related-risks>
- New York State Department of Financial Services. *Industry Letter —
  Heightened Cybersecurity Risks Associated with Frontier AI Models.*
  May 21, 2026.
  <https://www.dfs.ny.gov/industry-guidance/industry-letters/20260521-heightened-cybersecurity-risks-assoc-with-frontier-ai-models>
- 23 NYCRR Part 500, *Cybersecurity Requirements for Financial Services
  Companies* (Second Amendment effective November 1, 2023).
- Patterns in this repo:
  `src/finserv_agent_audit/governance/model_inventory.py`,
  `src/finserv_agent_audit/governance/audit_chain.py`,
  `src/finserv_agent_audit/governance/defcon.py`,
  `src/finserv_agent_audit/governance/mi_proxy.py`,
  `src/finserv_agent_audit/governance/sovereign_veto.py`,
  `src/finserv_agent_audit/governance/adverse_action_gate.py`,
  `src/finserv_agent_audit/governance/vendor_score_gate.py`,
  `src/finserv_agent_audit/governance/shadow_mode.py`,
  `src/finserv_agent_audit/governance/ledger_store.py`,
  `src/finserv_agent_audit/governance/ledger_store_worm.py`,
  `src/finserv_agent_audit/governance/witness_anchor.py`,
  `docs/autonomy_ladder.md`,
  `docs/pre_examination_ai_self_assessment.md`,
  `docs/ai_incident_retrospective_template.md`,
  `vendor-clauses/`.
- Related mappings:
  [`docs/sr11_7_mapping.md`](sr11_7_mapping.md),
  [`docs/interagency_mrm_2026_overlay.md`](interagency_mrm_2026_overlay.md),
  [`docs/glba_safeguards_mapping.md`](glba_safeguards_mapping.md),
  [`docs/cfpb_ai_lending_supervisory_landscape.md`](cfpb_ai_lending_supervisory_landscape.md),
  [`docs/state_ag_ai_fair_lending_matrix.md`](state_ag_ai_fair_lending_matrix.md).
