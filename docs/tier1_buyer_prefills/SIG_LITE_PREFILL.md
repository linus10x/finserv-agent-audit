# SIG_LITE_PREFILL.md — Shared Assessments SIG Lite pre-fill (representative subset)

**Status:** v1.0 · Author-facing pre-fill · Last reviewed: 2026-05-28
**Companion to:** [`../../MANUAL_REMEDIATION_AUTHOR.md`](../../MANUAL_REMEDIATION_AUTHOR.md)
**Audience:** the author (Kunjar). Use these pre-filled answers as the starting point for the SIG Lite questionnaire when a Tier-1 buyer's vendor-risk team sends one during engagement onboarding. Full questionnaire to be completed by the author per engagement.

---

## What is SIG Lite

The Shared Assessments **Standardized Information Gathering (SIG)** questionnaire is the most widely-used third-party vendor-risk-management questionnaire in US financial services. **SIG Lite** is the lighter-weight (~125-question) version that most Tier-1 buyers send to suppliers in the discovery / scope-assessment phase before they send the full SIG Core (~850 questions) for higher-risk engagements.

The framework's commercial-advisory practice will receive SIG Lite from any Tier-1 FSI buyer. The pre-fills below cover ~20 representative controls demonstrating the framework's discipline; the full questionnaire is completed per engagement.

---

## Representative pre-fills

### A. Risk Assessment and Treatment

**A.1.1 — Does the organization have a documented risk assessment program?**
Yes. The framework documents its threat model in `ARCHITECTURE.md` § Threat Model and ADR-0018 (Threat Model Expansion). Operational risk for the advisory entity (NTCI Consulting, LLC) is assessed annually with documented review per `docs/ETHICS_WALL.md` annual cadence. Per-engagement risk assessment is documented in the engagement-letter Risk Annex.

**A.1.2 — Does the organization conduct risk assessments at least annually?**
Yes. Annual cadence documented in `docs/ETHICS_WALL.md`. Out-of-cycle review triggers listed.

**A.1.3 — Is there a documented process for risk treatment decisions?**
Yes. Risk treatment decisions are documented in ADRs (Architectural Decision Records) following Michael Nygard's ADR template. 34 ADRs as of the date of this document. Each ADR captures the decision, the alternatives considered, the consequences, and the operator-side risk treatment.

### B. Security Policy

**B.2.1 — Does the organization have a documented information security policy?**
Yes. Published as `SECURITY.md` at repository root. Covers vulnerability reporting, response timeline (acknowledgment within 5 business days; assessment within 30 calendar days; fix release per CHANGELOG cadence), Sigstore cosign signature attestation on releases.

**B.2.2 — Is the security policy reviewed annually?**
Yes. Last reviewed date is committed in the file header. Review log preserved in git history.

**B.2.3 — Are employees and contractors trained on security policy?**
The framework is single-maintainer at the date of this document (per `OWNERSHIP.md` and `MANUAL_REMEDIATION_AUTHOR.md` Item 7); the author is the sole party subject to training. The author maintains current certifications and continuing education as documented in the author's professional profile. Co-maintainer training will be documented in `docs/TSC_CHARTER.md` post-formation.

### C. Asset Management

**C.3.1 — Is there an inventory of information assets?**
Yes. The framework's information assets are: (a) the public GitHub repository (`linus10x/finserv-agent-audit`); (b) the public sibling repository (`linus10x/cre-agent-audit`); (c) the autonomy-ladder.io domain; (d) advisory-engagement confidential materials (per engagement letter); (e) the author's IP and operating documents held by NTCI Consulting, LLC.

**C.3.2 — Are assets classified by sensitivity?**
Yes. Public (open-source code, documentation, autonomy-ladder.io content) vs Engagement-Confidential (advisory-engagement materials per engagement letter) vs Internal (NTCI Consulting, LLC operating documents).

### D. Access Control

**D.4.1 — Is access to information systems controlled?**
Yes. GitHub access: author + future TSC co-maintainers per granted-permission discipline. PyPI publish access: GitHub Actions OIDC via Trusted Publishing (no long-lived API token); see `docs/PYPI_TRUSTED_PUBLISHING_SETUP.md`. Two-factor authentication required on all account types.

**D.4.2 — Are privileged access events logged?**
Yes. GitHub maintains audit logs for organization-level and repository-level privileged events. PyPI maintains publish-event logs. Engagement-confidential storage maintains its own access log.

**D.4.3 — Are access rights reviewed periodically?**
Yes. Repository collaborator review is quarterly. Co-maintainer access is reviewed at each annual TSC charter renewal.

### E. Cryptography

**E.5.1 — Is cryptography used to protect information at rest?**
Yes. The framework's hash-chain ledger uses SHA-256 (per `src/finserv_agent_audit/governance/audit_chain.py`). RFC 3161 timestamp source for non-repudiation per `src/finserv_agent_audit/governance/rfc3161_codec.py`. Release artifacts signed with Sigstore cosign attestation. Engagement-confidential storage uses provider-side encryption at rest.

**E.5.2 — Is cryptography used to protect information in transit?**
Yes. HTTPS / TLS for all framework distribution (GitHub, PyPI, autonomy-ladder.io). Engagement-confidential transmission uses TLS plus per-engagement key exchange.

### F. Physical and Environmental Security

**F.6.1 — Is access to physical premises controlled?**
The author operates from a home office in Dallas, Texas. Physical access controlled by standard residential security. No dedicated office premises; no engagement-confidential materials are stored in physical form (electronic-only).

