# MANUAL_REMEDIATION_AUTHOR.md — Tier-2 author-action backlog

**Status:** v1.0 · Last reviewed: 2026-05-28
**Audience:** the author (Kunjar Bhaduri). NOT a public-facing document by intent — committed to the repo for transparency, but the operative voice here is operator-to-operator.
**Companion:** This doc closes the structural / commercial findings from the v2.0 → v2.1 adversarial-review sweep that cannot be closed in code by the parent agent. Code-level findings (CR-1 … CR-12) sit in the parent agent's worklog; this doc captures the twelve author-action items that require entity formation, counsel review, insurance procurement, professional engagement, or trademark filing.

> **How to use this doc.** Read top to bottom once. Each item has a checkbox; mark `[x]` as you complete. The order below reflects sequencing (entity formation precedes insurance precedes vendor questionnaires). Cost and timeline estimates are budgeting anchors, not bids. All commercial decisions go through your IP counsel and CPA of record before execution.

---

## Table of contents

1. [Item 1 — Dual-license to Apache 2.0](#item-1--dual-license-to-apache-20)
2. [Item 2 — Form IP-holding entity + fill `OWNERSHIP.md`](#item-2--form-ip-holding-entity--fill-ownershipmd)
3. [Item 3 — Form separate advisory entity from NTCI + ethics wall](#item-3--form-separate-advisory-entity-from-ntci--ethics-wall)
4. [Item 4 — Procure E&O + cyber insurance](#item-4--procure-eo--cyber-insurance)
5. [Item 5 — Engage CPA firm for SOC 2 Type I → Type II](#item-5--engage-cpa-firm-for-soc-2-type-i--type-ii)
6. [Item 6 — File USPTO trademark for "Autonomy Ladder" + publish `TRADEMARK.md`](#item-6--file-uspto-trademark-for-autonomy-ladder--publish-trademarkmd)
7. [Item 7 — Recruit co-maintainers → Technical Steering Committee](#item-7--recruit-co-maintainers--technical-steering-committee)
8. [Item 8 — LF AI & Data Foundation Sandbox application](#item-8--lf-ai--data-foundation-sandbox-application)
9. [Item 9 — Downgrade `Development Status :: 5` classifier → `4 - Beta`](#item-9--downgrade-development-status--5-classifier--4---beta)
10. [Item 10 — Rewrite or NDA-restrict Schwab Matter 4 in `fsi_settled_matters.md`](#item-10--rewrite-or-nda-restrict-schwab-matter-4-in-fsi_settled_mattersmd)
11. [Item 11 — Publish Cohort-Zero $1K pricing on `autonomy-ladder.io/services`](#item-11--publish-cohort-zero-1k-pricing-on-autonomy-ladderioservices)
12. [Item 12 — Pursue FRM (GARP) or CISSP credential](#item-12--pursue-frm-garp-or-cissp-credential)
13. [Sequencing summary](#sequencing-summary)
14. [Cost roll-up](#cost-roll-up)

---

## Item 1 — Dual-license to Apache 2.0

- [ ] **Status: pending author + counsel decision**

**The finding.** The repo ships MIT-only. Several Tier-1 buyers (JPMorgan Chase, Goldman Sachs, Capital One, Wells Fargo, BNY Mellon, Morgan Stanley) prefer or require Apache 2.0 for incoming open-source dependencies because Apache 2.0 carries an explicit patent grant. MIT does not. The patent-grant gap is the single most-cited blocker in vendor open-source-intake review at large US banks.

**Why it blocks Tier-1 adoption.** JPMorgan Chase OSS-intake (per their public OSS contribution guidelines) prefers Apache 2.0 for any incoming dependency that ships code that could plausibly be the subject of a future patent claim. Goldman Sachs' OSS-intake policy treats Apache 2.0 as the default acceptance license and treats MIT as a case-by-case review. Capital One's open-source program office documents the same preference. The framework's claims around novel patterns (sovereign veto, autonomy-ladder governance, the four protocol seams in CR-5) make the patent-grant gap material — counsel could read the MIT-only posture as leaving Apache 2.0 firms exposed.

**Action required.**

1. **Counsel review (required before any license change).** Engage IP counsel for a one-hour consultation. Question to put on the table: "Is dual-licensing under MIT + Apache 2.0 (adopter chooses) the right posture, or should the project re-license Apache-2.0-only with `LICENSE-MIT` retained for adopters who specifically request MIT terms?" The answer depends on your counsel's read of the patent-grant exposure and on whether any third-party contributor has already submitted code under MIT-inbound that would need re-licensing consent.
2. **If dual-license:** keep current `LICENSE` (MIT), add `LICENSE-APACHE-2.0` (shipped in this commit). Update `README.md` license section to read: "Licensed under the MIT License AND the Apache License, Version 2.0. Adopters may choose either license at their option. See `LICENSE` and `LICENSE-APACHE-2.0`."
3. **If Apache-2.0-only:** rename `LICENSE` → `LICENSE-MIT`, rename `LICENSE-APACHE-2.0` → `LICENSE`. Update `pyproject.toml` `license = { text = "Apache-2.0" }`. Update `CITATION.cff` `license: Apache-2.0`. Update `OWNERSHIP.md`, `DISCLAIMER.md`, `CONTRIBUTING.md` references from "MIT" to "Apache 2.0" (or "MIT or Apache 2.0" for dual). Add a `NOTICE` file at repo root (Apache 2.0 attribution-notice file: copyright Kunjar Bhaduri 2026; project name; URL).
4. **Either path:** announce in `CHANGELOG.md` under v2.1 release. Pin the announcement in `README.md` for one full release cycle.

**Estimated cost + timeline.** $750-$2,500 for one-hour counsel consultation (IP attorney, hourly $400-$700 in DFW market). Author execution time: 2-3 hours (file rename, README/pyproject/CITATION edits, CHANGELOG entry, NOTICE file). Total wall clock: 5 business days (counsel scheduling lag dominates).

**What's already in this commit.**

- `LICENSE-APACHE-2.0` — full Apache 2.0 text, copyright Kunjar Bhaduri 2026, ready to use.
- This author-action doc preserves the existing `LICENSE` (MIT) untouched. Per the parent agent's working rules, the existing `LICENSE` is NOT modified until counsel approves the re-license — this is the single highest-stakes file in the repo from an adopter-rights perspective.

---

## Item 2 — Form IP-holding entity + fill `OWNERSHIP.md`

- [ ] **Status: pending entity formation**

**The finding.** `OWNERSHIP.md` carries two `[PLACEHOLDER]` blocks: the IP-holding entity field and the acquisition-readiness statement. The placeholders flag to a sophisticated reader (M&A counsel, search-fund principal, search-firm researcher) that the IP estate is currently held by an individual, not a formed entity. For acquihire scenarios that price the IP estate at a multiple of operator salary, the cleanest acquisition surface is an LLC or C-corp with a clean cap table and a single named signatory.

**Why it blocks Tier-1 adoption.** Two blocker patterns: (1) corporate development at a bank or PE-backed portco will not engage on commercial-license terms with an individual; they require a counterparty entity with EIN, registered agent, and standing for contract execution; (2) the placeholder reads as "not ready for serious conversation" to any acquirer scoping a buy-vs-build decision against the framework.

**Action required.**

1. **Form the entity.** The recommended default is **NTCI Consulting, LLC**, a Texas single-member LLC, principal place of business Dallas, Texas, authorized signatory Kunjar Bhaduri. Texas LLC formation is filed via the Texas Secretary of State (Form 205, $300 filing fee, online via SOSDirect). For acquisition-readiness optimization, the alternative is a Delaware C-corp (Form 1, $89 filing fee + $50/yr franchise tax minimum, online via Delaware Division of Corporations) — Delaware C-corp is the form acquirers expect for sub-$50M asset purchases, but adds annual filing complexity and the federal corporate-tax surface. Author decision deferred to counsel + CPA.
2. **EIN.** File IRS Form SS-4 online (free, immediate issuance for US-formed entities with a US-resident signatory).
3. **Registered agent.** Texas LLCs require a registered agent with a Texas street address. Author may serve as own registered agent if Dallas address is acceptable; otherwise use a commercial registered agent ($100-$300/yr).
4. **Operating agreement.** Single-member LLC operating agreement (template available from any startup-attorney form library; counsel review $500-$1,500). Records who owns the membership interest (Kunjar Bhaduri, 100%), who has signing authority, what triggers dissolution.
5. **Bank account.** Open a business checking account in the entity name. Required for separation of personal and business funds (the LLC liability shield depends on it).
6. **Assign IP.** Author signs an IP assignment from individual → LLC for all copyright, trademark, and trade-secret rights in the framework. Counsel-drafted template ($500-$1,500). Filed in the LLC's permanent records.
7. **Update `OWNERSHIP.md`.** Replace the two `[PLACEHOLDER]` blocks per the defaults below; commit the update with the LLC formation date as the effective date.

**Defaults for `OWNERSHIP.md` (author confirms before merging):**

- **IP-holding entity:** NTCI Consulting, LLC (a Texas limited liability company), formed [DATE], EIN [REDACTED-public-safe-citation], principal place of business Dallas, Texas, authorized signatory Kunjar Bhaduri. (Author may amend to Delaware C-corp if pursuing acquisition; the entity-formation tradeoff is documented above.)
- **Founded:** 2026
- **Principal place of business:** Dallas, Texas
- **Authorized signatory:** Kunjar Bhaduri
- **Acquisition readiness statement:** "The author entertains acquisition discussions. Framework IP is held in a single entity (NTCI Consulting, LLC) to preserve a clean cap table for acquihire or asset-purchase scenarios. Preferred deal-shape conversation: asset purchase of the IP estate (copyright + trademark + trade-secret), with the author available for 6-12 month transition consulting at market rate. Standing constraints: no right-of-first-refusal commitments; no exclusive license commitments; no prior licensee obligations beyond the open-source license terms governing existing adopters. Contact: kunjarbhaduri@gmail.com with subject prefix `[ACQUISITION]` for routing distinct from general support."
- **Contributor IP assignment:** "Apache 2.0 ICLA template required for non-trivial contributions (template referenced from `CONTRIBUTING.md` once the LF AI & Data Foundation Sandbox application is in motion; until then, the GitHub-default inbound-license-equals-outbound-license posture continues to apply)."

**Estimated cost + timeline.** $1,500-$5,000 all-in (Texas LLC filing $300 + counsel review of operating agreement $500-$1,500 + IP-assignment doc $500-$1,500 + registered agent year 1 $100-$300 + bank account opening $0). Delaware C-corp path: $3,000-$10,000 all-in (filing $89 + registered agent $300 + counsel for corp formation $2,000-$5,000 + initial 83(b) election filing if single-founder common stock issued + first-year franchise tax). Total wall clock: Texas LLC 5-10 business days; Delaware C-corp 15-30 business days.

**What's already in this commit.**

- `OWNERSHIP.md` is NOT modified in this commit. The placeholders remain so the author has the choice to file the entity first and then update with the entity's actual formation date and EIN, rather than committing speculative entity details.

---

## Item 3 — Form separate advisory entity from NTCI + ethics wall

- [ ] **Status: pending counsel decision**

**The finding.** NTCI is referenced in this repo (`CITATION.cff` affiliation: "North Texas Capital Investments") AND in the author's public brand surfaces (autonomy-ladder.io) AND in the author's private quantitative research program ("NTCI as self-funded AI research lab" per the author's master identity document). The same name is being used for two distinct activities: (1) a private quantitative research / proprietary trading program and (2) an open-source-and-advisory framework around regulated-AI governance. A sophisticated FSI compliance reviewer reads this as an unmanaged conflict-of-interest surface: if the advisory entity advises a buy-side firm on AI governance while the research entity trades the same securities the buy-side firm holds, the framework's credibility takes a hit and the advisory entity becomes a regulator question.

**Why it blocks Tier-1 adoption.** Buy-side compliance at firms like Bridgewater, AQR, Citadel, Millennium, Two Sigma will not engage an advisor whose related entity trades. The Investment Advisers Act of 1940 § 202(a)(11) definition of "investment adviser" turns on giving advice about securities for compensation; the framework's commercial-advisory path (Diagnostic → Audit → Retainer) sits close enough to "advice about securities for compensation" that the lab's trading activity needs an explicit ethics-wall disclosure or a counsel-vetted carve-out. The cleanest fix is a separate advisory entity with documented information barriers.

**Action required.**

1. **Counsel call.** One hour with IP / securities counsel. Question: "Does NTCI's research-lab activity rise to the level of investment adviser under § 202(a)(11), and if so, is the cleanest fix (a) registering NTCI as a state-registered investment adviser (Form ADV); (b) reorganizing into two entities with a documented ethics wall; or (c) confirming the research lab's activity falls within the § 203(b) exemptions and documenting that determination in counsel's file?"
2. **If two-entity structure:** form NTCI Consulting, LLC for advisory + open-source IP (per Item 2 above) and keep NTCI (the research lab) under its existing structure. Publish `docs/ETHICS_WALL.md` (shipped in this commit) documenting the information barriers, pre-clearance process, and disclosure paragraph.
3. **Engagement-letter template.** Every advisory engagement letter executed by NTCI Consulting, LLC must include the ethics-wall disclosure paragraph drafted in `docs/ETHICS_WALL.md`.
4. **Annual review.** Counsel reviews the ethics-wall posture annually. If the research lab's trading activity changes scope (e.g. moves from paper-trading Phase 0 to deployed capital), the review triggers immediately, not at the annual cadence.

**Estimated cost + timeline.** $1,500-$5,000 for one-hour counsel call + counsel-drafted ethics-wall framework + engagement-letter template language. Annual review thereafter $500-$1,500. Total wall clock: 10-15 business days (counsel scheduling).

**What's already in this commit.**

- `docs/ETHICS_WALL.md` — the documented information barriers, pre-clearance process, and engagement-letter disclosure paragraph. Author reviews with counsel before relying on this in any commercial conversation.

---

## Item 4 — Procure E&O + cyber insurance

- [ ] **Status: pending broker engagement**

**The finding.** The repo ships an MIT-licensed framework with extensive disclaimers (`DISCLAIMER.md`, `LIMITATIONS.md`, `NEGATIVE-USE-CASES.md`) but no underlying insurance behind the disclaimers. The disclaimers are necessary and well-drafted; they are not a substitute for insurance. For the commercial-advisory path (Diagnostic / Audit / Retainer engagements with named clients), errors-and-omissions (E&O) insurance is the standard market practice and is routinely required in Master Services Agreement boilerplate at any Tier-1 buyer. Cyber insurance is the standard market practice for any party that touches client data, even if the touch is incidental (e.g. a client emails a redacted log file as an attachment to a Diagnostic engagement).

**Why it blocks Tier-1 adoption.** Tier-1 MSA boilerplate (sample sources: JPMorgan Chase OneSourcing, Goldman Sachs vendor MSA, Capital One supplier MSA, BNY Mellon supplier MSA) routinely requires the supplier to carry: (1) E&O insurance with $1M-$5M per-claim limits; (2) cyber insurance with $1M-$5M per-claim limits; (3) general commercial liability with $1M per-occurrence / $2M aggregate; (4) workers' comp per state minimums (waived for single-member LLCs in Texas where the sole member is the only worker). Without these in place, the supplier cannot pass MSA intake.

**Action required.**

1. **Engage a commercial-insurance broker.** Recommended broker classes: a regional independent commercial-lines broker (DFW market: Higginbotham, Lockton, Hub International, Marsh McLennan Agency). Independent brokers shop multiple carriers; captive agents (one carrier only) limit the market.
2. **Quote specification.** Request quotes for: E&O ($1M / $3M aggregate to start; can scale to $5M / $10M for Tier-1 engagements that require it); cyber ($1M / $3M aggregate to start, with ransomware sub-limit not less than the main limit, and with breach-counsel + forensics included); general commercial liability ($1M / $2M); commercial property (waived if no leased office); cyber-incident response retainer (some carriers bundle).
3. **Disclose the open-source framework.** When the broker submits the application to carriers, disclose that the author publishes open-source software under MIT / Apache 2.0 (per Item 1) and that some adopters may attempt to claim coverage incidentally. Underwriters need this disclosure; surprises trigger denials.
4. **Disclose the advisory-engagement scope.** Same disclosure: the author runs a productized advisory practice (Diagnostic $5K / $1K Cohort-Zero per Item 11 / Audit $40K / Retainer $15K/q) targeting Private Capital and CRE buyers. Underwriters price on revenue band; understate and you risk a coverage gap, overstate and you overpay.
5. **Bind coverage.** Bind before the first commercial engagement letter is signed. Insurance procured after the act giving rise to a claim does not cover the act.

**Estimated cost + timeline.** E&O $2,500-$8,000/yr for the recommended limits at the author's revenue band (depends heavily on claims history, scope, and carrier appetite for advisory/consulting risk in regulated FSI); cyber $1,500-$5,000/yr; commercial liability $500-$1,500/yr. Total annual premium budget: $4,500-$14,500. Broker fee typically zero (broker is paid by carrier commission). Total wall clock: 10-20 business days (broker shops quotes, underwriting questions take 5-10 business days each).

**What's already in this commit.** Nothing. Insurance procurement is an external workflow; this doc captures the spec.

---

## Item 5 — Engage CPA firm for SOC 2 Type I / II

- [ ] **Status: pending RFP**

**The finding.** Tier-1 FSI vendor questionnaires (SIG Lite, CAIQ, BITS AUP — see Item 11 below) ask SOC 2 status as a top-line gate. The framework currently has no SOC 2 report. The ASSURANCE-GUIDE explicitly states the framework is governance scaffolding, not a service — and that is correct — but the *process* (code repo, CI/CD, release management, vulnerability response) IS auditable under SOC 2, and a SOC 2 Type I report on the *process* gives Tier-1 buyers something to attach to their vendor file even where the framework itself is open-source.

**Why it blocks Tier-1 adoption.** Vendor-risk-management teams at large banks are gated by checklists; "no SOC 2 report" is a hard gate at most Tier-1 buyers for any supplier touching their environment (advisory engagement, code dependency intake, or both). A SOC 2 Type I on the framework's release process gives them a defensible "we reviewed the supplier's controls" entry for their vendor file, even where the supplier-controls scope is narrow.

**Action required.**

1. **Send the SOC 2 engagement RFP** (`docs/SOC2_ENGAGEMENT_RFP.md` shipped in this commit) to three CPA firms: Schellman, A-LIGN, Coalfire. These three are the OSS-aware SOC 2 firms most often cited in OSS-project SOC 2 reports (Linux Foundation projects, CNCF projects, open-source company SOC 2s). All three have engagement-letter templates for narrow-scope Type I engagements.
2. **Compare bids on:** (a) total fee for Type I (year 1) + Type II (year 2); (b) named partner experience with OSS-project SOC 2 (request 3 references); (c) acceptable trust-services-criteria scope (CC1-CC9 at minimum; A1 Availability minimal scope); (d) timeline to first Type I report (target Q4 2026); (e) auditor-of-record acceptance at Tier-1 buyers (all three above are acceptable at every Tier-1 FSI buyer — confirm with the buyer's vendor team if uncertain).
3. **Pick one and sign engagement letter.** Standard CPA engagement letter is a 10-15 page document; counsel review before signing ($500-$1,500).
4. **Kickoff Q3 2026; Type I report Q4 2026; Type II observation period Q4 2026 → Q3 2027; Type II report Q4 2027.** This is the standard sequencing; compressing it costs more and is rarely worth it for a first-time SOC 2.

**Estimated cost + timeline.** Type I report: $30,000-$75,000 (narrow scope, single-person operation). Type II report: $50,000-$120,000/yr (annual recurring). Counsel review of engagement letter: $500-$1,500. Internal-readiness work (policies, evidence collection, control matrix): 80-160 hours of author time (cannot be outsourced effectively for a first-time SOC 2). Total wall clock: 12 months kickoff → Type I report; 24 months to Type II report.

**What's already in this commit.**

- `docs/SOC2_ENGAGEMENT_RFP.md` — single-page RFP the author sends to the three CPA firms above. Includes scope, trust-services criteria, timeline, budget tier expectation, and the request for 3 references from OSS-project SOC 2 engagements.

---

## Item 6 — File USPTO trademark for "Autonomy Ladder" + publish `TRADEMARK.md`

- [ ] **Status: pending USPTO filing**

**The finding.** "Autonomy Ladder" is the framework's headline term and the brand under which the cross-vertical discipline (this repo + `cre-agent-audit` + future siblings) is published. The mark is in use as a common-law mark across the author's published surfaces. No federal trademark registration exists yet. Without a registration, the mark is exposed to a third party filing for a similar mark in the same classes and forcing a rebrand or an opposition proceeding.

**Why it blocks Tier-1 adoption.** Two patterns: (1) Tier-1 enterprise procurement reviewers ask "is the mark you're licensing me registered?" — they want a TM ID number, not a common-law claim; (2) any acquirer pricing the IP estate (per Item 2 above) prices the trademark as a separate asset, and an unregistered mark is priced at a discount to a registered mark.

**Action required.**

1. **Trademark search.** Run a clearance search via `tmsearch.uspto.gov` (USPTO TESS was retired in 2023; tmsearch.uspto.gov is the current system). Search "Autonomy Ladder" exact + "Autonomy" wildcard + phonetic variants ("Autonomie Ladder", "Auto-Ladder", etc.). Counsel-run search is the gold standard; self-service search via tmsearch.uspto.gov is the budget version.
2. **File the application.** USPTO classes: 9 (downloadable software), 35 (business consulting services), 41 (educational services), 42 (technology consulting). Filing basis: § 1(a) use-in-commerce for classes already in use (35, 41, 42 for the advisory and educational surfaces) or § 1(b) intent-to-use for classes not yet in commercial use (9 for the software product if no commercial licensing has occurred yet). Filing fee: $350 per class for TEAS Standard filing, $250 per class for TEAS Plus if the specimen and goods-and-services description are filed correctly the first time. Four classes × $350 = $1,400 in filing fees; or four classes × $250 = $1,000 if TEAS Plus.
3. **Specimen filing.** For each class, a specimen showing the mark in use (screenshot of autonomy-ladder.io, screenshot of github.com/linus10x/finserv-agent-audit README banner, advisory engagement-letter cover page, workbook PDF cover).
4. **Counsel review.** Recommended for first-time filer. Counsel-handled USPTO filing fee: $1,000-$2,500 above the USPTO filing fees themselves.
5. **Office actions.** USPTO examining attorney issues an office action ~3-4 months after filing. Response window is 3 months (extendable once for a fee). Counsel-handled response: $500-$2,000 per office action.
6. **Publication.** If accepted, mark publishes for opposition (30 days). If no opposition, registration issues ~6-12 months after publication.
7. **Publish `docs/TRADEMARK.md`** (shipped in this commit) describing permitted uses, prohibited uses, fair-use carve-out, and contact for trademark inquiries.

**Estimated cost + timeline.** $3,400-$3,900 all-in (USPTO fees $1,000-$1,400 + counsel filing $1,000-$2,500). Office-action response budget: $500-$2,000. Total budget envelope: $4,000-$6,000 to registration. Total wall clock: 9-15 months from filing to registration. Filing target: **June 15, 2026** per the author's master identity document.

**What's already in this commit.**

- `docs/TRADEMARK.md` — trademark usage guidelines for the framework. Author reviews with counsel before publishing publicly (the guidelines document is itself a trademark-policy artifact and counsel may want changes).

---

## Item 7 — Recruit co-maintainers → Technical Steering Committee

- [ ] **Status: pending recruitment**

**The finding.** The framework currently ships single-maintainer (`CONTRIBUTING.md`: "Maintainership is currently single-maintainer; expansion to a multi-maintainer model is on the roadmap once contribution volume justifies it"). Tier-1 OSS-intake reviewers ask about bus-factor (what happens if the sole maintainer is hit by a bus) as a routine vendor-risk question. The current answer — "nothing; the MIT/Apache license preserves the adopter's right to fork and continue" — is technically correct but is read as inadequate by procurement.

**Why it blocks Tier-1 adoption.** Vendor-risk-management teams at large banks have explicit bus-factor scoring rubrics. Single-maintainer projects score the lowest. Two-maintainer with documented succession planning scores higher. Linux-Foundation-hosted projects score the highest (because the Foundation provides neutral home governance). Item 8 below addresses LF AI & Data Foundation Sandbox; this item addresses the precursor — a documented Technical Steering Committee.

**Action required.**

1. **Publish the recruitment post.** `docs/CO_MAINTAINER_RECRUITMENT_DRAFT.md` (shipped in this commit) is the LinkedIn-friendly version. Cross-post to GitHub Discussions and to the author's X account.
2. **Filter applicants.** Profile target: FSI engineering leader OR AI-governance researcher with published work in regulated-AI compliance OR a senior engineer at a Tier-1 bank with explicit permission from their employer to maintain open-source on company time. Avoid: vendors whose product competes with the framework; consultants whose practice would benefit from "co-maintainer" credit without contribution; PhD students whose advisor's lab competes for credit.
3. **30-minute interview.** Discuss: time commitment (1 hour/week review cadence + quarterly TSC meeting), commit-access expectations, conflict-of-interest disclosure (their employer's policies on OSS contribution), co-author rights on the next major release.
4. **Charter the TSC.** Once two co-maintainers are confirmed, publish `docs/TSC_CHARTER.md` (not in this commit — to be drafted after recruitment; the charter is downstream of who joins). Standard charter elements: membership terms (12 months renewable), voting rules (lazy consensus + 3-day window for objection), decision scope (technical direction, release approval, contributor escalation), conflict-of-interest disclosure, quorum (2 of 3).
5. **Update `OWNERSHIP.md`** and `CONTRIBUTING.md` once the TSC is chartered.

**Estimated cost + timeline.** Zero cost (volunteer co-maintainer model). Author time: 4-6 hours of interview + charter drafting. Total wall clock: 60-day recruitment window (recommended); could compress to 30 days if the author already has candidates in mind from their LinkedIn network.

**What's already in this commit.**

- `docs/CO_MAINTAINER_RECRUITMENT_DRAFT.md` — the LinkedIn-friendly recruitment post.

---

## Item 8 — LF AI & Data Foundation Sandbox application

- [ ] **Status: pending application**

**The finding.** Tier-1 FSI buyers prefer neutral-home open-source projects (Linux Foundation, Apache Foundation, CNCF) over individual-author projects for the same vendor-risk-management bus-factor reason as Item 7. Donation to the Linux Foundation AI & Data Foundation as a Sandbox project solves the bus-factor concern AND solves the Tier-1-concentration-risk concern (the buyer is no longer dependent on a single supplier) in one move. The application is non-trivial (60+ pages of governance documentation, charter, code-of-conduct review, neutral-domain transfer) and takes 6-9 months to Sandbox stage, 18-24 months to Incubation, multi-year to Graduated.

**Why it blocks Tier-1 adoption.** Without an LF / neutral-home affiliation, the project will always score below an LF-hosted equivalent at any Tier-1 buyer's vendor-risk review. Sandbox-stage is the minimum threshold most buyers recognize.

**Action required.**

1. **Pre-application checklist.** Per the LF AI & Data Foundation Sandbox application requirements (see `docs/LFAI_SANDBOX_APPLICATION_DRAFT.md` shipped in this commit): (a) Apache 2.0 license (per Item 1); (b) clear governance (per Item 2 + Item 7); (c) public code-of-conduct (already in repo: `CODE_OF_CONDUCT.md`); (d) public contribution guide (already in repo: `CONTRIBUTING.md`); (e) neutral domain (autonomy-ladder.io is currently author-owned; donation includes domain transfer to LF); (f) public roadmap (already in repo: `ROADMAP.md`); (g) functional CI/CD with public test pass record (already in repo: `.github/workflows/`).
2. **Find a TAC sponsor.** LF AI & Data Foundation TAC (Technical Advisory Council) sponsors are required for Sandbox application. Approach 2-3 current TAC members at the next LF AI & Data Foundation public event or via LinkedIn DM with the project's pitch.
3. **Submit the application.** GitHub PR against the LF AI & Data Foundation TAC repo with the filled-in application template. The application is a 60+ page document covering: project description, mission, target users, governance, neutral-home rationale, maturity assessment, donor entity (NTCI Consulting, LLC per Item 2), license, code-of-conduct, contribution guide, current contributors, roadmap.
4. **TAC review.** TAC reviews monthly; expect 2-4 review cycles with revisions before vote.
5. **Donation transfer.** If accepted, transfer: GitHub org ownership, domain ownership, trademark license (the TM stays with NTCI Consulting, LLC per the LF default; LF gets a perpetual license for the project's use), website assets.
6. **Strategic implication.** The donation solves bus-factor + Tier-1 concentration-risk in one move. The tradeoff: the author no longer has unilateral control over project direction (TSC + LF governance constrains it). This is the right tradeoff for a project that is becoming the regulator-side governance reference; it is the wrong tradeoff if the author intends to keep the framework as a captive lead-gen surface for the advisory practice.

**Estimated cost + timeline.** Zero LF fees for Sandbox (Sandbox is free). Counsel review of donation agreement: $2,500-$7,500. Author time: 40-80 hours over the application window. Total wall clock: 6-9 months to Sandbox acceptance; 18-24 months from Sandbox to Incubation; 24+ months from Incubation to Graduated.

**What's already in this commit.**

- `docs/LFAI_SANDBOX_APPLICATION_DRAFT.md` — pre-filled template for the LF AI & Data Foundation Sandbox application, including the pre-application checklist and estimated timeline.

---

## Item 9 — Downgrade `Development Status :: 5` classifier → `4 - Beta`

- [ ] **Status: pending author decision**

**The finding.** `pyproject.toml` line 38 ships `"Development Status :: 5 - Production/Stable"`. The adversarial-review chamber (Hostile Acquirer) flagged this as overstated for a project that (a) lacks SOC 2 (Item 5), (b) lacks insurance behind the disclaimers (Item 4), (c) has single-maintainer status (Item 7), (d) lacks LF / neutral-home affiliation (Item 8). "Production/Stable" is the highest stability claim PyPI's classifier vocabulary supports; using it for a project with these structural gaps reads as overclaim to a sophisticated reviewer.

**Why it blocks Tier-1 adoption.** Procurement reviewers scrutinizing PyPI metadata (some do; most don't, but Goldman Sachs and JPMorgan Chase explicitly do) will read the discrepancy as a credibility hit. The framework's voice register is "the operator who states what is true and bounds what is not"; "Production/Stable" without the supporting controls infrastructure violates the register.

**Action required.**

1. **Author decision.** Either: (a) downgrade to `"Development Status :: 4 - Beta"` and revert to `"Development Status :: 5 - Production/Stable"` once SOC 2 + insurance + co-maintainer + LF Sandbox are in place; OR (b) keep `"Development Status :: 5 - Production/Stable"` and address each gap in `README.md` with explicit "what we have and what we don't" language. Option (a) is the recommended path; option (b) is harder to defend in a vendor-questionnaire conversation.
2. **If option (a):** edit `pyproject.toml` line 38 from `"Development Status :: 5 - Production/Stable"` to `"Development Status :: 4 - Beta"`. Bump version in `pyproject.toml` and `CITATION.cff` to `2.1.0` for the release that carries the change. Note the change in `CHANGELOG.md` under v2.1.

**Estimated cost + timeline.** Zero cost. Author time: 5 minutes. Total wall clock: 1 business day (just needs to bundle with the next release).

**What's already in this commit.**

- Per the parent agent's working rules, `pyproject.toml` is NOT modified in this commit. The change is documented here for the author to apply.

---

## Item 10 — Rewrite or NDA-restrict Schwab Matter 4 in `fsi_settled_matters.md`

- [ ] **Status: pending author decision (Option A vs Option B)**

**The finding.** `docs/fsi_settled_matters.md` Matter 4 directly cites "SEC v. Charles Schwab & Co., et al. — Schwab Intelligent Portfolios ($187M, June 13, 2022)" with the specific respondent names, the specific settlement amount, the specific statutory basis, and a paragraph-length description of the underlying conduct. The matter is on the public record (SEC press release; SEC administrative order; Schwab 8-K disclosure) so the citation is not in itself a confidentiality issue. The issue is different: a counsel-facing or procurement-facing reader at any wealth-platform Tier-1 buyer (Schwab itself, but also any Schwab competitor) reads "the author cites our matter as the canonical operator-side enforcement against algorithmically-driven recommendation surfaces" as an antagonistic posture — even though the framing in the matter section is neutral and counsel-defensible. The defensive read pre-empts a commercial conversation.

The adversarial-review chamber's recommendation: rewrite Matter 4 to use a neutral citation that preserves the regulatory teaching without naming the respondent, OR move the matter to a private NDA-only appendix accessible only to engaged clients.

**Why it blocks Tier-1 adoption.** Schwab is one of the framework's natural Tier-1 buyers (CCM/CXM modernization + algorithmic-recommendation governance is the author's exact lane). Naming Schwab as the canonical bad-actor example in the public framework documentation forecloses that conversation. The same dynamic applies, with less force, to any wealth-platform buyer who reads the matter section and reasonably wonders whether their matter would be next.

**Action required.**

1. **Author decision: Option A (neutral citation rewrite) or Option B (move to NDA-only private appendix).**
2. **If Option A** — apply the patch below to `docs/fsi_settled_matters.md` Matter 4.
3. **If Option B** — delete Matter 4 from `docs/fsi_settled_matters.md` and move the existing content to `private/fsi_settled_matters_appendix.md` (a private repo or a gitignored path; do NOT commit the private appendix to the public repo). Update the table of contents in `docs/fsi_settled_matters.md` to read "Three public anchor matters + one NDA-only matter; full case available under NDA on request."
4. **Update `CHANGELOG.md`** for v2.1 noting the rewrite or restriction.

**Option A — neutral-citation rewrite (full replacement text for Matter 4):**

```markdown
## Matter 4 (anonymized) — Robo-advisor cash-sweep allocation matter (SEC, 2022)

**Agency:** U.S. Securities and Exchange Commission
**Respondents:** A major US wealth platform and its registered investment adviser
affiliates (matter on the public record; full case citation available under NDA
on request).
**Date:** June 13, 2022
**Dollar amount:** $187 million aggregate ($52 million civil penalty + $135 million
disgorgement and prejudgment interest)

### Factual summary

A 2022 SEC settled matter against a major US wealth platform's robo-advisor
cash-sweep allocation logic. The SEC found that the program's allocation logic
systematically held a higher cash allocation than a competing investment of an
equivalent risk profile would have held, with the cash swept to an affiliate
bank that earned a spread on the funds. The economic effect, per the SEC's
order, was that clients earned less than they would have in a comparable
non-cash-heavy portfolio, while the wealth platform earned undisclosed revenue
on the cash spread. The matter was settled on an Investment Advisers Act of
1940 § 206(2) basis (negligent breach of fiduciary duty) and § 206(4) basis
(anti-fraud rule for advisers). The order required the wealth platform to
retain an independent compliance consultant in addition to the monetary
components.

### Regulatory significance

This matter is the canonical operator-side enforcement against an algorithmically-
driven recommendation surface in U.S. asset management. The theory of liability:
failure to disclose conflict of interest in algorithmic recommendations. It
establishes three points directly relevant to autonomous-agent governance in
wealth and capital markets: (1) the recommendation surface itself is the
regulated artifact, not the disclaimer language wrapped around it; (2) a conflict
of interest baked into the allocation logic is treated identically to a conflict
of interest in a human adviser's recommendation; (3) the SEC will and does
compute disgorgement on the spread the operator earned, not just the customer
harm. The matter is the closest existing analogue under U.S. securities law to
the operator-side bar that Regulation Best Interest (effective June 30, 2020)
and the related Form CRS rule impose on broker-dealer recommendations to retail
customers.

### What the framework would have engaged with

The recommendation-surface decision is exactly the surface ADR-0013-equivalent
(`BestInterestGate`) addresses. The `BestInterestCheck` and `EquityAudit`
patterns directly address the gap pattern this matter exposed. Every
recommendation emitted by an autonomous-agent stack to a retail customer or to
an internal portfolio-allocation engine routes through a pre-emit gate that
records `AuditEventType.BEST_INTEREST_CHECKED` with the customer-profile
inputs, the universe considered, the chosen recommendation, and the
conflict-of-interest declarations attached to each option. Where the allocation
logic carries a conflict (cash sweep spread, payment-for-order-flow, affiliated-
fund preference, payment-of-revenue-share), the conflict is a first-class field
on the audit event, not a footnote in a prospectus. ADR-0007 (`SR 11-7 model-
validation overlay`) would have engaged with the allocation-model validation
gap. The hash-chain ledger would have made the four-year spread economically
reconstructable on demand from a regulator request, not from internal product-
team memory.

Full case citation, including respondent names and primary-source URLs,
available under NDA on request.
```

**Option B — full removal from public; private NDA-only appendix.** Replace Matter 4 with the single-paragraph stub:

```markdown
## Matter 4 (NDA-only)

A 2022 SEC settled matter against a major US wealth platform's robo-advisor
cash-sweep allocation logic, ~$187M aggregate, Investment Advisers Act of 1940
§ 206(2) + § 206(4) basis, with regulatory significance for algorithmic-
recommendation governance under Regulation Best Interest. Full case summary
available under NDA on request. Adopters and prospective engagement counterparts
should contact the author for the NDA-gated appendix.
```

**Estimated cost + timeline.** Zero cost. Author time: 15 minutes to apply Option A or Option B; counsel review optional but recommended ($200-$500 for a 15-minute counsel call on which option fits the author's commercial posture). Total wall clock: 1 business day.

**What's already in this commit.** Per the parent agent's working rules, `docs/fsi_settled_matters.md` is NOT modified in this commit. Both option texts above are ready to copy-paste; the author picks A or B and applies in a separate commit.

---

## Item 11 — Publish Cohort-Zero $1K pricing on `autonomy-ladder.io/services`

- [ ] **Status: pending publication decision**

**The finding.** The author's private `Commercial/` directory (per the author's master identity document) documents a Cohort-Zero pricing pilot: $5K standard Diagnostic price, with a $1K pilot rate for the first 5 logos to seed case studies. The pilot is not externally published. The standard $5K Diagnostic / $40K Audit / $15K-per-quarter Retainer ladder IS the published pricing on `autonomy-ladder.io/services` (per the v3 LOCKED plan).

The gap: without the Cohort-Zero pricing externally published, the author has to repeat the pilot pitch one-on-one to every prospective Logo 1-5 contact, which is friction the published Cohort-Zero offer would remove.

**Why it blocks Tier-1 adoption.** Not a Tier-1 blocker per se; it's a top-of-funnel friction issue for the Cohort-Zero phase. Tier-1 buyers will pay the $5K standard price (and would view a $1K offer as anti-signal). The Cohort-Zero offer is targeted at PE operating partners, family-office CIOs, and wealth-platform CTO/CIO contacts who are willing to be the first reference customer in exchange for a one-paragraph testimonial (anonymized to GC sign-off level).

**Action required.**

1. **Author decision.** Publish the Cohort-Zero $1K pricing offer on `autonomy-ladder.io/services` (public) OR keep it private and surface it only in 1:1 conversations. The argument for public publication: removes friction in the Cohort-Zero phase, makes the offer crisp, signals confidence in the Diagnostic methodology. The argument against: anchors the brand at $1K rather than $5K in the casual reader's mind; risks dilution if Cohort-Zero cap (5 logos) is not enforced.
2. **If publish:** add the page content from `docs/COHORT_ZERO_PRICING_PUBLIC.md` (shipped in this commit) to autonomy-ladder.io/services. Add a hard cap of 5 logos with a public counter ("Pilot logos remaining: N of 5") to enforce the anti-dilution rule.
3. **Either path:** keep this file (`docs/COHORT_ZERO_PRICING_PUBLIC.md`) in the repo as the canonical text. Author chooses whether to publish to the public website.

**Estimated cost + timeline.** Zero cost. Author time: 30 minutes to publish to autonomy-ladder.io/services. Total wall clock: 1 business day.

**What's already in this commit.**

- `docs/COHORT_ZERO_PRICING_PUBLIC.md` — the single-page formal publication of the Cohort-Zero pilot pricing, ready to copy to autonomy-ladder.io/services.

---

## Item 12 — Pursue FRM (GARP) or CISSP credential

- [ ] **Status: pending author commitment**

**The finding.** The author's credential stack (Wharton certificates, Carnegie Mellon Executive Ed, 25+ year operator track record, named-advisor relationship with López de Prado on adjacent work, $750M Broadridge deal, ransomware-to-cloud rebuild) is strong on operator scarcity and weak on letter-after-name discipline credentials. For the FSI advisory practice specifically, two credentials carry signaling weight with risk officers and CISOs: (a) the GARP Financial Risk Manager (FRM) — the standard risk-officer credential at any bank or asset manager; (b) the (ISC)² Certified Information Systems Security Professional (CISSP) — the standard CISO-track credential, frequently required in MSA vendor-spec boilerplate.

**Why it blocks Tier-1 adoption.** Not a hard blocker; the author's operator track record carries the weight. The credential gap is most visible when (a) the prospective buyer's chief risk officer is doing the credential-check and the author's resume goes to procurement-side review without the CRO seeing the operator narrative, OR (b) the MSA boilerplate requires a credentialed individual on the supplier side ("Supplier represents that at least one named principal holds a current CISSP or equivalent certification..."). Both patterns are common in Tier-1 vendor onboarding.

**Action required.**

1. **Pick one credential, not both.** Both take 9-18 months and meaningful study time. The framework's commercial center of gravity is AI-governance + FSI risk; the FRM is the closer fit to that center. The CISSP is the closer fit if the author intends to position the framework as a security-product line rather than a governance-product line.
2. **If FRM:** GARP Part I + Part II. Cost: $1,500-$2,500 in exam + program fees + study material. Study time: 200-400 hours. Wall clock: 12-18 months (Part I in May or November; Part II at the next sitting after Part I pass).
3. **If CISSP:** (ISC)² CISSP. Cost: $749 exam fee + $500-$1,500 in study material + $125/yr maintenance after pass. Study time: 100-300 hours. Wall clock: 6-9 months to first sitting. Note: CISSP requires 5 years of cumulative information-security work experience; author's track record satisfies (Wipro CTO during ransomware; SOC 2 Type 2 + ISO 27001 within 50 days qualifies).
4. **Either path:** add the credential to `OWNERSHIP.md` authorship section + `CITATION.cff` once awarded.

**Estimated cost + timeline.** FRM: $1,500-$2,500 + 200-400 study hours + 12-18 months wall clock. CISSP: $1,250-$2,750 + 100-300 study hours + 6-9 months wall clock. Recurring: GARP membership $195/yr; (ISC)² maintenance $125/yr.

**What's already in this commit.** Nothing. Credential pursuit is an external workflow.

---

## Sequencing summary

Recommended sequencing — do not start Item N+1 until Item N is in flight (not necessarily complete):

| Order | Item | Gating reason |
|---|---|---|
| 1 | Item 2 — Form IP-holding entity | All commercial conversations require a counterparty entity; this gates Items 4 / 5 / 6 / 11 |
| 2 | Item 1 — Dual-license / Apache 2.0 | Decisions on license posture affect Item 8 (LF requires Apache 2.0) and Item 6 (TM filing entity = IP-holding entity from Item 2) |
| 3 | Item 3 — Ethics wall | Required before any commercial-advisory engagement (Item 11) is executed |
| 4 | Item 9 — Downgrade Beta classifier | Quick win; bundle with v2.1 release |
| 5 | Item 10 — Schwab matter rewrite | Quick win; bundle with v2.1 release |
| 6 | Item 4 — Insurance | Required before first commercial engagement letter is signed |
| 7 | Item 6 — USPTO TM filing | June 15, 2026 filing target per master identity document |
| 8 | Item 7 — Recruit co-maintainers | Gates Item 8 (LF Sandbox requires multi-maintainer governance) |
| 9 | Item 11 — Cohort-Zero pricing publish | Top-of-funnel for advisory; runs in parallel with Items 4-8 |
| 10 | Item 5 — SOC 2 engagement | Kickoff Q3 2026; Type I report Q4 2026 |
| 11 | Item 8 — LF Sandbox application | 6-9 months to acceptance; submit Q4 2026 |
| 12 | Item 12 — Credential (FRM or CISSP) | Long horizon; start whenever, complete in 2027 |

---

## Cost roll-up

| Item | One-time cost | Recurring cost |
|---|---|---|
| Item 1 — License counsel review | $750-$2,500 | — |
| Item 2 — IP-holding entity (Texas LLC path) | $1,500-$5,000 | $100-$300/yr registered agent |
| Item 3 — Ethics-wall counsel call | $1,500-$5,000 | $500-$1,500/yr review |
| Item 4 — Insurance bind | — | $4,500-$14,500/yr premium |
| Item 5 — SOC 2 Type I | $30,000-$75,000 | $50,000-$120,000/yr (Type II) |
| Item 6 — USPTO TM filing | $3,400-$6,000 | $300-$500 per 10-yr maintenance |
| Item 7 — Co-maintainer recruitment | $0 (author time) | $0 |
| Item 8 — LF Sandbox application | $2,500-$7,500 (counsel) | $0 (LF Sandbox is free) |
| Item 9 — Downgrade classifier | $0 | $0 |
| Item 10 — Schwab matter rewrite | $200-$500 (optional counsel) | $0 |
| Item 11 — Cohort-Zero publish | $0 | $0 |
| Item 12 — FRM or CISSP | $1,250-$2,750 | $125-$195/yr maintenance |
| **TOTAL (low end)** | **~$41,100** | **~$55,400/yr** |
| **TOTAL (high end)** | **~$104,250** | **~$137,000/yr** |

Year-1 cash burn envelope for full Tier-1-ready posture: $41K-$104K one-time + $55K-$137K recurring = $96K-$241K. The single largest line is SOC 2 (year 1 Type I $30K-$75K; year 2 Type II $50K-$120K/yr). Without SOC 2, the year-1 envelope drops to $11K-$29K one-time + $5K-$17K recurring = $16K-$46K. Author makes the SOC 2 decision based on commercial pipeline; the rest of the items are below the cost of one Diagnostic engagement.

---

## Related

- [`OWNERSHIP.md`](OWNERSHIP.md) — IP-holding entity (Item 2)
- [`LICENSE`](LICENSE) — current MIT license (Item 1)
- [`LICENSE-APACHE-2.0`](LICENSE-APACHE-2.0) — Apache 2.0 text shipped this commit (Item 1)
- [`docs/ETHICS_WALL.md`](docs/ETHICS_WALL.md) — NTCI advisory / lab ethics-wall (Item 3)
- [`docs/SOC2_ENGAGEMENT_RFP.md`](docs/SOC2_ENGAGEMENT_RFP.md) — CPA-firm RFP template (Item 5)
- [`docs/TRADEMARK.md`](docs/TRADEMARK.md) — trademark usage guidelines (Item 6)
- [`docs/CO_MAINTAINER_RECRUITMENT_DRAFT.md`](docs/CO_MAINTAINER_RECRUITMENT_DRAFT.md) — co-maintainer recruitment post (Item 7)
- [`docs/LFAI_SANDBOX_APPLICATION_DRAFT.md`](docs/LFAI_SANDBOX_APPLICATION_DRAFT.md) — LF AI & Data Foundation Sandbox application draft (Item 8)
- [`docs/COHORT_ZERO_PRICING_PUBLIC.md`](docs/COHORT_ZERO_PRICING_PUBLIC.md) — Cohort-Zero pricing (Item 11)
- [`docs/tier1_buyer_prefills/`](docs/tier1_buyer_prefills/) — vendor questionnaire pre-fills

---

*End MANUAL_REMEDIATION_AUTHOR.md — 12 items, author-action.*
