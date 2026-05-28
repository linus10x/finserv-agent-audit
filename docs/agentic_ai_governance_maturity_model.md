# Agentic-AI Governance Maturity Model

**Status:** v1.2.0-draft · Last reviewed: 2026-05-28.
**Audience:** Chief AI Officer, Chief Risk Officer, Chief Internal Auditor, Big-4 advisory partner advising an FSI client on its agentic-AI governance trajectory.

> **Patterns are software, not legal advice.** The maturity levels below are a self-assessment scaffolding, not a regulatory rating. See repo-root [`DISCLAIMER.md`](../DISCLAIMER.md).

---

## Context

The headline industry statistics in mid-2026: **only ~21% of firms report "mature" agentic-AI governance** per Deloitte's State of AI 2026 [UNVERIFIED — verify against the most-recent Deloitte publication], and **~33% per McKinsey's 2026 enterprise AI survey** [UNVERIFIED]. Mature here means: documented, operational, auditable, board-reported. The gap is not in AI deployment volume — most large FSI firms are saturated with AI use cases. The gap is in governance maturity around those use cases.

A CMMI-style 5-level maturity model gives the CAIO a defensible self-score, a defensible plan to move levels, and a defensible reporting language for the board and the regulator. Each level is calibrated against named `finserv-agent-audit` modules, named regulator expectations, and named board-reporting indicators.

**How to score.** Run [`scripts/maturity_self_score.py`](../scripts/maturity_self_score.py) for an interactive CLI walk-through. Or self-score by reading the level descriptions below and choosing the highest level where every required evidence item is in place.

---

## Level 1 — Initial

**Description.** Governance is ad-hoc. AI is in production but not enumerated. There is no audit trail dedicated to AI activity. Decisions about model promotion, vendor selection, and incident response are made case-by-case without a written framework.

**Typical firm profile.** Pre-Chief-AI-Officer; AI is owned by individual business units; the institution discovers its own AI surface during examinations.

### Required evidence — Level 1 (de facto state)

- (none — Level 1 is the baseline)

### Regulator expectation alignment

- Below the bar of any meaningful regulator expectation. An examiner walking in will write findings.

### Board-reporting indicators

- AI activity reported as part of general technology updates; no AI-specific governance update on the board calendar.

### How to advance to Level 2

- Hire or appoint a Chief AI Officer (or equivalent named accountable executive).
- Begin the AI-inventory canvass; enumerate every known AI use.
- Deploy the SovereignVeto and a baseline AuditChain so any AI activity going forward is captured.

---

## Level 2 — Repeatable

**Description.** The institution has named an accountable executive, has begun enumerating AI use, and has deployed two foundational controls: SovereignVeto and AuditChain. The model inventory is ad-hoc — partial, possibly out-of-date, not reconciled to source-of-truth systems.

**Typical firm profile.** Day 30-Day 60 in a CAIO's first 90 days, per the [first-90-days playbook](caio_first_90_days_playbook.md).

### Required evidence — Level 2

- `finserv_agent_audit.governance.sovereign_veto.SovereignVeto` deployed
- `finserv_agent_audit.governance.audit_chain.AuditChain` deployed with at least an `InMemoryLedgerStore` or `JsonlLedgerStore` backend
- An AI inventory exists (ad-hoc form acceptable)
- A named accountable executive (CAIO or equivalent)

### Regulator expectation alignment

- Begins to meet SR 11-7 § VI baseline ("governance, policies, and controls"); model-inventory documentation gap is the most-cited finding at this level.

### Board-reporting indicators

- AI governance is a named agenda item at quarterly board meetings; the report is qualitative, not quantitative.

### How to advance to Level 3

- Reconcile the AI inventory against CI/CD, procurement spend, and model-registry systems.
- Deploy the Autonomy Ladder (A0-A4) classification across every use case.
- Document the MRM process for agentic-AI systems specifically; align to the EU AI Act mapping if any EU surface exists.

---

## Level 3 — Defined

**Description.** Foundational v1.0 governance is in production. Autonomy Ladder is the classification language. EU AI Act mapping is documented. The MRM process is written and operational. Pre-promotion gates run programmatically (not via slide deck).

**Typical firm profile.** Day 60-Day 90 in a CAIO's first 90 days; many institutions have a Level 3 posture for at least their highest-risk surfaces by Day 90.

### Required evidence — Level 3

