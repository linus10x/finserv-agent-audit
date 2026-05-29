# SOC2_ENGAGEMENT_RFP.md — Request for Proposal · SOC 2 Type I → Type II

**Status:** v1.0 · Template · Last reviewed: 2026-05-28
**Audience:** Schellman, A-LIGN, Coalfire (or comparable AICPA-licensed CPA firms with documented OSS-project SOC 2 experience)
**Author contact:** Kunjar Bhaduri · kunjarbhaduri@gmail.com · Dallas, TX
**Engagement entity:** NTCI Consulting, LLC (per [`../OWNERSHIP.md`](../OWNERSHIP.md))

---

## Project context

`finserv-agent-audit` is an open-source governance framework for autonomous AI agents in regulated financial services. The repository ships under the MIT License (with Apache 2.0 dual-license under counsel review) at `https://github.com/linus10x/finserv-agent-audit`. The author publishes the framework as a reference patterns library and delivers productized advisory engagements to FSI buyers around its adoption.

The framework itself is software-as-source-code (a Python package, schemas, ADRs, and reference patterns). The proposed SOC 2 scope is not the *code* of the framework — code is software, not a service, and SOC 2 trust-services criteria do not apply to source code distributed under an open-source license. The proposed SOC 2 scope is the **process** by which the code is developed, released, and maintained: the code repository, the CI/CD pipeline, the release management process, the vulnerability response process, and the key management used to sign releases.

The objective of the SOC 2 engagement is to produce a Type I report (year 1) and a Type II report (year 2) that adopters and prospective enterprise buyers can attach to their vendor file. The target buyer is a Tier-1 US bank or asset manager whose vendor-risk-management team asks for SOC 2 status as a top-line gate.

---

## In-scope (proposed)

The following systems and processes are in-scope for the proposed engagement:

| In-scope system or process | Description |
|---|---|
| Source code repository | The `finserv-agent-audit` GitHub repository: branch protection rules, access control, commit signing, code-review enforcement |
| CI/CD pipeline | GitHub Actions workflows in `.github/workflows/`: test, lint, type-check, coverage, security-scan, release publish |
| Release management | Tag → build → sign → publish sequence to PyPI via Trusted Publishing (see [`PYPI_TRUSTED_PUBLISHING_SETUP.md`](PYPI_TRUSTED_PUBLISHING_SETUP.md)) |
| Vulnerability response | Issue intake, triage, fix, release, advisory publication per [`../SECURITY.md`](../SECURITY.md) |
| Key management for releases | GitHub OIDC token issuance to PyPI Trusted Publisher (no long-lived secrets); Sigstore cosign signature attestation |
| Dependency intake | The framework has zero runtime dependencies (stdlib only); dev-time dependencies are pinned in `pyproject.toml` and renovated on a quarterly cadence |

---

## Out-of-scope

The following are explicitly out-of-scope:

| Out-of-scope item | Reason |
|---|---|
| Adopter deployments | The framework is open-source software adopted by third parties; their deployments operate outside the engagement entity's controls |
| Advisory engagements | Diagnostic / Audit / Retainer engagements are delivered under separate engagement letters with their own confidentiality and security commitments; these may be in-scope of a future separate SOC 2 engagement |
| Author personal infrastructure | The author's personal laptop, personal email, and personal browser are out of scope; engagement-relevant work product is stored in the entity's controlled storage |
| Adopter-side substrate | The framework's hash-chain ledger, WORM persistence, TSA timestamp source, witness register, and MI-proxy implementations are pluggable Protocol seams (see [`../ARCHITECTURE.md`](../ARCHITECTURE.md)); the adopter chooses the substrate, and the substrate's SOC 2 posture is the adopter's responsibility |

---

## Trust Services Criteria scope

The engagement is scoped against the AICPA Trust Services Criteria (TSP Section 100):

