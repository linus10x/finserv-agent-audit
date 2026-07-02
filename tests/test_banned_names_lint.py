"""Tests for scripts/banned_names_lint.py — focus on the FAIL-CLOSED gate.

Polarity discipline: the load-bearing assertions verify that fail-closed mode
*errors* (exit 2) when the names-file guard is ABSENT or EMPTY — i.e. they check
for the PRESENCE of the safe behavior (a loud failure), not merely the absence of
an unsafe one. A stale/removed guard must break these tests, not pass them.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "banned_names_lint.py"


def _run(env_extra: dict[str, str]) -> subprocess.CompletedProcess[str]:
    import os

    env = os.environ.copy()
    # neutralize any ambient CI settings so tests are hermetic
    env.pop("CI_REQUIRE_BANNED_NAMES", None)
    env.pop("BANNED_NAMES_FILE", None)
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
    )


# --- opt-in (backward-compatible) mode: absent/empty names file passes -------


def test_absent_names_file_no_flag_passes(tmp_path: Path) -> None:
    missing = tmp_path / "nope.txt"
    r = _run({"BANNED_NAMES_FILE": str(missing)})
    assert r.returncode == 0, r.stderr
    assert "skipping" in r.stdout


def test_empty_names_file_no_flag_passes(tmp_path: Path) -> None:
    empty = tmp_path / "empty.txt"
    empty.write_text("", encoding="utf-8")
    r = _run({"BANNED_NAMES_FILE": str(empty)})
    assert r.returncode == 0, r.stderr


# --- FAIL-CLOSED mode: absent/empty names file is a CONFIG ERROR (exit 2) ----


def test_absent_names_file_with_flag_fails_closed(tmp_path: Path) -> None:
    missing = tmp_path / "nope.txt"
    r = _run({"BANNED_NAMES_FILE": str(missing), "CI_REQUIRE_BANNED_NAMES": "1"})
    assert r.returncode == 2, (
        f"expected fail-closed exit 2, got {r.returncode}: {r.stdout}{r.stderr}"
    )
    assert "FAIL-CLOSED" in r.stderr


def test_empty_names_file_with_flag_fails_closed(tmp_path: Path) -> None:
    empty = tmp_path / "empty.txt"
    empty.write_text("# only a comment\n\n", encoding="utf-8")
    r = _run({"BANNED_NAMES_FILE": str(empty), "CI_REQUIRE_BANNED_NAMES": "1"})
    assert r.returncode == 2, f"expected fail-closed exit 2, got {r.returncode}"
    assert "FAIL-CLOSED" in r.stderr


def test_flag_truthy_variants_all_fail_closed(tmp_path: Path) -> None:
    missing = tmp_path / "nope.txt"
    for val in ("1", "true", "TRUE", "yes", "on"):
        r = _run({"BANNED_NAMES_FILE": str(missing), "CI_REQUIRE_BANNED_NAMES": val})
        assert r.returncode == 2, f"{val!r} should trigger fail-closed"


def test_flag_falsy_variants_do_not_fail_closed(tmp_path: Path) -> None:
    missing = tmp_path / "nope.txt"
    for val in ("0", "", "false", "no", "off"):
        r = _run({"BANNED_NAMES_FILE": str(missing), "CI_REQUIRE_BANNED_NAMES": val})
        assert r.returncode == 0, (
            f"{val!r} should NOT trigger fail-closed (opt-in), got {r.returncode}"
        )


# --- with a provisioned names file, real detection still works ---------------


def test_provisioned_file_detects_a_present_name(tmp_path: Path) -> None:
    # "Autonomy" is pervasive in the framework prose (.md), so this must fire.
    names = tmp_path / "names.txt"
    names.write_text("Autonomy\n", encoding="utf-8")
    r = _run({"BANNED_NAMES_FILE": str(names), "CI_REQUIRE_BANNED_NAMES": "1"})
    assert r.returncode == 1, (
        f"expected a detection hit (exit 1), got {r.returncode}: {r.stdout[:400]}"
    )
    assert "banned name" in r.stdout


def test_provisioned_file_clean_when_name_absent(tmp_path: Path) -> None:
    # Assemble the token from fragments so this literal never appears in-tree —
    # otherwise the lint (which scans .py test files too) would find it here.
    token = "Zzqxwv" + "-" + "".join(["No", "Such", "Token"]) + "-" + str(9931)
    names = tmp_path / "names.txt"
    names.write_text(token + "\n", encoding="utf-8")
    r = _run({"BANNED_NAMES_FILE": str(names), "CI_REQUIRE_BANNED_NAMES": "1"})
    assert r.returncode == 0, f"expected clean (exit 0), got {r.returncode}: {r.stdout[:400]}"
    assert "clean" in r.stdout
