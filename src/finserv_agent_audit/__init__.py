"""Governance patterns for autonomous AI agents in regulated financial services.

Public API (v2.0.0 — agentic-AI ecosystem + platform surfaces):

    from finserv_agent_audit.governance import SovereignVeto, DEFCONMachine
    from finserv_agent_audit.governance import (
        LDASearchHarness,
        LLMDisparateImpactHarness,
        EffectiveChallengeHarness,
        VendorAttestationLedger,
        RetrainingCadenceMonitor,
        DeprecationWatch,
        CustomerFacingChatbotGuardrail,
        AIBOMGenerator,
    )
    from finserv_agent_audit.integrations import (
        A2AAuditAdapter,
        LangGraphAuditCallback,
        MAFAuditAdapter,
        CrewAIAuditAdapter,
        OTELGenAIEmitter,
    )
    from finserv_agent_audit.schemas import AuditEvent, AuditChain, AuditEventType, AutonomyLevel

v2.0 adds four agentic-AI runtime adapters (Google A2A · LangGraph ·
Microsoft Agent Framework · CrewAI), the `AIBOMGenerator` (CycloneDX 1.7
ML-BOM + SPDX 3.0 AI Profile dual emit), a FastAPI governance endpoint
with OpenAPI 3.1 + Server-Sent Events live streams, a Kubernetes
operator stub with three custom resource definitions (AuditChain,
SovereignVeto, ChainSink) and Kyverno + OPA sample admission policies,
an adversarial test pack (Garak probes + Promptfoo scenarios + Python
harness) per the ADR-0018 threat model, eight new ADRs (0027-0034), and
five new strategic docs (NAIC insurance, DORA, EU AI Act August 2026
compliance pack, PE portfolio playbook, PCAOB AS 2201 amendments
appendix) plus a PE portfolio dashboard reference.

v2.0 is additive — no breaking API changes. The major version bump
signals ecosystem maturity (four runtime adapters + Kubernetes operator
+ REST endpoint + AIBOM dual emit), not a wire-format break. The
v1.1 deprecation re-export shims at `patterns/`, `schemas/`, and
`examples/defcon_state_machine.py` remain in place; their removal is
scheduled for v2.1. Migrate to the canonical `finserv_agent_audit.*`
paths to insulate from that follow-up bump.
"""

__version__ = "2.0.0"
