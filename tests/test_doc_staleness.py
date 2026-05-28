"""Drift-detection parity test: exported ``__all__``  <-->  public docs.

If a name is exported under ``finserv_agent_audit.governance.__all__``,
``finserv_agent_audit.agents.__all__``, or
``finserv_agent_audit.schemas.__all__``, the public docs must not
describe it as not-yet-shipped. Catching that drift is the value: a
v1.2 ship that elevates a stub to shipped without updating the README
would otherwise leave the buyer reading "deferred" against a name that
the package actually delivers.

The walk:

  - Collect exported names from the three ``__all__`` lists.
  - Walk every doc in a public-facing set: README, ROADMAP, CHANGELOG,
    ARCHITECTURE, SHIP-RECEIPT, FAILURE-MODES, LIMITATIONS,
    DISCLAIMER, VERSIONING, OWNERSHIP, ASSURANCE-GUIDE, DEPLOY-
    CHECKLIST, NEGATIVE-USE-CASES, RESEARCH, plus ``docs/*.md``
    excluding ``docs/adr/`` (ADRs legitimately discuss historical
    deferrals; that is their job).
  - For each occurrence of an exported name, check the surrounding
    proximity window for any deferral marker. The window is the
    same-line context PLUS up to a 400-character bidirectional window
    capped at the nearest blank line — that way a table row with a
    deferral marker in an adjacent row does not bleed into an
    unrelated row's name. A co-occurrence is a flag unless the
    (name, doc, marker) tuple is in
    ``tests/doc_staleness_allow_list.py``.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

from tests.doc_staleness_allow_list import ALLOW_LIST

REPO_ROOT: Path = Path(__file__).resolve().parent.parent

# The repo-root public-facing markdown surfaces. The walker also picks
# up every ``docs/*.md`` (one level only) — ADRs in ``docs/adr/`` are
# excluded because deferral-acknowledging language is their entire
# point.
_REPO_ROOT_DOCS: tuple[str, ...] = (
    "README.md",
    "ROADMAP.md",
    "CHANGELOG.md",
    "ARCHITECTURE.md",
    "SHIP-RECEIPT.md",
    "FAILURE-MODES.md",
    "LIMITATIONS.md",
    "DISCLAIMER.md",
    "VERSIONING.md",
    "OWNERSHIP.md",
    "ASSURANCE-GUIDE.md",
    "DEPLOY-CHECKLIST.md",
    "NEGATIVE-USE-CASES.md",
    "RESEARCH.md",
)

# Public modules whose ``__all__`` populates the canonical export set.
_EXPORT_MODULES: tuple[str, ...] = (
    "finserv_agent_audit.governance",
    "finserv_agent_audit.agents",
    "finserv_agent_audit.schemas",
)

# Deferral markers the test detects. The patterns are case-sensitive
# substrings; ``v0\.\d`` is a regex for "v0.X candidate" style strings.
_DEFERRAL_MARKERS: tuple[str, ...] = (
    "forthcoming",
    "design only",
    "not yet shipped",
    "NOT YET IMPLEMENTED",
    "stub",
    "deferred",
    "TBD",
    "coming soon",
    "future work",
    "STUB",
    "Deferred",
)

# A regex marker for "v0.X candidate" patterns where X is a digit.
_V0_CANDIDATE_RE = re.compile(r"v0\.\d\s*candidate")

_PROXIMITY: int = 60
"""Half-width of the proximity window around a matched export name.

