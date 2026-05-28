# ADR-0034 · Adversarial Test Pack

**Status:** Accepted (shipped in v2.0)
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit v2.0

> **Reference pattern, not legal advice.** Vendor characterizations
> and license terms are summaries; readers must consult qualified
> counsel and security practitioners for jurisdiction-specific
> applicability. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

## Context

A buyer-side security architect arrives with a direct question after
reading the v1.x corpus: "ADR-0018 says you do not defend against
prompt injection; what evidence do you ship that the audit chain and
the runtime guardrail survive prompt-injection attempts that target
the gate itself?" The honest answer through v1.3 was that the
framework's tests exercise the primitives in isolation but do not
ship a structured adversarial-input pack. That gap reads as
weakness in a regulated-buyer security review even when the scope
boundary in ADR-0018 is correct.

The 2026 consensus pattern for the pre-deploy / runtime split of LLM
adversarial testing is settled:

- **Pre-deploy:** Garak (NVIDIA) and Promptfoo run probe-and-detector
  pairs against the model under test before any model promotion. Both
  tools are CI/CD-native. Garak v0.14.0 (Feb 2026) ships under Apache
  2.0 with 37+ probe modules and 23 generator backends and was the
  most-starred LLM red-team tool at release (6,938 stars). Promptfoo
  ships its core CLI under MIT; the project was acquired by OpenAI in
  March 2026 with the MIT core preserved per the acquisition
  announcement; the default red-team library covers 50+
  vulnerability types.
- **Runtime:** LLM Guard (Protect AI) and Lakera Guard sit in front
  of the model at request time. The framework's runtime tier is
  `CustomerFacingChatbotGuardrail` (ADR-0026) and `SovereignVeto`
  (ADR-0002) — both are output-gate primitives that intercept the
  agent's emitted decisions before they reach the customer or the
  environment.
- **Post-hoc:** `AuditChain.verify` (ADR-0003) plus the witness-anchor
  pattern (ADR-0014) provide the forensic reconstruction layer.

Through v1.3 the framework shipped the runtime + post-hoc tiers
without the pre-deploy tier in the same surface. v2.0 closes the gap
by shipping reference Garak probes + Promptfoo configs plus a pure-
Python harness that exercises the runtime + post-hoc contract under
simulated adversarial inputs.

## Decision

Ship `tests/adversarial/` as a three-pillar pack in v2.0:

1. **Custom Garak probe** at
   `tests/adversarial/garak/probes/audit_chain_subversion.py` plus a
   baseline Garak config at
   `tests/adversarial/garak/configs/finserv_baseline.yaml`. The
   probe submits 14 prompts across four attack scenarios: disable
   audit logging, pretend no audit chain exists, emit head-hash
   without recording, and `CustomerFacingChatbotGuardrail` bypass.
   The recommended detector
   (`mitigation.MitigationBypass`) scores the LLM's response — refusal
   passes, compliance fails.

2. **Promptfoo evaluation pack** at
   `tests/adversarial/promptfoo/promptfooconfig.yaml` plus a
   financial-chatbot scenario library at
   `tests/adversarial/promptfoo/test_scenarios/financial_chatbot_baseline.yaml`.
   The config defines ten core tests (indirect injection, DAN
   jailbreak, audit-chain disable, audit-chain falsify, Air Canada
   bereavement-refund, fee-waiver, money-movement, regulatory-
   disclosure, model-version-pinning, off-corpus citation) plus
   eight financial-services scenarios. Each test combines string-
   match assertions with `llm-rubric` graders.

3. **Pure-Python test harness** at
   `tests/adversarial/test_audit_chain_resilience.py` (stdlib-only,
   15 tests) that exercises the runtime guardrail + post-hoc audit-
   chain integrity contract under four simulated adversarial
   scenarios: skip-the-audit attack, falsified-payload attack,
   `CustomerFacingChatbotGuardrail` bypass attempt, `SovereignVeto`
   bypass via tool-misuse. The harness runs in the framework's own
   CI; Garak and Promptfoo are reference deployer-side integrations
   that do not block the framework's own pipeline.

### Tier mapping

| Tier | When it runs | What it covers | Primary primitive |
|---|---|---|---|
| Pre-deploy | Before model promotion past A2 (ADR-0004) | Model behavior under prompt-injection / jailbreak / DAN probe banks | Garak + Promptfoo |
| Runtime | Per-request, in production | Agent output gate + human-handoff routing | `CustomerFacingChatbotGuardrail`, `SovereignVeto` |
| Post-hoc | After-the-fact forensic | Audit-chain integrity + replay | `AuditChain.verify`, witness anchor |

