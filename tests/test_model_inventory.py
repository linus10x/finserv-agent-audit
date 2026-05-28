"""Tests for the SR 11-7 ModelInventory primitive (ADR-0007).

Covers the registry lifecycle, status transitions that emit
`AuditEventType.MODEL_VALIDATED`, status / overdue queries, and the
ledger-store injection seam.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from finserv_agent_audit.governance.ledger_store import InMemoryLedgerStore
from finserv_agent_audit.governance.model_inventory import (
    ImplementationStatus,
    Model,
    ModelInventory,
    ModelNotFoundError,
)
from finserv_agent_audit.schemas.audit_event import AuditEventType

# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #


@pytest.fixture
def now() -> datetime:
    return datetime.now(UTC)


@pytest.fixture
def base_model(now: datetime) -> Model:
    return Model(
        id="credit_scorer_v3",
        version="3.0.1",
        owner="first-line@bank.example",
        validator="mrm@bank.example",
        implementation_status=ImplementationStatus.PROPOSED,
        validation_date=None,
        next_validation_due=now + timedelta(days=90),
    )


@pytest.fixture
def inventory() -> ModelInventory:
    return ModelInventory()


# --------------------------------------------------------------------------- #
# Model dataclass                                                             #
# --------------------------------------------------------------------------- #


class TestModelDataclass:
    def test_fields_exposed(self, base_model: Model, now: datetime) -> None:
        assert base_model.id == "credit_scorer_v3"
        assert base_model.version == "3.0.1"
        assert base_model.owner == "first-line@bank.example"
        assert base_model.validator == "mrm@bank.example"
        assert base_model.implementation_status == ImplementationStatus.PROPOSED
        assert base_model.validation_date is None
        assert base_model.next_validation_due > now

    def test_implementation_status_enum_members(self) -> None:
        members = {member.name for member in ImplementationStatus}
        assert members == {
            "PROPOSED",
            "IN_VALIDATION",
            "APPROVED_FOR_LIMITED_USE",
            "APPROVED_FOR_PRODUCTION",
            "RETIRED",
        }


# --------------------------------------------------------------------------- #
# Register + query                                                            #
# --------------------------------------------------------------------------- #


class TestRegisterAndQuery:
    def test_register_persists_model(self, inventory: ModelInventory, base_model: Model) -> None:
        inventory.register(base_model)
        retrieved = inventory.get(base_model.id)
        assert retrieved.id == base_model.id
        assert retrieved.implementation_status == ImplementationStatus.PROPOSED

    def test_register_duplicate_raises(self, inventory: ModelInventory, base_model: Model) -> None:
        inventory.register(base_model)
        with pytest.raises(ValueError, match="already registered"):
            inventory.register(base_model)

    def test_get_unknown_raises(self, inventory: ModelInventory) -> None:
        with pytest.raises(ModelNotFoundError):
            inventory.get("does-not-exist")

    def test_query_by_status_returns_matches(
        self, inventory: ModelInventory, now: datetime
    ) -> None:
        a = Model(
            id="a",
            version="1.0",
            owner="o",
            validator="v",
            implementation_status=ImplementationStatus.PROPOSED,
            validation_date=None,
            next_validation_due=now + timedelta(days=30),
        )
        b = Model(
            id="b",
            version="1.0",
            owner="o",
            validator="v",
            implementation_status=ImplementationStatus.APPROVED_FOR_PRODUCTION,
            validation_date=now,
            next_validation_due=now + timedelta(days=30),
        )
        c = Model(
            id="c",
            version="1.0",
            owner="o",
            validator="v",
            implementation_status=ImplementationStatus.APPROVED_FOR_PRODUCTION,
            validation_date=now,
            next_validation_due=now + timedelta(days=30),
        )
        inventory.register(a)
        inventory.register(b)
        inventory.register(c)
        production = inventory.query_by_status(ImplementationStatus.APPROVED_FOR_PRODUCTION)
        ids = {m.id for m in production}
        assert ids == {"b", "c"}

    def test_query_overdue_returns_models_past_revalidation(
        self, inventory: ModelInventory, now: datetime
    ) -> None:
        overdue = Model(
            id="overdue",
            version="1.0",
            owner="o",
            validator="v",
            implementation_status=ImplementationStatus.APPROVED_FOR_PRODUCTION,
            validation_date=now - timedelta(days=400),
            next_validation_due=now - timedelta(days=10),
        )
        current = Model(
            id="current",
            version="1.0",
            owner="o",
            validator="v",
            implementation_status=ImplementationStatus.APPROVED_FOR_PRODUCTION,
            validation_date=now - timedelta(days=30),
            next_validation_due=now + timedelta(days=60),
        )
        inventory.register(overdue)
        inventory.register(current)
        results = inventory.query_overdue(as_of=now)
        ids = {m.id for m in results}
        assert ids == {"overdue"}

    def test_query_overdue_excludes_retired(self, inventory: ModelInventory, now: datetime) -> None:
        retired = Model(
            id="retired",
            version="1.0",
            owner="o",
            validator="v",
            implementation_status=ImplementationStatus.RETIRED,
            validation_date=now - timedelta(days=400),
            next_validation_due=now - timedelta(days=10),
        )
        inventory.register(retired)
        results = inventory.query_overdue(as_of=now)
        assert results == []


# --------------------------------------------------------------------------- #
# Status transitions and audit emission                                       #
# --------------------------------------------------------------------------- #


class TestTransitionStatus:
    def test_transition_updates_status(self, inventory: ModelInventory, base_model: Model) -> None:
        inventory.register(base_model)
        inventory.transition_status(
            base_model.id,
            ImplementationStatus.IN_VALIDATION,
            actor_id="mrm@bank.example",
        )
        assert (
            inventory.get(base_model.id).implementation_status == ImplementationStatus.IN_VALIDATION
        )

    def test_transition_unknown_model_raises(self, inventory: ModelInventory) -> None:
        with pytest.raises(ModelNotFoundError):
            inventory.transition_status("missing", ImplementationStatus.IN_VALIDATION, actor_id="x")

    def test_validation_transition_emits_event(self, base_model: Model) -> None:
        store = InMemoryLedgerStore()
        inv = ModelInventory(ledger_store=store)
        inv.register(base_model)

        validated_at = datetime.now(UTC)
        inv.transition_status(
            base_model.id,
            ImplementationStatus.APPROVED_FOR_PRODUCTION,
            actor_id="mrm@bank.example",
            validation_date=validated_at,
            next_validation_due=validated_at + timedelta(days=365),
        )

        events = list(store)
        assert len(events) == 1
        event = events[0]
        assert event.event_type == AuditEventType.MODEL_VALIDATED
        assert event.payload["model_id"] == base_model.id
        assert event.payload["from_status"] == ImplementationStatus.PROPOSED.value
        assert event.payload["to_status"] == ImplementationStatus.APPROVED_FOR_PRODUCTION.value
        assert event.actor_id == "mrm@bank.example"

    def test_non_validation_transition_does_not_emit(self, base_model: Model) -> None:
        store = InMemoryLedgerStore()
        inv = ModelInventory(ledger_store=store)
        inv.register(base_model)
        # PROPOSED -> RETIRED is a non-validation transition (no validator sign-off).
        inv.transition_status(
            base_model.id, ImplementationStatus.RETIRED, actor_id="ops@bank.example"
        )
        assert list(store) == []

    def test_transition_updates_validation_dates(
        self, inventory: ModelInventory, base_model: Model, now: datetime
    ) -> None:
        inventory.register(base_model)
        new_validated_at = now + timedelta(hours=1)
        new_next_due = now + timedelta(days=365)
        inventory.transition_status(
            base_model.id,
            ImplementationStatus.APPROVED_FOR_LIMITED_USE,
            actor_id="mrm@bank.example",
            validation_date=new_validated_at,
            next_validation_due=new_next_due,
        )
        m = inventory.get(base_model.id)
        assert m.validation_date == new_validated_at
        assert m.next_validation_due == new_next_due

    def test_transition_without_ledger_store_does_not_raise(
        self, inventory: ModelInventory, base_model: Model
    ) -> None:
        # No ledger_store injected; the transition should still succeed silently.
        inventory.register(base_model)
        inventory.transition_status(
            base_model.id,
            ImplementationStatus.APPROVED_FOR_PRODUCTION,
            actor_id="mrm@bank.example",
            validation_date=datetime.now(UTC),
        )
        assert (
            inventory.get(base_model.id).implementation_status
            == ImplementationStatus.APPROVED_FOR_PRODUCTION
        )

    def test_three_lines_of_defense_trail_complete(self, base_model: Model) -> None:
        """Full lifecycle: PROPOSED -> IN_VALIDATION -> APPROVED_FOR_PRODUCTION."""
        store = InMemoryLedgerStore()
        inv = ModelInventory(ledger_store=store)
        inv.register(base_model)

        inv.transition_status(
            base_model.id,
            ImplementationStatus.IN_VALIDATION,
            actor_id="mrm@bank.example",
        )
        inv.transition_status(
            base_model.id,
            ImplementationStatus.APPROVED_FOR_PRODUCTION,
            actor_id="mrm@bank.example",
            validation_date=datetime.now(UTC),
        )

        events = list(store)
        # Both transitions touch the validation lifecycle and emit events.
        assert len(events) == 2
        assert all(e.event_type == AuditEventType.MODEL_VALIDATED for e in events)


# --------------------------------------------------------------------------- #
# Snapshot / enumeration                                                      #
# --------------------------------------------------------------------------- #


class TestEnumeration:
    def test_all_returns_registered_models(
        self, inventory: ModelInventory, base_model: Model, now: datetime
    ) -> None:
        other = Model(
            id="other",
            version="1.0",
            owner="o",
            validator="v",
            implementation_status=ImplementationStatus.RETIRED,
            validation_date=now,
            next_validation_due=now,
        )
        inventory.register(base_model)
        inventory.register(other)
        ids = {m.id for m in inventory.all()}
        assert ids == {base_model.id, "other"}

    def test_len(self, inventory: ModelInventory, base_model: Model) -> None:
        assert len(inventory) == 0
        inventory.register(base_model)
        assert len(inventory) == 1


# --------------------------------------------------------------------------- #
# Sanity: the module's source file exists at the documented path              #
# --------------------------------------------------------------------------- #


def test_module_lives_at_documented_path() -> None:
    """ADR-0007 references the implementing module path; keep it stable."""
    root = Path(__file__).resolve().parent.parent
    expected = root / "src" / "finserv_agent_audit" / "governance" / "model_inventory.py"
    assert expected.is_file()
