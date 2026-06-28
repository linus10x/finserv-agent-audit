# BITS_AUP_PREFILL.md — BITS Acceptable Use Policy pre-fill (representative subset)

**Status:** v1.0 · Author-facing pre-fill · Last reviewed: 2026-05-28
**Companion to:** [`../../MANUAL_REMEDIATION_AUTHOR.md`](../../MANUAL_REMEDIATION_AUTHOR.md)
**Audience:** the author (Kunjar). Pre-filled starting point for the BITS Acceptable Use Policy supplier questionnaire when a Tier-1 buyer's vendor-management team sends one during onboarding.

---

## What is the BITS AUP

The BITS (formerly the Banking Industry Technology Secretariat, now under the Financial Services Roundtable) **Acceptable Use Policy (AUP)** questionnaire is a financial-services-specific supplier questionnaire that focuses on the supplier's information security, business resilience, and shared-use-environment commitments. The framework is shipped as open-source patterns code, so several BITS AUP controls (multi-tenant SaaS, customer-data segregation, shared-environment incident isolation) are not in scope; the questions are answered to that effect.

The BITS AUP is used at varying intensity by US bank-holding companies and their subsidiaries. Most Tier-1 bank-holding companies maintain BITS-AUP-derived supplier-onboarding flows.

---

## Representative pre-fills

### 1. Governance

**1.1 — Supplier maintains documented information security governance.**
Yes. Published as `SECURITY.md` (incident response), `ARCHITECTURE.md` (threat model), ADR-0018 (security-design discipline), `CONTRIBUTING.md` (secure development lifecycle), `OWNERSHIP.md` (governance entity), `docs/ETHICS_WALL.md` (advisory-engagement governance). Annual review cadence documented.

**1.2 — Supplier names a security accountability owner.**
Yes. Kunjar Bhaduri, author and authorized signatory of NTCI Consulting, LLC (per `OWNERSHIP.md`). Post Item 7 (TSC formation), security accountability extends to the TSC with the author retaining final-veto authority on security-disclosure decisions.

**1.3 — Supplier conducts independent security review.**
SOC 2 Type I engagement pending per `MANUAL_REMEDIATION_AUTHOR.md` Item 5; target Q4 2026 report. Pre-SOC 2, the supplier offers direct inspection of security artifacts under NDA.

### 2. Risk Management

**2.1 — Supplier maintains a documented risk-management program.**
Yes. Threat model in `ARCHITECTURE.md` § Threat Model + ADR-0018. Operational risk per `docs/ETHICS_WALL.md` annual review. Per-engagement risk per engagement-letter Risk Annex.

**2.2 — Supplier identifies material risks affecting customer engagements.**
Yes. Each engagement letter includes a Risk Annex enumerating identified material risks (e.g. data-flow dependencies on customer systems, third-party dependencies in customer environment, integration-point assumptions). Risks reviewed and updated quarterly during the engagement window.

**2.3 — Supplier maintains insurance commensurate with engagement risk.**
Insurance procurement pending per `MANUAL_REMEDIATION_AUTHOR.md` Item 4. Target coverage: E&O $1M-$5M per claim, cyber $1M-$5M per claim, general commercial liability $1M-$2M. Coverage binds before first commercial engagement letter is signed.

### 3. Personnel

**3.1 — Supplier conducts background checks on personnel with access to customer data.**
Author background is public per professional profile (LinkedIn, GitHub, autonomy-ladder.io). Co-maintainer background-check policy is a TSC-charter item per Item 7. Engagement-specific background-check requirements are addressed in the engagement-letter Personnel Annex.

**3.2 — Supplier maintains personnel security training.**
Single-maintainer at the date of this document. Author maintains current professional certifications and continuing education. Post Item 7 (TSC formation), co-maintainer security training is documented in the TSC charter.

**3.3 — Supplier maintains personnel acceptable-use policy.**
Yes. The author operates under the entity's published policy stack (this BITS AUP pre-fill, `SECURITY.md`, `CODE_OF_CONDUCT.md`, engagement-letter confidentiality clauses). Co-maintainer acceptable-use policy is a TSC-charter item.

### 4. Data Security

**4.1 — Supplier classifies customer data.**
Yes. Engagement-confidential data is the operative customer-data class under any advisory engagement. Classification scheme: Public / Internal / Engagement-Confidential / Engagement-Privileged (per engagement-letter Confidentiality Annex).

