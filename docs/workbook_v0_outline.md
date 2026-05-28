# Autonomy Ladder™ Workbook v0 — Outline

**Status:** v0 outline (preview · subject to revision before v1 ships Week 7)
**Repo:** github.com/linus10x/finserv-agent-audit
**Companion:** Autonomy Ladder™ Pitch Deck v1 (also in `/docs/`)
**License:** MIT (same as parent repo)
**Date:** 2026-05-24

---

## Why this outline ships now

The polished v1 workbook ships Week 7 of the Autonomy Ladder™ campaign (~July 2026). This v0 outline ships now so PE-CRE operating partners, Chief AI Officers, and search-firm researchers have a forwardable artifact today — before they have to ask for one.

The v0 outline is a forwarding reference, not a polished deliverable. It states the structure, the chapter-level argument, the example artifacts each chapter will produce, and the buyer outcome. The full v1 expands each chapter to 4-8 pages with real examples and templates.

---

## Workbook positioning

**Title:** *Autonomy Ladder™ — The First 90 Days as a PE-Backed Operator's CTO*
**Audience:** CTOs and Chief AI Officers entering a PE-backed portfolio company within their first 90 days. Specifically calibrated to: CRE operating platforms (RealPage / Yardi / MRI / AppFolio adjacent), Private Capital / wealth platforms, and regulated SaaS handling sensitive data under SOC 2, HIPAA, PCI, or FINRA/SEC oversight.
**Length (v1 target):** 28-32 pages
**Format:** PDF + Markdown source · ungated · watermarked with version
**Outcome:** A defensible 90-day plan the operator can show the PE sponsor on Day 7 and execute through Day 90, anchored on the Autonomy Ladder A0→A4 framework

---

## Chapter outline

### Chapter 1 — The 7-Day Gap Diagnosis

What the operator inherits when they walk in. Six workstreams that get mapped, ranked, and triaged in the first 7 days:

1. Security posture (NIST CSF 2.0 baseline)
2. Infrastructure + cloud (cloud-vs-on-prem, identity, backup/DR, EOL inventory)
3. Tech governance + policy (decision rights, role definitions, policy framework)
4. IT operations + helpdesk (ticketing, ITSM hygiene, incident management)
5. Vendor + partner ecosystem (MSP relationships, contract hygiene, vendor portfolio)
6. Data security + DLP + data quality (classification, access controls, lineage)

Output artifact: a 1-page gap-diagnosis brief the operator hands the PE sponsor on Day 7.

### Chapter 2 — The Autonomy Ladder Applied to the Inherited Stack

Map every system the operator inherits to its current A0-A4 rung. Most legacy stacks sit at A0 (human-driven) or A1 (AI-assisted under human review). The chapter walks through:

- A0 — Human-driven decisions (the starting baseline)
- A1 — AI-assisted (human approval required)
- A2 — AI-driven with veto (human can override)
- A3 — AI-autonomous with audit (human reviews post-hoc)
- A4 — AI-autonomous with cryptographic audit + sovereign veto

Output artifact: a system-by-system A0-A4 inventory + a target-rung-by-Day-90 plan.

### Chapter 3 — Sovereign Veto Architecture for Regulated Operations

Why every AI-driven decision in a regulated environment needs a sovereign veto path. The pattern (SHIELD) with worked examples from the finserv-agent-audit repo. Decision authority, escalation triggers, and the audit-trail requirement.

Output artifact: a sovereign-veto decision matrix template ready to fill in for the operator's specific stack.

### Chapter 4 — DEFCON State Machine for Crisis Readiness

Every PE-backed portco hits an incident in the first 12 months. The DEFCON state machine pattern, calibrated to the operator's six workstreams. Trigger thresholds, escalation paths, and the playbook each DEFCON level invokes.

Output artifact: a DEFCON runbook tailored to the operator's stack + escalation contact tree.

### Chapter 5 — Hash-Chain Audit Ledger for Sponsor Reporting

PE sponsors require audit-defensible decision trails. The hash-chain audit ledger pattern, with worked SQL + Python examples from the finserv-agent-audit repo. Performance trade-offs, retention policy, and the sponsor-reporting interface.

Output artifact: an audit-ledger schema + ingestion code stub the operator can deploy in Sprint 1.

