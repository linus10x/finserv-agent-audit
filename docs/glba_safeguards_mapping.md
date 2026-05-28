# GLBA Safeguards Rule — Control Mapping for Autonomous AI Agents

This document maps the governance patterns in this repository to specific
obligations under the Gramm-Leach-Bliley Act Safeguards Rule (16 C.F.R. Part 314),
as revised by the Federal Trade Commission effective June 9, 2023. Autonomous
agents in financial services routinely read, compose, summarize, or act on
customer non-public personal information (NPI); the Safeguards Rule applies to
that activity whether the actor is a human session or an LLM-backed agent.

> **Disclaimer:** Reference pattern, not legal advice. Regulatory characterizations
> are summaries; engage qualified counsel for your specific compliance
> determination. See repo-root [`DISCLAIMER.md`](../DISCLAIMER.md).

---

## Framework Overview

The Safeguards Rule requires every covered "financial institution" to develop,
implement, and maintain a comprehensive written information security program
(WISP) appropriate to the institution's size, the nature of its activities, and
the sensitivity of the customer information at issue. The June 2023 revision
prescribed specific elements where the prior rule allowed generic discretion:
designation of a qualified individual (16 C.F.R. § 314.4(a)), risk assessment
(§ 314.4(b)), nine enumerated safeguard elements (§ 314.4(c)(1)–(8)), regular
testing (§ 314.4(d)), service-provider oversight (§ 314.4(f)), a written
incident-response plan (§ 314.4(h)), and a 30-day notice obligation to the FTC
for security events affecting 500 or more consumers (§ 314.5).

The pattern coverage below treats the agent as a first-class authorized user
whose every NPI read is gated, purpose-tagged, and recorded on the hash-chain
audit ledger.

---

## Primary-Source Citations

| Source | Retrieved | Status |
|---|---|---|
| 16 C.F.R. Part 314, Safeguards Rule (FTC) | 2026-05-28, https://www.ftc.gov/legal-library/browse/rules/safeguards-rule | `[UNVERIFIED — primary source not fetched: HTTP 403 on FTC.gov]` |
| 16 C.F.R. § 314.4 (Cornell LII mirror) | 2026-05-28, https://www.law.cornell.edu/cfr/text/16/314.4 | Verified — nine elements, qualified individual, risk assessment, testing, service-provider oversight, incident-response plan confirmed verbatim |
| 16 C.F.R. § 314.5 (Cornell LII index) | 2026-05-28, https://www.law.cornell.edu/cfr/text/16/part-314 | Verified — 30-day FTC notice for events affecting 500+ consumers confirmed |
| 15 U.S.C. § 6801 et seq. (GLBA statutory foundation) | Referenced; consult eCFR / govinfo for the operative statutory text |

The 16 C.F.R. § 314.2 definitions list (including "customer information" and
"nonpublic personal information") was not fetched verbatim in this pass; the
definitions used below follow the FTC's published rule text and the operative
language adopted in ADR-0008.

---

## Control Mapping Table

| Safeguards Rule Requirement | Section | Pattern in This Repo | File |
|---|---|---|---|
| Written information security program | § 314.3 | Repo as published reference architecture; per-institution WISP composes these patterns | repo root |
| Qualified individual designated | § 314.4(a) | Sovereign-veto authority and incident-window declarations carry the Qualified Individual's principal | `patterns/sovereign_veto.py` |
| Risk assessment, periodically re-examined | § 314.4(b) | DEFCON risk-state machine — continuous evaluation, hysteresis on de-escalation | `examples/defcon_state_machine.py` |
| Access controls (technical and physical), periodically reviewed | § 314.4(c)(1) | `GLBASafeguardsGate` — per-read authorization against named element; `GLBA-RECORD-WILDCARD` veto on unbounded reads | `src/finserv_agent_audit/governance/glba_safeguards_gate.py` (ADR-0008, Tranche 2C) |
| Identify and manage data, personnel, devices, systems, facilities by business importance | § 314.4(c)(2) | Data-inventory map referenced by every `NPIAccessIntent`; encryption-routing check derives from this map | ADR-0008 |
| Encryption of customer information in transit and at rest | § 314.4(c)(3) | `GLBA-ENCRYPTION-DOWNGRADE` veto — read is blocked if the transport or sink does not meet the encryption standard recorded in the data inventory | ADR-0008 |
| Secure development practices for in-house applications | § 314.4(c)(4) | CI gate, mypy strict, ruff, branch-coverage threshold; vendor-score gate for third-party dependencies | `.github/workflows/ci.yml`, `pyproject.toml` |
| Multi-factor authentication for any individual accessing an information system | § 314.4(c)(5) | `GLBA-MFA-MISSING` veto — human-actor reads must carry an MFA proof identifier; agent-actor reads carry identity-provider-verified principal | ADR-0008 |
| Secure disposal of customer information | § 314.4(c)(6) | Audit-chain retention policy defines the disposal envelope; hash-chain anchoring guarantees disposal is itself a recorded event | `src/finserv_agent_audit/governance/ledger_store_worm.py` |
| Change management procedures | § 314.4(c)(7) | DEFCON transitions on gate-disable or configuration drift; audit-chain entry on every governance-config change | `src/finserv_agent_audit/governance/defcon.py` |
| Monitor and log activity of authorized users; detect unauthorized access | § 314.4(c)(8) | Hash-chain audit ledger — every NPI read carries actor, purpose, named GLBA element, record IDs; tamper-evident; queryable per consumer | `src/finserv_agent_audit/schemas/audit_event.py`, `src/finserv_agent_audit/governance/ledger_store_sqlite.py` |
| Regular testing of safeguards' key controls (penetration test annually; vulnerability assessment every six months) | § 314.4(d) | CI matrix runs the governance test suite on every commit; vendor-score gate enforces dependency hygiene | `.github/workflows/ci.yml` |
| Service-provider oversight (selection, contracting, periodic assessment) | § 314.4(f) | Vendor-score gate — third-party dependencies carry a vendor-score and a renewal cadence; downgrade triggers DEFCON-2 | `src/finserv_agent_audit/governance/vendor_score_gate.py` (Tranche 2C) |
| Written incident-response plan | § 314.4(h) | `GLBA-INCIDENT-WINDOW` veto state — program enters incident mode; all reads route through an incident allowlist | ADR-0008 |
| Notice of security event to FTC within 30 days for events affecting 500+ consumers | § 314.5 | Audit chain supplies affected-record count by query rather than forensic reconstruction; witness-anchor (RFC 3161) carries timestamp evidence | `src/finserv_agent_audit/governance/witness_anchor.py` |

