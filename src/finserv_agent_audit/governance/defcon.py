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

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


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


@dataclass
class AuditEvent:
    """Immutable audit record for every state transition."""

    event_id: str
    timestamp: str
    from_level: str
    to_level: str
    trigger: str
    metrics_snapshot: dict[str, Any]
    prev_hash: str
    event_hash: str = ""

    def __post_init__(self) -> None:
        payload = json.dumps(
            {
                "event_id": self.event_id,
                "timestamp": self.timestamp,
                "from_level": self.from_level,
                "to_level": self.to_level,
                "trigger": self.trigger,
                "prev_hash": self.prev_hash,
            },
            sort_keys=True,
        )
        self.event_hash = hashlib.sha256(payload.encode()).hexdigest()


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

        Args:
            target: Target DEFCON level.
            operator_id: Identity of the human authorizing the override.
            reason: Free-text justification (required for audit).
            metrics: Optional current risk snapshot.

        Returns:
            The new DEFCON level.
        """
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
        """Confirm a state transition, write audit record, persist state."""
        from_level = self._current_level
        self._current_level = target
        self._pending_target = None
        self._confirmation_count = 0
        self._transition_count += 1

        event = AuditEvent(
            event_id=f"defcon-{self._transition_count:06d}",
            timestamp=metrics.timestamp.isoformat(),
            from_level=from_level.name,
            to_level=target.name,
            trigger=trigger,
            metrics_snapshot={
                "portfolio_drawdown": metrics.portfolio_drawdown,
                "daily_loss": metrics.daily_loss,
                "consecutive_losses": metrics.consecutive_losses,
            },
            prev_hash=self._prev_hash,
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
        with self.audit_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(vars(event)) + "\n")


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
