# Private-Equity Portfolio AI-Governance Playbook

**Status:** v2.0.0-draft · Last reviewed: 2026-05-28.
**Audience:** AI Operating Partner at a mid-market to upper-mid-market PE fund with a 10-30 portco book; fractional Chief AI Officer engaged across multiple portcos under a single AI Operating Partner; Big-4 advisory partner supporting a PE fund's portfolio AI-governance build.

> **Disclaimer:** This playbook is provided for reference only and does
> not constitute legal advice. Engage qualified counsel for your
> specific compliance determination. See repo-root
> [`DISCLAIMER.md`](../DISCLAIMER.md).

---

## Persona Context — The AI Operating Partner

The Korn Ferry / FoxTrove 2026 mapping of the operating-partner role
identifies the **AI Operating Partner** as the newly-named role
emerging across the upper-mid-market and large-cap PE landscape. Two
adjacent realities shape the role's mandate:

1. **No single portco can afford a full-time Chief AI Officer** in the
   $50M-$500M EV bracket where mid-market PE concentrates. The
   fractional CAIO sits **underneath** the AI Operating Partner — one
   AI Operating Partner steers a 10-30 portco book, with 4-8 fractional
   CAIOs deployed across the highest-AI-exposure portcos. The
   remainder of the book gets quarterly check-ins from the AI Operating
   Partner directly.

2. **No portfolio-wide AI-governance playbook exists** as a published
   pattern. PE Operating Partners cite this gap as the single largest
   pain point in their first 12 months in the role. Each portco runs
   its own AI program with its own maturity, its own vendor surface,
   and its own audit posture; the fund has no consolidated view, no
   aggregated risk signal, no portfolio-level reporting language.

This playbook closes that gap.

---

## The Portfolio-Wide Governance Problem

The AI Operating Partner inherits a heterogeneous portfolio. A typical
mid-market PE fund's 10-30 portco book includes:

- A specialty-finance lender running an LLM-mediated underwriting
  agent on AWS Bedrock with a homegrown rules engine
- A mid-market wealth-advisory rollup using a third-party robo-advisor
  vendor with no documented retraining cadence
- A health-insurance-adjacent payor running a claims-triage agent on
  Azure OpenAI with no protected-class testing
- A B2B SaaS portco selling LLM-mediated customer-service tools to
  banks (third-party-AI vendor risk for the buyer; provider posture
  under the EU AI Act if any EU customers exist)
- A title-insurance portco running an OCR-and-LLM document-review
  pipeline with no audit trail
- A consumer-lending portco running a credit-decision agent without an
  adverse-action gate or FCRA Reg V analog
- A regional-bank portco subject to OCC examination but pre-Chief-AI-
  Officer

Each portco's tech stack differs. Each portco's regulatory exposure
differs (some are bank-supervised, some are insurance-supervised, some
are CFPB-supervised, some have EU exposure under the AI Act + DORA).
Each portco's AI maturity differs (some are at Maturity Level 1,
others are at Level 3+). The AI Operating Partner cannot govern this
heterogeneity by deploying a single uniform process — but cannot
permit it to remain ungoverned either.

The pattern that works:

- **Each portco runs its own AuditChain locally.** The portco's CAIO
  or fractional CAIO is accountable for the portco-level governance
  artifacts. The fund does not run the portco's AI program.
- **The fund-side AI Operating Partner collects read-only audit-chain
  data from each portco.** The aggregator computes portfolio-level
  metrics across the 10-30 portco book without taking control.
- **Portfolio-level governance reporting goes to the investment
  committee, the fund's LPs, and (where applicable) the portco's
  own board.** The aggregator's output is the substrate; the AI
  Operating Partner is the narrator.

---

## Multi-Tenant Audit-Chain Aggregation Model

The framework's `examples/portfolio_governance_dashboard.py` is the
reference implementation of the aggregator. The design holds the
following invariants:

1. **Each portco operates an independent AuditChain.** The portco's
   chain is the system of record for the portco. The aggregator never
   writes to the portco's chain.
