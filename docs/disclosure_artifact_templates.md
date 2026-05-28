# Disclosure Artifact Templates — AI Governance

Three reusable text-block templates that disclosure counsel can defend
because each clause is anchored to a deployed v1.1-v1.3 module in this
repository. The templates cover the three filings where AI-governance
disclosure has become standard practice:

1. **10-K Item 1A AI risk factor** — annual report risk-factor language.
2. **Proxy statement AI-governance disclosure** — Audit or Risk
   Committee section of the annual proxy.
3. **Earnings-release management-commentary AI paragraph** — quarterly
   earnings release.

Disclosure of AI risk in 10-Ks rose roughly **700% between 2022 and
2024**; approximately **33% of FY25 filings** flag AI as a standalone
risk factor; the SEC AI task force is active. Counsel needs templates
that say something substantive and defensible — not boilerplate, not
overstatement, and not unanchored.

Each template names the specific repository modules whose presence in
the bank's deployed governance stack justifies each clause. The result
is a disclosure with an evidentiary back-chain rather than a marketing
paragraph.

> **Disclaimer:** Reference pattern, not legal advice. Disclosure
> counsel must adapt each template to the institution's specific
> facts and engagement structure. See repo-root
> [`DISCLAIMER.md`](../DISCLAIMER.md).

---

## Template Discipline

Three rules govern every template here:

1. **No unanchored claim.** Every substantive sentence has a footnote
   pointing at the v1.1-v1.3 module that anchors it. If the bank
   has not deployed the module, the sentence must be cut or downgraded.
2. **No banned claim.** Cross-reference [`NEGATIVE-USE-CASES.md`](../NEGATIVE-USE-CASES.md)
   for the list of claims this framework explicitly does not support.
   In particular: never claim "tamper-proof"; the hash-chain mechanism
   is detection within the trust boundary, not prevention.
3. **No marketing voice.** Disclosure prose is sober, specific, and
   includes the residual-risk paragraph. Disclosure that reads as
   marketing invites securities-fraud exposure.

---

## Template 1 — 10-K Item 1A AI Risk Factor

> **Use:** annual report Item 1A risk-factor section.
> **Length:** ~350-500 words.
> **Anchor modules:** `model_inventory`, `audit_chain`, `autonomy_ladder`,
> `equity_audit`, `vendor_score_gate`, `defcon`, `sovereign_veto`,
> `adverse_action_gate`, `protected_class_proxy_detector`,
> `shadow_mode`.

---

**Risks related to our use of artificial intelligence and autonomous
agents.**

We deploy artificial-intelligence systems, including autonomous
software agents, across multiple functions of our business, including
credit decisioning, suitability review, customer service, fraud
detection, model risk management, and operational support. Our use of
these systems exposes us to a set of risks that are evolving and that
the regulatory and supervisory environment is actively addressing.

**Regulatory landscape.** Our AI systems operate within a regulatory
landscape that includes the federal banking agencies' April 17, 2026
revised model-risk-management guidance (OCC Bulletin 2026-13 and
Federal Reserve SR 26-2), the Federal Reserve's predecessor SR 11-7
guidance, the Consumer Financial Protection Bureau's adverse-action
circulars (Circular 2022-03 and Circular 2023-03), the European Union
AI Act, the New York State Department of Financial Services 23 NYCRR
Part 500 and its October 16, 2024 and May 21, 2026 AI-specific industry
letters, the Colorado SB 189 high-risk AI regime (effective January 1,
2027), the California SB 53 Transparency in Frontier AI Act (effective
January 1, 2026), and the Texas HB 149 Responsible AI Governance Act
(effective January 1, 2026). State attorneys general are increasingly
active enforcers, including the Massachusetts Attorney General's July
10, 2025 settlement with an online student-loan lender for AI-driven
disparate-impact discrimination.

**Specific categories of risk.** We are exposed to risks of model error
or drift; opacity that limits our ability to fully explain individual
decisions; training-data bias that may produce disparate impact on
protected classes; hallucinated or fabricated outputs from generative
models; third-party dependencies on foundation-model providers and
other vendors whose practices we do not fully control; and adversarial
inputs designed to manipulate model behaviour or extract non-public
personal information. Cyber-threat actors are themselves increasingly
deploying AI to identify and exploit vulnerabilities, as flagged by
the May 21, 2026 NYDFS frontier-AI industry letter.

