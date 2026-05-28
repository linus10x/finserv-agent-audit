"""Governance patterns for autonomous AI agents in regulated financial services.

Public API (v1.3.0 — discrimination frontier + vendor surface):

    from finserv_agent_audit.governance import SovereignVeto, DEFCONMachine
    from finserv_agent_audit.governance import (
        LDASearchHarness,
        LLMDisparateImpactHarness,
        EffectiveChallengeHarness,
        VendorAttestationLedger,
        RetrainingCadenceMonitor,
        DeprecationWatch,
        CustomerFacingChatbotGuardrail,
    )
    from finserv_agent_audit.schemas import AuditEvent, AuditChain, AuditEventType, AutonomyLevel

v1.3 adds seven new governance modules (LDA search beyond mutual-information,
LLM disparate-impact harness, effective-challenge harness, vendor-attestation
ledger, retraining-cadence monitor, deprecation-watch, customer-facing chatbot
guardrail), the foundation-model API vendor-clauses (sixth vendor class), six
new regulatory + incident + disclosure docs, and seven new ADRs (0020-0026).

The v1.1 legacy import shims at `patterns.*`, `schemas.*`, `examples.defcon_state_machine`
were scheduled for removal in v1.2; migrate to the canonical `finserv_agent_audit.*` paths.
"""

__version__ = "1.3.0"
