"""DEPRECATED in v1.1 — import from `finserv_agent_audit.schemas.audit_event` instead.

This re-export shim is kept for backward compatibility through the v1.1.x line; removed in v1.2.
"""

import warnings

from finserv_agent_audit.schemas.audit_event import (
    AuditChain,
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)

warnings.warn(
    "`schemas.audit_event` is deprecated; import from "
    "`finserv_agent_audit.schemas.audit_event` instead. "
    "This shim is removed in v1.2.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["AuditChain", "AuditEvent", "AuditEventType", "AutonomyLevel"]