**Our governance framework.** We maintain a documented AI-governance
framework consisting of a published autonomy classification per
decision class, a documented model inventory, a hash-chain decision
ledger (a detection mechanism within our trust boundary, not a
prevention control), per-decision rationale capture for adverse-action
surfaces, population-level fairness auditing, third-party-model
diligence gating, shadow-mode evaluation of candidate model versions,
run-time degradation under defined drift thresholds, and documented
human-override authority. Our framework is described in our public
governance disclosures.

**Residual risk.** Notwithstanding our framework, we cannot eliminate
the risks described above. A material AI-driven failure or
discrimination finding could result in regulatory action, civil
litigation, customer remediation, reputational harm, and remediation
costs that could be material to our results of operations or financial
condition. Our governance framework reduces but does not eliminate
these risks.

---

**Drafting notes for disclosure counsel.**

- The "governance framework" paragraph is the load-bearing paragraph.
  Each clause is anchored to a specific repository module:
  *published autonomy classification* → `docs/autonomy_ladder.md`;
  *documented model inventory* → `src/finserv_agent_audit/governance/model_inventory.py`;
  *hash-chain decision ledger* → `src/finserv_agent_audit/governance/audit_chain.py`;
  *per-decision rationale capture for adverse-action surfaces* →
  `src/finserv_agent_audit/governance/adverse_action_gate.py` +
  `patterns/explainability_stub.py`;
  *population-level fairness auditing* →
  `src/finserv_agent_audit/governance/equity_audit.py` +
  `src/finserv_agent_audit/governance/protected_class_proxy_detector.py`;
  *third-party-model diligence gating* →
  `src/finserv_agent_audit/governance/vendor_score_gate.py`;
  *shadow-mode evaluation* →
  `src/finserv_agent_audit/governance/shadow_mode.py`;
  *run-time degradation under defined drift thresholds* →
  `src/finserv_agent_audit/governance/defcon.py` +
  `src/finserv_agent_audit/governance/mi_proxy.py`;
  *documented human-override authority* →
  `src/finserv_agent_audit/governance/sovereign_veto.py`.
  If a module is not deployed, the corresponding clause must be cut.
