# BSA / AML — Control Mapping for Autonomous AI Agents

This document maps the governance patterns in this repository to the
anti-money-laundering program requirements of the Bank Secrecy Act, codified
at 31 U.S.C. § 5318(h), and to the FinCEN guidance that frames how AI and
machine-learning techniques are treated inside that program. Autonomous
agents working KYC adjudication, transaction monitoring, sanctions screening,
or SAR-narrative drafting sit squarely inside the BSA/AML control perimeter
and are subject to the same four pillars that govern human analysts.

> **Disclaimer:** Reference pattern, not legal advice. Regulatory
> characterizations are summaries; engage qualified BSA/AML counsel and the
> firm's BSA Officer for compliance determinations. See repo-root
> [`DISCLAIMER.md`](../DISCLAIMER.md).

---

## Framework Overview

31 U.S.C. § 5318(h)(1) requires every covered financial institution to
establish an AML program containing four mandatory elements:

1. The development of internal policies, procedures, and controls.
2. The designation of a compliance officer.
3. An ongoing employee training program.
4. An independent audit function to test the program.

The four-pillar structure is the spine. FinCEN regulations under 31 C.F.R.
Chapter X layer the operational specifics: Customer Identification Program
(31 C.F.R. § 1020.220), Customer Due Diligence and Beneficial Ownership
(31 C.F.R. § 1010.230), Suspicious Activity Report filing thresholds
(31 C.F.R. § 1020.320 for banks; § 1023.320 for broker-dealers), and the
records-retention overlay at 31 C.F.R. § 1010.430. The interagency Joint
Statement on Innovative Efforts to Combat Money Laundering and Terrorist
Financing (December 3, 2018) confirmed that supervisors view AI and ML
techniques as permitted tools inside the AML program — not a free pass on
the four pillars and not a substitute for the BSA Officer's accountability.

The pattern coverage below treats the AI agent as a first-class participant
in the BSA program: every screening, scoring, narrative-draft, and clearance
action is gated, purpose-tagged, audit-logged, and routed through the
SARWorkflowAudit pattern when the decision crosses the SAR-relevance line.

---

## Primary-Source Citations

| Source | Retrieved | Status |
|---|---|---|
| 31 U.S.C. § 5318(h) (govinfo, 2018 USCODE compilation) | 2026-05-28, https://www.govinfo.gov/content/pkg/USCODE-2018-title31/html/USCODE-2018-title31-subtitleIV-chap53-subchapII-sec5318.htm | Verified — four mandatory program elements quoted verbatim above |
| 31 C.F.R. Chapter X (FinCEN regulations — CIP, CDD, SAR, recordkeeping) | Referenced; consult eCFR for the operative regulatory text | Not re-fetched in this pass |
| FinCEN/FRB/FDIC/NCUA/OCC Joint Statement on Innovative Efforts to Combat Money Laundering and Terrorist Financing, December 3, 2018 | 2026-05-28, https://www.fincen.gov/news/news-releases/joint-statement-innovative-efforts-combat-money-laundering | `[UNVERIFIED — primary source not fetched: socket closed]` — citation framing follows the public summary; confirm exact text from FinCEN before publication |
| FinCEN Customer Due Diligence Rule (31 C.F.R. § 1010.230) | Referenced in ADR-0002 (Sovereign Veto EDD-band check) | Not re-fetched in this pass |

The 31 C.F.R. Chapter X subsections were not fetched verbatim in this pass;
the operational framing below follows the published rule text and the
SARWorkflowAudit design adopted in Tranche 2C.

---

## Control Mapping Table

