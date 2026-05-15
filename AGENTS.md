# Agent Contributor Guidelines

This repo encodes governance patterns for autonomous AI agents in regulated financial services. If you are an AI coding agent (Claude, Copilot, Gemini, Codex, etc.) opening a PR here, follow these rules to avoid "agentic slop."

## Hard rules
1. Never weaken DEFCON state transitions or Sovereign Veto semantics without an ADR in `docs/adr/` explaining the regulatory impact.
2. Every change touching `patterns/`, `schemas/`, or `examples/` MUST include a corresponding test in `tests/` and a CHANGELOG entry.
3. Audit Chain entries are append-only. Never rewrite history in `examples/audit_chain/`.
4. Human-in-the-loop checkpoints are non-negotiable. Do not refactor them into auto-approve paths.

## PR hygiene
- One logical change per PR. No drive-by reformatting.
- Include the agent session transcript (or a link to it) in the PR body.
- Run `pre-commit run --all-files` and `pytest -q` before pushing.
- Map the change to EU AI Act articles when relevant (see `docs/eu_ai_act_mapping.md`).

## Tone
- Commit messages: Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`).
- No marketing language in code comments.
- Cite sources for any regulatory claim.
