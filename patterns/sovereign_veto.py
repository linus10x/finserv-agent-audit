"""DEPRECATED in v1.1 — import from `finserv_agent_audit.governance.sovereign_veto` instead.

This re-export shim is kept for backward compatibility through the v1.1.x line; removed in v1.2.
"""

import warnings

from finserv_agent_audit.governance.sovereign_veto import (
    SovereignVeto,
    VetoBlockedError,
    VetoReason,
    VetoRecord,
)

warnings.warn(
    "`patterns.sovereign_veto` is deprecated; import from "
    "`finserv_agent_audit.governance.sovereign_veto` instead. "
    "This shim is removed in v1.2.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["SovereignVeto", "VetoBlockedError", "VetoReason", "VetoRecord"]