| BSA / AML Requirement | Citation | Pattern in This Repo | File |
|---|---|---|---|
| Internal policies, procedures, controls (Pillar 1) | 31 U.S.C. § 5318(h)(1)(A) | Sovereign Veto + DEFCON state machine — codified control surface around every agent decision class | `src/finserv_agent_audit/governance/sovereign_veto.py`, `src/finserv_agent_audit/governance/defcon.py` |
| BSA Officer designation (Pillar 2) | 31 U.S.C. § 5318(h)(1)(B) | Sovereign-veto bypass-owner field carries the BSA Officer's named principal on every BSA-class clearance | `patterns/sovereign_veto.py` (ADR-0002) |
| Ongoing employee training (Pillar 3) | 31 U.S.C. § 5318(h)(1)(C) | Out of scope for an agent-governance repository; the agent-side equivalent is the named-element discipline these patterns enforce | n/a |
| Independent audit (Pillar 4) | 31 U.S.C. § 5318(h)(1)(D) | Hash-chain audit ledger supplies the evidence substrate; MI Proxy verifier-attestation pattern attests the audit pipeline itself | `src/finserv_agent_audit/schemas/audit_event.py`, `src/finserv_agent_audit/governance/mi_proxy.py` |
| Customer Identification Program (CIP) | 31 C.F.R. § 1020.220 | KYC agent reads route through GLBASafeguardsGate; identifier-class records require enumerated record IDs and MFA proof | `src/finserv_agent_audit/governance/glba_safeguards_gate.py` (Tranche 2C) |
| Customer Due Diligence + Beneficial Ownership | 31 C.F.R. § 1010.230 | Sovereign Veto `BSA-EDD-BAND-UNCLEARED` reason code — agent cannot self-clear customers in the Enhanced Due Diligence risk band | ADR-0002 |
| Suspicious Activity Report workflow | 31 C.F.R. § 1020.320 (banks); § 1023.320 (broker-dealers) | SARWorkflowAudit pattern — every SAR-adjacent agent action (narrative draft, escalation, dismissal) carries a workflow-state transition logged on the hash chain | `src/finserv_agent_audit/governance/sar_workflow_audit.py` (Tranche 2C) |
| Recordkeeping and retention | 31 C.F.R. § 1010.430 | WORMLedgerStore default 7-year retention; substrate-attestation field records the storage-layer immutability posture | `src/finserv_agent_audit/governance/ledger_store_worm.py` (ADR-0013) |
| Currency Transaction Report (CTR) thresholds | 31 C.F.R. § 1010.311 | Out of scope for the agent-governance layer; the agent's CTR-relevant outputs are tagged for the firm's CTR workflow | n/a |
| Sanctions screening (OFAC parallel obligation) | 31 C.F.R. Chapter V (OFAC); not BSA per se but co-resident | DEFCON elevation on sanctions-feed outage — agent KYC clearances suspended during a known data-feed gap (see ADR-0001 example) | `src/finserv_agent_audit/governance/defcon.py` |

---

## SAR Workflow Walkthrough

The Suspicious Activity Report is the load-bearing artifact of the BSA/AML
regime. A SAR filing decision carries criminal-referral consequence, the
30-day-from-detection filing clock (60 days when no suspect is identified
under 31 C.F.R. § 1020.320(b)(3)), and a non-disclosure obligation that
binds every system that touches the workflow. The SARWorkflowAudit pattern
sits at this gate and treats every agent action as a workflow-state
transition rather than a free-text annotation.

The pattern enforces five properties:

1. **Workflow-state vocabulary.** Each agent action declares one of a closed
   set of states: `ALERT_RAISED`, `TRIAGE_IN_PROGRESS`, `NARRATIVE_DRAFTED`,
   `ESCALATED_TO_REVIEWER`, `DISMISSED_WITH_RATIONALE`, `SAR_FILED`,
   `30_DAY_CLOCK_BREACHED`. Free-text fields exist for the narrative; the
   state field does not.

2. **Bound to a case identifier.** Every transition carries a case ID that
   ties the agent action to the firm's BSA case-management system. The hash
   chain becomes the cross-reference; the firm's BSA system holds the case
   substance.

3. **Reviewer attribution on every state advance.** An agent can draft a
   narrative; an agent cannot file a SAR. The `SAR_FILED` state requires a
   named human reviewer principal in the `bypass_owner` field, sourced from
   the same Sovereign Veto pattern that gates trading and credit decisions.