2. **The aggregator collects chain files (or pre-extracted summary
   feeds) read-only.** This can be a periodic SFTP pull, an S3 pull, a
   direct chain-file mount, or a portco-side summary-export endpoint.
   The aggregator works against any source the portco's CAIO is willing
   to make available.
3. **The aggregator computes portfolio-level metrics from local-only
   reads.** No portco-side state mutation. No cross-portco event
   merge into a single chain (which would create both legal-privilege
   and data-segregation problems).
4. **The portfolio-level metrics are persisted in the fund's own
   AuditChain.** The aggregator's read events themselves are logged in
   the fund-side chain so the LP investment committee can audit what
   the aggregator did when.
5. **DEFCON-style state machines roll up to a portfolio-level state.**
   The portfolio DEFCON is the max of the constituent portco DEFCONs,
   with cooldown so a single portco's transient HALT does not flap the
   portfolio-level state.

---

## Portfolio-Level Patterns

### Aggregated DEFCON state

Each portco emits a DEFCON state (NORMAL / CAUTION / ALERT / DANGER /
HALT). The aggregator pulls the latest per-portco state, applies
cooldown logic, and reports the portfolio's worst-but-stable state.
The portfolio DEFCON is the headline indicator at the quarterly
investment-committee review.

### Aggregated vendor-score-gate alerts

Each portco's `vendor_score_gate` emits alerts when a third-party
model fails a pre-promotion check or when drift is detected
post-promotion. The aggregator surfaces vendor concentration across
the portfolio — if eight of the 22 portcos all depend on Anthropic
Claude as the underlying LLM, that's a portfolio-level concentration
risk the AI Operating Partner needs to manage.

### Aggregated model-inventory health

Each portco's `ModelInventory` exposes count by lifecycle state and
count overdue-for-revalidation. The aggregator reports portfolio-wide
totals and identifies the portcos with the worst posture (most
overdue, most stuck in IN_VALIDATION, most APPROVED_FOR_PRODUCTION
without a documented validation memo).

### Aggregated maturity self-score

Each portco runs `scripts/maturity_self_score.py` on a documented
cadence (suggested quarterly). The aggregator pulls the most-recent
level per portco and reports the portfolio distribution (count at
Level 1 / Level 2 / Level 3 / Level 4 / Level 5). The distribution
itself is the AI Operating Partner's investment-committee narrative.

### Aggregated incident posture

Each portco files AI-incident retrospectives per the framework's
template. The aggregator counts incidents by severity, by root-cause
class, by recurrence within 90 days. The aggregator is the early-
warning system for portfolio-wide pattern recognition: if three
portcos all suffered model-deprecation incidents in the same quarter,
that's a portfolio-level vendor-management gap, not three independent
portco events.

---

## Quarterly Portfolio Review Process

The 90-minute quarterly review is the operative forcing function for
the AI Operating Partner's governance posture. The agenda below
assumes a 22-portco book; scale up or down as the book size dictates.

### Pre-Review Preparation (T-7 days)

- AI Operating Partner runs the aggregator against the latest pulled
  chain files / summary feeds from each portco
- Each fractional CAIO submits a one-page portco status (one
  paragraph: state, top three issues, next-quarter ask)
- AI Operating Partner generates the markdown report via
  `PortfolioGovernanceDashboard.emit_quarterly_report()`

### Investment Committee Review Agenda (90 min)

**Minutes 0-10 — Portfolio DEFCON narrative.** What's the portfolio
DEFCON? Which portco drove the worst state? What's the trajectory
versus the prior quarter?

**Minutes 10-25 — Maturity distribution.** Where is the portfolio on
the maturity model? Which portcos moved up a level this quarter?
Which portcos slipped? What's the gap between current state and the
fund's investment-thesis-implied maturity target?

**Minutes 25-45 — Vendor concentration.** Which third-party models
dominate the portfolio's third-party-AI surface? What's the exposure
if any single vendor sunsets? What's the deprecation-watch posture
across the portfolio?

**Minutes 45-65 — Model-inventory health.** Total models in
production. Total overdue for revalidation. Worst-posture portcos.
Specific portfolio-wide action: which portcos need fractional-CAIO
intervention this quarter?

