#!/usr/bin/env python3
"""Banned-names lint for framework prose.

Loads a newline-delimited list of names from ``$BANNED_NAMES_FILE``
(default ``.banned-names.txt``) and fails CI on any case-insensitive
match in repo ``.md`` / ``.py`` files. The default file is intentionally
NOT committed to the repo; the lint is opt-in for the author's local
environment and CI runs where the file is provided via secret.

Exemptions:
  * lines inside fenced code blocks
  * lines carrying ``# noqa: banned-name``
  * ADR pages that explicitly recite the banned-names list as a
    discipline reference (``docs/adr/*BANNED_NAMES*``, ``docs/adr/*Voice*``).

Gracefully passes (exit 0) when the names file is absent.
"""

from __future__ import annotations

import os
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

NOQA_RE = re.compile(r"#\s*noqa:\s*banned-name", re.IGNORECASE)
FENCE_RE = re.compile(r"^\s*```")

ADR_EXEMPT_MARKERS: tuple[str, ...] = (
    "banned_names",
    "banned-names",
    "voice_register",
    "voice-register",
)


def load_banned_names(path: Path) -> list[str]:
    if not path.exists():
        return []
    names: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        names.append(stripped)
    return names


def is_adr_exempt(path: Path) -> bool:
    parts = path.parts
    if "docs" not in parts or "adr" not in parts:
        return False
    name = path.name.lower()
    return any(marker in name for marker in ADR_EXEMPT_MARKERS)


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


def lint_file(
    path: Path,
    patterns: list[tuple[str, re.Pattern[str]]],
) -> list[tuple[int, str, str]]:
    hits: list[tuple[int, str, str]] = []
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
        if NOQA_RE.search(line):
            continue
        for name, pattern in patterns:
            if pattern.search(line):
                hits.append((lineno, name, line.rstrip()))
    return hits


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    names_path_str = os.environ.get("BANNED_NAMES_FILE", ".banned-names.txt")
    names_path = Path(names_path_str)
    if not names_path.is_absolute():
        names_path = repo_root / names_path

    if not names_path.exists():
        print(f"banned_names_lint: no names file at {names_path} -> skipping (opt-in lint)")
        return 0

    banned = load_banned_names(names_path)
    if not banned:
        print(f"banned_names_lint: {names_path} is empty -> nothing to check")
        return 0

    patterns: list[tuple[str, re.Pattern[str]]] = []
    for name in banned:
        anchor_l = r"\b" if name[:1].isalnum() else ""
        anchor_r = r"\b" if name[-1:].isalnum() else ""
        patterns.append((name, re.compile(anchor_l + re.escape(name) + anchor_r, re.IGNORECASE)))

    files = walk_repo(repo_root)
    total_hits = 0
    for path in sorted(files):
        rel = path.relative_to(repo_root)
        if rel.as_posix() == "scripts/banned_names_lint.py":
            continue
        if is_adr_exempt(path):
            continue
        hits = lint_file(path, patterns)
        for lineno, name, line_text in hits:
            print(f"{rel}:{lineno}: banned name '{name}' -> {line_text}")
            total_hits += 1

    if total_hits:
        print(f"\nbanned_names_lint: {total_hits} hit(s) across framework prose")
        return 1
    print(f"banned_names_lint: clean ({len(banned)} name(s) checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
