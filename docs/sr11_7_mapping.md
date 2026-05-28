# SR 11-7 — Control Mapping for Autonomous AI Agents

> **STATUS — SUPERSEDED FOR NEW EXAMINATIONS.** Federal Reserve SR 11-7 was
> superseded for new examination cycles by the joint OCC / Federal Reserve Board /
> FDIC issuance of April 17, 2026 (OCC counterpart: **OCC Bulletin 2026-13,
> _Model Risk Management: Revised Guidance_**), which **explicitly excludes
> generative and agentic AI from scope** and defers those workloads to a
> forthcoming joint RFI. For the framework's positioning during the pre-RFI
> interval, see **[`docs/interagency_mrm_2026_overlay.md`](interagency_mrm_2026_overlay.md)**.
> This document is retained as conceptual ancestry and for institutions still
> operating under the 2011 citation lineage in respect of in-flight validations
> or non-agentic-AI statistical models that pre-date the 2026 issuance.

Federal Reserve **SR 11-7, _Supervisory Guidance on Model Risk Management_** (April 4,
2011; **superseded for new examinations by the April 17, 2026 joint issuance —
see OCC Bulletin 2026-13 and `docs/interagency_mrm_2026_overlay.md`**), issued
jointly with OCC Bulletin 2011-12 (also rescinded April 17, 2026) and later
adopted by the FDIC via FIL-22-2017, was the foundational US prudential standard
for model governance at banking organizations through April 16, 2026. An autonomous AI agent that makes or materially influences
a regulated decision — credit, trading, AML triage, suitability, valuation — is a
**model** under the SR 11-7 definition ("a quantitative method, system, or
approach that applies statistical, economic, financial, or mathematical theories,
techniques, and assumptions to process input data into quantitative estimates").
That brings every such agent inside the four expectations of the guidance:
**(1) sound development, implementation, and use; (2) effective validation;
(3) governance, policies, and controls; (4) the discipline of effective
challenge.** This document maps each pattern in the repository to the SR 11-7
section that supervisory examiners will read it against.

> **Disclaimer:** This mapping is provided for reference only and does not
> constitute legal or supervisory advice. Engage qualified counsel and your
> primary federal regulator for any specific MRM determination.

---

## Control Mapping Table — Three Lines of Defense

SR 11-7 does not name "three lines of defense" by that label, but the governance
section assigns the same role separation: the **first line** owns model
development and use; the **second line** owns independent validation and risk
oversight; the **third line** (internal audit) assesses the framework itself.
The patterns map as follows.

| SR 11-7 Section | Requirement | Line | Pattern in This Repo | File |
|---|---|---|---|---|
| III. Overview of Model Risk Management | Model definition and risk identification | 1L | `model_inventory` — enumerates every agent decision class as a model | `patterns/model_inventory.py` |
| IV. Model Development, Implementation, and Use | Documented development with stated purpose and limitations | 1L | `autonomy_ladder` — published A0→A4 classification per decision type | `docs/autonomy_ladder.md` |
| IV. Model Development, Implementation, and Use | Controlled implementation, code controls, change management | 1L | `audit_chain` — every decision, input, version, and code hash recorded | `schemas/audit_event.py` |
| IV. Model Development, Implementation, and Use | Use monitoring; override tracking; reporting to decision-makers | 1L | `defcon` state machine — continuous run-time risk state with hysteresis | `examples/defcon_state_machine.py` |
| V. Model Validation — Conceptual Soundness | Review of design, theory, assumptions, developmental evidence | 2L | `shadow_mode` — parallel non-binding evaluation against the production decision | `patterns/shadow_mode.py` |
| V. Model Validation — Ongoing Monitoring | Process verification, benchmarking, performance metrics | 2L | `mi_proxy` — model-integrity proxy signals fed into DEFCON | `patterns/mi_proxy.py` |
| V. Model Validation — Outcomes Analysis | Back-testing, sensitivity analysis, error attribution | 2L | `audit_chain` decision logs replayed against realized outcomes | `schemas/audit_event.py` |
| V. Model Validation — Effective Challenge | Critical analysis by objective, informed parties with influence | 2L | `sovereign_veto` — second-line block with documented human clearance | `patterns/sovereign_veto.py` |
| VI. Governance, Policies, and Controls — Board and Senior Management | Establish framework; set risk appetite | Board | `autonomy_ladder` — board-approved A-band ceiling per decision class | `docs/autonomy_ladder.md` |
| VI. Governance, Policies, and Controls — Policies | Written MRM policy, model inventory, tiering | 1L/2L | `model_inventory` plus `autonomy_ladder` tiering table | `patterns/model_inventory.py` |
| VI. Governance, Policies, and Controls — Internal Audit | Independent assessment of the MRM framework | 3L | `audit_chain` + `witness_anchor` — tamper-evident evidence trail (hash-chain mechanism with external witness) for audit walk-through | `patterns/witness_anchor.py` |
| VI. Governance, Policies, and Controls — External Resources | Vendor model risk same standard as internal | 1L/2L | `vendor_score_gate` — pre-deployment gate for third-party models | `patterns/vendor_score_gate.py` |
| Footnote — Record-keeping for examiner inspection | Validation evidence retained and retrievable | 3L | `ledger_store` (WORM-eligible) plus `timestamp_source` (RFC 3161) | `patterns/ledger_store.py`, `patterns/timestamp_source.py` |

---

## Model Lifecycle Walkthrough

SR 11-7 organizes expectations across the lifecycle. The pattern stack covers
each stage as follows.

### 1. Development

- **Stated purpose, intended use, and limitations.** `autonomy_ladder` publishes
  the A-band, the decision class, and the human-clearance requirement before any
  agent runs in production. A0 (advisory) and A4 (sovereign-only) are
  intentionally far apart so use-creep is detectable.
- **Documentation and conceptual soundness evidence.** Every decision the agent
  emits writes an `AuditEvent` carrying input hash, model version, prompt /
  policy version, rationale string, and downstream effect — supplying the
  development-record artifacts an examiner will request.

### 2. Implementation

- **Code controls and change management.** `audit_chain` records the code hash
  and configuration hash for every decision so a production drift is detectable
  by replay. Version bumps trigger a fresh `model_inventory` entry.
- **Pre-production gates for vendor or pre-trained components.** `vendor_score_gate`
  blocks promotion of any third-party model or foundation-model-backed agent that
  lacks documentation, license attestation, and red-team evidence.

### 3. Use

- **Run-time monitoring.** `defcon` evaluates aggregate model-integrity signals
  on every decision and degrades autonomy (A4 → A2 → A1 → A0) when thresholds
  trip. Hysteresis prevents oscillation under adversarial inputs.
- **Override tracking.** `sovereign_veto` events are first-class `AuditEvent`
  records with the human approver identity, the rationale, and the timestamp
  anchored by `timestamp_source`.

### 4. Validation

- **Independent re-execution.** `shadow_mode` runs the candidate version against
  live inputs without binding effect; deltas are streamed to validators.
- **Ongoing performance signals.** `mi_proxy` exposes calibration drift,
  population stability, and outcome agreement as observable metrics.
- **Tamper-evident validation evidence (hash-chain mechanism).**
  `witness_anchor` anchors validation result hashes to an external
  witness (e.g., RFC 3161 TSA, blockchain anchor) so the validation
  record cannot be silently rewritten.

### 5. Retirement

- **Controlled decommissioning.** The `model_inventory` lifecycle field flips
  to `retired`; the final `audit_chain` entry references the migration plan and
  the `ledger_store` retention window per supervisory record-keeping
  expectations.

---

## Effective Challenge — Architectural Translation

SR 11-7 names three preconditions for effective challenge: **competence,
incentives, influence.** The pattern stack converts each into a system
guarantee:

| Precondition | Architectural translation |
|---|---|
| Competence | `shadow_mode` and `mi_proxy` give validators the same telemetry the developers see — no information asymmetry. |
| Incentives | `vendor_score_gate` and `sovereign_veto` are owned outside the model-developer reporting line; their decisions write to the same `audit_chain` developers cannot rewrite. |
| Influence | `defcon` autonomy degradations and `sovereign_veto` blocks take effect immediately and cannot be silently overridden — the production path checks the gate on every call. |

---

## Gap Analysis — What This Repo Does NOT Cover

These patterns close the technical control surface. The following SR 11-7
expectations require organizational, contractual, or program-level work outside
the repository.

| SR 11-7 Expectation | Gap | Guidance |
|---|---|---|
| Board-approved MRM policy | Document outside code | Adopt a written MRM policy that names this pattern stack as the technical evidence layer. |
| Model risk tiering (high / medium / low) | Conceptual, per-bank | Tie tiering to `autonomy_ladder` A-bands and decision-class blast radius. |
| Validation independence (organizational) | Reporting-line design | Validators must report into the second line of defense, not the model developer's chain. |
| Vendor MRM contractual rights | Procurement workflow | Vendor contracts must grant inspection rights matching `vendor_score_gate` evidence requirements. |
| Annual MRM report to the board | Reporting cadence | Aggregate `audit_chain`, `defcon` transition counts, and `sovereign_veto` activations into a quarterly board pack. |
| Capital model governance under CCAR / DFAST | Separate supervisory regime | SR 15-18 and the stress-testing rule layer on top — not covered here. |
| BSA / AML model exception | SR 21-8 grants conditional relief | The interagency BSA/AML statement (April 9, 2021) sets a different validation cadence; see SR 21-8. |

---

## References

- Board of Governors of the Federal Reserve System. _Supervisory Letter SR 11-7:
  Guidance on Model Risk Management._ April 4, 2011.
  <https://www.federalreserve.gov/supervisionreg/srletters/sr1107.htm>
  (verified via mirror at <https://www.federalreserve.gov/boarddocs/srletters/2011/sr1107.htm>;
  retrieved 2026-05-28).
- Federal Reserve. _Supervisory Guidance on Model Risk Management — FRRS entry._
  <https://www.federalreserve.gov/frrs/guidance/supervisory-guidance-on-model-risk-management.htm>
  (retrieved 2026-05-28).
- FDIC. _Financial Institution Letter FIL-22-2017: Adoption of Supervisory
  Guidance on Model Risk Management._ June 7, 2017.
  <https://www.fdic.gov/news/financial-institution-letters/2017/fil17022.html>
  (retrieved 2026-05-28).
- Federal Reserve. _SR 21-8: Interagency Statement on Model Risk Management for
  Bank Systems Supporting Bank Secrecy Act/Anti-Money Laundering Compliance._
  April 9, 2021.
  <https://www.federalreserve.gov/supervisionreg/srletters/SR2108.htm>
  (retrieved 2026-05-28).
- Federal Reserve. _SR 26-2: Revised Guidance on Model Risk Management._
  April 17, 2026 (supersedes SR 11-7; this mapping reflects the legacy SR 11-7
  control set, which remains examiner-relevant for historical examination
  cycles).
  <https://www.federalreserve.gov/supervisionreg/srletters/SR2602.htm>
  (retrieved 2026-05-28).
