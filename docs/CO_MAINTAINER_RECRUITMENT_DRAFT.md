# CO_MAINTAINER_RECRUITMENT_DRAFT.md — Recruitment post for 2 co-maintainers

**Status:** v1.0 draft · Last reviewed: 2026-05-28
**Companion to:** [`../MANUAL_REMEDIATION_AUTHOR.md`](../MANUAL_REMEDIATION_AUTHOR.md) Item 7
**Author:** Kunjar Bhaduri

> **Author note.** This is the LinkedIn-friendly recruitment post the author publishes to find two co-maintainers for the framework's Technical Steering Committee. Cross-post to GitHub Discussions, the author's X account, and (with permission) the LF AI & Data Foundation mailing list once the LF Sandbox application is in motion.

---

## The post (LinkedIn draft)

**Title:** Recruiting two co-maintainers for `finserv-agent-audit` — open-source governance patterns for autonomous AI in regulated FSI

I'm looking for two co-maintainers to join the Technical Steering Committee for `finserv-agent-audit`.

What the framework is: a reference patterns library for autonomous-agent governance in regulated financial services. Six core patterns (autonomy-level classification A0-A4, sovereign veto, DEFCON risk-state, shadow-mode rollout, hash-chain audit logging, vendor scoring drift detection), six FSI-specific governance gates (model inventory for SR 11-7, adverse-action gate for FCRA + CFPB Circular 2022-03, SAR-workflow audit for BSA/AML, ECOA / Reg B fair-lending pre-emit check, SEC Reg-BI best-interest check, mutual-information protected-class proxy detector), seven v1.3 modules covering the discrimination frontier and third-party vendor surface, plus the v2.0 agentic-runtime adapters (A2A, LangGraph, Microsoft Agent Framework, CrewAI), CycloneDX 1.7 + SPDX 3.0 ML-BOM generator, FastAPI governance endpoint, and a Kubernetes operator scaffold. 34 ADRs. 142+ tests. 90%+ branch coverage. Maps to 20+ regulatory frameworks. Single-maintainer today.

Where I need help: two co-maintainers with one or both of these profiles —

1. **FSI engineering leader.** You've built audit-grade systems at a US bank, asset manager, insurance carrier, or wealth platform. You've sat across the table from SR 11-7 model risk, OCC examinations, SEC 17a-4 books-and-records, or CFPB supervisory exams. You read the framework's ADRs and have a view on what the next missing pattern is.

2. **AI-governance researcher.** You've published or built around regulated-AI compliance, autonomous-agent risk, fair-lending model validation, or LLM disparate-impact testing. Academic, think-tank, regulator-side, or consulting backgrounds welcome. The framework's threat model and pattern set are the working subject; deep prior FSI seat is helpful but not required.

What you'd commit to:

- **One hour per week** of review cadence — PRs, issues, ADR drafts, release-readiness checks
- **One quarterly TSC meeting** — 90 minutes, video, decisions on roadmap and pattern direction
- **Co-author rights on the next major release** — your name on `CITATION.cff`, your bio on the project site, the public commit history reflects your contributions
- **Commit access** on a graduated trust ladder — start with review-and-comment, progress to merge rights as you make 3-5 substantive contributions

What I'd commit to:

- A 60-minute interview before commitment so we both confirm fit
- A documented TSC charter once you join (membership terms, voting rules, conflict-of-interest disclosure, decision scope)
- Public recognition consistent with your contribution — no captive labor; your work is your work
- A 60-day exit window if the role doesn't fit, with no expectation of explanation

What this is not:

- This is not a vendor-relationship lead-gen channel. If your day job sells AI-governance software that competes with the framework's patterns, the conflict of interest is structural and we'll need to talk about whether it's manageable.
- This is not free consulting for your day job. The framework's MIT/Apache 2.0 license lets your employer use it; co-maintainer time is committed to the open-source project, not to your employer's adoption.
- This is not a credentialing scheme. Co-maintainer is a contribution role, not a title to put on a CV beyond the actual contributions you make.

Apply by opening a GitHub Issue at `github.com/linus10x/finserv-agent-audit/issues/new` with title prefix **`[co-maintainer]`** and the following content:

1. Your background (linked CV or LinkedIn welcome)
2. Which of the two profiles fits (or both)
3. One contribution you'd want to make in your first 90 days
4. Your current employer + their position on OSS contribution on work time (or your status if independent / between roles / academic)
5. Any conflict-of-interest disclosure you want on the record from day one

I'll respond within 5 business days with either a 30-minute interview slot or a polite decline. Two slots open. Recruitment window: **60 days** from this post.

#OpenSource #AIGovernance #FinancialServices #RegulatedAI #FinTech

---

## The post (X / Twitter draft)

**Thread, 5 posts:**

1/ Recruiting two co-maintainers for `finserv-agent-audit` — open-source governance patterns for autonomous AI in regulated FSI. Single-maintainer today; looking to charter a Technical Steering Committee with two co-maintainers in the next 60 days.