| TSC | Engagement scope |
|---|---|
| CC1 — Control Environment | In-scope. Documented in `OWNERSHIP.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and engagement-entity operating documents |
| CC2 — Communication and Information | In-scope. Documented in `SECURITY.md`, `CHANGELOG.md`, release notes, and the public issue tracker |
| CC3 — Risk Assessment | In-scope. Documented in `ARCHITECTURE.md` threat model, ADR-0018, `FAILURE-MODES.md`, `LIMITATIONS.md`, `NEGATIVE-USE-CASES.md` |
| CC4 — Monitoring Activities | In-scope. CI pipeline test pass rate, coverage trend, dependency-vulnerability scan output |
| CC5 — Control Activities | In-scope. Branch protection, code review, signed commits, two-factor on GitHub, PyPI Trusted Publishing |
| CC6 — Logical and Physical Access Controls | In-scope. GitHub access control + PyPI access control; physical access not in scope (no physical premises) |
| CC7 — System Operations | In-scope. CI/CD operation, release publish, incident response |
| CC8 — Change Management | In-scope. PR review, version bump, CHANGELOG update, release-instructions adherence |
| CC9 — Risk Mitigation | In-scope. `SECURITY.md` vulnerability response procedure, dependency-pin discipline, SBOM publication |
| A1 — Availability | In-scope, minimal. PyPI is the distribution surface; PyPI uptime is PyPI's responsibility. Engagement-entity availability commitment is best-effort for issue response per `SECURITY.md` |
| C1 — Confidentiality | Out of scope. The framework is open-source; there is no confidentiality commitment to adopters of the open-source code. Confidentiality commitments to advisory-engagement clients are governed by individual engagement letters |
| PI1 — Processing Integrity | Out of scope. The framework's correctness is asserted via tests; SOC 2 PI scope is not the right vehicle for code-correctness assertions |
| P1 — Privacy | Out of scope. The engagement entity does not collect personal data from open-source adopters |

---

## Timeline

| Milestone | Target | Notes |
|---|---|---|
| RFP issued | 2026-Q3 | Issued in parallel to three firms |
| Bid responses | 2026-Q3 + 4 weeks | Author reviews; counsel reviews engagement-letter language |
| Engagement-letter signature | 2026-Q3 + 8 weeks | After firm selection and counsel review |
| Kickoff | 2026-Q3 + 10 weeks | Control matrix walkthrough |
| Readiness assessment | 2026-Q3 → 2026-Q4 | Author closes gaps identified in readiness |
| Type I report | 2026-Q4 (end-of-year target) | Point-in-time assessment |
| Type II observation period start | 2026-Q4 (same date as Type I) | 12-month observation |
| Type II observation period end | 2027-Q4 | |
| Type II report | 2027-Q4 (end-of-year target) | Recurring annual thereafter |

---

## Budget tier expectation

The author has anchored the budget at the OSS-project SOC 2 market rate as of 2026:

| Report | Budget tier expectation |
|---|---|
| Type I, year 1 | $30,000 - $75,000 |
| Type II, year 2 + recurring | $50,000 - $120,000 / yr |

Bids meaningfully outside these tiers should explain the variance in the bid response. The author values scope precision over price; an underbid that does not include readiness assessment, control-matrix design, or evidence collection is harder to use than an in-tier bid that includes them.

---

## Special requirements

**S1. Open-source-aware engagement.** The framework is open-source (MIT, with Apache 2.0 dual-license under counsel review). The bidder must understand that the audit applies to the *process* by which the open-source code is developed, released, and maintained, not to the code itself. Bidders who do not understand this distinction will produce a Type I report that is unusable in vendor-questionnaire contexts.

**S2. Counsel-reviewed engagement letter.** The engagement letter is subject to counsel review by the author's IP counsel. Bidders may submit their standard engagement letter template with the bid; the author will redline as needed.

**S3. No conflicting consulting engagement.** The bidder must not provide consulting services that would create an independence conflict with the SOC 2 audit (per AICPA independence standards). The bidder confirms in the bid response that no conflicting engagement exists.

**S4. References from OSS-project SOC 2 engagements.** The bidder provides three (3) references from prior OSS-project SOC 2 engagements (Linux Foundation projects, CNCF projects, OSS-company SOC 2s, or comparable). The author will contact at least two references before signing the engagement letter.

**S5. Named partner continuity.** The bidder commits in the bid response that the named partner on the engagement will continue to serve the engagement through the Type II report cycle, absent extraordinary circumstance.

---

## Bid response format

The bid response is a single PDF (or DOCX) covering:

1. Firm overview (1 page)
2. Named engagement team (lead partner, manager, senior; CVs or brief bios) (1 page)
3. Three OSS-project SOC 2 references (firm, project name, year, named partner on that engagement) (1 page)
4. Proposed engagement scope (in-scope / out-of-scope, TSC selection — confirming or modifying the proposed scope in this RFP) (1 page)
5. Proposed timeline (confirming or modifying the proposed timeline in this RFP) (1 page)
6. Pricing (Type I year 1 fixed fee + Type II year 2 fixed fee + recurring annual fee for years 3+) (1 page)
7. Special-requirement responses (one per S1-S5 above) (1-2 pages)
8. Engagement-letter template (standard form; redlines welcome from author) (attachment)

Total expected length: 8-15 pages plus the engagement-letter attachment.

---

## Bid submission

Submit bid response to **kunjarbhaduri@gmail.com** with subject prefix **`[SOC2 RFP]`** by the close of 2026-Q3 + 4 weeks. The author confirms receipt within 2 business days. Questions on the RFP are welcome on the same email; questions and answers are circulated to all three bidders to maintain bid parity.

---

## Author's posture

The author values a long-term audit relationship over a one-cycle engagement. The Type I report is the entry; the Type II report at year 2 is where the relationship becomes operationally meaningful. The author is willing to pay a market-rate fee for an audit firm that understands the OSS-project context and that will scale with the engagement entity as the advisory practice grows.

---

## Related

- [`../OWNERSHIP.md`](../OWNERSHIP.md) — engagement entity
- [`../SECURITY.md`](../SECURITY.md) — vulnerability response procedure
- [`PYPI_TRUSTED_PUBLISHING_SETUP.md`](PYPI_TRUSTED_PUBLISHING_SETUP.md) — release publishing infrastructure
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — system architecture, threat model context
- [`../MANUAL_REMEDIATION_AUTHOR.md`](../MANUAL_REMEDIATION_AUTHOR.md) — Item 5 (this RFP)

---

*RFP template. Counsel review of any returned engagement letter is required before signature.*
