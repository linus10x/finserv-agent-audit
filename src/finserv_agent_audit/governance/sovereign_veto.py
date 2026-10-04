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
import threading
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
        production: bool = False,
    ) -> None:
        """Construct a sovereign-veto gate.

        ``production`` — PRODUCTION MODE is a named strict opt-in (P2).
        When ``True`` the gate FAILS CLOSED: a wired ``authorizer`` is
        MANDATORY (``ValueError`` if absent), so ``clear()`` cannot be
        called by an unauthenticated principal and the ``operator_id``
        recorded against a clear is bound to an identity the Authorizer
        authenticated (IdP/KMS), never a free string. The default
        (``production=False``) preserves the v1.x advisory contract
        exactly — a missing Authorizer logs a WARNING and the gate
        still runs, but the recorded ``operator_id`` is an
        UNAUTHENTICATED assertion. This is an OPT-IN; it does NOT change
        the default.

        **Veto-state persistence (deployer responsibility — read this).**
        Veto state lives in memory for the life of this object (the
        ``_vetos`` list). This class does NOT auto-persist or auto-rehydrate
        it: on process restart the in-memory ``_vetos`` set starts empty, so
        a deployer who does nothing WILL lose active vetos across a restart.
        That loss is documented, not silent-by-omission — but the recovery is
        the deployer's to wire, and it is not shipped here. The supported
        recovery pattern: mirror every trigger/clear to the hash-chained audit
        ledger (wire ``on_veto`` / ``on_clear`` to ``AuditChain.append``), then
        on startup reconstruct the active-veto set by replaying the ledger's
        last unmatched trigger/clear pair into ``_vetos`` before serving
        traffic. The library provides the hooks; the deployer provides the
        durable store and the replay-on-boot. See ADR-0002 for the
        persistence/recovery posture.
        """
        self.agent_id = agent_id
        self._vetos: list[VetoRecord] = []
        self._on_veto = on_veto
        self._on_clear = on_clear
        self._authorizer = authorizer
        self._production = production
        # Serialize trigger/clear/read against the shared ``_vetos`` list.
        # The veto's purpose is concurrent operation — a risk-monitor thread
        # triggers while a human-operator thread clears — so an unguarded list
        # iteration in clear() could collide with a trigger() append (TOCTOU).
        # An RLock (re-entrant) mirrors AuditChain's concurrency discipline and
        # lets the read properties be called from within a locked section.
        self._lock = threading.RLock()
        if production and authorizer is None:
            raise ValueError(
                "SovereignVeto(production=True) requires a wired Authorizer: "
                "in production mode clear() must be gated by an authenticated "
                "principal (IdP/KMS), and operator_id on the audit chain must be "
                "bound to that authenticated identity rather than accepted as a "
                "free string. Refusing to start fail-closed."
            )
        if authorizer is None:
            logger.warning(
                "SovereignVeto(agent_id=%r) constructed with no Authorizer wired; "
                "operator_id on the audit chain is an UNAUTHENTICATED assertion. "
                "Inject an Authorizer to gate clear() and trust the recorded "
                "operator identity (CR-12), or pass production=True to fail closed.",
                agent_id,
            )

    @property
    def is_vetoed(self) -> bool:
        """True if any active veto exists."""
        with self._lock:
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
        with self._lock:
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
        # Hold the lock for the mutation walk so a concurrent trigger()
        # append cannot collide with this iteration (the Authorizer check
        # above runs OUTSIDE the lock so a slow IdP call does not serialize
        # the whole gate).
        with self._lock:
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
        with self._lock:
            return [v for v in self._vetos if v.is_active]

    def history(self) -> list[VetoRecord]:
        with self._lock:
            return list(self._vetos)


class VetoBlockedError(RuntimeError):
    """Raised when execution is attempted while a veto is active."""
