"""Retraining Cadence Monitor — ADR-0024.

SR 11-7 / OCC Bulletin 2026-13 expects an annual model-validation
cadence as the floor; that floor was written for credit-risk models
that are recalibrated quarterly. Foundation-model APIs and continuous
fine-tuning pipelines move on a different clock — weekly retrains and
continuous adapter updates are normal. The bank's MRM team needs a
classification scheme that distinguishes these regimes and emits the
required validation cadence per class.

This monitor is the bridge framework. OCC 2026-13 explicitly excluded
generative + agentic AI from scope pending a joint RFI; until that RFI
closes, the operator's MRM function carries the gap. This module is
the gap-closer: it registers each foundation-model surface against one
of four `RetrainingClass` regimes (`STATIC`, `MONTHLY_RETRAIN`,
`WEEKLY_RETRAIN`, `CONTINUOUS_FINE_TUNE`), records validation events
against each, and surfaces an overdue list the second line can act on.

Databricks's 2026 MRM commentary named the problem directly: "Models
that drift weekly need conditional approvals; lineage-based controls
must shift to vendor-transparency reviews." This monitor encodes that
shift.

Regulatory anchors:
    - SR 11-7 § IV (Model Validation) — independent validation as a
      core MRM control
    - OCC Bulletin 2026-13 — scope-exclusion of generative + agentic
      AI; this monitor is the bridge framework the bank uses until the
      joint RFI ships replacement guidance
    - FFIEC IT Examination Handbook § "Model Risk" — examination
      expectations for ongoing-monitoring evidence
    - Databricks MRM 2026 commentary — vendor-transparency-review
      cadence shift

> Reference pattern, not legal advice. Regulatory characterizations are
> summaries; consult counsel for applicability. See repo-root
> `DISCLAIMER.md`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum

from finserv_agent_audit.governance.ledger_store import LedgerStore
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)


class RetrainingClass(Enum):
    """Four cadence regimes for inventoried AI models.

    The cadence-validation requirement per class:

    * ``STATIC`` — annual validation. Vendor-pinned foundation model
      that the bank does not fine-tune; model card and SOC 2 are the
      primary controls.
    * ``MONTHLY_RETRAIN`` — quarterly validation minimum. In-house or
      vendor model retrained monthly on a stable feature set.
    * ``WEEKLY_RETRAIN`` — monthly validation plus continuous
      monitoring. Vendor or in-house model retrained weekly; feature
      drift becomes a first-class signal.
    * ``CONTINUOUS_FINE_TUNE`` — continuous monitoring; pre-deployment
      validation for each material change. RLHF / RLAIF / continuous
      adapter pipelines fit here.
    """

    STATIC = "STATIC"
    MONTHLY_RETRAIN = "MONTHLY_RETRAIN"
    WEEKLY_RETRAIN = "WEEKLY_RETRAIN"
    CONTINUOUS_FINE_TUNE = "CONTINUOUS_FINE_TUNE"


# Per-class required validation cadence (the maximum time allowed
# between successive validations before the model is "overdue").
_CADENCE_BY_CLASS: dict[RetrainingClass, timedelta] = {
    RetrainingClass.STATIC: timedelta(days=365),
    RetrainingClass.MONTHLY_RETRAIN: timedelta(days=90),
    RetrainingClass.WEEKLY_RETRAIN: timedelta(days=30),
    # Continuous fine-tune carries the tightest validation freshness
    # signal: 7 days. Treat any longer gap as overdue and force a fresh
    # pre-deployment review on the next material change.
    RetrainingClass.CONTINUOUS_FINE_TUNE: timedelta(days=7),
}


@dataclass
class _RegisteredModel:
    """Internal registry entry."""

    model_id: str
    retraining_class: RetrainingClass
    last_trained: datetime
    owner: str
    last_validated: datetime | None = None


@dataclass(frozen=True)
class RetrainingCadenceReport:
    """Snapshot of a model's current cadence-validation status.

    Fields:
        model_id: stable identifier.
        retraining_class: declared regime.
        last_trained: latest training timestamp the operator recorded.
        last_validated: latest second-line validation timestamp, or None.
        required_validation_cadence: the maximum allowed time between
            successive validations for this class.
        compliant: True iff the model has been validated within the
            required cadence as of the report's evaluation timestamp.
        next_validation_due: when the next validation must occur. When
            no prior validation exists, this is the registration time
            plus the cadence (the operator gets the first cadence
            window to complete the initial validation).
    """

    model_id: str
    retraining_class: RetrainingClass
    last_trained: datetime
    last_validated: datetime | None
    required_validation_cadence: timedelta
    compliant: bool
    next_validation_due: datetime


class RetrainingCadenceMonitor:
    """Track foundation-model surfaces against their retraining-class cadence.

    Wire a `LedgerStore` to receive a `COMPLIANCE_CHECK` event on every
    `register_model` and every `record_validation` call. Without a store
    the monitor still tracks registrations in memory; chain emission is
    silent.
    """

    def __init__(self, ledger_store: LedgerStore | None = None) -> None:
        self._store: LedgerStore | None = ledger_store
        self._models: dict[str, _RegisteredModel] = {}
        self._registered_at: dict[str, datetime] = {}
        self._agent_id = "system:retraining_cadence_monitor"

    # ------------------------------------------------------------------ #
    # Register                                                           #
    # ------------------------------------------------------------------ #

    def register_model(
        self,
        model_id: str,
        retraining_class: RetrainingClass,
        last_trained: datetime,
        owner: str,
    ) -> None:
        """Add a model to the registry and emit a chain entry."""
        if not model_id:
            raise ValueError("model_id must be a non-empty string")
        if not owner:
            raise ValueError("owner must be a non-empty string")
        if model_id in self._models:
            raise ValueError(f"model {model_id!r} already registered")
        registered = _RegisteredModel(
            model_id=model_id,
            retraining_class=retraining_class,
            last_trained=last_trained,
            owner=owner,
        )
        self._models[model_id] = registered
        self._registered_at[model_id] = datetime.now(UTC)
        self._emit_event(
            control="model_registered",
            model_id=model_id,
            retraining_class=retraining_class,
            extra={
                "last_trained": last_trained.isoformat(),
                "owner": owner,
                "required_validation_cadence_days": (_CADENCE_BY_CLASS[retraining_class].days),
            },
        )

    def record_validation(
        self,
        model_id: str,
        validated_at: datetime,
        actor_id: str,
    ) -> None:
        """Record a second-line validation event for `model_id`."""
        if model_id not in self._models:
            raise KeyError(model_id)
        if not actor_id:
            raise ValueError("actor_id must be a non-empty string")
        self._models[model_id].last_validated = validated_at
        self._emit_event(
            control="model_validation_recorded",
            model_id=model_id,
            retraining_class=self._models[model_id].retraining_class,
            extra={
                "validated_at": validated_at.isoformat(),
                "actor_id": actor_id,
            },
        )

    # ------------------------------------------------------------------ #
    # Evaluate                                                           #
    # ------------------------------------------------------------------ #

    def evaluate(
        self,
        model_id: str,
        as_of: datetime | None = None,
    ) -> RetrainingCadenceReport:
        """Return the current cadence-validation status for `model_id`."""
        if model_id not in self._models:
            raise KeyError(model_id)
        model = self._models[model_id]
        cadence = _CADENCE_BY_CLASS[model.retraining_class]
        evaluation_time = as_of if as_of is not None else datetime.now(UTC)

        if model.last_validated is None:
            # No prior validation. The model is non-compliant from the
            # moment the cadence window after registration elapses; we
            # surface non-compliant immediately and let the operator
            # decide whether to treat the first cadence window as a
            # grace period.
            registered_at = self._registered_at.get(model_id, evaluation_time)
            next_due = registered_at + cadence
            return RetrainingCadenceReport(
                model_id=model_id,
                retraining_class=model.retraining_class,
                last_trained=model.last_trained,
                last_validated=None,
                required_validation_cadence=cadence,
                compliant=False,
                next_validation_due=next_due,
            )

        next_due = model.last_validated + cadence
        compliant = evaluation_time <= next_due
        return RetrainingCadenceReport(
            model_id=model_id,
            retraining_class=model.retraining_class,
            last_trained=model.last_trained,
            last_validated=model.last_validated,
            required_validation_cadence=cadence,
            compliant=compliant,
            next_validation_due=next_due,
        )

    def query_overdue(self, as_of: datetime | None = None) -> list[RetrainingCadenceReport]:
        """Return reports for every registered model that is overdue."""
        evaluation_time = as_of if as_of is not None else datetime.now(UTC)
        out: list[RetrainingCadenceReport] = []
        for model_id in self._models:
            report = self.evaluate(model_id, as_of=evaluation_time)
            if not report.compliant:
                out.append(report)
        return out

    # ------------------------------------------------------------------ #
    # Internals                                                          #
    # ------------------------------------------------------------------ #

    def _emit_event(
        self,
        *,
        control: str,
        model_id: str,
        retraining_class: RetrainingClass,
        extra: dict[str, str | int | float | None] | None = None,
    ) -> None:
        if self._store is None:
            return
        payload: dict[str, str | int | float | None] = {
            "control": control,
            "model_id": model_id,
            "retraining_class": retraining_class.value,
        }
        if extra is not None:
            payload.update(extra)
        prev_hash = self._store.head_event_hash()
        event = AuditEvent(
            event_type=AuditEventType.COMPLIANCE_CHECK,
            autonomy_level=AutonomyLevel.A2,
            agent_id=self._agent_id,
            payload=dict(payload),
            prev_hash=prev_hash,
        )
        self._store.append(event)


__all__ = [
    "RetrainingCadenceMonitor",
    "RetrainingCadenceReport",
    "RetrainingClass",
]