**Minutes 65-80 — Incident posture and pattern recognition.** Recent
incidents. Recurring patterns across portcos. Cross-portco lessons.

**Minutes 80-90 — Forward look.** Regulatory calendar (next-quarter
EU AI Act milestones; NAIC bulletin adoptions; PCAOB AS 2201 amendment
effective dates; DORA examination cycles). Portfolio-wide
prioritization for the next 90 days.

### Red-Flag Triggers (any of these forces an immediate special review,
not the next-quarter cycle)

- Any portco in DEFCON HALT for more than 72 hours
- Any portco with a confirmed regulatory examination action
- Any portco with an unresolved Vendor Score Gate failure on a
  production decision class
- Any portco with a deprecation-watch alert under 30 days where the
  substitute is not yet shadow-mode validated
- Any portco-level AI incident classified as major (consumer-affecting
  adverse action issued in error; protected-class fairness regression;
  audit-chain integrity break)
- Any cross-portco pattern: three or more portcos with the same
  root-cause class within 90 days

---

## Portco Onboarding Checklist — Newly-Acquired Portfolio Company

The post-close 30/60/90 day checklist below assumes the portco was
acquired at any maturity level. The AI Operating Partner's first job
is to discover, classify, and bring the portco into the aggregator —
not to refactor the portco's AI program in the first 90 days.

### Days 0-30 — Discovery

- [ ] **Day 5.** Initial introduction call with the portco's CIO /
      CTO / Head of Data. Identify the AI use cases in production.
- [ ] **Day 10.** Receive the portco's AI inventory (in whatever form
      it exists; ad-hoc is acceptable). If no inventory exists, the
      AI Operating Partner runs an inventory canvass.
- [ ] **Day 15.** Identify the regulatory regime stack (US bank? US
      insurer? CFPB-covered? EU AI Act / DORA? NAIC bulletin states?).
- [ ] **Day 20.** Identify the portco's third-party-AI vendor surface
      (LLM providers, vector-DB vendors, agentic-orchestration
      platforms, model-eval platforms).
- [ ] **Day 25.** Document the portco's current AI-governance posture
      against the maturity model. Establish the baseline.
- [ ] **Day 30.** Onboarding read-out to the deal team and the AI
      Operating Partner's quarterly-review aggregator. Portco is now
      in the dashboard.

### Days 30-60 — Foundational Controls

- [ ] **Day 35.** Deploy `sovereign_veto` per in-scope decision class.
- [ ] **Day 40.** Deploy `AuditChain` with at least
      `JsonlLedgerStore`; identify the portco-side data-segregation
      controls.
- [ ] **Day 45.** Deploy `model_inventory` and populate from the
      Day 10-25 canvass.
- [ ] **Day 50.** Publish the Autonomy Ladder A0-A4 classification
      per decision class.
- [ ] **Day 55.** Stand up the aggregator's read connection to the
      portco's audit chain (SFTP pull, S3 pull, or summary feed).
- [ ] **Day 60.** First portfolio-aggregator pull including this
      portco; verify the portco shows up in `aggregate_defcon_status()`.

### Days 60-90 — Domain-Specific Controls

- [ ] **Day 65.** For credit / underwriting portcos: deploy
      `adverse_action_gate`, `equity_audit`, and
      `protected_class_proxy_detector`.
- [ ] **Day 70.** For insurance portcos: deploy
      `customer_facing_chatbot_guardrail`,
      `protected_class_proxy_detector`, and per-state NAIC bulletin
      mapping.
- [ ] **Day 75.** For any portco with EU customer touch: deploy
      `vendor_attestation_ledger` and stand up the DORA Art. 28(3)
      Register-of-Information feed.
- [ ] **Day 80.** Deploy `vendor_score_gate` and `deprecation_watch`
      per portco; populate the vendor-clauses companion templates.
- [ ] **Day 85.** Run `scripts/maturity_self_score.py`; document the
      Day-90 maturity level.
- [ ] **Day 90.** Quarterly-review read-out including this portco's
      Day-30, Day-60, and Day-90 milestones.

---