- All Level 2 evidence
- `finserv_agent_audit.governance.autonomy_ladder.AutonomyTier` classification documented for every AI use case
- A2-to-A3 autonomy-band promotion-gate evaluation is programmatic, using `finserv_agent_audit.governance.autonomy_ladder.check_a2_to_a3_promotion`
- `finserv_agent_audit.governance.defcon.DEFCONMachine` is in the CAIO ops dashboard
- Written MRM policy with an agentic-AI section
- [`docs/eu_ai_act_mapping.md`](eu_ai_act_mapping.md) reviewed against the institution's AI surface; in-scope use cases identified

### Regulator expectation alignment

- Meets SR 11-7 + OCC 2011-12 + the April 17, 2026 interagency MRM revision agentic-AI carve-out (where issued) [UNVERIFIED — confirm exact issue date and citation].
- Meets the NIST AI RMF 1.0 "Manage" function baseline.
- Begins to meet the EU AI Act 2024/1689 Article 17 quality-management-system expectations for in-scope high-risk systems [UNVERIFIED — verify exact article and section against the AI Act final text].

### Board-reporting indicators

- Quarterly board report includes: AI inventory counts by `ImplementationStatus`, overdue-revalidation count, autonomy-band distribution, incident summary.

### How to advance to Level 4

- Deploy the four Protocol seams (LedgerStore + TimestampSource + WitnessRegister + MIProxy).
- Deploy VendorScoreGate against the institution's highest-volume vendor.
- Deploy the FSI-specific gates per vertical (AdverseActionGate for credit; SARWorkflowAudit for AML; BestInterestCheck for wealth).
- Track quantitative drift metrics on vendor scores; report quarterly to Risk Committee.

---

## Level 4 — Managed

**Description.** Quantitative governance is the operating language. The audit-chain integrity layer is hardened (the four Protocol seams). Vendor scoring is captured into the audit chain. FSI-specific gates run in every applicable vertical. Drift metrics, gate-violation rates, and verification-success rates are tracked.

**Typical firm profile.** Day 90-Day 180 in a mature CAIO function; a Level 4 posture at this point is a stretch goal, not a baseline.

### Required evidence — Level 4

- All Level 3 evidence
- `finserv_agent_audit.governance.ledger_store.LedgerStore` Protocol deployed with a substrate-appropriate backend (`SqliteLedgerStore`, `WORMLedgerStore` + S3 Object Lock COMPLIANCE)
- `finserv_agent_audit.governance.timestamp_source.RFC3161Source` deployed for high-integrity surfaces with explicit `fallback_to_local_on_failure` policy
- `finserv_agent_audit.governance.witness_anchor.anchor_to_witness` cron deployed; `RekorWitness` or `OpenTimestampsWitness` (or both) operational
- `finserv_agent_audit.governance.mi_proxy.LocalMIProxy` (minimum) wired; production verifier attestation produced on every `verify_strict()` run
- `finserv_agent_audit.governance.vendor_score_gate.InMemoryVendorScoreGate` deployed against at least one production vendor; drift detection demonstrated in production
- `finserv_agent_audit.governance.adverse_action_gate.AdverseActionGate` deployed where credit / lending applies
- `finserv_agent_audit.governance.sar_workflow_audit.SARWorkflowAudit` deployed where BSA / AML applies
- `finserv_agent_audit.governance.best_interest_check.BestInterestCheck` deployed where Reg-BI applies
- `finserv_agent_audit.governance.equity_audit.EquityAudit` deployed where fair-lending applies
- Quantitative drift metrics tracked and reported quarterly

### Regulator expectation alignment

- Meets the FFIEC IT Examination Handbook Architecture, Infrastructure, and Operations (AIO) booklet baseline expectations on AI-system controls [UNVERIFIED — confirm current AIO booklet text].
- Meets the OCC Bulletin 2024-26 third-party risk-management expectations on vendor model risk [UNVERIFIED].
- Meets the CFPB Circular 2022-03 specificity standard for AI-driven adverse-action notices [UNVERIFIED].
- Where applicable: meets the 23 NYCRR Part 500 cybersecurity-governance expectations as applied to AI surfaces [UNVERIFIED].

### Board-reporting indicators

- Quarterly board report includes: chain-verification success rate, vendor-drift count + disposition, gate-violation rate, MIProxy attestation success rate, model-inventory delta. Risk Committee receives extended package monthly.

### How to advance to Level 5

