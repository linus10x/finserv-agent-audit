#!/usr/bin/env python3
"""Banned-term lint for framework prose.

Enforces the framework's voice register by failing CI on hits to a
hand-curated list of corporate-buzzword and filler terms. Skips:

  * lines inside fenced code blocks (``` ... ```)
  * lines carrying a ``# noqa: banned-term`` directive
  * ``docs/adr/*.md`` lines inside a "Regulatory Mapping" or "Statutory
    Quotation" section that quote primary-source statutory titles (e.g.
    EU AI Act Art. 15 "accuracy, robustness, cybersecurity").

Walks every ``.md`` and ``.py`` file in the repo, excluding common
build / vendor / cache directories. Exit code 1 on any hit.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BANNED_TERMS: tuple[str, ...] = (
    "delve",
    "leverage",
    "navigate",
    "journey",
    "transformative",
    "unleash",
    "unlock",
    "game-changer",
    "in today's",
    "as a leader",
    "robust",
    "cutting-edge",
    "seamless",
)

EXCLUDE_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "htmlcov",
        "build",
        "dist",
        ".tox",
        "vendor-clauses",
    }
)

# Sections in ADRs where primary-source statutory titles may legitimately
# appear and trigger banned-term hits (e.g. EU AI Act Art. 15 cites the
# word "robustness"). We honour these section headers as exemption gates
# until the next ``## `` heading.
ADR_QUOTE_SECTIONS: tuple[str, ...] = (
    "## Regulatory Mapping",
    "## Statutory Quotation",
    "## Primary Source",
    "### Regulatory Mapping",
    "### Statutory Quotation",
)

NOQA_RE = re.compile(r"#\s*noqa:\s*banned-term", re.IGNORECASE)
FENCE_RE = re.compile(r"^\s*```")
TERM_RES: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (
        term,
        re.compile(
            (r"\b" if term[0].isalnum() else "")
            + re.escape(term)
            + (r"\b" if term[-1].isalnum() else ""),
            re.IGNORECASE,
        ),
    )
    for term in BANNED_TERMS
)


def is_in_adr_quote_section(path: Path) -> bool:
    """Return True iff path is inside docs/adr/*.md."""
    parts = path.parts
    return "docs" in parts and "adr" in parts and path.suffix == ".md"


def walk_repo(root: Path) -> list[Path]:
    """Return every .md and .py file under root, excluding noisy dirs."""
    out: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in (".md", ".py"):
            continue
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        out.append(path)
    return out


def lint_file(path: Path) -> list[tuple[int, str, str]]:
    """Return list of (line_number, term, line_text) hits."""
    hits: list[tuple[int, str, str]] = []
    in_fence = False
    in_quote_section = False
    adr_exempt = is_in_adr_quote_section(path)

    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return hits

    for lineno, line in enumerate(text.splitlines(), start=1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        if adr_exempt:
            stripped = line.strip()
            if stripped.startswith("## ") or stripped.startswith("### "):
                in_quote_section = any(stripped.startswith(hdr) for hdr in ADR_QUOTE_SECTIONS)
                continue
            if in_quote_section:
                continue

        if NOQA_RE.search(line):
            continue

        for term, pattern in TERM_RES:
            if pattern.search(line):
                hits.append((lineno, term, line.rstrip()))

    return hits


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    files = walk_repo(repo_root)

    total_hits = 0
    for path in sorted(files):
        rel = path.relative_to(repo_root)
        # Self-exempt: this lint script naturally enumerates the very
        # tokens it bans. Suppress hits in scripts that DECLARE the list.
        if rel.as_posix() == "scripts/banned_term_lint.py":
            continue
        hits = lint_file(path)
        for lineno, term, line_text in hits:
            print(f"{rel}:{lineno}: banned term '{term}' -> {line_text}")
            total_hits += 1

    if total_hits:
        print(f"\nbanned_term_lint: {total_hits} hit(s) across framework prose")
        return 1
    print("banned_term_lint: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