## Exit-Planning — What to Leave Behind When the Portco Exits the Fund

When a portco exits the PE fund (strategic sale, secondary buyout, or
IPO), the AI-governance artifacts must transfer with the company. The
exit-planning checklist:

- [ ] **All portco-side audit chains** transfer to the acquirer.
      Verify the chain integrity with `AuditChain.verify()` at signing.
- [ ] **Model inventory** transfers as the system of record for the
      portco's AI programs.
- [ ] **Vendor attestation ledger** transfers with the portco; the
      acquirer inherits the third-party-AI vendor history.
- [ ] **All AI-incident retrospectives** transfer; the acquirer
      inherits the postmortem record.
- [ ] **The portco is removed from the fund's portfolio aggregator.**
      Last aggregator entry per portco is preserved in the fund-side
      audit chain for LP-side discovery posture.
- [ ] **The portco's maturity self-score history** transfers as the
      governance-trajectory record.
- [ ] **Where the portco operates an EU AI Act high-risk system**:
      the technical documentation, conformity-assessment artifacts,
      and post-market-monitoring records transfer.
- [ ] **Where the portco is in a NAIC-bulletin adopting state**: the
      AIS program documentation transfers.

The exit-planning artifact bundle is itself the substrate for the
acquirer's first-90-days CAIO. The aggregator's prior view of the
portco becomes the historical baseline.

---

## Reference Dashboard Implementation

The reference dashboard implementation is at
[`examples/portfolio_governance_dashboard.py`](../examples/portfolio_governance_dashboard.py).
The dashboard is stdlib-only, ruff- and mypy-strict-clean, and
designed for AI-Operating-Partner-level use.

API surface:

- `PortfolioGovernanceDashboard()` — instantiate the aggregator
- `register_portco(portco_id, audit_chain_paths)` — register a portco's
  audit-chain file paths (the aggregator never writes to these)
- `aggregate_defcon_status() -> dict[str, str]` — current DEFCON state
  per portco
- `aggregate_drift_alerts(window_hours=24) -> dict[str, list]` —
  vendor-score-gate drift alerts per portco in the window
- `aggregate_model_inventory_health() -> dict[str, dict]` — number of
  models in inventory and number overdue-for-validation per portco
- `aggregate_maturity_scores() -> dict[str, int]` — current maturity
  level per portco
- `emit_quarterly_report() -> str` — markdown report ready for the
  AI Operating Partner's quarterly review

The dashboard's demo runner (`if __name__ == "__main__":`) generates
a synthetic 3-portco aggregation suitable for understanding the
output shape without a real portfolio's data.

---

## How This Playbook Stacks with Other Framework Docs

| Use case | Read with |
|---|---|
| Per-portco first 90 days | [`docs/caio_first_90_days_playbook.md`](caio_first_90_days_playbook.md) |
| Per-portco maturity scoring | [`docs/agentic_ai_governance_maturity_model.md`](agentic_ai_governance_maturity_model.md), [`scripts/maturity_self_score.py`](../scripts/maturity_self_score.py) |
| Per-portco regulatory mapping (bank-supervised) | [`docs/sr11_7_mapping.md`](sr11_7_mapping.md), [`docs/interagency_mrm_2026_overlay.md`](interagency_mrm_2026_overlay.md), [`docs/nydfs_part500_ai_mapping.md`](nydfs_part500_ai_mapping.md), [`docs/glba_safeguards_mapping.md`](glba_safeguards_mapping.md) |
| Per-portco regulatory mapping (insurer) | [`docs/naic_model_bulletin_insurance_mapping.md`](naic_model_bulletin_insurance_mapping.md) |
| Per-portco regulatory mapping (EU customer touch) | [`docs/eu_ai_act_mapping.md`](eu_ai_act_mapping.md), [`docs/eu_ai_act_aug_2026_compliance_pack.md`](eu_ai_act_aug_2026_compliance_pack.md), [`docs/dora_mapping.md`](dora_mapping.md) |
| Per-portco regulatory mapping (CFPB-covered) | [`docs/cfpb_circular_2022_03_mapping.md`](cfpb_circular_2022_03_mapping.md), [`docs/cfpb_circular_2023_09_mapping.md`](cfpb_circular_2023_09_mapping.md), [`docs/cfpb_ai_lending_supervisory_landscape.md`](cfpb_ai_lending_supervisory_landscape.md), [`docs/ecoa_reg_b_mapping.md`](ecoa_reg_b_mapping.md), [`docs/fcra_reg_v_mapping.md`](fcra_reg_v_mapping.md) |
| Per-portco pre-examination prep | [`docs/pre_examination_ai_self_assessment.md`](pre_examination_ai_self_assessment.md) |
| Per-portco post-incident learning | [`docs/ai_incident_retrospective_template.md`](ai_incident_retrospective_template.md) |
| Per-portco Big-4 advisory engagement | [`docs/big4_engagement_letter_exhibit.md`](big4_engagement_letter_exhibit.md), [`ASSURANCE-GUIDE.md`](../ASSURANCE-GUIDE.md) |

