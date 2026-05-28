# Big-4 Engagement Letter Exhibit — AI / Agentic-AI Assurance

**Status:** v1.2.0-draft · Last reviewed: 2026-05-28.
**Format:** Drop-in exhibit for attachment to a Statement of Work between a Big-4 (or comparable assurance) firm and an audit client whose AI / agentic-AI surface uses `finserv-agent-audit` v1.x.

> **Patterns are software, not legal advice.** This exhibit is a starting-point template; firm counsel + engagement-team leadership must finalize the language for the specific audit, client, and jurisdiction. See repo-root [`DISCLAIMER.md`](../DISCLAIMER.md).

---

## Purpose and Scope

This exhibit is designed for attachment to engagements conducted under the PCAOB's auditing standards, including **AS 2201** (an audit of internal control over financial reporting integrated with an audit of financial statements) and **AS 2101** (audit planning), as well as integrated SOC 1 / SOC 2 / SOX 404 engagements where the client's financial-reporting or trust-services environment includes AI or agentic-AI systems.

The PCAOB amendments to AS 2201 and AS 2101 that take effect for audits of financial statements for fiscal years beginning on or after December 15, 2026 [UNVERIFIED — confirm exact effective date and citation against the PCAOB final rule] include sharpened expectations on the auditor's treatment of automated controls and the auditor's evaluation of management's risk-assessment process when complex IT or AI systems are involved.

The exhibit translates those expectations into the control points, evidence requests, and test procedures the engagement team will use when the client has deployed `finserv-agent-audit` v1.x as part of its agentic-AI governance baseline.

---

## Section 1 — Client Framework Declaration

> *(Engagement team: complete with the client controller / Chief Risk Officer / Chief AI Officer before fieldwork begins.)*

| Field | Value |
|---|---|
| Client legal name |   |
| Client primary federal regulator (OCC / FDIC / FRB / NCUA / SEC / state-banking-dept) |   |
| Audit-period coverage (start / end) |   |
| Framework deployed | `finserv-agent-audit` |
| Framework version (e.g. `v1.1.0`) |   |
| Framework licensing scope (MIT, no SaaS dependency) | MIT — no SaaS dependency; no vendor lock-in |
| AI use scope (decision classes covered) |   |
| Number of agents in production at the start of audit period |   |
| Number of third-party AI scorers in production at the start of audit period |   |
| Audit-chain ledger backend in production (`JsonlLedgerStore` / `SqliteLedgerStore` / `WORMLedgerStore` / deployer-supplied Protocol) |   |
| Witness register backend in production (`RekorWitness` / `OpenTimestampsWitness` / none / deployer-supplied) |   |
| MIProxy backend in production (`LocalMIProxy` / SLSA / in-toto / deployer-supplied) |   |
| TimestampSource in production (`LocalClock` / `RFC3161Source` + TSA name) |   |
| Pre-examination self-assessment completed (date of most-recent completion) |   |
| Materiality threshold for IT controls testing (per engagement letter) |   |

---

## Section 2 — Auditor Scope

The engagement team will test the operating effectiveness of the following control areas during the audit period stated in Section 1. Testing follows the PCAOB risk-based approach: areas with higher inherent risk (LLM-based decisioning, third-party model dependency, agentic-AI autonomy bands A2 and above) receive expanded sample sizes and walk-through testing; areas with lower inherent risk (A0 advisory-only use) receive abbreviated procedures.

In-scope control areas:

1. **Audit-chain integrity** — the integrity of the audit chain as a system of record for AI / agentic-AI activity.
2. **Model risk management (MRM)** — the operation of the model inventory, the validation lifecycle, and the second-line effective-challenge process.
3. **Third-party AI risk** — the operation of vendor-score capture, drift detection, and the vendor-review queue.
4. **Fair lending and adverse action** — the operation of the adverse-action gate, the reason-code traceability, and the disparate-impact testing cadence.
5. **BSA / AML SAR workflow** — the operation of the SAR-workflow audit trail, the 30-day (and 60-day extension) deadline tracking, and the § 5318(g)(2) safe-harbor metadata capture.
6. **Best-interest recommendation control** — the operation of the SEC Reg-BI care-obligation gate for in-scope broker-dealer / RIA use cases.
7. **Verifier integrity** — the attestation of the audit-chain verifier binary itself (MI Proxy).
8. **Incident response** — the operation of the AI / agentic-AI-specific incident-response procedure during the audit period.

Out-of-scope (explicitly noted to manage expectations):

- The institution's underlying model accuracy, fairness, or training-data lineage (these are MRM-function responsibilities, not IT-control testing).
- The vendor's underlying model architecture, training data, or fine-tuning data (these are vendor due-diligence responsibilities).
- The legal effectiveness of any contract clause (engaged counsel responsibility).
- The institution's compliance with any law or regulation as a legal opinion (engaged counsel responsibility).

---

## Section 3 — Control Points and Test Procedures

Each control point below maps a `finserv-agent-audit` v1.1 module to (a) the AS 2201 control category, (b) the typical Big-4 evidence-request line item, and (c) the sample test procedure the engagement team will execute.

