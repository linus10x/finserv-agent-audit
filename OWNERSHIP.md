# OWNERSHIP.md — IP-holding entity and assignment posture

**Status:** v1.1.0 · Last reviewed: 2026-05-28.

This document exists because the Hostile Acquirer chamber of the council asked it to. Adopters and prospective enterprise partners considering deeper engagement (commercial license, support contract, joint development, acquisition of the IP estate) need a clear view of who holds the IP, how contributions flow, and what assignment / acquisition posture the IP-holding entity maintains.

> Companion to [`LICENSE`](LICENSE), [`CONTRIBUTING.md`](CONTRIBUTING.md), [`CITATION.cff`](CITATION.cff).

---

## Authorship

**Author:** Kunjar Bhaduri
**Contact:** kunjarbhaduri@gmail.com
**Location:** Dallas, TX, USA

The framework is authored as an individual research and pattern-publication effort. Contribution credits are recorded in commit history and in the contributor-acknowledgments section of release notes.

---

## IP-holding entity

**Entity:** *[PLACEHOLDER — flag for author to fill: Individual / NTCI LLC / Delaware C-corp / other formed entity]*

The IP-holding entity is the legal person that owns the copyright in the source code and documentation, holds the trademark filings, and is the counterparty for any commercial license or acquisition discussion. The placeholder above reflects that the author maintains optionality between individual ownership and a formed entity until the commercial path crystallizes.

For the avoidance of doubt: the MIT license in [`LICENSE`](LICENSE) governs the framework's use regardless of how the IP-holding entity is constituted. Changes to the IP-holding entity do not change the rights granted under the existing MIT license to existing adopters.

---

## License

**Open source:** [MIT License](LICENSE) — permissive for both commercial and academic use.

**Commercial license:** Not currently offered as a separate SKU. The MIT license is the only license. If a prospective enterprise partner requires terms different from MIT (warranty, indemnification, support SLA), the path is a separate commercial contract with the IP-holding entity that supplements — but does not replace — the MIT license under which the code itself is distributed.

---

## Contribution model

All contributions flow through the [`CONTRIBUTING.md`](CONTRIBUTING.md) PR / issue process:

1. Issue or pattern-request first — significant changes are discussed in an issue before a PR is opened.
2. PRs include tests, ADR (for architectural changes), and conform to the project's ruff / mypy / pytest standards.
3. The author reviews and merges. Maintainership is currently single-maintainer; expansion to a multi-maintainer model is on the roadmap once contribution volume justifies it.
4. Contributors retain copyright in their contributions. By submitting a PR, contributors license their contribution to the project under the same MIT license that governs the project as a whole. There is no contributor license agreement (CLA) beyond the inbound-license = outbound-license posture (the GitHub Terms of Service inbound-license clause).

---

## Trademark

**"Autonomy Ladder"** is the framework's headline term and the brand under which the cross-vertical discipline (this repo + `cre-agent-audit` + future vertical-specific siblings) is published.

**Trademark filing target:** USPTO classes 9 / 35 / 41 / 42, filing target **June 15, 2026** via `tmsearch.uspto.gov`. The filing is a parallel author workstream and not tracked in this repo's issues.

Until registration completes, the term is used as a common-law mark with consistent use across the author's published surfaces.

---

## Acquisition / assignment readiness

*[PLACEHOLDER — flag for author to fill: explicit posture on acquisition / assignment readiness, including:*
*- whether the IP-holding entity is open to discussion of acquisition / license / joint-venture*
*- preferred deal shape (asset purchase of the IP estate, equity in a formed entity, exclusive license, etc.)*
*- contact point for acquisition discussions distinct from the general kunjarbhaduri@gmail.com address*
*- any standing constraints (right-of-first-refusal commitments, prior licensee obligations, etc.)]*

For prospective adopters whose interest in the framework rises to the level of a commercial conversation (enterprise support, custom development, joint-development, acquisition), the author's preferred posture is a preliminary conversation under NDA before any formal commercial process. Contact through the author's published channels.

---

## Citation

Academic and compliance citation metadata is in [`CITATION.cff`](CITATION.cff). The canonical citation form for v1.1.0 is captured there; DOI assignment is via Zenodo on release tag (see [`RELEASE-INSTRUCTIONS.md`](RELEASE-INSTRUCTIONS.md)).

---

## Related

- [`LICENSE`](LICENSE) — the legal contract
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribution process
- [`CITATION.cff`](CITATION.cff) — citation metadata
- [`DISCLAIMER.md`](DISCLAIMER.md) — bounded claims
- [`RELEASE-INSTRUCTIONS.md`](RELEASE-INSTRUCTIONS.md) — release-tag procedure
