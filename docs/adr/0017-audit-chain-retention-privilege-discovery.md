# ADR-0017 · Audit-Chain Retention, Privilege & Discovery Posture (FSI)

**Status:** Accepted · v1.1 · layered policy ADR (no separate runtime primitive)
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit v1.1

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).
>
> **Citation update (April 17, 2026):** Where this ADR references SR 11-7 / OCC Bulletin 2011-12 as the prudential MRM citation, note that those instruments were superseded for new examinations / rescinded by the joint OCC / FRB / FDIC issuance of April 17, 2026 (OCC Bulletin 2026-13), which **excluded generative + agentic AI from scope** pending a forthcoming joint RFI. The retention / privilege / discovery posture described here is independent of the MRM citation lineage; the audit-chain evidence pipeline survives the rescission. See [`docs/interagency_mrm_2026_overlay.md`](../interagency_mrm_2026_overlay.md).

## Context

Every governance pattern in this repository produces evidentiary artifacts on purpose. The hash-chained Audit Ledger (ADR-0003) carries per-decision rationale; the Sovereign Veto (ADR-0002) carries bypass-justification fields with named human owners; DEFCON (ADR-0001) carries posture-change records; Shadow Mode (ADR-0006) carries divergence statistics; the Vendor Score Gate (ADR-0010) and Model Inventory (ADR-0011) carry dataset and model-provenance records. The same property that makes agent behavior reconstructable makes the artifacts **discoverable**.

The FSI production surface is distinct from the consumer-protection surface that drove the parallel `cre-agent-audit` ADR:

- **SEC Rule 17a-4 / 17a-3** (17 C.F.R. § 240.17a-4) — broker-dealer records subject to SEC subpoena and routine examination; six-year retention; WORM storage for originals.
- **FINRA Rule 4511** — books-and-records retention; subpoena power runs through Rule 8210; refusal is itself disciplinable.
- **SR 11-7** (FRB / OCC supervisory guidance) — model documentation, validation reports, ongoing-monitoring evidence routinely demanded in FRB and OCC examinations. The audit chain's per-model rationale entries are model documentation in everything but name.
- **CFPB civil investigative demands** under 12 U.S.C. § 5562 — the Bureau can compel testimony and documentary production from any covered person.
- **State financial-regulator subpoenas** — NYDFS, Texas Department of Banking, California DFPI, each with their own production regimes.
- **Private securities litigation discovery** — Section 10(b), Section 11 class-action plaintiffs propound RFPs against the same artifacts.

The patterns alone do not address this. They produce the artifacts; the operator owns the policy layer.

## Decision

Adopters of v1.1 layer four policy artifacts on top of the engineering primitives.

### 1. Retention schedule synchronized to FSI statutes and supervisory windows

The audit chain retains decision records for the **longer** of the following, plus any active litigation hold:

- **SEC 17a-4** — six years for broker-dealer required records; first two years readily accessible (17 C.F.R. § 240.17a-4(b))
- **FINRA Rule 4511** — six-year default, longer where another rule attaches
- **SR 11-7 model documentation** — life-of-model plus the supervisory cycle (commonly seven years from model retirement) [UNVERIFIED — primary source not fetched]
- **BSA / AML** — five years for transaction monitoring (31 C.F.R. § 1010.430)
- **ECOA / Regulation B** — twenty-five months for consumer credit, twelve months for business credit (12 C.F.R. § 1002.12)
- **CFPB CID scope** — preserve from notice through final disposition
- **Sarbanes-Oxley § 802** — seven years for audit work papers (18 U.S.C. § 1520)
- **Litigation hold** — overrides retention-based deletion

Deletion is itself an audit-chain entry; the tombstone remains after cryptographic shredding.

### 2. Privilege classification metadata on every audit-chain entry

The framework provides a `privilege_classification` field on the `AuditEvent` schema. The field is **operator-populated**; the framework does not infer privilege. Permitted values: `attorney-client`, `work-product`, `mandatory-disclosure`, `none`. Legal counsel makes the call per-event or per-event-class. The presence of the field is the contract; correct classification is counsel's work.

A critical FSI caveat: `mandatory-disclosure` overrides privilege claims. Records subject to SEC 17a-4 or FINRA Rule 4511 statutory production cannot be withheld on privilege grounds for the originally-required category. Counsel-routed bypass justifications layered on top are a separate class.