| Control Point | Module (canonical path) | AS 2201 Category | Evidence Request | Sample Test Procedure |
|---|---|---|---|---|
| Audit chain integrity | `finserv_agent_audit.governance.audit_chain.AuditChain` | IT general control (ITGC) — audit-trail integrity | Production chain export (JSONL or backend-native); recent `verify_strict()` log; verifier attestation | Re-execute `AuditChain.verify_strict()` in client's presence; mutate one byte of a non-production copy; observe `AuditChainTamperError` raise |
| Sequence monotonicity | `finserv_agent_audit.governance.audit_chain.AuditChain.verify_strict` | ITGC — change management | Verify-strict run output | Pull random 30-entry window; confirm contiguous sequence numbers; attempt insert at gap on non-production copy; observe rejection |
| WORM / substrate-layer immutability | `finserv_agent_audit.governance.ledger_store_worm.WORMLedgerStore` | ITGC — recordkeeping | S3 Object Lock policy export; bucket configuration; sample `WORMViolationError` from non-production | Attempt overwrite of a chain entry against client's substrate; observe substrate-level AccessDenied; observe framework-level `WORMViolationError` on non-production demonstration |
| External witness anchor | `finserv_agent_audit.governance.witness_anchor.anchor_to_witness` | ITGC — third-party integrity | Recent `WITNESS_ANCHOR` chain entries; witness-cron schedule; alerting destination on failure | Pick last 3 `WITNESS_ANCHOR` entries; verify receipt against Rekor / OpenTimestamps public log; confirm cron cadence + failure alerting |
| Verifier attestation | `finserv_agent_audit.governance.mi_proxy.LocalMIProxy.verify_integrity` | ITGC — privileged-software change management | Most-recent attestation receipt; signing-key custody documentation | Re-run attestation on production verifier; swap verifier source in non-production environment; observe `IntegrityVerificationError` raise |
| Model inventory completeness | `finserv_agent_audit.governance.model_inventory.ModelInventory.query_by_status` | Process-level control — IT inventory | Full `query_by_status()` dump for each status | Spot-check 5 production models against client's model-risk inventory of record; confirm version, owner, validator, validation date match |
| Model validation lifecycle | `finserv_agent_audit.governance.model_inventory.ModelInventory.transition_status` | Process-level control — validation evidence | `MODEL_VALIDATED` chain entries; validation memos for spot-checked models | Tie 3 randomly-selected `MODEL_VALIDATED` chain entries to second-line validation memos; confirm signature, date, and IN_VALIDATION → APPROVED_FOR_PRODUCTION transition timing |
| Model overdue tracking | `finserv_agent_audit.governance.model_inventory.ModelInventory.query_overdue` | Process-level control — recertification | `query_overdue()` output | Confirm zero overdue models; if non-zero, request remediation memo + risk-committee notification for each |
| Vendor score capture | `finserv_agent_audit.governance.vendor_score_gate.InMemoryVendorScoreGate.emit` | Process-level control — third-party | `VENDOR_SCORE_RECORDED` count per vendor; sample chain entries | Pick top 3 vendors by call volume; confirm chain entries match vendor's own logs (where available); confirm `vendor_class` is set correctly |
| Vendor drift detection | `finserv_agent_audit.governance.vendor_score_gate.VendorScoreDriftDetected` | Process-level control — third-party model risk | `VENDOR_SCORE_DRIFT_DETECTED` entries for audit period | Tie each drift entry to vendor-review ticket; confirm disposition; if vendor change accepted, confirm re-validation memo |
| Adverse-action reason-code traceability | `finserv_agent_audit.governance.adverse_action_gate.AdverseActionGate` | Process-level control — consumer-facing communication | `ADVERSE_ACTION_TAKEN` chain entries; sample notices | Spot-check 10 entries; pull corresponding consumer notice; confirm reason codes are specific, accurate, and traceable to the decision factors (per CFPB Circular 2022-03 [UNVERIFIED]) |
| Fair-lending equity audit | `finserv_agent_audit.governance.equity_audit.EquityAudit` | Process-level control — fair-lending | Pre-deployment equity-audit memos; quarterly disparate-impact reports | Confirm equity audit ran before each model promotion; confirm quarterly cadence; review for `EquityAuditViolation` events |
| SAR workflow audit | `finserv_agent_audit.governance.sar_workflow_audit.SARWorkflowAudit` | Process-level control — regulatory recordkeeping | `SAR_FILED` chain entries; deadline-compliance metric | Tie 5 randomly-selected `SAR_FILED` entries to filing receipts; confirm 30-day (or 60-day extension) deadline met; confirm § 5318(g)(2) safe-harbor metadata captured |
| Best-interest recommendation | `finserv_agent_audit.governance.best_interest_check.BestInterestCheck` | Process-level control — suitability / Reg-BI | `BEST_INTEREST_CHECKED` chain entries; sample recommendation packages | Spot-check 5 recommendations; confirm investor-profile match + care-obligation rationale |
| Sovereign veto operability | `finserv_agent_audit.governance.sovereign_veto.SovereignVeto` | Process-level control — kill-switch | `VetoRecord` audit entries; quarterly test of veto path | Confirm quarterly veto-path test recorded; confirm `VetoBlockedError` raises during test; confirm authorized-actor list current |
| Autonomy-band promotion gate | `finserv_agent_audit.governance.autonomy_ladder.check_a2_to_a3_promotion` | Process-level control — change management | Promotion-gate reports for each A2→A3 promotion in audit period | Confirm `check_a2_to_a3_promotion()` was run and PASSED for each in-scope promotion; tie to board / risk-committee approval where required |

---

## Section 4 — Sample Audit-Evidence Artifacts

The engagement team will request access to the following client-repository paths during fieldwork. These paths assume the client has not renamed the standard `finserv-agent-audit` directory structure.

| Artifact | Path (client repo) | Purpose |
|---|---|---|
| Production audit chain export | `<client>/audit_chain/production.jsonl` *(client-named)* | Full chain for the audit period |
| Sample audit chain (demonstration) | `output/demo_audit.jsonl` *(per framework convention)* | Walk-through demonstration |
| Failure-modes matrix | `FAILURE-MODES.md` (framework) | Auditor's adversarial reference |
| Assurance guide | `ASSURANCE-GUIDE.md` (framework) | Engagement-team's walk-through guide |
| Ship receipt classification | `SHIP-RECEIPT.md` (framework) | Module-by-module shipping status |
| Model inventory CSV export | `<client>/exports/model_inventory.csv` *(client-named)* | Inventory snapshot per status |
| Vendor scores log | `<client>/exports/vendor_scores_log.csv` *(client-named)* | Vendor-scoring activity for audit period |
| Pre-examination self-assessment | `docs/pre_examination_ai_self_assessment.md` (framework) | Client's most-recent self-assessment |
| ADR ledger | `docs/adr/000*-*.md` (framework) | Decision rationale per pattern |
| Per-regime mapping documents | `docs/sr11_7_mapping.md` + 13 sibling files | Regulatory-control crosswalk |
| Vendor-clauses templates | `vendor-clauses/*.md` (framework) | Procurement-clause reference |
| Sample evidence pack | `examples/evidence_pack_sample/` (framework) | Walk-through training pack for audit trainees |

