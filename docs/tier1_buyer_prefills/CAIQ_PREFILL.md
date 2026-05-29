# CAIQ_PREFILL.md — Cloud Security Alliance CAIQ pre-fill (representative subset)

**Status:** v1.0 · Author-facing pre-fill · Last reviewed: 2026-05-28
**Companion to:** [`../../MANUAL_REMEDIATION_AUTHOR.md`](../../MANUAL_REMEDIATION_AUTHOR.md)
**Audience:** the author (Kunjar). Pre-filled starting point for the Cloud Security Alliance Consensus Assessments Initiative Questionnaire when a Tier-1 buyer's cloud-risk-management team sends one during engagement onboarding.

---

## What is the CAIQ

The Cloud Security Alliance (CSA) **Consensus Assessments Initiative Questionnaire (CAIQ)** is the standard cloud-vendor security questionnaire. The current version (CAIQ v4) maps to the CSA Cloud Controls Matrix (CCM) v4 across 17 control domains and ~261 question-pairs. Tier-1 FSI buyers send the CAIQ when the engagement involves any cloud-touching surface (SaaS evaluation, supplier code that runs in the buyer's cloud environment, supplier-hosted services).

The framework itself is shipped as a Python package — not a cloud service. The CAIQ is therefore typically not a primary fit, but Tier-1 buyers will send it anyway for completeness, and the framework's CI / release infrastructure (GitHub-hosted, PyPI-distributed) does engage with several CAIQ control domains.

---

## Representative pre-fills

### AIS — Application & Interface Security

**AIS-01.1 — Are application security policies defined?**
Yes. The framework's secure-development discipline is documented in `CONTRIBUTING.md`. Type-checking (mypy strict), linting (ruff), branch coverage floor (90%), signed releases (Sigstore cosign), threat model per ADR-0018.

**AIS-02.1 — Are customer-deployed applications tested for security?**
The framework is open-source patterns code, not a deployed application. Adopter deployments are the adopter's responsibility. The framework ships an adversarial test pack (v2.0) for adopters to use against their deployments.

### AAC — Audit Assurance & Compliance

**AAC-01.1 — Is there an audit and assurance program?**
Yes, scoped to the framework's nature. Internal: per-PR review + CI test pass + ADR documentation for architectural changes. External: SOC 2 Type I engagement pending per `MANUAL_REMEDIATION_AUTHOR.md` Item 5, target Q4 2026.

**AAC-02.1 — Are independent third-party audits performed?**
SOC 2 Type I engagement pending; reports expected Q4 2026 (Type I) and Q4 2027 (Type II). Pre-SOC 2, buyer review on direct inspection is available under NDA.

### BCR — Business Continuity & Operational Resilience

**BCR-01.1 — Is there a business continuity plan?**
Yes. Authoritative repository on GitHub with full git history. Multi-mirror distribution via PyPI. Author-side single-maintainer continuity addressed per `MANUAL_REMEDIATION_AUTHOR.md` Item 7 (co-maintainer recruitment) and Item 8 (LF AI & Data Foundation Sandbox donation).

**BCR-02.1 — Are backups tested?**
The framework's authoritative copy is GitHub-hosted with GitHub-provided backup-and-recovery infrastructure. Author maintains an additional local clone updated daily. Restoration tested quarterly.

### CCC — Change Control & Configuration Management

**CCC-01.1 — Are changes documented and reviewed?**
Yes. Every code change is a pull request with required review per `CONTRIBUTING.md`. ADRs for architectural decisions. CHANGELOG for every release. Branch protection rules enforce review.

**CCC-02.1 — Is software development lifecycle documented?**
Yes. `CONTRIBUTING.md` is the operative SDLC documentation. Pre-commit hooks (ruff + mypy) enforce code-style and type-checking at commit time. CI pipeline enforces test + lint + coverage at PR time.

### DSI — Data Security & Information Lifecycle

**DSI-01.1 — Is data classified?**
Yes. Public (open-source code, documentation, public-website content) vs Engagement-Confidential (advisory-engagement materials) vs Internal (NTCI Consulting, LLC operating documents).

**DSI-02.1 — Is data labeling applied?**
Yes. Public data carries no marking (the open-source repository is by default public). Engagement-confidential data carries the engagement-letter cover page that identifies the engagement and the confidentiality scope. Internal data carries the entity-internal marking.

**DSI-03.1 — Is data handling controlled?**
Yes. Public data is published per the open-source license; no handling restriction beyond the license. Engagement-confidential data handled per engagement-letter confidentiality clause. Internal data handled per the entity's operating documents.

### DCS — Datacenter Security

**DCS-01.1 — Are datacenter physical access controls in place?**
The framework is hosted by GitHub (US) and PyPI (US); their respective datacenter physical access controls govern. The author has no dedicated datacenter; the home office in Dallas, Texas is the operating location.

### EKM — Encryption & Key Management

**EKM-01.1 — Are encryption keys managed?**
Yes. The framework's hash-chain ledger uses SHA-256 (per `src/finserv_agent_audit/governance/audit_chain.py`). Adopter-deployed key management is the adopter's responsibility per the framework's Protocol seam design. Release signing uses Sigstore cosign with GitHub OIDC token issuance — no long-lived signing keys held by the author.

**EKM-02.1 — Are encryption algorithms approved?**
Yes. SHA-256 (FIPS 180-4 approved). RFC 3161 timestamping. Sigstore cosign uses standard ECDSA + Rekor. TLS 1.2+ for all transport.

### GRM — Governance & Risk Management

**GRM-01.1 — Is governance documented?**
Yes. `OWNERSHIP.md` (IP-holding entity), `CONTRIBUTING.md` (contribution governance), `CODE_OF_CONDUCT.md` (community governance). TSC charter pending per `MANUAL_REMEDIATION_AUTHOR.md` Item 7.

**GRM-02.1 — Is risk management documented?**
Yes. Threat model in `ARCHITECTURE.md` § Threat Model and ADR-0018. Operational risk per `docs/ETHICS_WALL.md` annual review cadence. Per-engagement risk per engagement-letter Risk Annex.

### HRS — Human Resources

**HRS-01.1 — Are background checks performed?**
The framework is single-maintainer at the date of this document. Author's background is public per the author's professional profile. Co-maintainer background-check policy is a TSC-charter item per Item 7.

**HRS-02.1 — Are employees trained on security?**
The framework is single-maintainer. Author maintains current professional certifications and continuing education. Co-maintainer training policy is a TSC-charter item.

### IAM — Identity & Access Management

**IAM-01.1 — Is identity management in place?**
Yes. GitHub identity for repository access. PyPI Trusted Publishing for release publish (no shared API tokens). Two-factor authentication required on author-side accounts.

**IAM-02.1 — Is access provisioning controlled?**
Yes. Repository collaborator additions reviewed quarterly. PyPI publish access controlled via GitHub Actions OIDC, not via shared tokens.

### IVS — Infrastructure & Virtualization Security

**IVS-01.1 — Is infrastructure hardened?**
The framework's primary infrastructure is GitHub Actions runners (ephemeral, GitHub-managed) and PyPI distribution (PyPI-managed). The author-side workstation runs commercial endpoint protection and current OS patches.

### IPY — Interoperability & Portability

**IPY-01.1 — Are data portability standards supported?**
Yes. The framework is open-source under MIT (Apache 2.0 dual-license under counsel review per Item 1); adopters can fork and continue maintenance at any time. Repository is git-based; portability is inherent.

### MOS — Mobile Security

**MOS-01.1 — Are mobile devices managed?**
Author-side mobile devices use commercial mobile-device management with full-disk encryption, biometric / PIN authentication, and remote-wipe capability. Engagement-confidential materials are not stored on author-side mobile devices.

### SEF — Security Incident Management, E-Discovery, & Cloud Forensics

**SEF-01.1 — Is incident response documented?**
Yes. `SECURITY.md` is the operative incident response procedure. GitHub Security Advisory protocol for public-disclosure-track incidents. Private security-advisory channel for embargoed disclosure.

**SEF-02.1 — Are incidents reported?**
Yes. Security advisories published per GitHub protocol. CHANGELOG entries for any release that addresses a security issue. Notification to known adopters where the issue requires adopter action.

### STA — Supply Chain Management, Transparency, & Accountability

**STA-01.1 — Are supplier dependencies documented?**
Yes. The framework has zero runtime dependencies (stdlib only per `pyproject.toml`). Optional integrations are import-guarded behind extras. Dev-time dependencies pinned and renovated quarterly. CycloneDX 1.7 ML-BOM + SPDX 3.0 AI Profile generated by AIBOMGenerator (v2.0) for every release.

**STA-02.1 — Are supplier risks assessed?**
Yes. The framework's supplier surface is GitHub + PyPI. Both are documented commitments under their respective terms-of-service. Optional integration dependencies are at adopter discretion.

### TVM — Threat & Vulnerability Management

**TVM-01.1 — Is vulnerability scanning performed?**
Yes. Per-PR dependency-vulnerability scan via GitHub-native tools (Dependabot). Pre-commit hooks run ruff + mypy. Public security advisories tracked via GitHub Security Advisory.

**TVM-02.1 — Is patch management performed?**
Yes. Dependency-pin updates on a quarterly cadence. Security-driven updates on demand per `SECURITY.md` response timeline. Releases tagged and signed per `RELEASE-INSTRUCTIONS.md`.

---

## Disclaimers attached to the pre-fill

1. **Pre-fill, not certification.** Per the standard CAIQ disclaimer convention, the answers are the author's good-faith answers as of the date of this document.
2. **Open-source-patterns scope.** The framework is open-source patterns code, not a cloud service. Many CAIQ controls (datacenter physical security, mobile device management at scale, supplier-risk-management of cloud sub-processors) are not in scope for the framework's surface and are answered to that effect.
3. **SOC 2 maturity.** Post-SOC-2 Type I (target Q4 2026), several "documented and observed" answers will additionally answer "audited by independent CPA firm."

---

## Related

- [`SIG_LITE_PREFILL.md`](SIG_LITE_PREFILL.md) — Shared Assessments SIG Lite pre-fill
- [`BITS_AUP_PREFILL.md`](BITS_AUP_PREFILL.md) — BITS Acceptable Use Policy pre-fill
- [`../SOC2_ENGAGEMENT_RFP.md`](../SOC2_ENGAGEMENT_RFP.md) — SOC 2 engagement RFP
- [`../../SECURITY.md`](../../SECURITY.md) — vulnerability response procedure
- [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md) — system architecture and threat model

---

*Vendor-questionnaire pre-fill, not certification.*