2/ The framework: 6 core patterns + 6 FSI governance gates + 7 v1.3 discrimination-frontier modules + v2.0 agentic-runtime adapters (A2A / LangGraph / MAF / CrewAI). 34 ADRs. 142+ tests. 90%+ branch coverage. Maps to 20+ regulatory frameworks. MIT today, Apache 2.0 under counsel review.

3/ Profile A — FSI engineering leader who's built audit-grade systems at a US bank / asset manager / insurance carrier / wealth platform. SR 11-7, OCC, SEC 17a-4, CFPB supervisory exam experience welcome. Read the ADRs, tell me what the next missing pattern is.

4/ Profile B — AI-governance researcher with published or built work in regulated-AI compliance, autonomous-agent risk, fair-lending validation, or LLM disparate impact. Academic / think-tank / regulator-side / consulting backgrounds all in scope.

5/ Commit: 1h/wk review cadence + quarterly TSC meeting + co-author rights on next major release + commit access on graduated trust ladder. Apply via GitHub Issue with title prefix `[co-maintainer]` at github.com/linus10x/finserv-agent-audit. Two slots. 60-day window.

---

## The interview script (30 minutes)

**Author preparation:** read the applicant's GitHub Issue, scan their public commits / publications, note any conflict-of-interest flags they've disclosed.

**0:00-0:05 — Intro.** Author: project context (60 seconds) → applicant: background (3-4 minutes).

**0:05-0:15 — Technical conversation.** Pick one of: (a) the applicant's proposed first-90-day contribution; (b) the framework's most ambitious open ADR (currently ADR-0018 threat model expansion or ADR-0032 governance-endpoint extension); (c) a pattern the applicant believes is missing.

**0:15-0:22 — Commitments + conflict.** Author confirms time commitment (1h/wk + quarterly), commit-access progression, co-author rights. Applicant confirms employer position on OSS contribution and conflict-of-interest disclosure. Both sides agree the disclosure is complete.

**0:22-0:28 — Open questions.** Applicant asks anything. Author answers honestly, including what is not yet decided (LF Sandbox application status; SOC 2 engagement status; trademark filing status; the framework's commercial-advisory adjacency and the ethics-wall posture per `docs/ETHICS_WALL.md`).

**0:28-0:30 — Next step.** Author commits to a yes/no within 5 business days. If yes: scheduling next call to walk through the charter and the first PR. If no: brief polite decline reason emailed within the same 5-business-day window.

---

## Post-acceptance: TSC charter drafting

Once two co-maintainers are confirmed and the interview process is closed, the author drafts `docs/TSC_CHARTER.md` (not in this commit; downstream of who joins) with these standard elements:

1. Membership (named list, terms, renewal)
2. Voting rules (lazy consensus + 3-day objection window for technical decisions; explicit majority for governance changes; super-majority for charter amendments)
3. Decision scope (technical direction, release approval, contributor escalation, conflict-of-interest disclosure)
4. Quorum (2 of 3)
5. Public minutes (every quarterly meeting publishes minutes to `docs/tsc_minutes/`)
6. Conflict-of-interest disclosure (every TSC member maintains a public disclosure file with current employer, financial interests in adopting firms, and recusal log)
7. Code of conduct enforcement role (TSC handles escalations per `CODE_OF_CONDUCT.md`)
8. Amendment process (charter amendment requires unanimous TSC vote + 30-day public comment window)

The charter is published to the repo within 30 days of the second co-maintainer joining.

---

## Decline language template

For applicants the author declines:

> Thank you for applying for the co-maintainer role on `finserv-agent-audit`. After reviewing your background and our 30-minute conversation, I've decided not to move forward for [specific reason: profile mismatch / conflict-of-interest concern that the structure doesn't cleanly address / timing on the other side / specific contribution direction that doesn't fit the current roadmap]. This is not a comment on your skill or your work; it's a fit decision specific to the two slots open right now.
>
> I appreciate the time you put into the application. The framework is open-source, the contribution guide is at `CONTRIBUTING.md`, and I'd welcome PRs from you in the normal contributor flow even though the co-maintainer path didn't fit.
>
> Best,
> Kunjar

---

## Related

- [`../CONTRIBUTING.md`](../CONTRIBUTING.md) — contribution flow (the normal-contributor path applicants can use regardless of co-maintainer outcome)
- [`../CODE_OF_CONDUCT.md`](../CODE_OF_CONDUCT.md) — code of conduct (TSC enforcement role)
- [`../OWNERSHIP.md`](../OWNERSHIP.md) — current single-maintainer posture (this recruitment changes that)
- [`../MANUAL_REMEDIATION_AUTHOR.md`](../MANUAL_REMEDIATION_AUTHOR.md) — Item 7 (this recruitment workstream)
- [`LFAI_SANDBOX_APPLICATION_DRAFT.md`](LFAI_SANDBOX_APPLICATION_DRAFT.md) — LF Sandbox application (downstream of TSC formation)

---

*Recruitment draft. Author publishes post-counsel review of the conflict-of-interest language.*
