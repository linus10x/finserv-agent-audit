# SOX 404 IT General Controls — Mapping for Autonomous AI Agents

This document maps the governance patterns in this repository to the four
IT General Controls (ITGC) categories that PCAOB-registered auditors apply
when evaluating Section 404 of the Sarbanes-Oxley Act (15 U.S.C. § 7262).
Any SEC-registrant adopter of this repository is operating under SOX 404;
any AI-mediated workflow that touches a financial-reporting flow — revenue
recognition, fair-value mark, customer-credit reserve, trading P&L, AML
transaction record — is in the ICFR (Internal Control over Financial
Reporting) scope and inherits the ITGC overlay.

> **Disclaimer:** Reference pattern, not legal advice and not auditor
> guidance. The firm's external auditor, internal audit, and qualified
> counsel control the methodology applied to a specific registrant. See
> repo-root [`DISCLAIMER.md`](../DISCLAIMER.md).

---

## Framework Overview

Section 404 of the Sarbanes-Oxley Act, codified at 15 U.S.C. § 7262,
requires two annual artifacts. Subsection (a) requires the SEC to establish
rules that mandate an internal-control report in every annual report; the
report states management's responsibility for "an adequate internal control
structure and procedures for financial reporting" and contains "an
assessment, as of the end of the most recent fiscal year of the issuer, of
the effectiveness of the internal control structure and procedures of the
issuer for financial reporting." Subsection (b) requires that the
registered public accounting firm "attest to, and report on, the assessment
made by the management of the issuer" — and prohibits the attestation from
being treated as a separate engagement.

PCAOB Auditing Standard 2201 (*An Audit of Internal Control Over Financial
Reporting That Is Integrated with An Audit of Financial Statements*) is the
operative auditor framework. AS 2201, in practice, has settled on four ITGC
categories: **Access Controls, Change Management, Computer Operations,
Program Development**. The same four categories appear in COBIT 2019 and in
the AICPA's Trust Services Criteria. A repository that ships an
AI-governance pattern catalog without a named mapping to these four
categories forces every SEC-registrant adopter to do the mapping privately
— and audit risk is the asymmetric cost of getting it wrong.

ADR-0012 is the architectural commitment to a single overlay document. This
mapping is the published surface that overlay produces.

---

## Primary-Source Citations

| Source | Retrieved | Status |
|---|---|---|
| 15 U.S.C. § 7262 (Cornell LII) | 2026-05-28, https://www.law.cornell.edu/uscode/text/15/7262 | Verified — § 7262(a) management assessment and § 7262(b) auditor attestation language confirmed verbatim above |
| Sarbanes-Oxley Act of 2002, Public Law 107-204 (Congress.gov PDF) | 2026-05-28, https://www.congress.gov/107/plaws/publ204/PLAW-107publ204.pdf | `[UNVERIFIED — primary source not fetched: PDF binary not parsed]`; § 7262 codified text obtained via Cornell mirror above |
| PCAOB Auditing Standard 2201 — *An Audit of Internal Control Over Financial Reporting That Is Integrated with An Audit of Financial Statements* | Referenced; consult pcaobus.org for operative text | `[UNVERIFIED — primary source not fetched]` |
| SEC Final Rule 33-8238 — Management's Reports on Internal Control Over Financial Reporting (June 2003) | Referenced | `[UNVERIFIED — primary source not fetched]` |
| COBIT 2019 (ISACA) | Referenced as informing the four-category ITGC framing | Proprietary — not a public primary source |

---

## ITGC Control Mapping Table

The table maps every Tranche 2 pattern surface to one or more ITGC
categories, names the control objective in PCAOB AS 2201 framing, and points
at the audit-evidence artifact the pattern already produces. Adopters cross-
reference the mapping in their internal-control matrix using their own
control identifiers (`ITGC-AC-007`, `ITGC-CM-014`, etc.).