---

## Section 5 — Auditor Independence and Objectivity

The engagement team confirms that the use of `finserv-agent-audit` as a reference framework does not impair the firm's independence under PCAOB Rule 3520 or SEC Rule 2-01 of Regulation S-X. The framework is open-source software licensed under MIT; the audit firm has no contractual, employment, financial, or affiliated-personnel relationship with the framework's authors that would constitute an impairing relationship under applicable independence rules [UNVERIFIED — verify current independence-rule applicability with firm's national office before signing].

The engagement team conducts its testing as an independent third party; the framework's existence does not substitute for the auditor's professional judgment, sample-selection methodology, or risk-based prioritization. Where the framework provides evidence (a `MODEL_VALIDATED` chain entry, a `VENDOR_SCORE_DRIFT_DETECTED` chain entry), the auditor tests that evidence against the underlying business records to confirm that the chain entry accurately represents the operational event.

The engagement team will not provide non-audit services in the same period that would impair independence, including but not limited to: designing or operating the client's `finserv-agent-audit` deployment, authoring the client's `ModelInventory` content, or making management decisions about model promotion or vendor disposition.

---

## Section 6 — Signatures

By signing below, the parties acknowledge that this exhibit forms part of the engagement letter referenced above and governs the engagement team's treatment of the client's AI / agentic-AI surface during the audit period stated in Section 1.

**For the engagement firm:**

| Role | Name | Signature | Date |
|---|---|---|---|
| Engagement Partner |   |   |   |
| Engagement Quality Reviewer |   |   |   |
| Senior Manager — IT Audit |   |   |   |

**For the client:**

| Role | Name | Signature | Date |
|---|---|---|---|
| Controller (or Chief Accounting Officer) |   |   |   |
| Chief Risk Officer |   |   |   |
| Chief Technology Officer (or Chief AI Officer) |   |   |   |

---

## Related Reference Documents

- [`ASSURANCE-GUIDE.md`](../ASSURANCE-GUIDE.md) — full assurance walk-through with 10-question auditor interview script
- [`SHIP-RECEIPT.md`](../SHIP-RECEIPT.md) — module-by-module shipping status (shipped / stub-with-tracking / deferred-with-tracking)
- [`FAILURE-MODES.md`](../FAILURE-MODES.md) — adversarial / partition / corruption matrix with detection callable references
- [`LIMITATIONS.md`](../LIMITATIONS.md) — bounded claims for the v1.1 baseline
- [`docs/pre_examination_ai_self_assessment.md`](pre_examination_ai_self_assessment.md) — client-side pre-examination worksheet
- [`docs/sox_404_itgc_mapping.md`](sox_404_itgc_mapping.md) — SOX 404 ITGC mapping
- [`docs/sr11_7_mapping.md`](sr11_7_mapping.md) — SR 11-7 model-risk mapping
- [`docs/coso_icair_mapping.md`](coso_icair_mapping.md) — COSO ICAIR mapping

---

*Patterns are software, not legal advice. PCAOB / SEC / firm-independence citations are reference; engagement-firm counsel + national office must finalize. Citations flagged [UNVERIFIED] require primary-source confirmation before the exhibit is countersigned.*
