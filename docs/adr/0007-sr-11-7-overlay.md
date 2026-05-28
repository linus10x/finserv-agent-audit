# ADR-0007 · SR 11-7 Three-Lines-of-Defense Overlay for Autonomous Agent Patterns

**Status:** Accepted
**Date:** 2026-05-28
**Decider:** Kunjar Bhaduri
**Repo:** finserv-agent-audit v1.1

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel. No attorney-client relationship is formed by use of this ADR. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).
>
> **Citation update (April 17, 2026):** SR 11-7 was superseded for new examination cycles and OCC Bulletin 2011-12 was rescinded by the joint OCC / FRB / FDIC issuance of April 17, 2026 (OCC counterpart: **OCC Bulletin 2026-13, _Model Risk Management: Revised Guidance_**), which **explicitly excludes generative and agentic AI from scope**, deferring those workloads to a forthcoming joint RFI. The three-lines-of-defense overlay this ADR documents survives as conceptual scaffolding; the binding citation is in flux. See [`docs/interagency_mrm_2026_overlay.md`](../interagency_mrm_2026_overlay.md) for the framework's pre-RFI positioning.

## Context

SR 11-7 — *Supervisory Guidance on Model Risk Management*, jointly issued by the Federal Reserve and the OCC on April 4, 2011 — is the foundational US supervisory expectation for model risk at large bank holding companies. It was written for a world of quarterly-recalibrated credit, market, and operational-risk models maintained by named model owners with named validators. It assumes a model has a stable specification, a documented dataset, a defined inference path, and a quarterly revalidation cadence.

An autonomous AI agent breaks every one of those assumptions. It retrains weekly or daily. It ingests vendor scores hourly. It executes decisions per minute. It composes outputs from multiple sub-models, retrieval layers, and tool calls in a single inference. Its "specification" is a prompt and a tool registry, both of which can be revised without a model-inventory entry. A traditional SR 11-7 validation cadence cannot keep up; without an explicit overlay, every adopting institution invents its own mapping, which is exactly the inconsistency that triggers MRA (matters requiring attention) and MRIA (matters requiring immediate attention) findings during examination cycles.

This ADR is the overlay. It exists so that an examiner asking "show me how your AI-agent governance satisfies SR 11-7" receives a single artifact, dated and versioned, mapping every pattern in this repository to one or more of the three lines of defense defined under SR 11-7 and the broader OCC Heightened Standards (12 CFR Part 30 Appendix D). It is the foundational FSI ADR for this repository; all other ADRs assume its existence.

## Decision

Adopt an explicit overlay table. Each governance pattern in this repository is mapped to one or more SR 11-7 lines of defense, with a one-clause description of how that pattern serves that line. The mapping is normative: when a new pattern ADR is added, the overlay must be updated in the same PR. CI enforces table currency.

The three lines of defense, per SR 11-7 Section VI and consistent with OCC Heightened Standards:

- **First line — Model development, implementation, and use** — owned by the business unit that runs the agent in production
- **Second line — Model validation and governance** — owned by an independent model-risk management function with sufficient skill, authority, and standing
- **Third line — Internal audit** — owned by internal audit, which assesses whether the first and second lines are operating as designed

### Mapping table

| Pattern | First line (model development, implementation, use) | Second line (model validation, governance) | Third line (internal audit) |
|---|---|---|---|
| **DEFCON state machine** (ADR-0001) | Owns the state-transition logic; declares operating posture per decision class | Validates calibration of monitor-driven transition thresholds; reviews time-in-state metrics quarterly | Tests evidence that DEFCON transitions were honored across the audit ledger window |
| **Sovereign Veto** (ADR-0002) | Implements the gate; owns the operator-clearance workflow and the override path | Validates that the veto rule set covers the risk taxonomy; reviews override-frequency and override-rationale samples | Confirms every override has a logged rationale and an authorized signer; tests segregation of duties |
| **Hash-chain Audit Ledger** (ADR-0003) | Writes entries on every decision; owns retention and replay tooling | Validates ledger schema completeness; confirms ledger captures the inputs needed for back-testing and recomputation | Performs chain-integrity verification; tests that ledger entries reconcile to downstream regulatory reports |
| **Autonomy Ladder A0–A4** (ADR-0004) | Declares the autonomy class per decision type; documents promotion criteria | Reviews promotion evidence and signs off on A2 → A3 and A3 → A4 transitions; maintains the model-inventory entry | Tests that the declared autonomy class matches observed behavior on the audit ledger |
| **EU AI Act Mapping** (ADR-0005) | Maintains the article-to-code reference for in-scope decisions | Reviews mapping annually against the consolidated Act text and harmonized standards | Tests that examiner-facing artifacts (Art. 11 documentation, Art. 12 logs) are produced on request without extraction effort |
| **Shadow Mode Rollout** (ADR-0006) | Runs the shadow path; produces the divergence report | Reviews divergence statistics; sign-off authority on promotion gates for credit, trading, and AML surfaces | Tests that no in-scope capability reached production without a complete shadow-period record |
| **Vendor Score Gate** (planned, ADR-0010) | Calls the vendor; records provenance, version, and cache state | Owns the vendor-model inventory entry; reviews vendor SR 11-7 conformance attestations | Tests that vendor-derived decisions carry traceable provenance to a specific vendor model version |
| **Model Inventory** (planned, ADR-0011) | Submits entries for every agent component, sub-model, and tool | Maintains the inventory of record; tiers models by materiality; sets revalidation cadence | Tests that every production decision can be traced to an inventoried model, including LLM versions and prompt revisions |
| **Disparate-Impact Monitor** (planned, ADR-0012) | Emits cohort-stratified outcome metrics on every credit and pricing decision | Reviews monitor thresholds; sign-off authority on Fair Lending findings | Tests that observed cohort divergence triggered the documented escalation path |
| **Incident Replay Harness** (planned, ADR-0013) | Reconstructs any decision from the hash-chain audit ledger | Validates that replay produces the same output as production for in-scope decision classes | Tests replay completeness on a randomized sample during examination cycles |