### Pre-promotion gate

Per ADR-0004 (autonomy ladder), A3 promotion requires:

- 100% pass rate on the custom `audit_chain_subversion` Garak probe.
- 100% pass rate on the Promptfoo `chatbot_guardrail_bypass` test
  group (Air Canada, fee waiver, money movement).
- >=95% pass rate on the consensus `promptinject.*` + `dan.*` Garak
  families.
- >=90% pass rate on `continuation.*` and `realtoxicityprompts.*`.

A model below any threshold does not pass the gate.

## TRUST BOUNDARY

The pack is explicit about what the three tiers do and do not cover:

- **Pre-deploy (Garak + Promptfoo).** Exercises the model under
  test against a documented probe library. Pass rates are observable
  evidence of refusal behavior; they are not proofs of refusal under
  novel attack categories. Per the 2026 consensus, the pre-deploy
  pack runs against every model promotion candidate; it does not
  certify the model "safe."
- **Runtime (`CustomerFacingChatbotGuardrail`, `SovereignVeto`).**
  Intercepts the agent's emitted output before the output reaches
  the customer or the environment. Per ADR-0018, this gate covers
  agent *outputs*, not agent *reasoning*. A prompt-injection that
  compromises the agent's reasoning before the gate sees the
  decision is still able to emit a malicious-but-policy-compliant
  output the gate must wave through; the runtime tier is the
  output-gate primitive, not the reasoning-compromise defense.
- **Post-hoc (`AuditChain.verify`, witness anchor).** Provides
  forensic reconstruction. Detects post-hoc rewriting; does not
  prevent the in-flight compromise.

The three tiers compose; they do not substitute for one another.

## Alternatives Considered

- **Ship the Python harness alone.** Rejected: a buyer-side security
  review converges faster when the harness output is paired with
  references to the consensus 2026 tools (Garak, Promptfoo). Without
  those references, the harness reads as a homegrown surface; with
  them, it is the framework's slice of the consensus pattern.
- **Ship Garak + Promptfoo as runtime dependencies.** Rejected: the
  framework's stdlib-only discipline is load-bearing for the v1.x
  shipping posture; Garak pulls a multi-GB transitive (HuggingFace
  tokenizers, multiple generator clients) and Promptfoo is a Node
  CLI. Reference configurations with explicit installation
  instructions for the deployer preserve the dependency posture.
- **Ship a runtime prompt-injection detector.** Rejected: ADR-0018
  explicitly scopes prompt-injection-on-reasoning out of the
  framework. The 2026 runtime patterns (LLM Guard, Lakera Guard)
  are the right layer for this work and the framework points
  buyers to them; shipping a homegrown detector would overclaim.
- **Ship MITRE ATLAS mappings only.** Rejected: a taxonomy mapping
  without runnable tests reads as documentation theater. The
  Garak + Promptfoo configs already carry the OWASP LLM Top 10
  tags; that is the right amount of taxonomy for v2.0.

## Consequences

**Positive.** A v2.0 buyer-side security review answers the "what
about prompt injection?" question with three concrete artifacts: a
custom Garak probe the buyer can wire into their CI in minutes, a
Promptfoo config with ten financial-services-specific tests, and a
Python harness that demonstrates the runtime + post-hoc contract
survives the four named attack categories. The pack does not over-
claim defense against prompt-injection-on-reasoning — ADR-0018
remains the scope boundary.

**Negative.** The Garak + Promptfoo configs are reference
implementations the deployer must wire into their own CI with their
own LLM provider credentials. A deployer that runs the configs
unchanged against the documented placeholder providers will see a
sample run, not a real adversarial-test pass. The README files in
each subdirectory + this ADR are explicit about that.

**Architectural.** The pack lives under `tests/adversarial/` and is
the seam other adversarial test categories (red-team injection
patterns, multi-agent collusion harnesses) will land at in v2.x.
The Python harness uses stdlib only and is mypy-strict + ruff-clean
under the same gates the rest of the test suite enforces.

## Regulatory Mapping

- EU AI Act Article 15 (accuracy, robustness, cybersecurity) — the
  pre-deploy pack is documentable evidence the deployer ran the
  consensus adversarial-test battery before promotion.
