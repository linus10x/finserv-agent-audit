# RELEASE-INSTRUCTIONS.md — v1.1.0 release procedure

**Status:** v1.1.0 · Last reviewed: 2026-05-28.

This document is the manual checklist for cutting the v1.1.0 release. It is calibrated for a single-maintainer release flow; expansion to a multi-maintainer release process is on the roadmap.

> Companion to [`CHANGELOG.md`](CHANGELOG.md), [`ROADMAP.md`](ROADMAP.md), [`VERSIONING.md`](VERSIONING.md).

---

## Pre-tag checklist

Confirm each of the following before tagging:

- [ ] `CHANGELOG.md` `[1.1.0]` block is filled with the full Added / Changed / Tests / Dependencies sections (see [`VERSIONING.md`](VERSIONING.md) for the summary).
- [ ] `ROADMAP.md` v1.1 checkboxes are ticked for everything that shipped; anything that did not ship is moved to v1.2 or marked deferred with an ADR reference.
- [ ] `CITATION.cff` `version` field is updated to `1.1.0` and `date-released` is set.
- [ ] `pyproject.toml` `version` field is updated to `1.1.0`.
- [ ] All 273 tests pass on Python 3.12 and 3.13 in CI on the head commit.
- [ ] `ruff check` and `ruff format --check` pass.
- [ ] `mypy --strict` passes.
- [ ] `SHIP-RECEIPT.md` classification counts match the live `__all__` exports.
- [ ] The 19 ADRs in `docs/adr/` (0001–0019 governance + OPS-001 ops) all have `Status: Accepted` or explicit `Status: Deferred` (ADR-0019).
- [ ] The 14 mapping documents in `docs/` have a `Last reviewed: 2026-05-28` (or current) line.
- [ ] All 12 repo-root governance / release surfaces (`FAILURE-MODES.md`, `LIMITATIONS.md`, `ARCHITECTURE.md`, `DISCLAIMER.md`, `SHIP-RECEIPT.md`, `VERSIONING.md`, `NEGATIVE-USE-CASES.md`, `RESEARCH.md`, `ASSURANCE-GUIDE.md`, `DEPLOY-CHECKLIST.md`, `OWNERSHIP.md`, `RELEASE-INSTRUCTIONS.md`) exist and reference each other consistently.
- [ ] `OWNERSHIP.md` placeholders are either filled or explicitly acknowledged as remaining placeholders for the v1.1 cut.
- [ ] The release notes file `.github/releases/v1.1.0-notes.md` exists and is reviewed.

---

## Tag the release

```bash
cd "/path/to/finserv-agent-audit"
git tag -a v1.1.0 -m "v1.1.0 — Parity port + FSI overlay + council additions"
```

The tag message above is the canonical one-line summary; the long-form release narrative lives in the GitHub release notes file.

## Push the tag

```bash
git push origin v1.1.0
```

This triggers any tag-driven CI (release-asset build, documentation publish, etc.) configured in `.github/workflows/`.

## Create the GitHub release

```bash
gh release create v1.1.0 --notes-file .github/releases/v1.1.0-notes.md
```

If the release notes file does not yet exist, draft it from the `CHANGELOG.md` `[1.1.0]` block plus a forward-looking paragraph pointing to [`ROADMAP.md`](ROADMAP.md) v1.2.

## Zenodo DOI mint

If GitHub-Zenodo integration is configured for the repo, the DOI is minted automatically on release publish. Confirm by visiting `https://zenodo.org/account/settings/github/` and verifying the repo is enabled.

If integration is not configured:

1. Visit `https://zenodo.org/uploads/new` while logged in.
2. Upload the GitHub release archive.
3. Fill metadata from `CITATION.cff` (title, authors, version `1.1.0`, license MIT, related identifier = repository URL).
4. Mint the DOI and capture the badge URL.
5. Update the README DOI badge URL to point at the new DOI.

## Content launch trigger

The Tranche 1 content campaign drafted alongside the v1.1.0 ship is staged at:

```
Applications-May-2026/v2-Refresh/Content/v1.1.0_Ship_Campaign_Drafts_2026-05-28.md
```

That file holds the LinkedIn long-form post, the X thread (5–8 tweets), the five outbound DMs (warm prospects + recruiter), and the three trade-press pitch drafts ready to publish. Trigger the campaign after the GitHub release is live and the DOI badge is updated.

## Post-tag operational rhythm

- **Within 24 hours of release:** run the [CLAUDE.md](../../CLAUDE.md) standing-outreach rule for the content launch — LinkedIn connect requests to 1–3 stakeholders + 1 recruiter per inbound conversation the release surfaces.
- **Within 48 hours:** monitor GitHub Issues and Discussions for adopter questions; route blocking questions to a v1.1.1 patch cycle if needed.
- **Within one week:** review inbound DMs and email triggered by the content launch; qualify per the CLAUDE.md inbound-recruiter posture.

---

## Patch cycle (if needed)

If a v1.1.1 patch is required:

1. Open the issue describing the bug or doc correction.
2. Fix on a branch with a test that fails before the fix and passes after.
3. PR with reference to the issue.
4. Bump `pyproject.toml` and `CITATION.cff` to `1.1.1`; add a `[1.1.1]` block to `CHANGELOG.md`.
5. Repeat the tag / push / release / Zenodo sequence above.

Patch releases do not change `__all__` exports, callable signatures, or default behavior; if the change requires any of those, it is a MINOR (v1.2.0) release, not a PATCH (see [`VERSIONING.md`](VERSIONING.md)).

---

## Related

- [`CHANGELOG.md`](CHANGELOG.md)
- [`ROADMAP.md`](ROADMAP.md)
- [`VERSIONING.md`](VERSIONING.md)
- [`SHIP-RECEIPT.md`](SHIP-RECEIPT.md)
- [`CITATION.cff`](CITATION.cff)
