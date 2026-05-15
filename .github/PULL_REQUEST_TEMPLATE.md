## Summary

<!-- One paragraph: what this PR adds or fixes and why -->

## Changes

- 
- 

## Pattern / File Affected

<!-- Which pattern or module does this touch? -->
- [ ] `examples/defcon_state_machine.py`
- [ ] `patterns/sovereign_veto.py`
- [ ] `schemas/audit_event.py`
- [ ] `docs/`
- [ ] CI / infrastructure
- [ ] New pattern (describe below)

## Checklist

### Code Quality
- [ ] `ruff check .` passes with no errors
- [ ] `mypy examples/ schemas/ patterns/` passes
- [ ] `pytest tests/ -v` passes — all existing tests green
- [ ] New tests added for new behavior (or explain why not needed)
- [ ] Coverage does not decrease below current baseline

### Governance Standard
- [ ] No strategy logic, alpha signals, or execution venue references included
- [ ] All numeric thresholds (if any) are clearly marked as illustrative examples
- [ ] Audit trail is preserved — no changes break `AuditChain.verify()`
- [ ] Human-in-the-loop requirements are maintained — no agent can self-clear a veto
- [ ] `CHANGELOG.md` updated under `[Unreleased]` with a concise entry

### Documentation
- [ ] Docstrings updated for any changed public API
- [ ] `README.md` updated if a new pattern is added to the patterns table
- [ ] Compliance notes updated if regulatory mapping changes

## Testing Notes

<!-- How did you verify this? What edge cases did you test? -->

## Regulatory Context

<!-- Optional: which regulation or audit finding motivated this change? -->


## Agent attribution (if AI-authored)
- Agent: <!-- claude-code / copilot / gemini / codex / human -->
- Session transcript / link:
- Human reviewer who validated the changes:
- [ ] Followed `AGENTS.md` hard rules
