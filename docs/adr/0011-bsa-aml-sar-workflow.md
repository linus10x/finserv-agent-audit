# ADR-0011 · BSA / AML — SARWorkflowAudit

**Status:** Accepted · FSI-native
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel. No attorney-client relationship is formed by use of this ADR. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

## Context

The Bank Secrecy Act (BSA) Suspicious Activity Report (SAR) regime is the most consequential operator-facing AI surface in financial-services compliance. A SAR is the institution's formal communication to FinCEN that a transaction or series of transactions may involve illegal activity; the operative obligation under 31 U.S.C. § 5318(g) and 31 C.F.R. § 1020.320 (banks) plus parallel rules at § 1023.320, § 1024.320, § 1025.320, and § 1026.320 (broker-dealers, MSBs, mutual funds, futures commission merchants) is to file within 30 calendar days of initial detection of facts that may constitute a basis for filing (extendable to 60 if no suspect identified). The supervisory cost of getting this wrong runs in both directions: under-filing produces enforcement actions and personal liability for the BSA officer; over-filing produces dilution of intelligence value to FinCEN and supervisory criticism for an unfocused program.

Three artifacts frame the operator-side AI-governance gap this pattern addresses:

- **FinCEN / Federal Reserve / OCC / FDIC / NCUA joint statement on innovative efforts to combat money laundering and terrorist financing (December 3, 2018).** Encourages use of innovative technology in BSA/AML programs while affirming that the existing supervisory framework applies. `[UNVERIFIED — primary source not re-fetched; cited from FinCEN press release of the same date.]`
- **FinCEN / OCC / Federal Reserve / FDIC / NCUA interagency statement on model risk management for BSA/AML compliance (April 9, 2021).** Clarifies that BSA/AML models are subject to model-risk-management principles consistent with SR 11-7 / OCC 2011-12, while not imposing a separate regime. `[UNVERIFIED — date and signatory list to be confirmed before publication.]`
- **Civil money penalties for SAR-program failures.** Multiple multi-million-dollar consent orders over the last decade have named transaction-monitoring system failures (alert tuning, model validation, governance) as the underlying control gap; specific institution citations omitted here to avoid claim-grade precision without re-fetch.

An autonomous-agent stack changes the operational shape of three SAR-program activities: (i) **alert triage** — the agent reviews and dispositions transaction-monitoring alerts; (ii) **narrative auto-population** — the agent drafts the SAR narrative for analyst review; (iii) **flagged-entity scoring** — the agent contributes a risk score that escalates or de-escalates suspect entities for human review. Each of these creates a chain of AI-influenced inputs to a decision (file / no file, narrative content, suspect prioritization) that the institution must be able to defend to examiners with a record of who decided what, when, on what input, with what model, under what supervisory regime.

The pattern that works is **per-event audit-chain entries for every AI-influenced SAR-workflow decision, structured so that the chain alone reconstructs the agency-relevant story without forensic recovery.**

## Decision

Every agent action that contributes to a SAR-workflow decision routes through the **SARWorkflowAudit** module before the decision is recorded. The audit emits a typed entry to the hash-chain audit ledger (ADR-0003) for each of the three named decision surfaces. The audit is **emit-mandatory**: if the audit entry cannot be written, the sovereign veto (ADR-0002) blocks the underlying decision.

### The data model

```python
class SARDecisionSurface(Enum):
    ALERT_DISPOSITION = "alert_disposition"      # close / escalate / case
    FILE_DECISION = "file_decision"              # file / no-file recommendation
    NARRATIVE_AUTO_POPULATION = "narrative_auto" # narrative draft contribution
    FLAGGED_ENTITY_SCORE = "flagged_entity_score"
    EXTENSION_DECISION = "extension_decision"    # 30-day extend to 60-day

class SARActionTaken(Enum):
    CLOSE = "close"
    ESCALATE_TO_ANALYST = "escalate_to_analyst"
    OPEN_CASE = "open_case"
    RECOMMEND_FILE = "recommend_file"
    RECOMMEND_NO_FILE = "recommend_no_file"
    NARRATIVE_DRAFTED = "narrative_drafted"
    SCORE_EMITTED = "score_emitted"

@dataclass(frozen=True)
class SARWorkflowEntry:
    entry_id: str
    surface: SARDecisionSurface
    action: SARActionTaken
    case_id: str
    alert_ids: tuple[str, ...]
    suspect_party_ids: tuple[str, ...]
    model_id: str
    model_version: str
    model_validation_id: str            # SR 11-7 / 2021 interagency statement artifact
    detection_anchor_timestamp: datetime  # the 30-day clock starts here
    decision_timestamp: datetime
    human_reviewer: str | None          # principal if a human approved or co-signed
    narrative_hash: str | None          # hash of narrative text contributed
    score_value: float | None
    score_factors: tuple[str, ...]      # feature ids that drove the score
    rationale: str                      # specific · not generic
```

### The audit-emit veto

Vetoes fire on any of:

1. **`BSA-AUDIT-WRITE-FAILED`** — the audit ledger could not accept the entry. The underlying decision is blocked.
2. **`BSA-DETECTION-ANCHOR-MISSING`** — `detection_anchor_timestamp` is null. Without an anchor the 30/60-day filing clock cannot be tracked.
3. **`BSA-VALIDATION-MISSING`** — `model_validation_id` does not resolve to an active model-validation artifact per the 2021 interagency statement.
4. **`BSA-RATIONALE-VAGUE`** — `rationale` matches the generic-rationale blocklist ("model decision", "score below threshold", "no further action warranted").
5. **`BSA-NARRATIVE-UNHASHED`** — `surface == NARRATIVE_AUTO_POPULATION` and `narrative_hash` is null. The exact text the agent contributed must be hashable and recoverable.
6. **`BSA-EXTENSION-UNJUSTIFIED`** — `surface == EXTENSION_DECISION` and the rationale does not name the specific reason no suspect has yet been identified (the regulatory predicate for the 30-to-60-day extension).

