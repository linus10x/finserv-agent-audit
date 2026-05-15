#!/usr/bin/env python3
"""
CI Self-Healing Watch Loop for finserv-agent-audit.

Ports the APEX Check-Revise-Escalate pattern to GitHub Actions CI.
Runs after every push to main, polls the workflow run, classifies
failures, and emits structured fix guidance for the next iteration.

Usage:
    python scripts/ci_watch.py --sha <commit-sha> [--max-iter 3] [--token <GH_TOKEN>]

Exit codes:
    0  All CI gates green
    1  CI failed — escalation report printed to stdout
    2  Loop stalled (issue count not decreasing) — human required
    3  Max iterations reached — human required
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

try:
    import urllib.request as _req
except ImportError:
    _req = None  # type: ignore[assignment]

OWNER = "linus10x"
REPO = "finserv-agent-audit"
API_BASE = "https://api.github.com"
POLL_INTERVAL_S = 15
POLL_TIMEOUT_S = 600  # 10 minutes max wait for a run to complete


class FailureCategory(StrEnum):
    RUFF_LINT = "ruff-lint"
    RUFF_FORMAT = "ruff-format"
    MYPY = "mypy"
    PYTEST = "pytest"
    COVERAGE = "coverage"
    UNKNOWN = "unknown"


@dataclass
class CIFailure:
    category: FailureCategory
    job_name: str
    step_name: str
    raw_conclusion: str
    fix_hint: str


# ---------------------------------------------------------------------------
# Fix hint catalogue — mirrors the ruff rule taxonomy in pyproject.toml
# ---------------------------------------------------------------------------
FIX_HINTS: dict[FailureCategory, str] = {
    FailureCategory.RUFF_LINT: (
        "Run: ruff check --fix . && ruff check .\n"
        "Common rules: E501 (line > 100 chars), E401 (multi-import), "
        "F811 (redefined import), E402 (import not at top).\n"
        "After fix: confirm `ruff check .` exits 0 before pushing."
    ),
    FailureCategory.RUFF_FORMAT: (
        "Run: ruff format .\n"
        "Then verify: ruff format --check . exits 0.\n"
        "Common causes: manual alignment spacing, trailing whitespace, "
        "un-wrapped long lines that ruff-check passed but formatter rejects."
    ),
    FailureCategory.MYPY: (
        "Run: mypy src/ examples/ schemas/ patterns/\n"
        "Common fixes: missing return type annotations, Optional not imported, "
        "wrong TypeVar usage. Check mypy.ini [tool.mypy] strict flags."
    ),
    FailureCategory.PYTEST: (
        "Run: pytest tests/ -x -v\n"
        "Read the first FAILED block — fixture scope, import error, or assertion.\n"
        "If import error: check that the module path in conftest.py matches src layout."
    ),
    FailureCategory.COVERAGE: (
        "Run: pytest tests/ --cov=src --cov-report=term-missing\n"
        "Find uncovered lines in the MISSING column.\n"
        "Add a test that exercises the missing branch — typically error/exception paths."
    ),
    FailureCategory.UNKNOWN: (
        "Check the Actions tab for the raw log.\n"
        "URL: https://github.com/linus10x/finserv-agent-audit/actions"
    ),
}


def _gh_request(path: str, token: str | None) -> Any:
    url = f"{API_BASE}{path}"
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = _req.Request(url, headers=headers)
    with _req.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def get_latest_run_for_sha(sha: str, token: str | None) -> dict[str, Any] | None:
    data = _gh_request(f"/repos/{OWNER}/{REPO}/actions/runs?head_sha={sha}&per_page=10", token)
    runs = data.get("workflow_runs", [])
    if not runs:
        return None
    # Return the most recent run (first in list)
    return runs[0]


def wait_for_completion(sha: str, token: str | None) -> dict[str, Any]:
    """Poll until run completes or timeout."""
    deadline = time.time() + POLL_TIMEOUT_S
    attempt = 0
    while time.time() < deadline:
        run = get_latest_run_for_sha(sha, token)
        if run is None:
            print(f"  [poll {attempt}] No run found yet for {sha[:12]} — waiting...")
        else:
            status = run.get("status", "unknown")
            conclusion = run.get("conclusion") or "in_progress"
            print(f"  [poll {attempt}] run={run['id']} status={status} conclusion={conclusion}")
            if status == "completed":
                return run
        attempt += 1
        time.sleep(POLL_INTERVAL_S)
    msg = f"Timeout: CI run for {sha[:12]} did not complete within {POLL_TIMEOUT_S}s"
    raise TimeoutError(msg)


def get_failed_jobs(run_id: int, token: str | None) -> list[dict[str, Any]]:
    data = _gh_request(f"/repos/{OWNER}/{REPO}/actions/runs/{run_id}/jobs", token)
    return [j for j in data.get("jobs", []) if j.get("conclusion") == "failure"]


def classify_failure(job: dict[str, Any]) -> CIFailure:
    failed_step = next(
        (s for s in job.get("steps", []) if s.get("conclusion") == "failure"),
        {"name": "unknown"},
    )
    step_name: str = failed_step.get("name", "unknown").lower()

    if "lint" in step_name or "ruff check" in step_name:
        cat = FailureCategory.RUFF_LINT
    elif "format" in step_name or "ruff format" in step_name:
        cat = FailureCategory.RUFF_FORMAT
    elif "mypy" in step_name or "type" in step_name:
        cat = FailureCategory.MYPY
    elif "coverage" in step_name or "cov" in step_name:
        cat = FailureCategory.COVERAGE
    elif "pytest" in step_name or "test" in step_name:
        cat = FailureCategory.PYTEST
    else:
        cat = FailureCategory.UNKNOWN

    return CIFailure(
        category=cat,
        job_name=job.get("name", "unknown"),
        step_name=failed_step.get("name", "unknown"),
        raw_conclusion=job.get("conclusion", "unknown"),
        fix_hint=FIX_HINTS[cat],
    )


# ---------------------------------------------------------------------------
# APEX Check-Revise-Escalate loop
# ---------------------------------------------------------------------------


@dataclass
class LoopState:
    iteration: int = 0
    prev_issue_count: int = 9999
    failures: list[CIFailure] = field(default_factory=list)


def run_loop(sha: str, token: str | None, max_iter: int = 3) -> int:
    """
    APEX revision loop — Check-Revise-Escalate.

    Iteration flow (mirrors revision-loop.md):
      1. Wait for CI run to complete
      2. If green -> exit 0
      3. Classify failures -> compute issue_count
      4. If issue_count >= prev_issue_count -> stall escalation (exit 2)
      5. If iteration >= max_iter -> max-iter escalation (exit 3)
      6. Print structured fix report -> caller (human or future bot) applies fix
      7. Increment iteration, update prev_issue_count, loop
    """
    state = LoopState()

    print(f"\n{'=' * 60}")
    print("CI SELF-HEAL LOOP — finserv-agent-audit")
    print(f"SHA: {sha}")
    print(f"Max iterations: {max_iter}")
    print(f"{'=' * 60}\n")

    while True:
        state.iteration += 1
        print(f"--- Iteration {state.iteration}/{max_iter} ---")

        # Step 1: wait for CI
        try:
            run = wait_for_completion(sha, token)
        except TimeoutError as exc:
            print(f"ESCALATE: {exc}")
            return 1

        conclusion = run.get("conclusion", "unknown")
        run_url = run.get("html_url", "")

        # Step 2: green path
        if conclusion == "success":
            print("\n✅ CI GREEN — all gates passed.")
            print(f"   Run: {run_url}")
            return 0

        # Step 3: classify failures
        failed_jobs = get_failed_jobs(run["id"], token)
        state.failures = [classify_failure(j) for j in failed_jobs]
        issue_count = len(state.failures)

        print(f"\n❌ CI FAILED — {issue_count} job(s) failed.")
        print(f"   Run: {run_url}\n")

        # Step 4: stall detection
        if issue_count >= state.prev_issue_count and state.iteration > 1:
            print("ESCALATE: Loop stalled — issue count not decreasing.")
            print("Human review required. Remaining failures:")
            _print_failures(state.failures)
            return 2

        # Step 5: max iterations
        if state.iteration >= max_iter:
            print(f"ESCALATE: Max iterations ({max_iter}) reached.")
            print("Human review required. Remaining failures:")
            _print_failures(state.failures)
            return 3

        # Step 6: structured fix report
        state.prev_issue_count = issue_count
        print(f"Revision iteration {state.iteration}/{max_iter} -- {issue_count} failure(s)\n")
        _print_failures(state.failures)
        print(
            "\nApply the fix hints above, push a new commit, "
            "then re-run this script with the new SHA."
        )
        # In a fully autonomous loop, a bot would apply the fix here.
        # In the current human-in-loop design, we exit 1 so the operator
        # can apply the fix and re-invoke with the new SHA.
        return 1


def _print_failures(failures: list[CIFailure]) -> None:
    for i, f in enumerate(failures, 1):
        print(f"  [{i}] category  : {f.category.value}")
        print(f"       job       : {f.job_name}")
        print(f"       step      : {f.step_name}")
        print("       fix hint  :")
        for line in f.fix_hint.splitlines():
            print(f"                   {line}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="CI self-heal watch loop")
    parser.add_argument("--sha", required=True, help="Git commit SHA to monitor")
    parser.add_argument("--max-iter", type=int, default=3, help="Max fix iterations (default 3)")
    parser.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN"),
        help="GitHub token (or set GITHUB_TOKEN env var)",
    )
    args = parser.parse_args()
    sys.exit(run_loop(args.sha, args.token, args.max_iter))


if __name__ == "__main__":
    main()