4. **30-day clock enforcement.** The pattern tracks elapsed time from the
   `ALERT_RAISED` timestamp. A case approaching the 30-day threshold emits a
   `30_DAY_CLOCK_APPROACHING` event; a breached threshold emits
   `30_DAY_CLOCK_BREACHED` and elevates DEFCON. The breach itself is logged;
   the firm's BSA Officer owns the remediation.

5. **Non-disclosure scoping.** SAR-state events carry a `confidentiality:
   sar_safe_harbor` flag that downstream consumers (dashboards, exports,
   third-party analytics) must respect. The flag is a contract; enforcement
   is the consumer's responsibility — but the flag is present and the chain
   carries evidence of its presence at the time of write.

---

## AI / ML Posture Inside the BSA Program

The 2018 interagency Joint Statement framed the regulator posture: AI and ML
techniques are permitted inside the BSA program when they strengthen the
program's risk-based detection capability and do not displace the four
pillars. The operational reading is direct. An ML-based transaction-monitoring
model that fires alerts is an AML control whose validation runs under SR 11-7
(see ADR-0007). A generative-AI narrative drafter that proposes SAR
narrative text is an agent whose outputs route through the SARWorkflowAudit
pattern and require human-reviewer attribution before filing. A KYC-triage
agent that scores customer risk runs under the Sovereign Veto EDD-band
check and cannot self-clear customers above the institution's risk-band
threshold.

What the pattern stack does NOT do: it does not substitute for the BSA
Officer's accountability. The Officer remains the named human principal on
every BSA-class clearance and on every SAR filing. The pattern stack
produces the evidence that supports the Officer's program oversight; it
does not relieve the Officer of program responsibility.

---

## Gap Analysis — What This Repo Does NOT Cover

| Requirement | Gap | Guidance |
|---|---|---|
| 314(a) information-sharing requests | Out of scope; institutional process | Route requests through the firm's BSA-information-sharing workflow |
| 314(b) voluntary information sharing between institutions | Out of scope; institutional process | Requires FinCEN registration; not an agent-layer concern |
| Beneficial Ownership reporting to FinCEN (Corporate Transparency Act) | Out of scope; entity-formation overlay distinct from CDD | Separate compliance workstream |
| BSA Officer designation, training, audit cadence | Institutional artifacts, not pattern surface | Owned by the BSA program; the patterns supply evidence substrate |
| OFAC sanctions program (separate authority) | Co-resident obligation; not BSA itself | Map separately; the audit chain is the common evidentiary substrate |
| Model validation for transaction-monitoring ML | Covered by SR 11-7 overlay (ADR-0007), not BSA per se | Cross-reference ADR-0007 |
| FFIEC BSA/AML Examination Manual procedures | Examination methodology, not agent surface | The patterns produce evidence the examiner samples |
| State money-transmitter overlays (e.g., NYDFS Part 504) | Substantive overlap; distinct triggers | Map separately |

---

## References

- 31 U.S.C. § 5318(h) — Anti-Money-Laundering Programs. Retrieved
  2026-05-28 via govinfo.
- 31 C.F.R. Chapter X — FinCEN regulations (CIP, CDD, SAR, recordkeeping).
- Joint Statement on Innovative Efforts to Combat Money Laundering and
  Terrorist Financing, FinCEN / FRB / FDIC / NCUA / OCC, December 3, 2018.
  `[UNVERIFIED — primary source not fetched: socket closed]`
- ADR-0011 · BSA / AML SAR-Workflow Audit (Tranche 2C).
- ADR-0002 · Sovereign Veto.
- ADR-0001 · DEFCON State Machine.
- ADR-0013 · SEC Rule 17a-4 WORM Persistence.
- Cross-references: ADR-0007 (SR 11-7 model risk), ADR-0008 (GLBA
  Safeguards), ADR-0017 (audit-chain retention).