### Reconciliation to the FinCEN filing

The institution's SAR e-filing system reads from the audit chain. Every filed SAR carries a chain-anchor sigil that resolves to the full SARWorkflowAudit entry set for that case. A FinCEN or supervisory inquiry on a specific filing returns the entire AI-influenced decision history with one query.

## Alternatives Considered

- **Audit only the file/no-file decision.** Rejected: the upstream alert-disposition and scoring decisions are exactly the AI surface examiners ask about. Auditing only the terminal decision recreates the "black box" supervisory criticism the joint statements are designed to prevent.
- **Audit narratives only when filed.** Rejected: a narrative the agent drafted that was overwritten by a human is exactly the artifact a supervisory review wants to see. Drop-on-overwrite destroys the relevant evidence.
- **Sampled audit (e.g., 5% of decisions).** Rejected: SAR-program supervisory review is case-specific, not population-statistical. Sampling cannot answer "show me what the system did on case X."

## Consequences

**Positive.** Every AI-influenced contribution to a SAR-workflow decision is recorded, hash-chained, attributable to a model version validated under the institution's MRM regime, and reconcilable to the filed SAR (if any). The 30/60-day filing clock is anchored to the actual detection event rather than to a downstream workflow milestone. An examiner asking "why did this alert close" or "who drafted this narrative" or "why was no-file the recommendation" receives a deterministic answer from the chain.

**Negative.** Storage cost on the audit ledger grows with alert volume; the audit-emit-mandatory veto means the ledger is on the hot path. Mitigation: the ledger is the project's WORM store (ADR-0003 / `ledger_store_worm.py`) and is engineered for the write-heavy workload; per-entry size is bounded.

**Operational.** The BSA officer gains an evidentiary backbone that survives staff turnover and vendor changes. Supervisory examination cycles compress because the audit chain answers the routine questions without analyst reconstruction.

## Regulatory Mapping

- **BSA, 31 U.S.C. § 5318(h).** Anti-money-laundering program requirement — the statutory mandate for the program of which SAR filing is a component. The audit chain is the program's evidentiary backbone for AI-influenced decisions.
- **SAR rule, 31 C.F.R. § 1020.320 (banks)** plus parallel rules § 1023.320 (broker-dealers), § 1024.320 (mutual funds), § 1025.320 (insurance), § 1026.320 (FCMs). 30-day filing window from initial detection; 60-day extension permitted if no suspect identified. The `detection_anchor_timestamp` enforces the clock's start; the `EXTENSION_DECISION` surface forces an articulated rationale for the extension.
- **FFIEC BSA/AML Examination Manual.** Transaction-monitoring system expectations including alert tuning, model validation, and governance. The audit chain produces the examination-ready evidence trail.
- **Interagency statement on model risk management for BSA/AML compliance (April 9, 2021).** Confirms SR 11-7 / OCC 2011-12 principles apply to BSA/AML models. `[UNVERIFIED — confirm citation before publication.]` The `BSA-VALIDATION-MISSING` veto operationalizes the model-validation expectation at decision time.
- **Joint statement on innovative efforts to combat money laundering and terrorist financing (December 3, 2018).** Encourages innovation while affirming the supervisory framework. `[UNVERIFIED — confirm citation before publication.]` The SARWorkflowAudit pattern is the operator-side evidence that innovation is operating within the framework.
- **31 U.S.C. § 5318(g)(2) safe harbor.** Voluntary or required SAR filers are protected from civil liability for the disclosure itself; the safe harbor presupposes good-faith filing. The audit chain evidences good faith.

## Pre-mortem

The way this gate fails is **rationale-text inflation**: agents and engineers cycle a small set of approved rationale templates that pass the vagueness blocklist without conveying specific facts. Mitigation: the Compliance function samples chain entries monthly; rationale-string entropy is a monitored metric; a rationale string that recurs on >2% of entries is treated as a blocklist candidate.

The other failure mode is **clock-anchor manipulation**: a `detection_anchor_timestamp` is set to a later workflow event rather than the true initial detection, buying program time on the 30-day window. Mitigation: the anchor is sourced from the upstream transaction-monitoring system's alert-creation event by reference, not by free assignment; manual override of the anchor requires BSA-officer sign-off and is itself a chain entry.

## Reversibility

Low. Once the SARWorkflowAudit module is in the agent compose order, disabling it removes the evidentiary backbone supervisory examination relies on. Disabling is itself a chain entry and forces the program to DEFCON-2 (ADR-0001) on all SAR-workflow surfaces — read-only mode, no AI-influenced SAR decisions until the audit is restored.

## Cross-references

- ADR-0001 (DEFCON State Machine) — audit-disable forces DEFCON-2 on SAR surfaces
- ADR-0002 (Sovereign Veto) — the enforcement layer
- ADR-0003 (Hash-chain Audit) — the chain receives every SARWorkflowEntry
- ADR-0008 (GLBA Safeguards) — customer NPI read into the SAR workflow is GLBA-gated with elevated purpose specificity
- ADR-0009 (FCRA / Reg V Adverse Action) — distinct decision surface; SAR processing does not itself trigger FCRA adverse-action notice obligations, but downstream account actions may

## Implementation status

**Deferred to Tranche 2C.** The reference implementation lands at `src/finserv_agent_audit/governance/sar_workflow_audit.py`. This ADR is the design contract; the module is not yet committed.