---

## Gap Analysis — What This Playbook Does NOT Cover

| Topic | Gap | Guidance |
|---|---|---|
| Single-portco operational program | Covered in per-portco docs (see stacking table above) | This playbook is portfolio-level only |
| LP-side AI governance | Out of scope | LP-side governance is a separate document; the aggregator's output feeds the LP-quarterly-letter narrative |
| Portfolio insurance / errors-and-omissions coverage for AI-related claims | Out of scope | Engage the fund's GP-side insurance broker; AI-specific E&O coverage is an emerging market |
| Cross-portco data-sharing arrangements | Out of scope and frequently a problem | Each portco's data is its own; the aggregator works against summary metrics, not raw event data |
| Specific deal-diligence AI checklist | Out of scope; covered separately | A pre-acquisition AI-diligence checklist is a separate v2.X work item |
| Sell-side preparation for the acquirer's CAIO | Lightweight in the exit-planning section above | A full sell-side AI-readiness pack is a separate v2.X work item |

---

## References

- Patterns in this repo:
  `examples/portfolio_governance_dashboard.py`,
  `src/finserv_agent_audit/governance/audit_chain.py`,
  `src/finserv_agent_audit/governance/defcon.py`,
  `src/finserv_agent_audit/governance/model_inventory.py`,
  `src/finserv_agent_audit/governance/sovereign_veto.py`,
  `src/finserv_agent_audit/governance/adverse_action_gate.py`,
  `src/finserv_agent_audit/governance/vendor_score_gate.py`,
  `src/finserv_agent_audit/governance/vendor_attestation_ledger.py`,
  `src/finserv_agent_audit/governance/deprecation_watch.py`,
  `src/finserv_agent_audit/governance/equity_audit.py`,
  `src/finserv_agent_audit/governance/protected_class_proxy_detector.py`,
  `src/finserv_agent_audit/governance/customer_facing_chatbot_guardrail.py`,
  `scripts/maturity_self_score.py`,
  `docs/autonomy_ladder.md`,
  `docs/agentic_ai_governance_maturity_model.md`,
  `docs/caio_first_90_days_playbook.md`,
  `docs/ai_incident_retrospective_template.md`,
  `docs/pre_examination_ai_self_assessment.md`,
  `docs/big4_engagement_letter_exhibit.md`,
  `vendor-clauses/`.
- ADR cross-references: ADR-0001 (DEFCON), ADR-0002 (Sovereign Veto),
  ADR-0003 (Hash-chain audit), ADR-0004 (Autonomy Ladder A0-A4),
  ADR-0007 (Model Inventory), ADR-0014 (Persistence / Witness /
  Timestamp), ADR-0016 (Vendor Score Gate), ADR-0023 (Vendor
  Attestation Ledger), ADR-0024 (Retraining Cadence Monitor),
  ADR-0025 (Deprecation Watch).
- External references:
  - Korn Ferry, *Operating Partner Survey* (2026 edition);
    `[UNVERIFIED — primary source not fetched this pass]`.
  - FoxTrove Search, *AI Operating Partner: A Newly-Named PE Role*
    (2026); `[UNVERIFIED — primary source not fetched this pass]`.
