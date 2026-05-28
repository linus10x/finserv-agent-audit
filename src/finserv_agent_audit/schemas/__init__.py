"""Audit event schemas and hash-chain logging primitives.

v1.0 (shipped):
    AuditEvent, AuditChain, AuditEventType, AutonomyLevel

v1.1:
    AuditEventType extension: VENDOR_SCORE_RECORDED, VENDOR_SCORE_DRIFT_DETECTED,
    WITNESS_ANCHOR, MODEL_VALIDATED, ADVERSE_ACTION_TAKEN, SAR_FILED,
    BEST_INTEREST_CHECKED. AuditChain extracted to
    finserv_agent_audit.governance.audit_chain (re-exported here via __getattr__
    to preserve the v1.0 import path).
"""

from typing import Any

from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)


def __getattr__(name: str) -> Any:
    if name == "AuditChain":
        from finserv_agent_audit.governance.audit_chain import AuditChain

        return AuditChain
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["AuditChain", "AuditEvent", "AuditEventType", "AutonomyLevel"]  # noqa: F822  # AuditChain resolved via __getattr__