---

## Customer NPI Categories — Operational Walkthrough

The Safeguards Rule scope is defined by what counts as "customer information"
(any record containing nonpublic personal information about a customer of the
financial institution, in any form). The operational question the autonomous-agent
stack must answer on every read is: **is this a customer NPI record, and under
what authorization element is the agent reading it?**

| Category | Examples (illustrative, not exhaustive) | Default agent-access posture | Authorizing element |
|---|---|---|---|
| Identifiers | Name + account number, SSN, government ID number | Read requires enumerated `record_ids`, no wildcards; MFA proof when actor is human | § 314.4(c)(1), § 314.4(c)(5) |
| Financial profile | Account balance, payment history, credit-line utilization, asset/liability snapshot | Read requires specific business purpose (not "analytics", "operations") | § 314.4(c)(1), § 314.4(c)(8) |
| Transaction history | Posted transactions, pending authorizations, recurring debits | Per-read ceiling default 1,000 records per agent per hour | § 314.4(c)(1), § 314.4(c)(8) |
| Application data | Income, employment, residence, dependents | Read tagged to a named application workflow; ECOA/Reg B protected-class fields routed to the EquityAudit pattern | § 314.4(c)(1), cross-reference ECOA mapping |
| Aggregated insights | Portfolio attrition scores, retention propensity | Default anonymization at the gate; re-identified reads require Qualified Individual blanket authorization | § 314.4(a), § 314.4(c)(1) |
| Service-provider routed data | Data sent to a third party for hosting, scoring, or analytics | Vendor-score gate must clear; encryption standard pinned per dependency | § 314.4(f) |

---

## Gap Analysis — What This Repo Does NOT Cover

The repository covers the agent-decision layer. The following Safeguards Rule
obligations require institution-level work beyond what these patterns provide:

| Requirement | Gap | Guidance |
|---|---|---|
| Risk assessment documentation (§ 314.4(b)) | DEFCON state machine evaluates risk; it does not produce the institution-level risk-assessment document | Compose DEFCON evidence into the WISP risk assessment owned by the Qualified Individual |
| Annual penetration test (§ 314.4(d)) | CI testing covers governance modules; full-scope pentest of the surrounding stack is out of scope for this repo | Engage qualified pentest vendor; surface results through the vendor-score gate |
| Service-provider contract terms (§ 314.4(f)) | Vendor-score gate enforces score and renewal cadence; it does not draft contract clauses | Coordinate with legal on Safeguards flow-down clauses; the gate enforces the operational posture downstream of the contract |
| Board / governing-body reporting (§ 314.4(i)) | Audit chain supports the report; the report itself is an institutional artifact | The Qualified Individual produces the annual report from audit-chain queries |
| Employee training (§ 314.4(e)) | Not in scope for an agent-governance repository | Institutional training program; the agent-side equivalent is the named-element discipline these patterns enforce |
| State-law overlays (e.g., NYDFS 23 NYCRR 500, CCPA / CPRA) | Substantive overlap with Safeguards but distinct triggers and reporting timelines | Map separately; the audit chain is the common evidentiary substrate |
| Interagency Safeguards parallels for bank-regulated institutions (12 C.F.R. Part 30 App. B (OCC); 12 C.F.R. Part 208 App. D-2 (FRB); 12 C.F.R. Part 364 App. B (FDIC)) | These patterns map cleanly to FTC-regulated covered institutions; bank-regulated parallels are substantively similar but cite distinct authorities | `[UNVERIFIED — primary source not fetched]` on the exact interagency citations; verify before publication for bank-regulated programs |

---

## References

- 16 C.F.R. Part 314 (Standards for Safeguarding Customer Information), as
  revised effective June 9, 2023. Retrieved 2026-05-28 via Cornell LII mirror;
  FTC source returned HTTP 403 on direct fetch.
- 15 U.S.C. § 6801 et seq. (Gramm-Leach-Bliley Act, Title V, Subtitle A).
- ADR-0008 · GLBA Safeguards Rule — Customer NPI Partitioning
  (`docs/adr/0008-glba-safeguards.md`).
- ADR-0002 · Sovereign Veto (`docs/adr/0002-sovereign-veto.md`).
- ADR-0001 · DEFCON State Machine (`docs/adr/0001-defcon-state-machine.md`).
- Cross-references: ADR-0009 (FCRA / Reg V), ADR-0010 (ECOA / Reg B),
  ADR-0011 (BSA / AML).
