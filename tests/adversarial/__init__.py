"""Adversarial test pack (v2.0 — ADR-0034).

Three-tier defense pattern:

1. Pre-deploy: Garak + Promptfoo configurations (see ``garak/`` and
   ``promptfoo/`` subdirectories) that exercise the agent against the
   2026 consensus prompt-injection / jailbreak / DAN probe banks before
   deployment.
2. Runtime: ``CustomerFacingChatbotGuardrail`` (v1.3 — ADR-0026) and
   ``SovereignVeto`` (v1.0 — ADR-0002) intercept the agent's outputs at
   the trust boundary.
3. Post-hoc: ``AuditChain.verify`` (v1.0 — ADR-0003) provides forensic
   reconstruction of what the agent emitted under attack.

The pure-Python harness in ``test_audit_chain_resilience.py`` exercises
tier 2 + tier 3 under simulated adversarial inputs — no Garak or
Promptfoo runtime dependency required for CI. The Garak probe and
Promptfoo config files are reference implementations the deployer wires
into their own CI pipeline with their own LLM provider credentials.

ADR-0018 names the boundary: this framework audits and gates agent
*outputs*, not agent *reasoning*. Prompt-injection that compromises
agent reasoning before the audit chain sees the decision is
out-of-scope; this pack ships the evidence that the audit and gate
layers survive attempts to subvert them, not the prompt-injection
defense itself.
"""
