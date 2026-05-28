#!/usr/bin/env python3
"""Tamper-language lint.

Detects unhedged uses of the phrase ``tamper-evident`` in framework
prose. The framework discipline is: tamper-evident hash chains detect
modification within the trust boundary but do not prevent it. Every
public use of ``tamper-evident`` must therefore co-occur on the same
line with at least one hedge marker:

  * ``hash-chain`` / ``hash chain``
  * ``within-trust-boundary`` / ``within trust boundary``
  * ``detection but not``
  * ``mechanism``
  * ``SHA-256``

Lines inside fenced code blocks (``` ... ```) are exempt. The lint
script itself is exempt (it must enumerate the very phrase it lints).

Walks every ``.md`` and ``.py`` file in the repo, excluding common
build / vendor / cache directories. Exit code 1 on any hit.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

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

TAMPER_RE = re.compile(r"\btamper-evident\b", re.IGNORECASE)
FENCE_RE = re.compile(r"^\s*```")
HEDGE_MARKERS: tuple[str, ...] = (
    "hash-chain",
    "hash chain",
    "within-trust-boundary",
    "within trust boundary",
    "detection but not",
    "mechanism",
    "SHA-256",
)


def walk_repo(root: Path) -> list[Path]:
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


def has_hedge(line: str) -> bool:
    lowered = line.lower()
    return any(marker.lower() in lowered for marker in HEDGE_MARKERS)


def lint_file(path: Path) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    in_fence = False

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
        if not TAMPER_RE.search(line):
            continue
        if has_hedge(line):
            continue
        hits.append((lineno, line.rstrip()))

    return hits


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    files = walk_repo(repo_root)

    total_hits = 0
    for path in sorted(files):
        rel = path.relative_to(repo_root)
        if rel.as_posix() == "scripts/tamper_language_lint.py":
            continue
        hits = lint_file(path)
        for lineno, line_text in hits:
            print(
                f"{rel}:{lineno}: unhedged 'tamper-evident' (needs one of "
                f"{list(HEDGE_MARKERS)}) -> {line_text}"
            )
            total_hits += 1

    if total_hits:
        print(f"\ntamper_language_lint: {total_hits} hit(s) across framework prose")
        return 1
    print("tamper_language_lint: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
