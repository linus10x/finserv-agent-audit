# ADR-0018 · Adversarial Agent Threat Model

**Status:** Accepted · v1.1 · scope-defining ADR
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit v1.1

> **Reference pattern, not legal advice.** Threat-model characterizations are summaries; readers must consult qualified security counsel and red-team practitioners. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

## Context

A buyer-side security architect asks the direct question: "What does this framework actually defend against, and what is it explicitly out of scope for?" Without a written threat model, every conversation drifts into either overclaiming (which sinks the framework on the first red-team finding) or underclaiming (which sinks adoption). The 8-chamber adversarial audit on 2026-05-28 surfaced this as an explicit gap.

The framework's contract is narrow and load-bearing: **audit and gate the agent's *outputs*, not the agent's *reasoning*.** Every primitive sits at the seam between the agent's emitted action and the environment that action would touch. The Sovereign Veto (ADR-0002) intercepts outputs before they reach the world. The Audit Ledger (ADR-0003) records outputs after the fact. DEFCON (ADR-0001) modulates the class of outputs permitted. Shadow Mode (ADR-0006) compares one agent's outputs to another's. The MIProxy verifier-attestation path (`mi_proxy.py`) attests the integrity of the verifier code that inspects outputs.

None of these primitives inspect the agent's chain-of-thought. None defeat an attacker who has compromised the agent's reasoning before the audit chain sees the decision. Honesty about that boundary is the foundation of the framework's trust posture — the limit is **scope discipline, not weakness**.

## Decision

Adopt this ADR as the authoritative threat model for v1.1. The scope-in and scope-out claims below are normative.

### Defends against (in-scope)

1. **Operator error.** Misconfigured DEFCON thresholds, missed Sovereign Veto integrations, retention-schedule typos. Detected by audit-chain invariants and Shadow Mode promotion gates.
2. **Model drift.** Production model behavior diverging from the validated baseline. Detected by Shadow Mode (ADR-0006) divergence statistics and model-inventory ongoing-monitoring entries (ADR-0011).
3. **Fallible-but-honest agent decisions.** An agent making a wrong but non-adversarial call within its tool surface. Caught at the Sovereign Veto gate for non-routine decision classes, or surfaced in audit-chain replay for post-hoc correction.
4. **Vendor model substitution.** A vendor silently swaps the model behind an API. Detected by the Vendor Score Gate (ADR-0010) when the substitution moves observable behavior outside the contracted envelope.
5. **Verifier-code compromise.** An attacker tampering with the verifier code that inspects agent outputs. The MIProxy verifier-attestation path produces a cryptographic attestation of the verifier image; tampered verifiers fail attestation before they can pass adversarial outputs as benign.
6. **Audit-chain tampering after the fact.** The hash-chained ledger (ADR-0003) plus the witness-anchor design (`witness_anchor.py`) and RFC 3161 timestamp codec (`rfc3161_codec.py`) make post-hoc rewriting detectable.
7. **Insider single-actor bypass.** The Sovereign Veto split-knowledge / dual-control pattern (ADR-0002) requires the bypass actor's identity, justification, and counter-signing chain-of-custody to be recorded; a single insider's silent override is forensically visible.

### Does NOT defend against (out-of-scope)

