"""Governance patterns for autonomous AI agents in regulated financial services.

Public API (v1.1.0.dev0 — Tranche 1 in progress; Tranches 2-3 add Protocol seams + FSI overlay):

    from finserv_agent_audit.governance import SovereignVeto, DEFCONMachine
    from finserv_agent_audit.schemas import AuditEvent, AuditChain, AuditEventType, AutonomyLevel

The legacy import paths `patterns.*`, `schemas.*`, `examples.defcon_state_machine` continue to
work in v1.1 via deprecation re-export shims; they are removed in v1.2.
"""

__version__ = "1.1.0.dev0"
