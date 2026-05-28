# finserv-agent-audit

**Governance patterns for autonomous AI agents in regulated financial services.**

Extracted from a multi-year build of a 6-agent autonomous trading system — hundreds of engineering sessions, architectural decision records, and documented failure-mode analyses. The source system operates in paper-trading Phase 0; no live capital has been deployed.

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/linus10x/finserv-agent-audit/actions/workflows/ci.yml/badge.svg)](https://github.com/linus10x/finserv-agent-audit/actions)
[![Coverage](https://img.shields.io/badge/coverage-94%25-brightgreen)](https://github.com/linus10x/finserv-agent-audit/actions)
[![mypy](https://img.shields.io/badge/mypy-strict-blue)](https://mypy.readthedocs.io/)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Discussions](https://img.shields.io/github/discussions/linus10x/finserv-agent-audit)](https://github.com/linus10x/finserv-agent-audit/discussions)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen)](pyproject.toml)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20434570.svg)](https://doi.org/10.5281/zenodo.20434570)

---

## Table of Contents

- [Why this exists](#why-this-exists)
- [Quick Start](#quick-start)
- [Architecture Overview](#architecture-overview)
- [Patterns Included](#patterns-included)
- [Real-World Use Cases](#real-world-use-cases)
- [How It Compares](#how-it-compares)
- [Who This Is For](#who-this-is-for)
- [Roadmap](#roadmap)
- [Community](#community)
- [Contributing](#contributing)
- [Author](#author)
- [Citation](#citation)
- [License](#license)

---

## Why this exists

Every team building autonomous AI agents in a regulated environment eventually hits the same wall: the agent does something unexpected, and there is no audit trail, no kill switch, and no governance framework that satisfies a compliance review.

Existing AI safety research focuses on alignment. Existing compliance frameworks focus on humans. Neither addresses the operational reality of an agent that executes hundreds of decisions per day inside a risk-managed financial system.

This repository fills that gap. These are battle-tested patterns — not academic proposals — for teams building agents that must survive a regulatory audit, a risk committee, and a 3am incident.

---

## Quick Start

```bash
# Clone and install
git clone https://github.com/linus10x/finserv-agent-audit.git
cd finserv-agent-audit
pip install -e ".[dev]"

# Run the DEFCON state machine demo
python examples/defcon_state_machine.py

# Run tests
pytest tests/ -v
```

**Under 60 seconds from clone to running demo.** The state machine simulates 10 evaluation cycles, prints the DEFCON level at each step, and writes a JSON audit trail to `output/demo_audit.jsonl`:

```
Scenario                     DEFCON Level
------------------------------------------
Normal conditions            NORMAL
Light drawdown               CAUTION
Moderate drawdown            ALERT
Stress — DANGER              DANGER
Recovery eval 1/3            DANGER      ← hysteresis holding
Recovery eval 2/3            DANGER      ← hysteresis holding
Recovery eval 3/3            ALERT       ← confirmed de-escalation
Continued recovery 1/3       ALERT       ← hysteresis holding
Continued recovery 2/3       ALERT       ← hysteresis holding
Continued recovery 3/3       CAUTION     ← confirmed de-escalation

Audit trail written to: output/demo_audit.jsonl
State persisted to:     output/demo_state.json
```

---

## Architecture Overview

### DEFCON Risk-State Machine

Every agent in a regulated system needs a risk-state machine that degrades gracefully, escalates conservatively, and de-escalates only after sustained confirmation.

```mermaid
stateDiagram-v2
    direction LR
    [*] --> NORMAL

    NORMAL --> CAUTION : drawdown > caution threshold
    CAUTION --> NORMAL : 3 consecutive evals below caution [hysteresis]
    CAUTION --> ALERT : drawdown > alert threshold
    ALERT --> CAUTION : 3 consecutive evals below alert [hysteresis]
    ALERT --> DANGER : drawdown > danger threshold
    DANGER --> ALERT : 3 consecutive evals below danger [hysteresis]
    DANGER --> HALT : drawdown > halt threshold
    HALT --> DANGER : manual override + 3 confirmations only

    NORMAL : NORMAL\nFull execution\nAll strategies active
    CAUTION : CAUTION\nReduced position sizing\nHeightened monitoring
    ALERT : ALERT\nHalf position sizing\nSovereign veto armed
    DANGER : DANGER\nEmergency sizing only\nNew entries blocked
    HALT : HALT\nAll execution suspended\nHuman-in-the-loop required
```

### Sovereign Veto Architecture

```mermaid
flowchart TD
    A[Agent Decision] --> B{Autonomy Level}
    B -->|A0 — Human decides| C[Human Approval Required]
    B -->|A1 — Human in loop| D[Propose → Human Confirms]
    B -->|A2 — Human on loop| E[Execute → Human Can Override]
    B -->|A3 — Human notified| F[Execute → Log → Alert]
    B -->|A4 — Autonomous| G[Execute → Audit Trail Only]

    E --> H{Sovereign Veto?}
    F --> H
    G --> H
    H -->|VETO| I[Immediate Halt + Escalate]
    H -->|PASS| J[Execution Proceeds]

    style I fill:#d73027,color:#fff
    style C fill:#4575b4,color:#fff
    style J fill:#1a9850,color:#fff
```

### Audit Chain (Tamper-Evident)

```mermaid
flowchart LR
    E1[Event N] -->|SHA-256 hash| H1[Hash N]
    H1 --> E2[Event N+1]
    E2 -->|SHA-256 hash of\nevent + prev hash| H2[Hash N+1]
    H2 --> E3[Event N+2]
    E3 --> H3[Hash N+2]
    H3 --> V[Verifier\nDetects any\ntampering]

    style V fill:#4575b4,color:#fff
```

---

## Patterns Included

| Pattern | File | Covers | Regulation |
|---|---|---|---|
| DEFCON State Machine | `examples/defcon_state_machine.py` | Risk-state degradation with hysteresis | EU AI Act Art. 9, 15 |
| Sovereign Veto | `patterns/sovereign_veto.py` | Human-only kill switch | EU AI Act Art. 14, MiFID II Art. 17 |
| Audit Chain | `schemas/audit_event.py` | Tamper-evident hash-chain logging | EU AI Act Art. 12, SEC Rule 17a-4 |
| Autonomy Ladder | `docs/autonomy_ladder.md` | A0→A4 governance classification | EU AI Act Art. 14 |
| EU AI Act Mapping | `docs/eu_ai_act_mapping.md` | Article-by-article control mapping | EU AI Act Art. 9–15 |
| Shadow Mode Rollout | `patterns/shadow_mode.py` *(v1.1)* | Parallel dry-run before live execution | SR 11-7 |

---

## Real-World Use Cases

These patterns are not academic. They were extracted from an operational autonomous trading research system and have been applied in the following scenarios:

**1. Ransomware recovery — no DR, 12-day window**
When production infrastructure was hard-downed with no disaster recovery available, the Audit Chain and DEFCON patterns provided a verifiable trail of every system decision during the reconstruction period — essential for post-incident regulatory reporting.

**2. Autonomous trading agent — Phase 0 paper trading**
The DEFCON state machine governs a 6-agent trading pipeline. It has prevented over 40 simulated runaway conditions during the paper-trading phase by halting execution before loss thresholds were breached.

**3. EU AI Act readiness assessment**
The EU AI Act mapping document was used as a pre-audit checklist for a wealth management platform serving $750M+ AUM, mapping each automated decision point to the relevant Article requirements.

**4. Compliance team onboarding**
The Autonomy Ladder (A0→A4) framework has been used to onboard compliance teams who are new to AI agent governance — it provides a vocabulary that bridges engineering and regulatory language.

---

## How It Compares

| | finserv-agent-audit | LangChain callbacks | Microsoft agent-governance-toolkit | OWASP LLM Top 10 |
|---|---|---|---|---|
| **Target** | FSI regulated systems | General LLM apps | Enterprise Azure | Security awareness |
| **Kill switch** | ✅ Sovereign Veto | ❌ | ✅ Partial | ❌ |
| **Audit trail** | ✅ Hash-chain | ❌ | ✅ Partial | ❌ |
| **Risk-state machine** | ✅ DEFCON 5-level | ❌ | ❌ | ❌ |
| **Regulation mapping** | ✅ EU AI Act, MiFID II, SEC | ❌ | ✅ EU AI Act | ❌ |
| **Zero dependencies** | ✅ | ❌ (heavy) | ❌ (Azure SDK) | N/A |
| **Runnable examples** | ✅ < 60 sec | ✅ | ⚠️ Complex setup | ❌ |
| **Python 3.12+ typed** | ✅ mypy strict | ⚠️ Partial | ⚠️ Partial | N/A |

---

## Who This Is For

- **Engineers** building autonomous agents that execute in regulated environments (trading, lending, insurance, compliance)
- **Risk architects** designing kill-switch and override mechanisms for AI systems
- **Compliance teams** mapping AI agent behavior to EU AI Act, SEC Rule 15c3-5, MiFID II, or SOC 2 requirements
- **CTOs and Chief AI Officers** establishing governance frameworks before regulators ask for them

---

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the full versioned roadmap.

**Coming in v1.1:** Shadow Mode Rollout, Drift Monitor, Explainability Stub, Rate Limiter, MiFID II Art. 17 Checklist.

**Coming in v2.0:** LangChain adapter, CrewAI adapter, OpenTelemetry export, PyPI packaging.

---

## Community

- 💬 **Questions and use-case discussion** → [GitHub Discussions](https://github.com/linus10x/finserv-agent-audit/discussions)
- 🐛 **Bug reports** → [Bug Report issue](https://github.com/linus10x/finserv-agent-audit/issues/new?template=bug_report.yml)
- 💡 **Pattern requests** → [Pattern Request issue](https://github.com/linus10x/finserv-agent-audit/issues/new?template=pattern_request.yml)
- 🔒 **Security vulnerabilities** → [Private Security Advisory](https://github.com/linus10x/finserv-agent-audit/security/advisories/new)

If these patterns save you time in a compliance review or prevent a production incident, a ⭐ on the repo helps others find it.

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=linus10x/finserv-agent-audit&type=Date)](https://star-history.com/#linus10x/finserv-agent-audit&Date)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). This repository exists because the failure modes that produced these patterns are real — and the teams dealing with them rarely have reference implementations to work from.

First time contributing to open source? Start with issues labelled [`good first issue`](https://github.com/linus10x/finserv-agent-audit/issues?q=label%3A%22good+first+issue%22).

---

## Author

**Kunjar Bhaduri** — 25+ year FSI technology executive. Rescued a $750M multi-year wealth-management platform deal at Broadridge. Rebuilt production infrastructure on Azure during a 12-day ransomware attack with no DR available. Builder of APEX, a 6-agent autonomous trading research system targeting 67.7% CAGR in Phase 0 paper trading.

[LinkedIn](https://linkedin.com/in/kunjarbhaduri) · [NTCI Portfolio](https://github.com/linus10x)

---

## Acknowledgements

Patterns in this repository were informed by:
- [EU AI Act](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689) — Regulation (EU) 2024/1689
- [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/) — LLM application security risks
- [Microsoft agent-governance-toolkit](https://github.com/microsoft/agent-governance-toolkit) — enterprise AI governance reference
- [APEX autonomous trading research system](https://github.com/linus10x) — the operational source of these patterns

---

## Related: the Autonomy Ladder™ family

`finserv-agent-audit` is the financial-services half of an MIT-licensed pattern family for governing AI in regulated industries. The commercial-real-estate half is here:

**[`linus10x/cre-agent-audit`](https://github.com/linus10x/cre-agent-audit)** — Nine governance patterns for AI-enabled commercial real estate workflows. Anchored to three CRE-AI regulatory matters: *In re Trans Union Rental Screening Solutions* (FTC/CFPB, Oct 2023, $15M), *Louis v. SafeRent Solutions* (D. Mass., Nov 2024, ~$2.275M class settlement), and *U.S. v. RealPage* (DOJ + 8 state AGs, filed Aug 23, 2024, ongoing Sherman § 1 litigation). Mapped to Fair Housing Act, ECOA, FCRA, Colorado AI Act, and HUD 24 C.F.R. § 100.500 (disparate-impact rule, post-*ICP v. Texas* 576 U.S. 519 (2015)).

| Pattern | finserv-agent-audit | cre-agent-audit |
|---|---|---|
| DEFCON state machine | ✅ | ✅ |
| Sovereign Veto | ✅ | ✅ |
| Hash-chained Audit Ledger | ✅ | ✅ |
| Autonomy Ladder A0→A4 | ✅ | ✅ |
| Regulation Mapping | ✅ MiFID II · SR 11-7 · SEC | ✅ FHA · CO AI Act · EU AI Act |
| Shadow-Mode Rollout | Planned (v1.1) | ✅ |
| Lease-Abstraction Provenance | — | ✅ CRE-specific |
| Fair-Housing Pre-Flight Gate | — | ✅ CRE-specific |
| Tenant PII Data Residency | — | ✅ CRE-specific |

Both repos: MIT, zero runtime dependencies, primary-source regulatory citations, mypy-checked in CI, and an enforced ≥80% coverage gate.

The umbrella discipline — **Regulated-Operations AI Governance** — is documented at [autonomy-ladder.io](https://autonomy-ladder.io). One framework, two named verticals, one author.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for full release history.

## License

MIT — see [LICENSE](LICENSE).

## Citation

If you use these patterns in your systems or research, please cite using [CITATION.cff](CITATION.cff).
