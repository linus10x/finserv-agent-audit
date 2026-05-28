"""SR 11-7 Model Inventory primitive — ADR-0007.

Every agent component, sub-model, LLM revision, or tool that materially
shapes a regulated decision is a model under the SR 11-7 definition. The
inventory is the system of record: who owns it, who validates it, what
status it occupies in its lifecycle, when it was last validated, and when
it is next due for revalidation.

The status enum maps to the three-lines-of-defense overlay published in
`docs/sr11_7_mapping.md`:

    PROPOSED                    - first line submitted the entry
    IN_VALIDATION               - second line is reviewing
    APPROVED_FOR_LIMITED_USE    - second line cleared a constrained scope
    APPROVED_FOR_PRODUCTION     - second line cleared the full scope
    RETIRED                     - removed from the production decision path

Transitions that touch the validation lifecycle (anything to or from a
state that requires second-line sign-off) emit
`AuditEventType.MODEL_VALIDATED` to the injected `LedgerStore`. Internal
audit (third line) reads those entries to attest that the first and second
lines are operating as designed.

Regulatory anchors:
    - SR 11-7 Sections III, V, VI (Federal Reserve, April 4, 2011)
    - OCC Bulletin 2011-12 (adopting SR 11-7 for OCC-regulated institutions)
    - OCC Heightened Standards, 12 C.F.R. Part 30 Appendix D
    - Reader-friendly mapping: `docs/sr11_7_mapping.md`

> Reference pattern, not legal advice. Regulatory characterizations are
> summaries; engage qualified counsel for compliance determinations. See
> repo-root `DISCLAIMER.md`.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from finserv_agent_audit.governance.ledger_store import LedgerStore
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)

GENESIS_PREV_HASH = "0" * 64


class ImplementationStatus(Enum):
    """SR 11-7 lifecycle states for an inventoried model."""

    PROPOSED = "proposed"
    IN_VALIDATION = "in_validation"
    APPROVED_FOR_LIMITED_USE = "approved_for_limited_use"
    APPROVED_FOR_PRODUCTION = "approved_for_production"
    RETIRED = "retired"


# Transitions to or from these states are validation-lifecycle transitions
# and emit `AuditEventType.MODEL_VALIDATED` for the second-line / third-line
# evidence trail.
_VALIDATION_STATES: frozenset[ImplementationStatus] = frozenset(
    {
        ImplementationStatus.IN_VALIDATION,
        ImplementationStatus.APPROVED_FOR_LIMITED_USE,
        ImplementationStatus.APPROVED_FOR_PRODUCTION,
    }
)


class ModelNotFoundError(KeyError):
    """Raised when a query references a model id not in the inventory."""


@dataclass
class Model:
    """Inventory entry for one model.

    Fields:
        id: stable identifier (institution-scoped).
        version: semantic or release version.
        owner: first-line owner identifier (team, principal, or service).
        validator: second-line validator identifier.
        implementation_status: lifecycle state.
        validation_date: timestamp of the most recent validation sign-off.
        next_validation_due: deadline for the next required revalidation.
    """

    id: str
    version: str
    owner: str
    validator: str
    implementation_status: ImplementationStatus
    validation_date: datetime | None
    next_validation_due: datetime


@dataclass
class ModelInventory:
    """Registry of inventoried models.

    Wire a `LedgerStore` to receive `MODEL_VALIDATED` events on every
    validation-lifecycle transition. Without a store the inventory still
    enforces uniqueness, supports queries, and tracks status; emissions
    become silent. The injection seam keeps the inventory composable with
    any of the shipped backends (InMemory, JSONL, SQLite, WORM) or an
    operator-supplied backend implementing the same Protocol.
    """

    ledger_store: LedgerStore | None = None
    agent_id: str = "system:model_inventory"
    _models: dict[str, Model] = field(default_factory=dict, init=False, repr=False)

    # ------------------------------------------------------------------ #
    # Registration                                                       #
    # ------------------------------------------------------------------ #

    def register(self, model: Model) -> None:
        """Add a new model. Raises `ValueError` on duplicate id."""
        if model.id in self._models:
            raise ValueError(f"model {model.id!r} already registered")
        self._models[model.id] = model

    def get(self, model_id: str) -> Model:
        """Return the inventory entry. Raises `ModelNotFoundError` if missing."""
        try:
            return self._models[model_id]
        except KeyError as exc:
            raise ModelNotFoundError(model_id) from exc

    def all(self) -> Iterator[Model]:
        """Iterate every registered model."""
        return iter(self._models.values())

    def __len__(self) -> int:
        return len(self._models)

    # ------------------------------------------------------------------ #
    # Lifecycle transitions                                              #
    # ------------------------------------------------------------------ #

    def transition_status(
        self,
        model_id: str,
        new_status: ImplementationStatus,
        *,
        actor_id: str,
        validation_date: datetime | None = None,
        next_validation_due: datetime | None = None,
    ) -> Model:
        """Move a model to `new_status`.

        Validation-lifecycle transitions (entering or leaving any of
        IN_VALIDATION / APPROVED_FOR_LIMITED_USE / APPROVED_FOR_PRODUCTION)
        emit `AuditEventType.MODEL_VALIDATED` to the wired ledger store.
        """
        model = self.get(model_id)
        prior_status = model.implementation_status
        model.implementation_status = new_status

        if validation_date is not None:
            model.validation_date = validation_date
        if next_validation_due is not None:
            model.next_validation_due = next_validation_due

        if self._is_validation_transition(prior_status, new_status):
            self._emit_validated_event(
                model=model,
                prior_status=prior_status,
                actor_id=actor_id,
            )
        return model

    # ------------------------------------------------------------------ #
    # Queries                                                            #
    # ------------------------------------------------------------------ #

    def query_by_status(self, status: ImplementationStatus) -> list[Model]:
        """Return every model currently in `status`."""
        return [m for m in self._models.values() if m.implementation_status == status]

    def query_overdue(self, *, as_of: datetime | None = None) -> list[Model]:
        """Return non-retired models whose `next_validation_due` is in the past."""
        cutoff = as_of if as_of is not None else datetime.now(UTC)
        return [
            m
            for m in self._models.values()
            if m.implementation_status != ImplementationStatus.RETIRED
            and m.next_validation_due < cutoff
        ]

    # ------------------------------------------------------------------ #
    # Internals                                                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _is_validation_transition(prior: ImplementationStatus, new: ImplementationStatus) -> bool:
        """True when either side of the transition is a validation-lifecycle state."""
        if prior == new:
            return False
        return new in _VALIDATION_STATES or prior in _VALIDATION_STATES

    def _emit_validated_event(
        self,
        *,
        model: Model,
        prior_status: ImplementationStatus,
        actor_id: str,
    ) -> None:
        if self.ledger_store is None:
            return
        prev_hash = self.ledger_store.head_event_hash()
        event = AuditEvent(
            event_type=AuditEventType.MODEL_VALIDATED,
            autonomy_level=AutonomyLevel.A2,
            agent_id=self.agent_id,
            payload={
                "model_id": model.id,
                "model_version": model.version,
                "owner": model.owner,
                "validator": model.validator,
                "from_status": prior_status.value,
                "to_status": model.implementation_status.value,
                "validation_date": (
                    model.validation_date.isoformat() if model.validation_date is not None else None
                ),
                "next_validation_due": model.next_validation_due.isoformat(),
            },
            prev_hash=prev_hash,
            actor_id=actor_id,
        )
        self.ledger_store.append(event)


__all__ = [
    "ImplementationStatus",
    "Model",
    "ModelInventory",
    "ModelNotFoundError",
]