### 3. Work-product framing for fair-lending and surveillance monitor outputs

Monitor outputs (disparate-impact statistics on credit decisions, surveillance alerts on suspected market abuse, Shadow Mode model-drift evidence) may qualify for work-product protection under FRCP 26(b)(3) if the monitor was deployed at counsel direction in anticipation of litigation or enforcement. The deployment record documents which counsel directed deployment, when, and against what anticipated matter. Without that documentation, the default position is that monitor output is discoverable.

### 4. Litigation-hold integration with the audit chain

When the operator receives a hold (preservation letter, SEC subpoena, FINRA Rule 8210 request, CFPB CID), retention-based deletion is suspended for the held scope. The hold is an audit-chain entry — scope, effective date, releasing event recorded.

## Alternatives Considered

- **Bake privilege classification into automated logic.** Rejected: privilege is jurisdiction-specific, fact-specific, and counsel's call. Automation would generate false claims.
- **Default to maximum retention everywhere.** Rejected: indefinite retention is itself a liability surface and conflicts with data-minimization regimes (GLBA, state privacy statutes).
- **Punt the policy layer to a downstream library.** Rejected: every adopter would re-derive the same answers. An ADR is the right artifact.

## Consequences

**Positive.** Operators get a defensible posture against regulator inquiries AND plaintiff-side discovery overreach. Privilege objections are supported by structured metadata, not post-hoc argument. Retention follows statute. Litigation holds work without error-prone manual processes.

**Negative.** The policy layer is the operator's work. General Counsel + Chief Compliance Officer + Model Risk Management own the policy in writing, reviewed annually.

**Architectural.** Engineering primitives stay agnostic to the policy layer. Operators choose retention windows, privilege framings, and hold integrations without modifying pattern code.

## Regulatory Mapping

- FRCP Rule 26(b)(3) (work-product); Rule 502 (privilege); Rule 37(e) (lost ESI)
- FRE 501 (privilege); 801(d)(2) (party admissions)
- *Upjohn Co. v. United States*, 449 U.S. 383 (1981) — corporate attorney-client privilege scope
- *Hickman v. Taylor*, 329 U.S. 495 (1947) — work-product doctrine
- SEC Rule 17a-4 — 17 C.F.R. § 240.17a-4
- FINRA Rule 4511 (books and records); Rule 8210 (information requests)
- SR 11-7 — FRB/OCC Supervisory Guidance on Model Risk Management (April 4, 2011)
- CFPB CID authority — 12 U.S.C. § 5562
- Sarbanes-Oxley § 802 — 18 U.S.C. § 1520

## Pre-mortem

A plaintiff in a Section 10(b) action propounds RFP #1 against the trading-surveillance audit chain. E-discovery pulls 14,000 entries; 600 carry `privilege_classification = "attorney-client"` from compliance-counsel review. The privilege log generates mechanically from the metadata. The plaintiff moves to compel; the court orders in camera review; the sample holds because the metadata reflects the actual review pattern documented in the compliance department's standing engagement letter.

The failure mode this ADR prevents: the operator never populated `privilege_classification`. Every entry produces as `none`. The 600 counsel-reviewed entries lose their privilege claim through waiver. This ADR makes that failure mode visible at adoption, not at deposition.

## Reversibility

Reversible at adoption time (retention windows and privilege schema can be re-keyed). After production has occurred in a regulatory matter or litigation, produced records are out of the operator's control. Adopt before the first CID, not after.

## Cross-references

- ADR-0001 (DEFCON) — posture-change records are mandatory-disclosure in most regulator contexts
- ADR-0002 (Sovereign Veto) — generates the bypass-justification fields the privilege classification protects
- ADR-0003 (Hash-chained Audit Ledger) — the underlying chain this ADR wraps
- ADR-0005 (EU AI Act mapping) — Art. 12 (logs) interacts with retention
- ADR-0006 (Shadow Mode) — promotion-decision logs carry SR 11-7 model-validation evidence
- ADR-0007 (SR 11-7 overlay) — the supervisory framework whose evidence pipeline this ADR governs
- ADR-0010 (Vendor Score Gate); ADR-0011 (Model Inventory) — generate vendor/model artifacts subject to examination
- ADR-0018 (Adversarial Agent Threat Model) — the privilege posture is independent of threat-model scope