- The hash-chain phrasing is deliberately hedged ("detection mechanism
  within our trust boundary, not a prevention control") to comply with
  [`NEGATIVE-USE-CASES.md`](../NEGATIVE-USE-CASES.md) discipline that
  bans "tamper-proof" claims. Counsel should preserve this hedge.
- The "residual risk" paragraph is required. Removing it converts the
  rest of the disclosure into a guarantee — a securities-fraud
  exposure.
- The regulatory-landscape paragraph names primary sources. Counsel
  should keep this list current at each annual filing.
- Avoid marketing buzzwords per the framework voice register (see
  `scripts/banned_term_lint.py` for the banned-term list).

---

## Template 2 — Proxy AI-Governance Disclosure for Audit / Risk Committee Chair

> **Use:** proxy statement, Audit Committee or Risk Committee
> description section, or a standalone AI-governance section if the
> board has chartered one.
> **Length:** ~200-300 words.
> **Anchor modules:** `autonomy_ladder`, `audit_chain`,
> `model_inventory`, `defcon`, `vendor_score_gate`, `sovereign_veto`.

---

**Board oversight of artificial intelligence.**

The [Audit / Risk] Committee has been charged with oversight of the
Company's use of artificial intelligence and autonomous software
agents in our business. The Committee receives a quarterly report
covering the Company's model inventory, the autonomy classification
applied to each material decision class, the volume and disposition
of decisions made or materially influenced by AI systems, the volume
of human-override events, and any AI-related incidents that were
material under the Company's incident-response framework.

The Company maintains an autonomy-classification scheme that assigns
each material AI-driven decision class to one of five autonomy bands,
from advisory-only to fully autonomous within defined limits. The
Committee approves the highest autonomy band the Company may operate
in for each decision class and reviews the classification annually.
The Company's third-party AI vendors and foundation-model providers
are subject to a documented pre-deployment evidence gate that the
Committee reviews on a quarterly basis.

The Company's AI decision pipeline produces a hash-chain decision
ledger that records inputs, model outputs, decision rationales, and
human-override events. The ledger provides detection of modification
within our trust boundary and supports both internal audit walk-
throughs and supervisory examination. The Committee receives summary
reports of ledger integrity verifications conducted by the Company's
internal audit function.

The Committee operates with the assistance of management's Chief Risk
Officer, Chief Information Security Officer, and General Counsel, who
attend Committee meetings on AI-governance matters.

---

**Drafting notes for disclosure counsel.**

- "Autonomy-classification scheme" → `docs/autonomy_ladder.md` (A0→A4).
- "Quarterly report ... model inventory" → `src/finserv_agent_audit/governance/model_inventory.py`.
- "Volume of human-override events" → `src/finserv_agent_audit/governance/sovereign_veto.py`
  event aggregation.
- "Pre-deployment evidence gate" →
  `src/finserv_agent_audit/governance/vendor_score_gate.py`.
- "Hash-chain decision ledger ... detection of modification within
  our trust boundary" → `src/finserv_agent_audit/governance/audit_chain.py`.
  This is again the load-bearing tamper-language hedge per
  [`NEGATIVE-USE-CASES.md`](../NEGATIVE-USE-CASES.md).
- The "Committee approves the highest autonomy band" sentence is the
  board-oversight artifact that NYDFS § 500.4(d) examiners will read.
  This sentence should not be deployed unless the board has actually
  voted on per-class A-band ceilings.
- If the Committee charter language has been amended to include AI
  oversight, attach the amended charter as an exhibit.

---

## Template 3 — Management-Commentary AI Paragraph for Earnings Releases

> **Use:** quarterly earnings release; can be lifted into the
> earnings-call prepared remarks.
> **Length:** ~120-180 words.
> **Anchor modules:** `model_inventory`, `autonomy_ladder`,
> `audit_chain`, `defcon`.

---

**Artificial intelligence.**

During the quarter, the Company continued the deployment of
artificial-intelligence systems across [credit decisioning] /
[suitability review] / [fraud detection] / [operational support]
functions. The Company's deployment is governed by the published
autonomy-classification framework that the [Audit / Risk] Committee
approved on [date]. The Company's model inventory at quarter end
included [number] AI decision systems in production, of which
[number] operate at the [A1] band requiring human review prior to
binding effect.

[Material AI initiative: e.g., "During the quarter the Company
deployed a generative-AI assistant in its [function] operations under
an A0 (advisory-only) classification."]

[Material AI incident: e.g., "On [date] the Company identified [a
discriminatory output / a model-drift event / a vendor-driven
rationale-distribution shift] in its [decision class] pipeline. The
Company [completed remediation / filed required regulator
notifications / re-validated the model] and the matter [is / is not]
expected to have a material impact on the Company's results of
operations or financial condition."]

The Company's AI governance framework is described in its most recent
annual report on Form 10-K.

---

**Drafting notes for disclosure counsel.**

- The model-inventory count and A-band distribution should be sourced
  directly from `src/finserv_agent_audit/governance/model_inventory.py`
  as of quarter-end; do not estimate.
- The "material AI initiative" sentence is optional; include only when
  there is an actually-material deployment to disclose.
- The "material AI incident" sentence is required only if there has
  been a material incident; consult the
  [`docs/ai_incident_retrospective_template.md`](ai_incident_retrospective_template.md)
  materiality determination. Counsel must make the Item 1.05
  / 8-K determination separately; this paragraph cannot substitute for
  the 8-K analysis.
- The cross-reference to the most recent 10-K is the integration
  anchor; the 10-K Item 1A risk factor (Template 1) carries the
  governance-framework description that this earnings paragraph
  references.
- Avoid claims of competitive advantage from AI deployment in the
  earnings-release paragraph; that framing is permissible in the MD&A
  but creates securities-fraud exposure when embedded in the headline
  release.

---

## Cross-References to Repository Surfaces

| Disclosure clause | Anchor module(s) | Negative-use-case discipline |
|---|---|---|
| "Published autonomy classification per decision class" | `docs/autonomy_ladder.md` | Do not claim A-bands the board has not approved |
| "Documented model inventory" | `src/finserv_agent_audit/governance/model_inventory.py` | Do not claim coverage of models not actually enumerated |
| "Hash-chain decision ledger (detection within trust boundary, not prevention)" | `src/finserv_agent_audit/governance/audit_chain.py` | Never claim "tamper-proof"; the hedge is required |
| "Per-decision rationale capture for adverse-action surfaces" | `src/finserv_agent_audit/governance/adverse_action_gate.py`, `patterns/explainability_stub.py` | Do not claim Circular 2022-03 / 2023-03 compliance without the gate deployed |
| "Population-level fairness auditing" | `src/finserv_agent_audit/governance/equity_audit.py`, `src/finserv_agent_audit/governance/protected_class_proxy_detector.py` | Do not claim disparate-impact testing without periodic execution and preservation |
| "Third-party-model diligence gating" | `src/finserv_agent_audit/governance/vendor_score_gate.py` | Do not claim TPSP coverage without the gate enforced pre-deployment |
| "Shadow-mode evaluation" | `src/finserv_agent_audit/governance/shadow_mode.py` | Do not claim shadow-mode coverage without the parallel-execution path |
| "Run-time degradation under drift thresholds" | `src/finserv_agent_audit/governance/defcon.py`, `src/finserv_agent_audit/governance/mi_proxy.py` | Do not claim automatic degradation without published thresholds |
| "Human-override authority" | `src/finserv_agent_audit/governance/sovereign_veto.py` | Do not claim human-in-the-loop where the override is theoretical |
| "External-witness anchoring for evidence preservation" | `src/finserv_agent_audit/governance/witness_anchor.py`, `src/finserv_agent_audit/governance/timestamp_source.py` | Do not claim external anchoring without an operational anchor schedule |

---

## References

- Securities Exchange Act of 1934, Form 10-K Item 1A (risk factors)
  and Item 1.05 (material cybersecurity incidents).
- SEC release on the Item 1.05 cybersecurity-disclosure rule
  (effective December 18, 2023).
- 23 NYCRR Part 500 § 500.4(d) — senior governing body oversight.
- Repository governance discipline:
  [`NEGATIVE-USE-CASES.md`](../NEGATIVE-USE-CASES.md),
  [`FAILURE-MODES.md`](../FAILURE-MODES.md),
  [`DISCLAIMER.md`](../DISCLAIMER.md),
  [`LIMITATIONS.md`](../LIMITATIONS.md).
- Patterns in this repo:
  `src/finserv_agent_audit/governance/audit_chain.py`,
  `src/finserv_agent_audit/governance/model_inventory.py`,
  `src/finserv_agent_audit/governance/adverse_action_gate.py`,
  `src/finserv_agent_audit/governance/equity_audit.py`,
  `src/finserv_agent_audit/governance/protected_class_proxy_detector.py`,
  `src/finserv_agent_audit/governance/vendor_score_gate.py`,
  `src/finserv_agent_audit/governance/shadow_mode.py`,
  `src/finserv_agent_audit/governance/defcon.py`,
  `src/finserv_agent_audit/governance/mi_proxy.py`,
  `src/finserv_agent_audit/governance/sovereign_veto.py`,
  `src/finserv_agent_audit/governance/witness_anchor.py`,
  `src/finserv_agent_audit/governance/timestamp_source.py`,
  `docs/autonomy_ladder.md`.
- Related mappings:
  [`docs/nydfs_part500_ai_mapping.md`](nydfs_part500_ai_mapping.md),
  [`docs/cfpb_ai_lending_supervisory_landscape.md`](cfpb_ai_lending_supervisory_landscape.md),
  [`docs/state_ag_ai_fair_lending_matrix.md`](state_ag_ai_fair_lending_matrix.md),
  [`docs/ai_incident_retrospective_template.md`](ai_incident_retrospective_template.md),
  [`docs/sr11_7_mapping.md`](sr11_7_mapping.md),
  [`docs/interagency_mrm_2026_overlay.md`](interagency_mrm_2026_overlay.md).