| ITGC Category | Control Objective | Pattern in This Repo | Audit-Evidence Artifact | File |
|---|---|---|---|---|
| **Access Controls** | Only authorized individuals access systems and data; segregation of duties enforced; privileged access reviewed periodically | Sovereign Veto (ADR-0002) — operator-clearance gate with named bypass owner; DEFCON-1 operator-only mode | Hash-chained audit entries with `bypass_owner` field; DEFCON transition logs with named actor; per-clearance reason code | `src/finserv_agent_audit/governance/sovereign_veto.py`, `src/finserv_agent_audit/governance/defcon.py` |
| **Access Controls** | Customer-NPI access gated by named element with MFA proof | GLBASafeguardsGate (ADR-0008) — per-read authorization against named GLBA element | Per-read audit entries with actor, purpose, named element, record IDs | `src/finserv_agent_audit/governance/glba_safeguards_gate.py` (Tranche 2C) |
| **Change Management** | Application and infrastructure changes authorized, tested, approved before production | Shadow Mode Rollout (ADR-0006) — pre-promotion divergence testing | Shadow-mode divergence reports; divergence-threshold breach events | `patterns/shadow_mode.py` (planned, ADR-0006) |
| **Change Management** | AI-agent capability promotions follow documented gates | Autonomy Ladder A0→A4 promotion gates (ADR-0004) | A-level promotion ADRs; per-capability assurance-case records | `docs/autonomy_ladder.md`, `docs/adr/0004-autonomy-ladder-a0-a4.md` |
| **Change Management** | Audit-pipeline integrity attested across changes | MI Proxy verifier-integrity pattern (ADR-0015) | MI Proxy attestation records on the audit pipeline | `src/finserv_agent_audit/governance/mi_proxy.py` |
| **Computer Operations** | Production jobs run as scheduled; failures detected and resolved | DEFCON state machine (ADR-0001) — system-wide operational posture with hysteresis | DEFCON transition timeline; per-transition triggering condition | `src/finserv_agent_audit/governance/defcon.py` |
| **Computer Operations** | Records preserved per retention schedule; backups and recovery tested | Hash-chained audit ledger (ADR-0003) with WORM persistence (ADR-0013) | Ledger retention reports; WORM-store retention attestation per entry | `src/finserv_agent_audit/governance/ledger_store_worm.py`, `src/finserv_agent_audit/schemas/audit_event.py` |
| **Computer Operations** | Time-source integrity for audit-chain evidence | RFC 3161 timestamp source (ADR-0014) — witness-anchor receipts on chain-head digests | RFC 3161 timestamp tokens; witness-anchor receipts | `src/finserv_agent_audit/governance/rfc3161_codec.py`, `src/finserv_agent_audit/governance/witness_anchor.py` |
| **Program Development** | New systems and major changes follow documented SDLC with testing and approval | Autonomy Ladder governance gates (ADR-0004); CI matrix with mypy strict + branch-coverage threshold | A-level promotion records; CI green status per commit; coverage reports | `.github/workflows/ci.yml`, `pyproject.toml` |
| **Program Development** | Third-party model and dependency onboarding gated | Vendor Score Gate (ADR-0016) — third-party dependencies carry vendor-score and renewal cadence | Vendor onboarding decision logs; downgrade-triggered DEFCON elevations | `src/finserv_agent_audit/governance/vendor_score_gate.py` (Tranche 2C) |
| **Program Development** | Audit-pipeline timestamp integrity preserved across releases | Persistence / Witness / Timestamp protocol (ADR-0014) | Witness-anchor receipts on chain-head digests; per-release attestation | ADR-0014 |

---

## ITGC Category Walkthrough

### Access Controls

The access-control overlay treats the AI agent as a first-class authorized
user whose every privileged action carries a recorded principal, a recorded
reason code, and (for human-bypass paths) a named human owner. The Sovereign
Veto pattern produces a structured reason code on every veto and on every
veto clearance; reason codes are the regulator-readable explanation. DEFCON
transitions to ALERT or HALT levels carry the named actor who initiated the
transition. The GLBASafeguardsGate (Tranche 2C) extends the same discipline
to customer-NPI reads: per-read authorization against a named GLBA
authorizing element, MFA proof for human-actor reads, IdP-verified principal
for agent-actor reads.

What an AS 2201 walkthrough samples here: a population of privileged-action
audit entries, an inspection that each entry carries a principal and a
reason code, and a test that segregation-of-duties properties hold (an
agent cannot clear its own veto; a SAR-class workflow advance to `SAR_FILED`
requires a human reviewer).

### Change Management

