"""Governance patterns for autonomous AI agents in regulated financial services.

Public API (v1.2.0 — OCC 2026-13 response + ecosystem onramps):

    from finserv_agent_audit.governance import SovereignVeto, DEFCONMachine
    from finserv_agent_audit.schemas import AuditEvent, AuditChain, AuditEventType, AutonomyLevel

The v1.1 legacy import shims at `patterns.*`, `schemas.*`, `examples.defcon_state_machine` are
scheduled for removal in v1.2; migrate to the canonical `finserv_agent_audit.*` paths.
"""

__version__ = "1.2.0"