### G. Operations Security

**G.7.1 — Is change management documented?**
Yes. Every code change is a pull request with required review per `CONTRIBUTING.md`. Every release is tagged per `RELEASE-INSTRUCTIONS.md`. Every architectural change is an ADR per `docs/adr/`. CHANGELOG.md captures every release.

**G.7.2 — Is malware protection in place?**
Yes. Author-side workstation runs standard endpoint protection. CI pipeline runs dependency-vulnerability scan on every PR (Dependabot + GitHub Advanced Security where licensed).

**G.7.3 — Are backups performed and tested?**
The framework's authoritative copy is GitHub (with PyPI as distribution). GitHub provides backup and disaster recovery as part of its service. The author maintains an additional local clone updated daily. Restoration tested quarterly.

### H. Communications Security

**H.8.1 — Is network security managed?**
Yes. Author-side workstation uses commercial VPN. Repository access requires HTTPS / TLS. Engagement-confidential transmission uses end-to-end-encrypted channels per engagement letter.

### I. System Acquisition, Development, and Maintenance

**I.9.1 — Is secure development lifecycle documented?**
Yes. `CONTRIBUTING.md` documents the contribution lifecycle. Type-checking (mypy strict), linting (ruff), test coverage (90%+ branch), dependency-pinning, signed releases. Threat model in `ARCHITECTURE.md`. ADR-0018 documents the security-design discipline.

**I.9.2 — Is application security testing performed?**
Yes. Per-PR test, lint, type-check, coverage. v2.0 ships an adversarial test pack combining Garak probes, Promptfoo scenarios, and a Python harness per ADR-0018. Hypothesis-based property test for the DER codec per `pyproject.toml` `test-property` extra.

### J. Supplier Relationships

**J.10.1 — Are supplier risks assessed?**
Yes. The framework has zero runtime dependencies (stdlib only per `pyproject.toml`). Optional integrations (MCP, OpenTelemetry, agentic-runtime adapters) are import-guarded behind extras. Dev-time dependencies are pinned and renovated quarterly.

**J.10.2 — Are supplier security obligations documented?**
The framework's supplier surface is minimal (GitHub, PyPI). Both are documented commitments under their respective terms-of-service. Optional integration dependencies are at the adopter's discretion per `pyproject.toml` extras.

### K. Information Security Incident Management

**K.11.1 — Is there a documented incident response procedure?**
Yes. Published as `SECURITY.md` at repository root. Vulnerability reporting via private security advisory (GitHub security tab) or email to author. Response timeline: acknowledgment within 5 business days, assessment within 30 calendar days.

**K.11.2 — Are incidents documented and reviewed?**
Yes. Security advisories published per GitHub Security Advisory protocol. Public CHANGELOG entries for any release that addresses a security issue. Post-incident retrospective per `docs/ai_incident_retrospective_template.md` for material incidents.

### L. Business Continuity Management

**L.12.1 — Is there a business continuity plan?**
Yes, scoped to the framework's nature. Authoritative repository on GitHub with full git history. Releases distributed via PyPI with backup-distribution path documented in `RELEASE-INSTRUCTIONS.md`. Author-side single-maintainer continuity is the open Item 7 in `MANUAL_REMEDIATION_AUTHOR.md`; LF AI & Data Foundation Sandbox application per Item 8 is the medium-term continuity strategy.

### M. Compliance

**M.13.1 — Are legal and regulatory requirements identified?**
Yes. The framework's regulatory mapping is documented in 25+ regulatory-mapping documents under `docs/`. The advisory entity's compliance posture is documented in `docs/ETHICS_WALL.md` (Investment Advisers Act § 202(a)(11) posture) and in counsel's file.

**M.13.2 — Are independent reviews of information security conducted?**
SOC 2 Type I engagement pending per `MANUAL_REMEDIATION_AUTHOR.md` Item 5. Target Type I report Q4 2026. Type II report Q4 2027. Pre-SOC 2, the security posture is documented in the framework's published security artifacts (`SECURITY.md`, `ARCHITECTURE.md`, ADRs); buyer review on direct inspection is available under NDA.

---

## Disclaimers attached to the pre-fill

1. **Pre-fill, not certification.** The answers above are the author's good-faith answers as of the date of this document. They are not a substitute for the buyer's own due diligence and are not a certification of compliance with any specific control framework.
2. **Engagement-specific updates.** Per-engagement SIG Lite responses may differ from the pre-fill above to reflect engagement-specific scope, deliverables, and confidentiality commitments. The pre-fill is a starting point; the engagement-letter Risk Annex is the operative document.
3. **SOC 2 maturity.** Several controls answer "documented and observed" today and will additionally answer "audited by independent CPA firm" once the SOC 2 engagement per Item 5 completes. Buyers requiring third-party-audit attestation should expect the SOC 2 Type I report by Q4 2026.

---

## Related

- [`CAIQ_PREFILL.md`](CAIQ_PREFILL.md) — Cloud Security Alliance CAIQ pre-fill
- [`BITS_AUP_PREFILL.md`](BITS_AUP_PREFILL.md) — BITS Acceptable Use Policy pre-fill
- [`../SOC2_ENGAGEMENT_RFP.md`](../SOC2_ENGAGEMENT_RFP.md) — SOC 2 engagement RFP
- [`../../SECURITY.md`](../../SECURITY.md) — vulnerability response procedure
- [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md) — system architecture and threat model

---

*Vendor-questionnaire pre-fill, not certification.*
