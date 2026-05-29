"""
DEFCON State Machine — Reference Implementation
================================================

A risk-state degradation machine for autonomous AI agents operating in
regulated financial environments. Implements five risk levels (NORMAL through
HALT) with hysteresis-controlled transitions — the system requires multiple
consecutive evaluations at a lower risk level before de-escalating, preventing
flapping under volatile conditions.

This module is a REFERENCE IMPLEMENTATION derived from patterns used in
a multi-year autonomous trading system build. The source system operates
in paper-trading Phase 0 — no live capital has been deployed.

IMPORTANT — ILLUSTRATIVE THRESHOLD VALUES:
    All numeric thresholds below are EXAMPLES ONLY — not drawn from any
    production system. Calibrate every threshold to your system's specific
    risk tolerance, capital base, strategy characteristics, and regulatory
    requirements before deploying. Calibration guidance: docs/DEFCON_ARCHITECTURE.md

Key design decisions:
    - Hysteresis prevents rapid oscillation between adjacent levels
    - De-escalation always requires more confirmations than escalation
    - HALT level requires manual override — no automatic de-escalation
    - State is persisted to disk; system reloads last confirmed level on restart
      (intentionally conservative: last confirmed level, not live evaluation)
    - All transitions are logged to an append-only audit trail

Usage::

    from examples.defcon_state_machine import DEFCONMachine, RiskMetrics

    machine = DEFCONMachine()
    metrics = RiskMetrics(
        portfolio_drawdown=0.06,
        daily_loss=0.02,
        consecutive_losses=2,
    )
    level = machine.evaluate(metrics)
    print(level)  # DEFCON.CAUTION
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from finserv_agent_audit.governance.sovereign_veto import Authorizer
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)

logger = logging.getLogger(__name__)


class DEFCONOverrideRejectedError(RuntimeError):
    """Raised when a DEFCONMachine.manual_override is rejected by the wired Authorizer (CR-12)."""


# ---------------------------------------------------------------------------
# Risk Levels
# ---------------------------------------------------------------------------


class DEFCON(Enum):
    """Risk levels from lowest (NORMAL) to highest (HALT)."""

    NORMAL = 1
    CAUTION = 2
    ALERT = 3
    DANGER = 4
    HALT = 5

    def __ge__(self, other: DEFCON) -> bool:
        return self.value >= other.value

    def __gt__(self, other: DEFCON) -> bool:
        return self.value > other.value

    def __le__(self, other: DEFCON) -> bool:
        return self.value <= other.value

    def __lt__(self, other: DEFCON) -> bool:
        return self.value < other.value


# ---------------------------------------------------------------------------
# Thresholds
#
# IMPORTANT: Values below are ILLUSTRATIVE EXAMPLES — not drawn from any
# production system. Calibrate every threshold to your system's specific
# risk tolerance, capital base, strategy characteristics, and regulatory
# requirements before deploying.
# ---------------------------------------------------------------------------

DRAWDOWN_HALT = 0.20  # Example: >=20% portfolio drawdown -> HALT
DRAWDOWN_DANGER = 0.15  # Example: >=15% portfolio drawdown -> DANGER
DRAWDOWN_ALERT = 0.10  # Example: >=10% portfolio drawdown -> ALERT
DRAWDOWN_CAUTION = 0.07  # Example: >=7%  portfolio drawdown -> CAUTION

DAILY_LOSS_HALT = 0.06  # Example: >=6% daily loss -> HALT
DAILY_LOSS_DANGER = 0.04  # Example: >=4% daily loss -> DANGER

CONSECUTIVE_LOSS_ALERT = 6  # Example: >=6 consecutive losses -> ALERT
CONSECUTIVE_LOSS_CAUTION = 4  # Example: >=4 consecutive losses -> CAUTION

HYSTERESIS_CONFIRMATIONS = 3  # Consecutive evaluations required to de-escalate


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class RiskMetrics:
    """Snapshot of risk indicators evaluated at each cycle."""

    portfolio_drawdown: float  # 0.0 to 1.0 (e.g., 0.12 = 12% drawdown)
    daily_loss: float  # 0.0 to 1.0 (e.g., 0.03 = 3% daily loss)
    consecutive_losses: int  # Count of consecutive losing trades/cycles
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


# CR-5 — the previous file shipped a *local* ``AuditEvent`` dataclass
# whose ``_compute_hash`` payload OMITTED ``metrics_snapshot``,
# leaving the metrics field freely rewritable on-disk without
# breaking ``verify``. We now consume the canonical
# ``finserv_agent_audit.schemas.audit_event.AuditEvent``, which folds
# the entire ``payload`` (including the metrics snapshot embedded in
# it) into the hash. Any post-hoc rewrite of metrics_snapshot is
# detected on ``from_jsonl`` replay — same contract the rest of the
# chain enforces.


# ---------------------------------------------------------------------------
# State Machine
# ---------------------------------------------------------------------------


class DEFCONMachine:
    """
    DEFCON risk-state machine with hysteresis and a tamper-detecting hash-chain
    audit trail (within-trust-boundary; ADR-0014 covers external witness anchoring).

    Escalation is immediate (single evaluation triggers upgrade).
    De-escalation requires HYSTERESIS_CONFIRMATIONS consecutive evaluations
    at a lower level before confirming the transition.
    HALT level requires manual_override() call — no automatic de-escalation.
    """

    def __init__(
        self,
        state_file: Path | None = None,
        audit_file: Path | None = None,
        authorizer: Authorizer | None = None,
    ) -> None:
        self._current_level: DEFCON = DEFCON.NORMAL
        self._pending_target: DEFCON | None = None
        self._confirmation_count: int = 0
        self._transition_count: int = 0
        self._prev_hash: str = "0" * 64  # Genesis hash

        self.state_file = state_file or Path("output/defcon_state.json")
        self.audit_file = audit_file or Path("output/defcon_audit.jsonl")

        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.audit_file.parent.mkdir(parents=True, exist_ok=True)

        self._authorizer = authorizer
        if authorizer is None:
            logger.warning(
                "DEFCONMachine constructed with no Authorizer wired; "
                "operator_id passed to manual_override is an UNAUTHENTICATED "
                "assertion. Inject an Authorizer to gate manual_override and "
                "trust the recorded operator identity (CR-12)."
            )

        self._load_state()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def level(self) -> DEFCON:
        """Current confirmed DEFCON level."""
        return self._current_level

    def evaluate(self, metrics: RiskMetrics) -> DEFCON:
        """
        Evaluate current risk metrics and update DEFCON level.

        Escalation is immediate. De-escalation requires
        HYSTERESIS_CONFIRMATIONS consecutive evaluations at a lower level.

        Args:
            metrics: Current risk snapshot.

        Returns:
            The current confirmed DEFCON level after this evaluation.
        """
        if self._current_level == DEFCON.HALT:
            logger.warning("System is HALTED. Call manual_override() to proceed.")
            return DEFCON.HALT

        target = self._compute_target(metrics)

        if target > self._current_level:
            # Immediate escalation
            self._confirm_transition(target, metrics, trigger="escalation")
        elif target < self._current_level:
            # Hysteresis: require N consecutive evaluations before de-escalating
            if self._pending_target != target:
                self._pending_target = target
                self._confirmation_count = 1
            else:
                self._confirmation_count += 1

            if self._confirmation_count >= HYSTERESIS_CONFIRMATIONS:
                self._confirm_transition(target, metrics, trigger="de-escalation")
        else:
            # No change — reset pending
            self._pending_target = None
            self._confirmation_count = 0

        return self._current_level

    def manual_override(
        self,
        target: DEFCON,
        operator_id: str,
        reason: str,
        metrics: RiskMetrics | None = None,
    ) -> DEFCON:
        """
        Human-in-the-loop override. Required for HALT de-escalation.
        All manual overrides are logged with operator identity.

        CR-12: when an :class:`Authorizer` is wired on the constructor,
        the ``authorize()`` check must return True before the override
        proceeds. ``DEFCONOverrideRejectedError`` fires on a deny.

        Args:
            target: Target DEFCON level.
            operator_id: Identity of the human authorizing the override.
            reason: Free-text justification (required for audit).
            metrics: Optional current risk snapshot.

        Returns:
            The new DEFCON level.

        Raises:
            DEFCONOverrideRejectedError: if the wired Authorizer rejects.
        """
        if self._authorizer is not None:
            context: dict[str, Any] = {
                "from_level": self._current_level.name,
                "target_level": target.name,
                "reason": reason,
            }
            if not self._authorizer.authorize(operator_id, "defcon_manual_override", context):
                logger.critical(
                    "REJECTED manual_override by Authorizer | operator: %s | target: %s",
                    operator_id,
                    target.name,
                )
                raise DEFCONOverrideRejectedError(
                    f"Authorizer rejected defcon_manual_override by "
                    f"operator_id={operator_id!r} to {target.name}"
                )
        trigger = f"MANUAL_OVERRIDE by {operator_id}: {reason}"
        snap_metrics = metrics or RiskMetrics(
            portfolio_drawdown=0.0, daily_loss=0.0, consecutive_losses=0
        )
        self._confirm_transition(target, snap_metrics, trigger=trigger)
        return self._current_level

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _compute_target(self, m: RiskMetrics) -> DEFCON:
        """Compute the target DEFCON level from current metrics."""
        if m.portfolio_drawdown >= DRAWDOWN_HALT or m.daily_loss >= DAILY_LOSS_HALT:
            return DEFCON.HALT
        if m.portfolio_drawdown >= DRAWDOWN_DANGER or m.daily_loss >= DAILY_LOSS_DANGER:
            return DEFCON.DANGER
        if m.portfolio_drawdown >= DRAWDOWN_ALERT or m.consecutive_losses >= CONSECUTIVE_LOSS_ALERT:
            return DEFCON.ALERT
        if (
            m.portfolio_drawdown >= DRAWDOWN_CAUTION
            or m.consecutive_losses >= CONSECUTIVE_LOSS_CAUTION
        ):
            return DEFCON.CAUTION
        return DEFCON.NORMAL

    def _confirm_transition(self, target: DEFCON, metrics: RiskMetrics, trigger: str) -> None:
        """Confirm a state transition, write audit record, persist state.

        CR-5 — the transition event is constructed via the canonical
        ``AuditEvent.create`` so the ``metrics_snapshot`` (carried in
        ``payload``) is folded into ``_compute_hash``. Pre-fix, a local
        AuditEvent omitted ``metrics_snapshot`` from the hash payload
        and an attacker could rewrite the metric without breaking
        ``verify``.
        """
        from_level = self._current_level
        self._current_level = target
        self._pending_target = None
        self._confirmation_count = 0
        self._transition_count += 1

        # Classify the transition as risk escalation, de-escalation,
        # or HALT trigger so the canonical event_type stream stays
        # honest. HALT is its own AuditEventType regardless of
        # direction so HALT-triggering transitions are filter-able
        # from the audit stream.
        if target == DEFCON.HALT:
            event_type = AuditEventType.HALT_TRIGGERED
        elif target.value > from_level.value:
            event_type = AuditEventType.RISK_ESCALATION
        else:
            event_type = AuditEventType.RISK_DEESCALATION

        # The ``metrics_snapshot`` MUST live inside the canonical
        # ``payload`` so it is covered by ``_compute_hash``.
        payload: dict[str, Any] = {
            "from_level": from_level.name,
            "to_level": target.name,
            "trigger": trigger,
            "metrics_snapshot": {
                "portfolio_drawdown": metrics.portfolio_drawdown,
                "daily_loss": metrics.daily_loss,
                "consecutive_losses": metrics.consecutive_losses,
            },
        }

        event = AuditEvent.create(
            event_type=event_type,
            autonomy_level=AutonomyLevel.A2,
            agent_id="defcon-state-machine",
            payload=payload,
            prev_hash=self._prev_hash,
            event_id=f"defcon-{self._transition_count:06d}",
            timestamp=metrics.timestamp.isoformat(),
        )
        self._prev_hash = event.event_hash

        self._append_audit(event)
        self._save_state()

        logger.info(
            "DEFCON transition: %s -> %s | trigger: %s | hash: %s...",
            from_level.name,
            target.name,
            trigger,
            event.event_hash[:12],
        )

    def _save_state(self) -> None:
        self.state_file.write_text(
            json.dumps(
                {
                    "level": self._current_level.name,
                    "transition_count": self._transition_count,
                    "prev_hash": self._prev_hash,
                    "saved_at": datetime.now(UTC).isoformat(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def _load_state(self) -> None:
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                self._current_level = DEFCON[data["level"]]
                self._transition_count = data.get("transition_count", 0)
                self._prev_hash = data.get("prev_hash", "0" * 64)
                logger.info("Loaded persisted DEFCON state: %s", self._current_level.name)
            except (json.JSONDecodeError, KeyError) as exc:
                logger.warning("Could not load state file (%s) — defaulting to NORMAL", exc)

    def _append_audit(self, event: AuditEvent) -> None:
        # CR-5 — write via the canonical ``to_jsonl`` so the on-disk
        # line matches the format the canonical ``from_jsonl`` gate
        # replays through (including the hash-covered payload).
        with self.audit_file.open("a", encoding="utf-8") as fh:
            fh.write(event.to_jsonl() + "\n")


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    machine = DEFCONMachine(
        state_file=Path("output/demo_state.json"),
        audit_file=Path("output/demo_audit.jsonl"),
    )

    scenarios = [
        ("Normal conditions", RiskMetrics(0.02, 0.01, 1)),
        ("Light drawdown", RiskMetrics(0.08, 0.02, 3)),
        ("Moderate drawdown", RiskMetrics(0.11, 0.03, 5)),
        ("Stress — DANGER", RiskMetrics(0.16, 0.05, 7)),
        ("Recovery eval 1/3", RiskMetrics(0.09, 0.02, 3)),
        ("Recovery eval 2/3", RiskMetrics(0.09, 0.02, 3)),
        ("Recovery eval 3/3", RiskMetrics(0.09, 0.02, 3)),
        ("Continued recovery 1/3", RiskMetrics(0.05, 0.01, 2)),
        ("Continued recovery 2/3", RiskMetrics(0.05, 0.01, 2)),
        ("Continued recovery 3/3", RiskMetrics(0.05, 0.01, 2)),
    ]

    print(f"\n{'Scenario':<28} {'DEFCON Level':<12}")
    print("-" * 42)
    for label, metrics in scenarios:
        level = machine.evaluate(metrics)
        print(f"{label:<28} {level.name:<12}")

    print(f"\nAudit trail written to: {machine.audit_file}")
    print(f"State persisted to:     {machine.state_file}")