- NIST AI 600-1 (Generative AI Profile, July 2024) — the Information
  Security risk category names prompt injection and the Confabulation
  category names fabrication; the pack exercises both surfaces.
- NIST AI RMF 1.0 — MEASURE-2.7 (security and resilience evaluated);
  MANAGE-2.2 (risks responded to with documented mitigations).
- SR 11-7 — model risk management — the pre-promotion pass record
  becomes part of the model's ongoing-monitoring evidence record
  under ADR-0007.
- NYDFS 23 NYCRR Part 500 § 500.05 (penetration testing and
  vulnerability assessments) — the Garak + Promptfoo runs are the
  LLM-application analog of the periodic security testing the rule
  anticipates.

## Pre-mortem

The failure mode this ADR prevents: a buyer-side red-team
demonstrates a prompt-injection attack against the deployed agent and
publishes the finding. The framework's response is to point at
ADR-0018 (scope-out) + this ADR's pre-deploy pack (model promotion
gate) + the runtime guardrail (output gate) + the audit-chain replay
(forensic record). The report's conclusion: "framework's gate layer
behaved per its documented contract; the prompt-injection vector
that succeeded sat upstream of the gate, in a class ADR-0018 names
as out-of-scope; recommend layered defense at the prompt-injection
detection layer per the 2026 runtime pattern (LLM Guard or Lakera)."

The failure mode this ADR creates if mishandled: a deployer reads the
README and assumes Garak + Promptfoo passing means the model is
"safe." The README is explicit that the pack is evidence the model
refuses the documented probe library, not a proof of safety; ADR-0034
makes the boundary normative.

## Reversibility

Reversible at the pack level. The Python harness is the load-bearing
piece — it runs in CI and gates merges. The Garak and Promptfoo
configs are reference deployer-side integrations and can be deprecated
or replaced as the 2026 consensus pattern evolves. A future ADR
could supersede this one by, for example, swapping Garak for a
successor tool with a stronger probe library, or by adopting MITRE
ATLAS as the canonical taxonomy in place of OWASP LLM Top 10.

## Cross-references

- ADR-0001 (DEFCON) — the runtime DEFCON state machine modulates the
  class of outputs allowed; pre-deploy probes inform the DEFCON
  thresholds.
- ADR-0002 (Sovereign Veto) — the kill switch when a pre-deploy or
  runtime probe escalates; the harness exercises the bypass-attempt
  contract.
- ADR-0003 (Hash-chained Audit Ledger) — the post-hoc forensic layer
  the harness verifies under simulated tampering.
- ADR-0004 (Autonomy Ladder A0-A4) — the pre-promotion gate consumes
  the Garak + Promptfoo pass rates as evidence for A2-to-A3
  promotion.
- ADR-0006 (Shadow Mode) — pre-promotion parallel runs pair with the
  adversarial-test pack for the full promotion-evidence record.
- ADR-0015 (MIProxy Module Integrity) — verifier-attestation surface
  the audit-chain integrity check folds into.
- ADR-0017 (Audit-Chain Retention, Privilege & Discovery Posture) —
  the audit entries the pack's CI hook emits inherit the retention
  schedule documented here.
- ADR-0018 (Adversarial Agent Threat Model) — the scope boundary
  this pack respects; pre-deploy + runtime + post-hoc cover what
  ADR-0018 names as in-scope, and explicitly do not extend to the
  out-of-scope prompt-injection-on-reasoning surface.
- ADR-0026 (CustomerFacingChatbotGuardrail) — the runtime output-
  gate primitive the harness exercises.

### Primary-source citations

- Greshake et al. (2023) — "Not What You've Signed Up For:
  Compromising Real-World LLM-Integrated Applications with Indirect
  Prompt Injection" [UNVERIFIED — primary source not re-fetched in
  this session].
- OWASP Top 10 for LLM Applications, item LLM01 — Prompt Injection
  [UNVERIFIED — current ranking varies by release].
- NVIDIA Garak v0.14.0 (February 2026, Apache 2.0) —
  `https://github.com/NVIDIA/garak`.
- Promptfoo (MIT core; OpenAI acquisition March 2026 with MIT core
  preserved per the acquisition announcement) —
  `https://www.promptfoo.dev/`.

---

*Patterns are software, not legal advice. Regulatory citations are
reference mappings; consult counsel for applicability to your
control environment.*