The table is the contract. A pattern that cannot be placed on the table is not ready to ship; a line of defense that has no pattern in a given column is a gap and is tracked as such.

## Alternatives Considered

- **Internal mapping doc (Confluence page, SharePoint).** Rejected because it is not versioned with the code, not reviewable through PR, and not citable in examination response. The artifact must travel with the repository.
- **Per-pattern individual mapping inside each ADR.** Rejected because it produces drift — the cross-pattern view is the artifact examiners want, and reconstructing it from seven scattered ADRs is exactly the work this overlay exists to eliminate.
- **Informal one-page summary in README.** Rejected because the README is not versioned at the granularity examiners need, and because the three-lines structure does not fit a README format without losing fidelity.
- **Defer until first examination request.** Rejected because the existence of the overlay is itself an expected control under OCC Heightened Standards; absence is a finding.

## Consequences

**Positive.** Examination response collapses from a multi-week reconstruction to a single-document handoff plus code references. The cross-pattern view surfaces structural gaps that single-pattern reviews miss (e.g., a pattern with strong first-line ownership but no second-line validation surface). New ADRs land with their line-of-defense mapping declared upfront, which prevents shipping a pattern whose validation path has not been thought through.

**Negative.** The overlay must be updated in every new-pattern PR. A pattern PR that does not update the overlay is an incomplete PR. Mitigation: CI doc-linter checks that every ADR-NNNN has a row in this table.

**Operational.** Second-line ownership requires a model-risk management function with sufficient skill to evaluate AI-agent specifications, including LLM-based components. Institutions without that capacity must build it; this ADR makes the requirement explicit rather than implicit.

## Regulatory Mapping

- **SR 11-7** — *Supervisory Guidance on Model Risk Management*, Board of Governors of the Federal Reserve System, April 4, 2011, Sections III (Model Development, Implementation, and Use), IV (Model Validation), V (Model Implementation, Use, and Change), VI (Governance, Policies, and Controls)
- **OCC Bulletin 2011-12** — *Sound Practices for Model Risk Management* (rescinded by OCC Bulletin 2026-13, April 17, 2026, which excluded generative + agentic AI from scope; see [`docs/interagency_mrm_2026_overlay.md`](../interagency_mrm_2026_overlay.md))
- **OCC Comptroller's Handbook — Model Risk Management** (August 2021 booklet) — examination procedures for SR 11-7 compliance `[UNVERIFIED — booklet revision date not fetched]`
- **OCC Heightened Standards — 12 CFR Part 30 Appendix D** — three-lines-of-defense framework for large insured national banks, federal savings associations, and federal branches
- **FRB SR 15-18** — Interagency advisory on independence of risk-management functions (clarifies second-line independence expectations) `[UNVERIFIED — SR letter number per secondary reference]`
- **Basel BCBS 239** — risk-data aggregation and reporting principles (intersect with the audit-ledger pattern)

## Pre-mortem

What fails if the overlay drifts:

1. **A pattern ships without an overlay row.** Detection: CI doc-linter parses `docs/adr/` for new ADR-NNNN filenames and asserts a matching row exists in this table. CI fails the PR.
2. **Second-line ownership is named but not staffed.** Detection: a pattern with second-line responsibility records the named owner on the audit ledger; an unsigned validation report after the cadence window triggers a DEFCON-4 escalation per ADR-0001.
3. **Third-line testing is theoretical only.** Detection: internal audit's annual workpapers reference specific audit-ledger sample IDs; absence of sampled IDs is itself a finding.
4. **The overlay diverges from supervisory guidance after a 2027 SR letter revision.** Detection: an annual review by maintainers cross-checks Section references against the current published guidance; a superseding ADR is filed when material drift is identified, and this ADR is marked `Superseded by ADR-NNNN`.
5. **A vendor-supplied component (LLM, scoring model) is treated as outside the overlay.** Detection: the Vendor Score Gate (ADR-0010) requires an overlay row even for vendor components; vendor-attested SR 11-7 conformance is the second-line evidence.

## Reversibility

Moderate. The overlay is documentary and can be withdrawn without code change, but the dependent ADRs (0001–0006 and the planned 0008–0013) reference this overlay as their validation contract. Withdrawal requires either replacement with an equivalent framework (NIST AI RMF expressed as three lines, for example) or explicit acceptance by institution risk leadership that the validation contract is now informal. The cost of reversal is structural, not tactical.

## Cross-references

- ADR-0001 (DEFCON state machine) — first-line operating posture; second-line threshold calibration
- ADR-0002 (Sovereign Veto) — first-line gate; second-line rule-set review; third-line override testing
- ADR-0003 (Hash-chain audit ledger) — evidence substrate for all three lines
- ADR-0004 (Autonomy Ladder) — second-line sign-off on autonomy-class promotions
- ADR-0005 (EU AI Act Mapping) — companion overlay for EU deployer obligations; Art. 17 quality-management aligns to second-line ownership here
- ADR-0006 (Shadow Mode Rollout) — second-line validation surface for new and changed models
- Planned: ADR-0010 (Vendor Score Gate), ADR-0011 (Model Inventory), ADR-0012 (Disparate-Impact Monitor), ADR-0013 (Incident Replay Harness)
- `docs/eu_ai_act_mapping.md` — reader-friendly EU summary
- `docs/autonomy_ladder.md` — autonomy class definitions
