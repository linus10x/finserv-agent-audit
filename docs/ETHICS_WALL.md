# ETHICS_WALL.md — Information barriers between NTCI advisory and NTCI research lab

**Status:** v1.0 · Last reviewed: 2026-05-28
**Companion to:** [`OWNERSHIP.md`](../OWNERSHIP.md), [`DISCLAIMER.md`](../DISCLAIMER.md), [`MANUAL_REMEDIATION_AUTHOR.md`](../MANUAL_REMEDIATION_AUTHOR.md) Item 3

> **Author note.** This document is published in the repo to make the information-barrier posture public. The operative legal status of every claim below is subject to counsel review; this document is a published policy artifact, not a legal opinion. Adopters and prospective engagement counterparts should treat the document as the author's stated posture and request counsel-side validation under NDA where commercially material.

---

## Why this document exists

The framework is published under the open-source license shipped at the repository root by an author who also operates two related-but-distinct activities under the NTCI name:

1. **NTCI Consulting, LLC (the advisory entity).** A Texas LLC formed to hold the framework IP and to deliver productized advisory engagements (Diagnostic, Audit, Retainer) to FSI and CRE buyers around AI-governance, autonomous-agent risk, and the patterns documented in this repository and in the sibling `cre-agent-audit` repository.
2. **NTCI (the research lab).** A self-funded research activity that develops private quantitative options research and adjacent capital-markets research. The lab operates in paper-trading Phase 0 as of the date of this document; no live capital has been deployed.

The two activities share an authoring principal (Kunjar Bhaduri) and share lineage in the patterns published in this repository. The framework's commercial-advisory path (under NTCI Consulting, LLC) routinely engages with buy-side, sell-side, and platform firms whose securities, vendor surfaces, or product lines could plausibly intersect with the research lab's universe. The intersection creates a conflict-of-interest surface that requires explicit information barriers, pre-clearance, and disclosure.

The remainder of this document captures the policies that govern that surface.

---

## The two entities at a glance

| Attribute | NTCI Consulting, LLC | NTCI (research lab) |
|---|---|---|
| Legal form | Texas single-member LLC (per `OWNERSHIP.md`, post-formation) | Author's self-funded research activity; no separate legal entity unless and until a separate entity is formed |
| Mission | Productized advisory + open-source framework stewardship | Private quantitative + capital-markets research |
| Revenue model | Diagnostic / Audit / Retainer (advisory fees) | None (pre-revenue; paper-trading Phase 0) |
| Public surfaces | autonomy-ladder.io · this repo · sibling `cre-agent-audit` repo · LinkedIn / X content under the brand | None public; research stays private |
| Counterparties | FSI / CRE buyers under engagement letter | None (pre-revenue research; no external clients) |
| Confidential information held | Adopter and engagement-client confidential data per engagement letter | Author's private research; vendor SDK keys; broker connectivity credentials |
| Counsel of record | TBD post-LLC formation | Same author; same counsel of record |

The two activities share an authoring principal. The information barriers below capture how the principal manages the conflict surface that the shared authorship creates.

---

## Information barriers

The following barriers are policy commitments. They are observable from external evidence (engagement-letter language, repo commit history, document storage segregation) and are subject to audit by any engagement-side counterparty under NDA on request.

**B1. Advisory-engagement confidential data does not flow into the research lab.** Adopter and engagement-client confidential data received under the advisory practice — system architecture diagrams, model-validation files, audit-trail samples, vendor contracts, internal control matrices — is held in advisory-engagement storage and is not used to inform the research lab's universe-selection, signal weighting, or position construction. The barrier is enforced at the storage layer (separate document repositories), at the processing layer (the research lab's data pipelines do not subscribe to advisory-engagement sources), and at the retention layer (engagement-confidential data is destroyed per the engagement-letter retention schedule).

**B2. Research-lab strategy IP does not flow into advisory engagements.** The research lab's signal logic, weighting schemes, and proprietary indicator constructions are not shared in advisory engagements, included in advisory deliverables, or referenced in the open-source framework. The framework documents *governance patterns* — autonomy-level classification, sovereign veto, hash-chain audit logging, the FSI-specific gates — which are conceptually adjacent to the research lab's discipline but do not encode the lab's strategy IP. Adopters and engagement clients receive governance scaffolding, not trading signals.

**B3. The author does not trade securities of advisory-engagement clients during the active engagement window or for a 30-day cool-off period after engagement termination.** "Trade" includes both the research-lab's paper-trading activity (the lab does not paper-trade the client's securities during the engagement window) and any personal investment activity in the client's securities. The 30-day cool-off is a policy commitment; counsel may extend it for specific engagements where the engagement scope produced material non-public information.

**B4. The author does not trade securities of firms that compete with advisory-engagement clients on the basis of any information learned in the engagement.** This barrier is functionally identical to the standard insider-trading discipline: information learned in confidence during an engagement does not inform any trading activity, whether of the client itself or of a competitor.

**B5. The framework's open-source content does not embed any confidential information from any advisory engagement.** The framework's content is derived from the author's accumulated experience across a 25+ year regulated financial-services and technology career and from the research lab's published-pattern abstractions. No engagement-client confidential information is ever included in the open-source repository, the documentation, the ADR record, or any commit message.

---

## Pre-clearance process

Any advisory engagement with a firm whose securities sit in the research lab's universe — defined here as any firm with ticker presence in the Russell 3000 or in the ETF universe the lab actively monitors — triggers a pre-engagement clearance review. The review answers three questions:

1. **Universe intersection.** Does the prospective client's ticker sit in any active research-lab universe? If no, the engagement clears for execution. If yes, proceed to question 2.
2. **Active-position check.** Does the research lab have any active position (including paper-trading position) in the client's securities at the time of the engagement-letter execution? If yes, the position is closed (or, for paper-trading positions, removed from the lab's tracking) before the engagement-letter is countersigned. If no, proceed to question 3.
3. **Scope review.** Does the engagement scope create a meaningful risk that the engagement will produce material non-public information that would affect the research lab's universe construction? If yes, counsel reviews and may impose additional conditions (longer cool-off, scope reduction, recusal of the principal from any lab activity affecting the client's universe for the engagement duration). If no, the engagement clears with the standard 30-day cool-off in B3 above.

The clearance review is documented in a single-page memo retained in the advisory entity's permanent records. The memo is available under NDA to the engagement counterparty on request.

---

## Disclosure paragraph (engagement-letter template)

Every advisory engagement letter executed by NTCI Consulting, LLC includes the following disclosure paragraph (or substantively equivalent counsel-approved language):

> **Disclosure of related research activity.** The author of the framework, Kunjar Bhaduri, also operates a private quantitative and capital-markets research activity under the NTCI name ("the research lab"). The research lab operates in paper-trading Phase 0 as of the date of this engagement letter; no live capital has been deployed. The advisory entity (NTCI Consulting, LLC) maintains information barriers between the engagement and the research lab, documented in the framework's published `docs/ETHICS_WALL.md`. Client confidential information received under this engagement does not flow to the research lab. The research lab's strategy IP does not flow into this engagement's deliverables. The author does not trade Client's securities during the active engagement window or for thirty (30) days after engagement termination. The pre-clearance process described in `docs/ETHICS_WALL.md` was executed before this engagement letter was countersigned, and Client is entitled to review the clearance memo under NDA on request.

The disclosure is repeated, in summary form, in any deliverable that names a client-affecting framework recommendation (Diagnostic deliverable cover page, Audit report cover page, quarterly Retainer status update).

---

## Investment Advisers Act § 202(a)(11) posture

The Investment Advisers Act of 1940, § 202(a)(11) (15 U.S.C. § 80b-2(a)(11)) defines "investment adviser" as "any person who, for compensation, engages in the business of advising others, either directly or through publications or writings, as to the value of securities or as to the advisability of investing in, purchasing, or selling securities, or who, for compensation and as part of a regular business, issues or promulgates analyses or reports concerning securities..."

The framework's commercial-advisory path delivers governance, audit-trail-design, and regulatory-mapping advice. It does not deliver advice as to the value of any specific security, the advisability of any specific investment, or any analysis or report concerning specific securities. The advisory entity's posture under § 202(a)(11) is therefore: **out of scope; advisory entity is not an investment adviser; no registration required**.

The research lab's activity sits in a different posture. Pre-revenue, paper-trading research that does not advise others for compensation is out of scope of § 202(a)(11) by its terms. If and when the research lab transitions to live capital deployment with external client funds, or to publication of investment recommendations for compensation, counsel review of the § 202(a)(11) posture is triggered immediately, not at any periodic cadence. The author commits in writing — through this published document — that the transition will not be made without prior counsel review and any registration that counsel determines is required.

The § 203(b) exemptions (intrastate adviser, adviser solely to insurance companies, adviser with fewer than 15 clients during the preceding 12 months and not holding out generally to the public as an investment adviser) are documented in counsel's file for the research lab activity as of the date of this document. The intrastate exemption is the operative exemption; the research lab's activity is intrastate (Texas) by its construction.

Counsel review of this posture is annual at minimum. Adopters and engagement counterparts may request the operative counsel-of-record letter under NDA.

---

## Form ADV posture

Per the § 202(a)(11) posture above, neither entity is currently registered as an investment adviser at the federal (SEC) or state (Texas State Securities Board) level. No Form ADV is currently on file. If counsel determines that registration is required for either entity at any time, a Form ADV filing is made and this document is updated to reflect the registration status, the disclosure-brochure delivery process, and the resulting changes to the engagement-letter template.

---

## Review cadence

This document is reviewed annually at minimum, on or before May 28 of each calendar year (anniversary of the document's first publication). Out-of-cycle review is triggered by any of:

- The research lab transitioning from paper-trading Phase 0 to any live-capital deployment.
- The research lab accepting external client funds.
- The advisory entity changing scope to include investment-related advice (security-specific value or advisability advice).
- An engagement-letter pre-clearance review surfacing a material conflict that the current information barriers do not cleanly address.
- Counsel of record changing.

The annual review is documented in a single-page memo retained in the advisory entity's permanent records. The memo's existence is publicly noted in the next-cycle update to this document.

---

## Related

- [`OWNERSHIP.md`](../OWNERSHIP.md) — IP-holding entity (the advisory entity that this document discusses)
- [`DISCLAIMER.md`](../DISCLAIMER.md) — bounded claims of the open-source framework
- [`MANUAL_REMEDIATION_AUTHOR.md`](../MANUAL_REMEDIATION_AUTHOR.md) — author-action backlog including Item 3 (ethics-wall formation)
- [`CITATION.cff`](../CITATION.cff) — framework citation metadata, including the NTCI / López de Prado attribution

---

*Ethics-wall posture, not legal advice. Counsel review required before any commercial reliance.*