- Deploy MCP server integration so audit-chain artifacts are accessible to peer AI systems under controlled discovery.
- Deploy OpenTelemetry emitter so chain events flow into the institution's observability backplane.
- Deploy an adversarial test pack against the chain (induced corruption, induced replay, induced witness disagreement) on a documented cadence.
- Build a portfolio-level governance dashboard that aggregates across business units and regulator regimes.

---

## Level 5 — Optimizing

**Description.** Governance is integrated across the institution's observability, peer-AI ecosystem, and adversarial testing surface. The institution practices its incident response on the audit chain itself (induced failures, recovery drills). Portfolio-level dashboards aggregate across business units. The institution is at or near the front of the industry on agentic-AI governance.

**Typical firm profile.** Day 180+ in a mature CAIO function; an institution that has invested in agentic-AI governance for at least 12-18 months. Less than 5% of large FSI firms are at Level 5 in mid-2026 [UNVERIFIED — qualitative estimate].

### Required evidence — Level 5

- All Level 4 evidence
- MCP (Model Context Protocol) server integration deployed; audit-chain artifacts accessible to authorized peer AI systems under controlled discovery
- OpenTelemetry emitter producing chain events to the institution's observability backplane (Datadog, Honeycomb, Splunk, equivalent)
- Adversarial test pack documented and run quarterly: induced storage drift, induced sequence gap, induced verifier swap, induced witness disagreement, induced vendor drift — all six rows of the FAILURE-MODES matrix exercised
- Portfolio-level governance dashboard aggregating across business units, autonomy bands, vendor classes, regulator regimes
- Quarterly tabletop exercise that reconstructs a full operational day from the audit chain alone
- Substrate-pluggable MIProxy backend (SLSA, in-toto, equivalent) deployed for at least one high-integrity surface

### Regulator expectation alignment

- Meets the high bar of every applicable regime and is in a position to advise regulators on emerging-practice expectations.
- The institution's governance work product is cited at industry conferences, standard-setting bodies, and peer benchmarking studies.

### Board-reporting indicators

- Quarterly board report includes a portfolio-level maturity trajectory; the institution is targeting Level-5-equivalent across new business lines as they come online.

### How to advance further

- Sustained Level 5 maturity is the goal; the institution invests in research collaborations, contributes to open-source governance frameworks (including `finserv-agent-audit` itself), and shapes industry-wide standards.

---

## Summary table

| Level | Posture | Cumulative module set deployed | Typical Day-N in CAIO tenure |
|---|---|---|---|
| 1 | Initial | (none) | Day 0 |
| 2 | Repeatable | SovereignVeto + AuditChain + ad-hoc inventory | Day 14-30 |
| 3 | Defined | + AutonomyLadder + DEFCONMachine + EU AI Act mapping + MRM policy | Day 60-90 |
| 4 | Managed | + 4 Protocol seams + VendorScoreGate + FSI vertical gates | Day 90-180 |
| 5 | Optimizing | + MCP integration + OTEL emitter + adversarial test pack + portfolio dashboard | Day 180+ (12-18 mo) |

---

## Related

- [`docs/caio_first_90_days_playbook.md`](caio_first_90_days_playbook.md) — the 90-day stand-up plan that advances Level 1 → Level 3
- [`docs/pre_examination_ai_self_assessment.md`](pre_examination_ai_self_assessment.md) — 50-question worksheet (most useful at Levels 3-4)
- [`docs/big4_engagement_letter_exhibit.md`](big4_engagement_letter_exhibit.md) — SOW exhibit (most useful at Levels 4-5)
- [`ASSURANCE-GUIDE.md`](../ASSURANCE-GUIDE.md) — Big-4 walk-through guide
- [`SHIP-RECEIPT.md`](../SHIP-RECEIPT.md) — module-by-module shipping status
- [`docs/sr11_7_mapping.md`](sr11_7_mapping.md) — SR 11-7 overlay
- [`docs/nist_ai_rmf_mapping.md`](nist_ai_rmf_mapping.md) — NIST AI RMF 1.0 mapping
- [`docs/eu_ai_act_mapping.md`](eu_ai_act_mapping.md) — EU AI Act mapping
- [`scripts/maturity_self_score.py`](../scripts/maturity_self_score.py) — the CLI self-score tool

---

*Patterns are software, not legal advice. The maturity levels above are self-assessment scaffolding; calibrate the level definitions to your institution's regulator, scale, and business mix. Citations flagged [UNVERIFIED] require primary-source confirmation before use in regulatory or board-facing documents.*
