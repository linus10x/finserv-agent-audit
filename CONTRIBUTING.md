# Contributing to finserv-agent-audit

Thank you for your interest in contributing. This repository exists because the failure modes that produced these patterns are real — and the teams dealing with them rarely have reference implementations to work from.

---

## What We Welcome

- **New governance patterns** — additional patterns for agent systems in regulated environments (insurance, lending, compliance, fraud detection)
- **Compliance mappings** — additional regulatory frameworks beyond EU AI Act (SEC, FCA, MAS, APRA)
- **Test coverage improvements** — edge cases, adversarial inputs, stress scenarios
- **Documentation improvements** — calibration guidance, worked examples, case studies (anonymized)
- **Bug reports** — incorrect behavior in the reference implementations

## What We Do Not Accept

- Production strategy logic or alpha signals of any kind
- Implementation code tied to specific brokers or execution venues
- Anything that is not governance-layer abstraction

---

## Development Setup

```bash
git clone https://github.com/linus10x/finserv-agent-audit.git
cd finserv-agent-audit
pip install -r requirements.txt
```

**Standards:**
- Python: 3.12+
- Formatter: `ruff format .`
- Linter: `ruff check .`
- Type checker: `mypy`
- Tests: `pytest tests/ -v`

All four must pass before submitting a PR. CI enforces this on every push.

---

## Submitting a Pattern

1. Fork the repository
2. Create a branch: `git checkout -b pattern/your-pattern-name`
3. Add your pattern file under `patterns/` or `examples/`
4. Add tests under `tests/`
5. Add documentation under `docs/` if the pattern warrants it
6. Ensure `ruff`, `mypy`, and `pytest` all pass
7. Open a PR with a clear title and description covering: what problem it solves, what regulated environment it targets, and what EU AI Act (or other framework) article it addresses

---

## Questions?

Open a GitHub Discussion rather than an issue for questions. Issues are for bugs and concrete feature requests.
