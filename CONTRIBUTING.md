# Contributing to finserv-agent-audit

Thank you for considering a contribution. This project exists because the failure modes that produced these patterns are real — and the teams dealing with them rarely have reference implementations to work from. Every contribution that improves reliability, coverage, or clarity directly helps engineers in regulated environments.

---

## Table of Contents

- [First Contribution](#first-contribution)
- [Development Setup](#development-setup)
- [What to Work On](#what-to-work-on)
- [Pattern Contribution Standards](#pattern-contribution-standards)
- [Commit Message Conventions](#commit-message-conventions)
- [Pull Request Process](#pull-request-process)
- [Code Style](#code-style)
- [Questions](#questions)

---

## First Contribution

New to open source or this project? Start here:

1. Look for issues labelled [`good first issue`](https://github.com/linus10x/finserv-agent-audit/issues?q=label%3A%22good+first+issue%22) — these are intentionally scoped to be completable without deep knowledge of the codebase.
2. Comment on the issue to let others know you're working on it.
3. Fork the repo, make your change, and open a PR against `main`.
4. Keep the PR focused — one issue per PR.

Not ready to write code? Documentation improvements, typo fixes, and adding test cases for edge conditions are equally valuable.

---

## Development Setup

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/finserv-agent-audit.git
cd finserv-agent-audit

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install in editable mode with dev dependencies
pip install -e ".[dev]"

# 4. Install pre-commit hooks (runs ruff + mypy on every commit)
pre-commit install

# 5. Verify everything passes
pytest tests/ -v --cov
ruff check .
ruff format --check .
mypy .
```

All four commands must pass before opening a PR. CI enforces the same checks.

---

## What to Work On

**Bug fixes** — anything in the [issues list](https://github.com/linus10x/finserv-agent-audit/issues) labelled `bug`.

**New governance patterns** — see [ROADMAP.md](ROADMAP.md) for planned patterns. If you want to contribute something not on the roadmap, open a [Pattern Request](https://github.com/linus10x/finserv-agent-audit/issues/new?template=pattern_request.yml) first to align before investing time.

**Test coverage** — the coverage floor is 80%; anything that brings it closer to 100% on untested branches is welcome.

**Documentation** — if a doc is unclear, fix it. The `docs/` directory is as important as the code.

---

## Pattern Contribution Standards

Every new pattern must include:

1. **Implementation file** in `patterns/` or `schemas/` with full type hints
2. **Docstring** at the module and class level explaining: what it does, what failure mode it addresses, and which regulation it maps to
3. **Regulation mapping** — at least one comment linking to a specific article or rule (e.g. `# EU AI Act Art. 14 — human oversight`)
4. **Test file** in `tests/` covering: happy path, at least one failure/edge case, and any state persistence logic
5. **README.md update** — add a row to the Patterns table
6. **CHANGELOG.md update** — add an entry under `[Unreleased]`

Patterns without tests will not be merged.

---

## Commit Message Conventions

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

[optional body]

[optional footer]
```

**Types:**
- `feat` — new pattern or feature
- `fix` — bug fix
- `docs` — documentation only
- `test` — adding or fixing tests
- `refactor` — no behaviour change
- `chore` — CI, tooling, dependencies
- `perf` — performance improvement

**Examples:**
```
feat(patterns): add circuit breaker for model drift (SR 11-7)
fix(schemas): handle JSONDecodeError in audit chain load
docs(autonomy-ladder): clarify A2 vs A3 human oversight boundary
test(defcon): add hysteresis edge case for rapid oscillation
```

Keep the subject line under 72 characters. Use the body to explain *why*, not *what*.

### Developer Certificate of Origin (DCO) — required on every commit

Every commit must include a `Signed-off-by:` line in the commit trailer attesting to the [Developer Certificate of Origin v1.1](https://developercertificate.org/). This is the same lightweight inbound-IP hygiene mechanism used by the Linux kernel, the Cloud Native Computing Foundation, and the Linux Foundation AI & Data Foundation. It does not require a CLA.

To sign off, append the `-s` flag to your commit:

```bash
git commit -s -m "feat(patterns): add circuit breaker for model drift (SR 11-7)"
```

This appends a line of the form:

```
Signed-off-by: Your Name <your.email@example.com>
```

By signing off, you certify that you wrote the contribution or otherwise have the right to submit it under the dual MIT OR Apache-2.0 license. The full DCO text is at `https://developercertificate.org/`.

CI rejects pull requests whose commits are missing the sign-off line. Adopters using `commit-msg` hooks can pre-empt CI rejection locally; see `pre-commit` configuration in `.pre-commit-config.yaml` for the local check.

---

## Pull Request Process

1. **Open a draft PR early** if you want feedback before the work is complete.
2. **Fill in the PR template** — every checkbox in the template is enforced by reviewers.
3. **Keep PRs small** — a PR that touches one pattern and its tests is easier to review than one that touches everything.
4. **Respond to review comments within a reasonable time** — if you need more time, say so in the PR thread.
5. **Squash or rebase before merge** — keep `main` history clean.

CI must be green before merge. No exceptions.

---

## Code Style

- **Formatter:** `ruff format` (Black-compatible)
- **Linter:** `ruff check` (PEP 8 + many additional rules — see `pyproject.toml`)
- **Type checker:** `mypy --strict`
- **Python version:** 3.12+
- **No external dependencies** in the core library — stdlib only. Dev/test dependencies are allowed in `[project.optional-dependencies]`.

The pre-commit hooks enforce ruff and mypy on every commit. Install them with `pre-commit install`.

---

## Questions

For questions about a contribution approach, design decisions, or regulatory interpretation:

- Open a [Discussion](https://github.com/linus10x/finserv-agent-audit/discussions) — preferred for design questions
- Comment on the relevant issue

Please do not open issues for questions — use Discussions.
