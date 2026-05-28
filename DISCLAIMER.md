# DISCLAIMER.md

**Status:** v1.1.0 · Last reviewed: 2026-05-28.

---

## The legal contract

The legal contract between the author of `finserv-agent-audit` and any adopter is the [MIT License](LICENSE) shipped at the root of this repository. Nothing in this document modifies, expands, or contracts that license.

## Provided "AS IS"

Per the MIT License, this software is provided "AS IS, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT." Use in production is at the adopter's own risk.

## Adopters retain regulatory obligations

Adopting this framework — in part or in whole — does not transfer, reduce, or satisfy the adopter's regulatory obligations to any supervisor, including but not limited to:

- The Office of the Comptroller of the Currency (OCC)
- The Board of Governors of the Federal Reserve System
- The Federal Deposit Insurance Corporation (FDIC)
- The U.S. Securities and Exchange Commission (SEC)
- The Financial Industry Regulatory Authority (FINRA)
- The Consumer Financial Protection Bureau (CFPB)
- The Financial Crimes Enforcement Network (FinCEN)
- State banking, securities, and insurance regulators
- Foreign supervisors and competent authorities under EU, UK, Singapore, or other jurisdictions

The regulatory mapping documents in `docs/` (SR 11-7, OCC Bulletin 2011-12, SOX 404 ITGC, SEC 17a-4, SEC Reg-BI, FCRA / Reg-V, ECOA / Reg-B, BSA/AML, GLBA Safeguards, EU AI Act, NIST AI RMF, ISO/IEC 42001, COSO ICAIR, CFPB Circular 2022-03) are **reference mappings**. They are intended to help adopters and their counsel point at relevant clauses. They are not opinions on whether the framework satisfies any specific clause.

## No engineering or legal advice intended

Nothing in this repository — including the README, CHANGELOG, ROADMAP, ADRs, mapping documents, code comments, docstrings, or this disclaimer — constitutes:

- Engineering advice for any specific deployment, threat model, or substrate.
- Legal advice for any specific regulatory regime, jurisdiction, or factual matter.
- A representation, warranty, or guarantee that the framework, as deployed, will satisfy any audit, examination, enforcement, or litigation posture.

## No representations about fitness for any specific regulatory regime

The author makes no representations that this framework — by itself, in combination with any adopter-supplied substrate, or in any configuration — satisfies the requirements of any specific law, regulation, supervisory guidance, examination procedure, accreditation standard, or industry framework.

Adopters considering production deployment in a regulated context should retain qualified counsel to advise on the specific obligations the framework may help evidence, the specific obligations the framework does not address, and the specific deployment posture the adopter's compliance program requires. Examples of regimes where qualified counsel is appropriate include (non-exhaustive): SR 11-7 model risk management, OCC examination procedures, SOX 404 internal controls over financial reporting, SEC 17a-4 books-and-records, FCRA adverse-action procedures, ECOA / Reg-B fair-lending compliance, BSA/AML reporting and recordkeeping, SEC Reg-BI care obligation, GLBA Safeguards Rule controls, EU AI Act conformity assessment, and state insurance regulator AI requirements.

## Bounded claims

For an explicit list of what this framework does and does not claim, see [`LIMITATIONS.md`](LIMITATIONS.md). For an explicit list of statements adopters should not make in reliance on this framework, see [`NEGATIVE-USE-CASES.md`](NEGATIVE-USE-CASES.md).

## Related

- [`LICENSE`](LICENSE) — the legal contract
- [`LIMITATIONS.md`](LIMITATIONS.md) — bounded claims
- [`NEGATIVE-USE-CASES.md`](NEGATIVE-USE-CASES.md) — statements the framework does not support
- [`SECURITY.md`](SECURITY.md) — vulnerability reporting
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribution model

---

*Patterns are software, not legal advice.*