Change Management covers both code-promotion and capability-promotion.
Code-promotion is the conventional CI/CD gate — the repository's `.github/
workflows/ci.yml` enforces mypy strict, ruff, pytest, and a branch-coverage
threshold on every commit, and the contributing guide requires an ADR row on
any pattern that materially changes the audit-evidence shape.
Capability-promotion is the Autonomy Ladder construct: an agent moving from
A2 to A3 on a given decision class is a change, and the change requires a
written assurance case in an A-level promotion ADR. Shadow Mode Rollout
(ADR-0006) supplies the pre-promotion divergence evidence that an A-level
promotion ADR consumes.

What an AS 2201 walkthrough samples here: the population of A-level
promotion ADRs since the prior audit, the divergence reports referenced by
each, and a test that no in-scope agent capability reached production
without an ADR.

### Computer Operations

Computer Operations is the substrate-integrity overlay. DEFCON state-machine
transitions are the system-wide operational posture; the audit chain
records every transition; the WORM-backed ledger store guarantees the
transitions cannot be silently overwritten. The witness-anchor pattern
(ADR-0014) produces RFC 3161 timestamp tokens on chain-head digests, which
bound the substitution window for any out-of-band tampering attempt.

What an AS 2201 walkthrough samples here: the audit-chain retention
configuration on the WORM-backed ledger, the substrate-attestation field on
a sample of audit entries, and a verification that the chain validates from
genesis through chain-head as of the test date.

### Program Development

Program Development covers the SDLC for the patterns themselves and for the
third-party dependencies they pull in. The Vendor Score Gate (ADR-0016)
treats every dependency as a vendor whose score and renewal cadence are
audit-evidence artifacts. The Autonomy Ladder governance gates extend the
SDLC discipline to AI-capability promotions. The MI Proxy verifier-integrity
pattern (ADR-0015) attests that the audit pipeline itself has not been
substituted with a tampered verifier.

What an AS 2201 walkthrough samples here: the vendor-score reports for
in-scope dependencies, the MI Proxy attestation records, and the A-level
promotion ADRs as the SDLC artifacts for AI-capability changes.

---

## What This Overlay Does NOT Do

- It does not prescribe a test-of-design or test-of-operating-effectiveness
  procedure. Those belong to the firm's internal-audit and external-audit
  teams.
- It does not substitute for SOC 1 Type 2 reports on third-party providers
  in the ICFR scope. Third-party SOC 1 reports remain a separate
  procurement requirement.
- It does not map to COSO 2013 entity-level controls. The COSO mapping is
  broader than ITGC and warrants a separate document if buyer demand
  surfaces.
- It does not address SOX 302 (CEO/CFO certifications), SOX 906 (criminal
  penalties), or SOX Title VIII (whistleblower protections). The scope here
  is ICFR ITGC under Section 404.

---

## Gap Analysis — What This Repo Does NOT Cover

| ITGC Concern | Gap | Guidance |
|---|---|---|
| Entity-level controls (COSO 2013 framework) | Not mapped; broader than ITGC | Separate document; the audit chain is the common evidentiary substrate |
| Application controls (configurable controls inside the financial reporting application) | Out of scope; agent-layer patterns, not application-layer | Map the financial-reporting application's configurable controls separately |
| SOC 1 Type 2 on third-party service providers | Procurement artifact, not pattern surface | Vendor Score Gate enforces operational posture; SOC 1 is contracted separately |
| Test-of-design / test-of-operating-effectiveness procedures | Auditor methodology, not pattern surface | Owned by internal audit and external auditor |
| Walk-through documentation | Auditor methodology | Owned by internal audit |
| Deficiency / significant deficiency / material weakness classification | Auditor judgment | Owned by external auditor |

---

## References

- 15 U.S.C. § 7262 — Management Assessment of Internal Controls. Retrieved
  2026-05-28 via Cornell LII mirror.
- Sarbanes-Oxley Act of 2002, Public Law 107-204, Section 404.
  `[UNVERIFIED — primary source not fetched]`
- PCAOB Auditing Standard 2201. `[UNVERIFIED — primary source not fetched]`
- SEC Final Rule 33-8238. `[UNVERIFIED — primary source not fetched]`
- COBIT 2019 — control framework informing ITGC categorization.
- ADR-0012 · SOX 404 ITGC Overlay.
- ADR-0002 · Sovereign Veto. ADR-0001 · DEFCON State Machine. ADR-0003 ·
  Hash-Chain Audit. ADR-0004 · Autonomy Ladder. ADR-0006 · Shadow Mode
  Rollout. ADR-0013 · SEC Rule 17a-4 WORM Persistence. ADR-0014 ·
  Persistence / Witness / Timestamp Protocol. ADR-0015 · MI Proxy
  Verifier-Integrity. ADR-0016 · Vendor Score Gate.
- Cross-references: ADR-0008 (GLBA Safeguards), ADR-0011 (BSA / AML),
  ADR-0017 (audit-chain retention).
