# OPS-001: CI Self-Healing Watch Loop

**Status:** ACTIVE  
**Date:** 2026-05-15  
**Author:** Kunjar Bhaduri  
**Repo:** finserv-agent-audit  

> **Scope note:** This ADR records an internal CI tooling decision (the `scripts/ci_watch.py` self-heal loop) and is **not** part of the published governance pattern set. Governance ADRs live in `docs/adr/` numbered 0001 onward. Operational tooling ADRs live here in `docs/adr/ops/` with the `OPS-NNN` prefix.

---

## Context

Three consecutive CI failures on `main` (F811 duplicate import, ruff format
alignment spacing, E401/E501 inline import + long signature) were caught
only after push, requiring manual fix cycles. Each cycle cost one
conversation turn + one GitHub Actions run (~90 seconds). The pattern
matches a recurring CI-failure class documented in the author's prior
operating-loop research.

Root cause: no structured loop exists to (1) poll CI deterministically,
(2) classify failures into actionable categories, and (3) enforce a
"issue count must decrease" invariant before declaring stall.

---

## Decision

Implement `scripts/ci_watch.py` — a CLI tool that ports a
**Check-Revise-Escalate** revision loop to
GitHub Actions CI monitoring.

### Loop Contract

```
prev_issue_count = ∞
iteration = 0

LOOP:
  1. Poll GitHub Actions until run status = completed (or timeout 600s)
  2. If conclusion = success  →  EXIT 0  (green)
  3. Classify each failed job into FailureCategory
  4. issue_count = len(classified failures)
  5. If iteration > 1 AND issue_count >= prev_issue_count
       →  ESCALATE exit 2  (stall: human required)
  6. If iteration >= max_iter (default 3)
       →  ESCALATE exit 3  (max iterations: human required)
  7. Print structured fix report (category + job + step + fix hint)
  8. iteration += 1; prev_issue_count = issue_count
  9. Operator applies fix, pushes new SHA, re-invokes with new SHA
  10. GOTO 1
```

### Failure Taxonomy

| Category | Detection | Fix strategy |
|---|---|---|
| `ruff-lint` | step name contains "lint" or "ruff check" | `ruff check --fix .` then verify |
| `ruff-format` | step name contains "format" | `ruff format .` then `--check` |
| `mypy` | step name contains "mypy" or "type" | `mypy src/ ...` — fix annotations |
| `pytest` | step name contains "pytest" or "test" | `pytest -x -v` — read first FAILED |
| `coverage` | step name contains "cov" | `pytest --cov --cov-report=term-missing` |
| `unknown` | none of the above | Check Actions tab raw log |

### Escalation Rules

| Condition | Exit code | Action |
|---|---|---|
| All gates green | 0 | Done |
| Failed, fixable, iteration < max | 1 | Print fix report, await next push |
| Issue count stalled (not decreasing) | 2 | Human review — structural problem |
| Max iterations reached | 3 | Human review — approach needs rethink |
| Timeout (600s) | 1 | Check Actions tab manually |

---

## Usage

```bash
# After pushing a commit:
python scripts/ci_watch.py --sha <commit-sha>

# With explicit GitHub token:
python scripts/ci_watch.py --sha <commit-sha> --token ghp_...

# With custom max iterations:
python scripts/ci_watch.py --sha <commit-sha> --max-iter 5

# GITHUB_TOKEN env var is read automatically if set:
export GITHUB_TOKEN=ghp_...
python scripts/ci_watch.py --sha $(git rev-parse HEAD)
```

---

## Pre-mortem

1. **GitHub API rate limit (60 req/hr unauth, 5000 req/hr auth).**  
   At 15s poll interval, a 600s wait = 40 requests. Well within limits with
   auth. Use `--token` or `GITHUB_TOKEN` in practice.

2. **Run not yet queued when script starts.**  
   `get_latest_run_for_sha` returns None → script prints "No run found yet"
   and retries. Safe.

3. **Multiple workflow runs for same SHA (e.g., push + manual trigger).**  
   Script takes the most recent run (`runs[0]` after GitHub sorts by
   created_at desc). Correct in the common case.

4. **Step name strings change if `.github/workflows/ci.yml` is edited.**  
   Classification is string-match based. If CI yaml step names change,
   re-sync the keyword strings in `classify_failure()`. Low maintenance cost.

5. **Network failure mid-poll.**  
   `_gh_request` raises — script exits with traceback. Add retry wrapper
   in a future patch if needed.

---

## Relationship to prior operating-loop research

This ADR ports patterns from the author's prior multi-agent operating-loop
work:

- a Check-Revise-Escalate 3-iteration revision contract
- an operating-loop event vocabulary (VERIFY_PASS / VERIFY_FAIL / INCIDENT_OPENED)
- a CI failure-category taxonomy with a PostToolUse early-warning philosophy

The `finserv-agent-audit` version operates at the GitHub Actions layer
(post-push) rather than the Claude Code tool-use layer (pre-push), because
this repo does not have a local Claude Code session with `.claude/settings.json`.
A pre-push git hook calling `ruff check . && ruff format --check .` is the
recommended local complement — see `docs/adr/pre-push-hook.md` (future).

---

## Reversibility

Single `git revert`. No src/ mutations. No test mutations. No CI yaml changes.
The watch script is invoked manually; it does not auto-push fixes without
human approval.