### Chapter 6 — Shadow-Mode Promotion for Every New AI Feature

The 90-day shadow A/B promotion clock. Why every new AI behavior runs in shadow before touching production capital, customer data, or regulatory-reportable decisions. Threshold criteria for promotion + the automatic kill-switch for shadow failure.

Output artifact: a shadow-mode promotion checklist + the kill-threshold formula calibrated to the operator's risk tolerance.

### Chapter 7 — Vendor + Partner Governance for AI Stack Components

When the AI is upstream — vendor-provided LLMs, SaaS scoring APIs, third-party data feeds — the operator's governance has to extend through the vendor contract. Contract-clause requirements, audit-rights language, and the "no third-party undisclosed AI" rule.

Output artifact: a vendor-AI-disclosure questionnaire + a contract-language template the operator can include in every new vendor agreement.

### Chapter 8 — The 30-60-90 Roadmap Template

How the operator presents the Autonomy Ladder maturity plan to the PE sponsor and the company Board. Phased adoption (A0→A1→A2→A3→A4) with budget, headcount, and risk-reduction outcomes per phase.

Output artifact: a 30-60-90 PowerPoint template + a sponsor-readable narrative outline.

### Chapter 9 — Communicating Maturity to External Stakeholders

How the operator talks about the AI maturity posture to insurance carriers, regulators (where applicable), auditors, and the customer-facing sales motion. What to say, what NOT to say, and the artifacts that prove what you've claimed.

Output artifact: a one-page external-stakeholder talking-points document.

### Appendix A — Private Capital Annex

How the Autonomy Ladder maps to multi-family-office, RIA, wealth-platform, and UHNW-data-aggregation operations specifically. Calibrated for SEC and FINRA scrutiny. Worked examples from the finserv-agent-audit repo's Private Capital subdirectory.

### Appendix B — CRE Annex (companion to cre-agent-audit repo)

How the Autonomy Ladder maps to CRE operating platforms — Fair Housing pre-flight, lease-abstraction provenance, tenant-PII residency, two settled matters of record (TransUnion · SafeRent) and one active DOJ + 8-AG antitrust action (US v. RealPage, M.D.N.C., filed Aug 23 2024, Sherman § 1 — ongoing). Worked examples ship with the cre-agent-audit repo June 2, 2026.

### Appendix C — Regulation-to-Pattern Mapping

Quick-reference cross-walk: NIST AI RMF function (GOVERN/MAP/MEASURE/MANAGE) × Treasury FS AI RMF 230 control objectives × EU AI Act risk categories × Colorado AI Act SB 24-205 (high-risk AI requirements effective February 1, 2026 per leg.colorado.gov) × SR 11-7 federal model-risk supervision.

---

## How to use this v0 outline

Three audiences, three uses:

1. **Operators inheriting a PE-portfolio CTO seat:** Read Chapters 1-2 + Appendix matching your vertical. Apply the 7-day gap diagnosis. Don't wait for the polished v1.
2. **PE operating partners evaluating a portco's AI posture:** Read the chapter table of contents + Chapters 5 (audit) and 6 (shadow-mode). These two patterns separate operators who ship governance from operators who slide-deck it.
3. **Search-firm researchers vetting a CTO/CAIO candidate:** Read the structure. The structure proves the candidate has thought through the operator-first 90 days as a system, not as a list of best practices.

---

## What's in v1 that's NOT in this v0

- Worked examples per chapter (real anonymized data, anonymized portcos)
- Filled-in template artifacts (gap-diagnosis brief, DEFCON runbook, audit-ledger schema, vendor questionnaire, 30-60-90 deck)
- Footnotes citing specific regulations, settled cases, and academic sources
- A foreword written by a named research advisor (subject to attribution resolution per 2026-06-01 hard gate)
- ~20 additional pages of operational detail and worked examples

---

## License + reuse

MIT licensed. Fork, adapt, white-label for your own portfolio company. The patterns are vendor-neutral by design. Attribution requested but not required.

---

*Authored by Kunjar Bhaduri · 25-year FSI technology operator · Autonomy Ladder™ campaign Week 1 · v0 outline 2026-05-24 · v1 ships Week 7 (July 2026) · github.com/linus10x · autonomy-ladder.io*
