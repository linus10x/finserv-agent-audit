"""
Sovereign Veto Pattern — Human-in-the-Loop Kill Switch
=======================================================

Implements a configurable veto layer that sits between agent decisions and
execution. At A2 autonomy level and below, every decision passes through the
veto gate. The veto can be triggered by:

    - Human operator (manual override)
    - Risk state machine (automatic at ALERT or above)
    - Policy engine (rule-based violation detection)
    - Peer agent (adversarial challenge from a monitoring agent)

Design principle: the veto is a HARD STOP. Once triggered, execution is
suspended until the veto is explicitly cleared by an authorized human operator
with a documented reason. No agent can clear its own veto.

Compliance notes:
    - EU AI Act Article 14: Human oversight measures
    - MiFID II Article 17: Algorithmic trading — kill-switch requirement
    - SR 11-7: Model governance — human review of automated decisions
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable

logger = logging.getLogger(__name__)


class VetoReason(Enum):
    RISK_LIMIT_BREACH    = "risk_limit_breach"
    POLICY_VIOLATION     = "policy_violation"
    ANOMALY_DETECTED     = "anomaly_detected"
    MANUAL_OPERATOR      = "manual_operator"
    PEER_AGENT_CHALLENGE = "peer_agent_challenge"
    COMPLIANCE_FLAG      = "compliance_flag"


@dataclass
class VetoRecord:
    veto_id: str
    reason: VetoReason
    triggered_by: str       # agent_id or operator_id
    description: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    cleared_by: str | None = None
    cleared_at: str | None = None
    clear_reason: str | None = None

    @property
    def is_active(self) -> bool:
        return self.cleared_by is None


class SovereignVeto:
    """
    Veto gate for autonomous agent decisions.

    Usage::

        veto = SovereignVeto(agent_id="zeus")

        # In risk monitor:
        if risk_level >= DEFCON.ALERT:
            veto.trigger(VetoReason.RISK_LIMIT_BREACH, "risk_monitor", "ALERT threshold reached")

        # In execution path:
        if not veto.allow_execution():
            raise VetoBlockedError("Execution blocked by sovereign veto")

        # Human clears (after investigation):
        veto.clear("operator_001", "Risk reviewed and accepted; drawdown within policy limits")
    """

    def __init__(
        self,
        agent_id: str,
        on_veto: Callable[[VetoRecord], None] | None = None,
        on_clear: Callable[[VetoRecord], None] | None = None,
    ) -> None:
        self.agent_id = agent_id
        self._vetos: list[VetoRecord] = []
        self._on_veto = on_veto
        self._on_clear = on_clear

    @property
    def is_vetoed(self) -> bool:
        """True if any active veto exists."""
        return any(v.is_active for v in self._vetos)

    def allow_execution(self) -> bool:
        """Gate check — call this before every agent action."""
        return not self.is_vetoed

    def trigger(
        self,
        reason: VetoReason,
        triggered_by: str,
        description: str,
    ) -> VetoRecord:
        """Trigger a veto. Idempotent for the same reason from the same source."""
        import uuid
        record = VetoRecord(
            veto_id=str(uuid.uuid4()),
            reason=reason,
            triggered_by=triggered_by,
            description=description,
        )
        self._vetos.append(record)

        logger.critical(
            "SOVEREIGN VETO triggered | agent: %s | reason: %s | by: %s | %s",
            self.agent_id, reason.value, triggered_by, description,
        )

        if self._on_veto:
            self._on_veto(record)

        return record

    def clear(
        self,
        operator_id: str,
        reason: str,
        veto_id: str | None = None,
    ) -> list[VetoRecord]:
        """
        Clear active veto(s). Only humans can clear vetos.
        If veto_id is None, clears all active vetos.

        Args:
            operator_id: Identity of the human clearing the veto.
            reason: Documented justification (required for audit).
            veto_id: Specific veto to clear, or None to clear all.

        Returns:
            List of cleared VetoRecords.
        """
        now = datetime.now(timezone.utc).isoformat()
        cleared = []
        for v in self._vetos:
            if v.is_active and (veto_id is None or v.veto_id == veto_id):
                v.cleared_by = operator_id
                v.cleared_at = now
                v.clear_reason = reason
                cleared.append(v)
                logger.info(
                    "VETO CLEARED | agent: %s | veto_id: %s | by: %s | reason: %s",
                    self.agent_id, v.veto_id, operator_id, reason,
                )
                if self._on_clear:
                    self._on_clear(v)
        return cleared

    def active_vetos(self) -> list[VetoRecord]:
        return [v for v in self._vetos if v.is_active]

    def history(self) -> list[VetoRecord]:
        return list(self._vetos)


class VetoBlockedError(RuntimeError):
    """Raised when execution is attempted while a veto is active."""