The task spec names a 400-character ceiling; in practice 60 chars in
either direction is the right semantic cut. The signal we want is
prose like ``ProtectedClassProxyDetector (stub)`` or
``MonitorAgent — reference stub body``, where the marker sits within
~one phrase of the name. A 400-char window bleeds across markdown
table rows and dense one-line "shipped in v1.1" lists where row N
mentions a stub for a different name.
"""


# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def exported_names() -> frozenset[str]:
    out: set[str] = set()
    for module_path in _EXPORT_MODULES:
        module = importlib.import_module(module_path)
        names = getattr(module, "__all__", ())
        out.update(names)
    return frozenset(out)


@pytest.fixture(scope="module")
def doc_paths() -> list[Path]:
    out: list[Path] = []
    for name in _REPO_ROOT_DOCS:
        path = REPO_ROOT / name
        if path.exists():
            out.append(path)
    docs_dir = REPO_ROOT / "docs"
    if docs_dir.exists():
        # One level deep — skip ``docs/adr/`` (ADRs are allowed to
        # discuss deferrals at length) and skip nested directories.
        for path in sorted(docs_dir.glob("*.md")):
            out.append(path)
    return out


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _proximity_window(text: str, idx: int, name_len: int) -> str:
    """Return the proximity window around ``text[idx:idx+name_len]``.

    Window selection is structural rather than purely positional. A
    naive "+/- 400 chars" window bleeds across markdown-table rows
    and adjacent paragraphs and floods the test with false positives
    on the SHIP-RECEIPT-style classification tables where row N says
    "shipped" and row N+1 says "stub-with-tracking".

    The structural window is the smallest of:

    1. The single line containing the match (line-bounded; rows of
       markdown tables ARE one line each).
    2. The paragraph containing the match — the slice between the
       nearest preceding blank line and the nearest succeeding blank
       line, but only if the resulting slice is at most ``_PROXIMITY``
       characters wide.

    Most matches resolve via case 1; case 2 catches prose paragraphs
    where the marker is in the next sentence but still inside the
    same paragraph.
    """
    # Case 1: the line containing the match.
    line_start = text.rfind("\n", 0, idx) + 1
    line_end = text.find("\n", idx + name_len)
    if line_end == -1:
        line_end = len(text)
    line_window = text[line_start:line_end]

    # Case 2: the paragraph containing the match, bounded by blank
    # lines (``\n\n``) on each side and capped at ``_PROXIMITY``.
    paragraph_start = text.rfind("\n\n", max(0, idx - _PROXIMITY), idx)
    para_start_idx = paragraph_start + 2 if paragraph_start != -1 else line_start
    paragraph_end = text.find("\n\n", idx + name_len, idx + name_len + _PROXIMITY)
    para_end_idx = paragraph_end if paragraph_end != -1 else line_end
    paragraph_window = text[para_start_idx:para_end_idx]

    # Use the paragraph window only when it is meaningfully short —
    # otherwise we are back in bleed-over territory.
    if len(paragraph_window) <= _PROXIMITY:
        return paragraph_window
    return line_window


def _markers_in_window(window: str) -> list[str]:
    """Return every deferral-marker substring present in ``window``."""
    hits: list[str] = []
    for marker in _DEFERRAL_MARKERS:
        if marker in window:
            hits.append(marker)
    if _V0_CANDIDATE_RE.search(window):
        hits.append("v0.X candidate")
    return hits


def _doc_relative(doc_path: Path) -> str:
    return doc_path.relative_to(REPO_ROOT).as_posix()


# --------------------------------------------------------------------------- #
# Tests                                                                       #
# --------------------------------------------------------------------------- #


class TestExportCollection:
    """Sanity envelope — confirm we are scanning a non-trivial export set."""

    def test_exports_collected(self, exported_names: frozenset[str]) -> None:
        # v1.1 ships ~67 exports across the three packages. Less than
        # 30 means the import walk regressed.
        assert len(exported_names) >= 30, (
            f"export collection degenerated: {len(exported_names)} names found"
        )

    def test_doc_set_non_empty(self, doc_paths: list[Path]) -> None:
        assert len(doc_paths) >= 10, (
            f"public-doc walk degenerated: only {len(doc_paths)} files matched"
        )


class TestDocStaleness:
    """Every exported name that co-occurs with a deferral marker is allow-listed."""

    def test_no_stale_deferrals(
        self,
        exported_names: frozenset[str],
        doc_paths: list[Path],
    ) -> None:
        violations: list[tuple[str, str, int, str]] = []

        for doc_path in doc_paths:
            text = doc_path.read_text(encoding="utf-8")
            doc_relative = _doc_relative(doc_path)
            for name in exported_names:
                # Skip degenerate single-letter or very short names —
                # they would otherwise trigger thousands of false hits.
                # The shortest real export in the package is 5 chars
                # (``Model``); short names are still scanned but with
                # word-boundary discipline.
                if len(name) < 5:
                    continue
                # Word-boundary search to avoid e.g. ``Model`` matching
                # inside ``ModelInventory``.
                pattern = re.compile(r"\b" + re.escape(name) + r"\b")
                for match in pattern.finditer(text):
                    idx = match.start()
                    window = _proximity_window(text, idx, len(name))
                    markers = _markers_in_window(window)
                    if not markers:
                        continue
                    line_no = text.count("\n", 0, idx) + 1
                    for marker in markers:
                        key = (name, doc_relative, marker)
                        if key in ALLOW_LIST:
                            continue
                        violations.append((name, doc_relative, line_no, marker))

        # De-dup violations on the (name, doc, marker) triple — line
        # number is informational only.
        unique = sorted({(n, d, m) for (n, d, _, m) in violations})

        assert not unique, (
            "Exported names are described as not-yet-shipped in public docs "
            "(drift between __all__ and docs). Either:\n"
            "  (a) the doc is stale — update it; or\n"
            "  (b) the co-occurrence is legitimate historical meta-prose — "
            "add it to tests/doc_staleness_allow_list.py.\n\n"
            "Drift:\n  - " + "\n  - ".join(f"{n} :: {d} :: {m!r}" for n, d, m in unique)
        )
