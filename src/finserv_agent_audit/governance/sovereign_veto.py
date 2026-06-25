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
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


def _scrub(v: object) -> str:
    """Neutralize CR/LF in untrusted values before they enter a log message.

    Agent-controlled fields (agent_id, operator_id, reasons, descriptions)
    interpolated into a log line could otherwise inject forged log records
    via embedded carriage-return / line-feed characters.
    """
    return str(v).replace("\n", " ").replace("\r", " ")


@runtime_checkable
class Authorizer(Protocol):
    """Protocol for authorizing privileged operations.

    Wired into :class:`SovereignVeto.clear` and
    :class:`DEFCONMachine.manual_override` (CR-12). The audit chain
    records the asserted ``operator_id``, but it can only be TRUSTED
    if the Authorizer.authorize() check passed. Without an Authorizer,
    operator identity on the chain is an unauthenticated assertion the
    deployer must reconcile out-of-band.
    """

    def authorize(
        self,
        operator_id: str,
        action: str,
        context: dict[str, Any],
    ) -> bool: ...


class _RejectAllAuthorizer:
    """Default Authorizer: rejects every authorization request.

    Used internally as the fail-closed sentinel when the deployer wires
    an Authorizer on the constructor. Operators MUST inject a real
    Authorizer for privileged-operation gating to work; the no-Authorizer
    construction path logs a WARNING in lieu of installing this rejector.
    """

    def authorize(
        self,
        operator_id: str,
        action: str,
        context: dict[str, Any],
    ) -> bool:
        return False


class VetoReason(Enum):
    RISK_LIMIT_BREACH = "risk_limit_breach"
    POLICY_VIOLATION = "policy_violation"
    ANOMALY_DETECTED = "anomaly_detected"
    MANUAL_OPERATOR = "manual_operator"
    PEER_AGENT_CHALLENGE = "peer_agent_challenge"
    COMPLIANCE_FLAG = "compliance_flag"


@dataclass
class VetoRecord:
    veto_id: str
    reason: VetoReason
    triggered_by: str  # agent_id or operator_id
    description: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
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
        authorizer: Authorizer | None = None,
    ) -> None:
        self.agent_id = agent_id
        self._vetos: list[VetoRecord] = []
        self._on_veto = on_veto
        self._on_clear = on_clear
        self._authorizer = authorizer
        if authorizer is None:
            logger.warning(
                "SovereignVeto(agent_id=%r) constructed with no Authorizer wired; "
                "operator_id on the audit chain is an UNAUTHENTICATED assertion. "
                "Inject an Authorizer to gate clear() and trust the recorded "
                "operator identity (CR-12).",
                agent_id,
            )

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
        record = VetoRecord(
            veto_id=str(uuid.uuid4()),
            reason=reason,
            triggered_by=triggered_by,
            description=description,
        )
        self._vetos.append(record)

        logger.critical(
            "SOVEREIGN VETO triggered | agent: %s | reason: %s | by: %s | %s",
            _scrub(self.agent_id),
            reason.value,
            _scrub(triggered_by),
            _scrub(description),
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

        CR-12: self-clearing is HARD-blocked. ``operator_id == agent_id``
        raises :class:`VetoBlockedError` even when the wired Authorizer
        would allow the action — no agent can clear its own veto.

        When an :class:`Authorizer` is wired on the constructor, the
        ``authorize()`` check must return True before the clear proceeds.

        Args:
            operator_id: Identity of the human clearing the veto.
            reason: Documented justification (required for audit).
            veto_id: Specific veto to clear, or None to clear all.

        Returns:
            List of cleared VetoRecords.

        Raises:
            VetoBlockedError: if the self-clearing rule fires, or if the
                wired Authorizer rejects the operation.
        """
        # CR-12 — self-clearing rule (always enforced, even with a
        # permissive Authorizer).
        if operator_id == self.agent_id:
            logger.critical(
                "REJECTED self-clearing attempt | agent: %s | operator: %s",
                _scrub(self.agent_id),
                _scrub(operator_id),
            )
            raise VetoBlockedError(
                f"self-clearing forbidden: operator_id={operator_id!r} "
                f"equals agent_id; no agent can clear its own veto"
            )
        # CR-12 — Authorizer gate.
        if self._authorizer is not None:
            context: dict[str, Any] = {
                "agent_id": self.agent_id,
                "veto_id": veto_id,
                "reason": reason,
            }
            if not self._authorizer.authorize(operator_id, "clear_veto", context):
                logger.critical(
                    "REJECTED clear by Authorizer | agent: %s | operator: %s",
                    _scrub(self.agent_id),
                    _scrub(operator_id),
                )
                raise VetoBlockedError(
                    f"Authorizer rejected clear_veto by operator_id={operator_id!r}"
                )
        now = datetime.now(UTC).isoformat()
        cleared = []
        for v in self._vetos:
            if v.is_active and (veto_id is None or v.veto_id == veto_id):
                v.cleared_by = operator_id
                v.cleared_at = now
                v.clear_reason = reason
                cleared.append(v)
                logger.info(
                    "VETO CLEARED | agent: %s | veto_id: %s | by: %s | reason: %s",
                    _scrub(self.agent_id),
                    _scrub(v.veto_id),
                    _scrub(operator_id),
                    _scrub(reason),
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