1. **Sovereign-agent intentional veto bypass via tool-misuse.** If the agent's human sovereign deliberately misuses the override, the framework records the bypass — it does not prevent it. The contract is forensic visibility, not authorization withdrawal.
2. **Prompt-injection attacks on the agent's reasoning.** An attacker who poisons the agent's context window (indirect prompt injection via retrieved documents, tool outputs, or user-supplied fields) can steer the agent toward a malicious decision that *appears* to be a normal output. The Sovereign Veto can still catch outputs that violate the gate's policy, but the underlying compromise of agent reasoning is invisible to this framework. See Greshake et al., "Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection" (2023) [UNVERIFIED — primary source not fetched] and the OWASP Top 10 for LLM Applications, item LLM01 Prompt Injection [UNVERIFIED — current ranking varies by release]. Defenses live in the prompt-injection / interpretability research community; this framework cross-references them and does not claim to ship them.
3. **Supply-chain attacks on the audit chain's hash function.** A theoretical post-SHA-256 collision attack would let an adversary substitute audit-chain content while preserving the chain's verification property. Mitigation is algorithm-agility (the chain's codec separates hash choice from chain structure) plus witness-anchor timestamping (which bounds the substitution window). Not an absolute defense.
4. **Compromise of the underlying compute platform.** A rooted host can lie to userspace about every primitive here. Hardware-attested compute (TEEs, confidential VMs) is the answer; the MIProxy attestation path is the integration point, not the platform.
5. **Adversarial model training.** A model trained from the ground up to evade specific audit signals while preserving plausible outputs is out of scope. Defenses live in model-evaluation methodology (red-team training-data audits, capability evaluations) before deployment.
6. **Coordinated multi-party fraud.** If the human sovereign, MRM reviewer, and audit-chain operator collude, the framework records the collusion's outputs but cannot prevent it. Mitigation is segregation-of-duties governance outside the framework.
7. **Regulatory-change risk.** A new rule that retroactively recharacterizes prior decisions is a counsel matter. The audit chain's evidentiary value supports the operator's defense; it does not predict the rule change.

## Alternatives Considered

- **Ship a "comprehensive" threat model claiming defenses against prompt injection.** Rejected: a defense that does not actually defend against the named class is worse than not shipping it. The cost of overclaiming is paid on the first credible red-team finding.
- **Stay silent on scope and let buyers infer.** Rejected: buyers in regulated industries infer worst-case. Silence reads as ignorance or hiding. Either kills adoption.
- **Cite academic literature without naming gaps in plain English.** Rejected: a buyer-side security architect needs the gaps named, not buried in a bibliography.

## Consequences

**Positive.** Buyer-side security review converges faster — the scope boundary is the conversation, not a discovery. The framework's reputation rests on a contract it can keep. Third-party defenses (prompt-injection filters, interpretability tools, hardware attestation) plug in cleanly because the integration surfaces are named.

**Negative.** The honest scope-out list reads as smaller than buyers initially hope. The value proposition is "audit and gate outputs with forensic discipline," not "make agents safe end-to-end." Honest framing requires sales discipline.

**Architectural.** Every future ADR is evaluated against this threat model. A proposed primitive claiming defense against an out-of-scope class either expands this ADR's scope-in with evidence or is rejected as overclaim.

## Regulatory Mapping

- EU AI Act Art. 15 (accuracy, robustness, cybersecurity) — this ADR documents the cybersecurity scope; Shadow Mode + DEFCON cover the accuracy and robustness obligations
- SR 11-7 — model risk management — scope-out items are documented limitations subject to the operator's compensating-controls analysis
- NIST AI RMF 1.0 — GOVERN-1.3 (risks and benefits documented); MANAGE-2.3 (third-party risks documented)
- NYDFS 23 NYCRR Part 500 § 500.09 (risk assessment) anticipates documented threat models

## Pre-mortem

A buyer's pen-test vendor demonstrates an indirect prompt-injection attack against the deployed agent. The agent emits a malicious output. The Sovereign Veto catches it because the output violates the gate's policy. The audit chain records the attack as a vetoed event. The pen-test report concludes "framework worked as documented; underlying prompt-injection vulnerability sits at the agent layer, outside the framework's threat model — recommend layered defense at the prompt-injection layer."

The failure mode this ADR prevents: the same pen-test report concludes "framework claimed to defend against prompt injection (page 4 of the README); demonstrably did not." Reputation survives the first scenario and does not survive the second.

## Reversibility

Reversible at the ADR level. If a future primitive credibly defends against a currently-out-of-scope class with red-team evidence, the ADR is superseded by a versioned revision. Out-of-scope today does not mean out-of-scope forever; it means "not shipping that defense in v1.1, and not claiming it."

## Cross-references

- ADR-0001 (DEFCON) — posture modulation is the in-scope defense against detected drift
- ADR-0002 (Sovereign Veto) — output-gate primitive whose contract is forensic visibility on bypass
- ADR-0003 (Hash-chained Audit Ledger) — post-hoc tamper detection
- ADR-0006 (Shadow Mode) — model-drift detection
- ADR-0007 (SR 11-7 overlay) — governance scaffolding around the threat-model gaps
- ADR-0010 (Vendor Score Gate) — vendor-substitution detection
- ADR-0011 (Model Inventory) — ongoing-monitoring entries support drift detection
- ADR-0017 (Audit-Chain Retention, Privilege & Discovery Posture) — privilege posture is independent of threat model
- ADR-0019 (Protected-Class Proxy Detector — deferred) — a planned primitive whose scope-in claim awaits this ADR's evidence bar