**4.2 — Supplier encrypts customer data at rest.**
Yes. Engagement-confidential storage uses provider-side encryption at rest (cloud-storage provider's standard AES-256 at-rest encryption). Author-side workstation full-disk encryption.

**4.3 — Supplier encrypts customer data in transit.**
Yes. TLS 1.2+ for all transmission. End-to-end-encrypted channels for engagement-privileged transmission per engagement letter.

**4.4 — Supplier handles customer data per documented retention schedule.**
Yes. Engagement-letter Retention Annex documents per-engagement retention. Default: engagement-confidential data destroyed 90 days after engagement termination, except where regulatory or legal-hold requirements impose longer retention.

**4.5 — Supplier returns or destroys customer data on engagement termination.**
Yes. Engagement-letter Termination Clause obligates return or destruction at customer's election. Destruction certified in writing within 30 days of termination.

### 5. Access Control

**5.1 — Supplier restricts access to customer data to authorized personnel.**
Yes. Author is currently the sole authorized party with access to engagement-confidential storage. Post Item 7 (TSC formation), engagement-confidential storage access remains restricted to the engagement-named principal; TSC co-maintainers do not have access to engagement-confidential data by default.

**5.2 — Supplier reviews access privileges periodically.**
Yes. Engagement-storage access reviewed at engagement-start and engagement-end (per engagement letter). Repository access reviewed quarterly. PyPI publish access reviewed at every release.

**5.3 — Supplier enforces multi-factor authentication.**
Yes. Two-factor authentication required on all author-side accounts (GitHub, PyPI, engagement-confidential storage, email).

### 6. Application & Infrastructure Security

**6.1 — Supplier follows a secure software development lifecycle.**
Yes. Documented in `CONTRIBUTING.md`. Pre-commit hooks (ruff + mypy strict). CI pipeline enforces test pass + lint clean + type-check clean + 90% branch coverage. Per-PR review required.

**6.2 — Supplier conducts application security testing.**
Yes. Per-PR test, lint, type-check, coverage. v2.0 ships an adversarial test pack (Garak + Promptfoo + Python harness per ADR-0018). Hypothesis-based property test for the DER codec per `pyproject.toml` `test-property` extra.

**6.3 — Supplier maintains a software bill of materials (SBOM).**
Yes. CycloneDX 1.7 ML-BOM + SPDX 3.0 AI Profile generated by AIBOMGenerator (v2.0) for every release. Published alongside the release artifact.

**6.4 — Supplier monitors vulnerability disclosures and patches in a timely manner.**
Yes. Per `SECURITY.md`: acknowledgment of reported vulnerability within 5 business days; assessment within 30 calendar days; fix release per CHANGELOG cadence. Dependency-vulnerability scan on every PR.

### 7. Incident Management

**7.1 — Supplier maintains a documented incident response procedure.**
Yes. Published as `SECURITY.md` at repository root. GitHub Security Advisory protocol for public-track disclosure; private security advisory channel for embargoed disclosure.

**7.2 — Supplier notifies affected customers of material incidents.**
Yes. Engagement-letter Notification Clause obligates notification within the engagement-specified window (default: 72 hours of discovery, conformant with major US state breach-notification statutes and the GLBA Safeguards Rule). Notification includes incident description, scope, mitigation status, and recommended customer-side action.

**7.3 — Supplier documents post-incident review.**
Yes. Material incidents trigger a retrospective per `docs/ai_incident_retrospective_template.md`. Retrospective shared with affected customers under NDA on request.

### 8. Business Continuity

**8.1 — Supplier maintains a documented business continuity plan.**
Yes, scoped to the framework's nature. Authoritative repository on GitHub with full git history. Distribution via PyPI. Author-side single-maintainer continuity addressed via Item 7 (TSC formation) and Item 8 (LF AI & Data Foundation Sandbox donation). Engagement-side continuity addressed in engagement-letter Continuity Annex.

**8.2 — Supplier tests business continuity plan periodically.**
Backup-and-restoration tested quarterly. Engagement-side continuity scenarios tested at engagement-letter execution (table-top exercise).

### 9. Audit & Compliance

**9.1 — Supplier permits customer audit of security controls.**
Yes. Engagement-letter Audit Annex permits customer audit of supplier-side security controls relevant to the engagement, on reasonable notice, during normal business hours, subject to confidentiality protections. Audit scope is bounded to the engagement-relevant controls.

**9.2 — Supplier maintains compliance with applicable laws and regulations.**
Yes. The advisory entity (NTCI Consulting, LLC) maintains compliance with applicable Texas business laws, federal tax obligations, and applicable employment / contractor laws. Investment Advisers Act § 202(a)(11) posture documented in `docs/ETHICS_WALL.md`.

**9.3 — Supplier maintains independent attestation of controls (SOC 2 / ISO 27001 / equivalent).**
SOC 2 Type I report pending; target Q4 2026 per Item 5. Pre-SOC 2, the supplier offers direct inspection of security artifacts under NDA in lieu of independent attestation. ISO 27001 is not currently pursued; SOC 2 is the US-FSI-market-standard attestation and is the supplier's chosen path.

### 10. Subcontractor Management

**10.1 — Supplier discloses subcontractors.**
Yes. The framework's subcontractor surface is: GitHub (code hosting + CI), PyPI (distribution), Sigstore (release signing), the author's CPA firm (post Item 5), the author's IP counsel of record, the author's commercial-insurance broker (post Item 4). No personnel subcontractors; engagements are delivered personally by the author.

**10.2 — Supplier flows down customer security obligations to subcontractors.**
Yes, to the extent subcontractors process customer data. GitHub, PyPI, and Sigstore process no customer-engagement data; their terms-of-service obligations are accepted as published. CPA firm, counsel, and broker engagements include confidentiality clauses that flow down customer-engagement confidentiality protections.

---

## Disclaimers attached to the pre-fill

1. **Pre-fill, not certification.** The answers are the author's good-faith answers as of the date of this document and are not a substitute for the buyer's own due diligence.
2. **Open-source-patterns scope.** The framework is open-source patterns code, not a multi-tenant SaaS. Several BITS AUP controls are answered "not in scope" with the reason stated.
3. **SOC 2 maturity.** Post-SOC-2 Type I (target Q4 2026), "documented and observed" answers will additionally answer "audited by independent CPA firm."
4. **Insurance maturity.** Post Item 4 (insurance bind), insurance-related controls will answer with active policy numbers and certificate-of-insurance attachments.

---

## Related

- [`SIG_LITE_PREFILL.md`](SIG_LITE_PREFILL.md) — Shared Assessments SIG Lite pre-fill
- [`CAIQ_PREFILL.md`](CAIQ_PREFILL.md) — Cloud Security Alliance CAIQ pre-fill
- [`../SOC2_ENGAGEMENT_RFP.md`](../SOC2_ENGAGEMENT_RFP.md) — SOC 2 engagement RFP
- [`../../SECURITY.md`](../../SECURITY.md) — vulnerability response procedure
- [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md) — system architecture and threat model

---

*Vendor-questionnaire pre-fill, not certification.*
