"""Tests for the SQLite-backed LedgerStore."""

from __future__ import annotations

from pathlib import Path

import pytest

from finserv_agent_audit.governance.ledger_store import GENESIS_PREV_HASH
from finserv_agent_audit.governance.ledger_store_sqlite import SqliteLedgerStore
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)


def _event(prev: str = GENESIS_PREV_HASH) -> AuditEvent:
    return AuditEvent(
        event_type=AuditEventType.MODEL_VALIDATED,
        autonomy_level=AutonomyLevel.A3,
        agent_id="sentinel",
        payload={"model_id": "credit-risk-v3", "sr_11_7_status": "effective"},
        prev_hash=prev,
    )


def test_empty_db_returns_genesis(tmp_path: Path) -> None:
    store = SqliteLedgerStore(tmp_path / "ledger.db")
    assert store.head_event_hash() == GENESIS_PREV_HASH
    assert store.head_sequence() == -1
    assert len(store) == 0


def test_append_round_trip(tmp_path: Path) -> None:
    store = SqliteLedgerStore(tmp_path / "ledger.db")
    e = _event()
    store.append(e)
    assert len(store) == 1
    fetched = store.get(0)
    assert fetched.event_id == e.event_id
    assert fetched.event_hash == e.event_hash
    assert store.head_event_hash() == e.event_hash


def test_persists_across_reopen(tmp_path: Path) -> None:
    db = tmp_path / "ledger.db"
    store_a = SqliteLedgerStore(db)
    e1 = _event()
    store_a.append(e1)
    store_a.append(_event(prev=e1.event_hash))
    del store_a

    store_b = SqliteLedgerStore(db)
    assert len(store_b) == 2
    event_ids = [e.event_id for e in store_b]
    assert len(event_ids) == 2


def test_iter_preserves_order_with_many_entries(tmp_path: Path) -> None:
    store = SqliteLedgerStore(tmp_path / "ledger.db")
    prev = GENESIS_PREV_HASH
    expected_ids = []
    for _ in range(50):
        e = _event(prev=prev)
        store.append(e)
        expected_ids.append(e.event_id)
        prev = e.event_hash
    seen = [e.event_id for e in store]
    assert seen == expected_ids


def test_no_update_path(tmp_path: Path) -> None:
    """The Protocol does not expose UPDATE; verify there is no method to mutate."""
    store = SqliteLedgerStore(tmp_path / "ledger.db")
    for forbidden in ("update", "delete", "truncate", "set"):
        assert not hasattr(store, forbidden), f"SqliteLedgerStore must not expose {forbidden}"


def test_get_out_of_range_raises(tmp_path: Path) -> None:
    store = SqliteLedgerStore(tmp_path / "ledger.db")
    store.append(_event())
    with pytest.raises(IndexError):
        store.get(99)


def test_custom_table_name(tmp_path: Path) -> None:
    store = SqliteLedgerStore(tmp_path / "ledger.db", table="custom_audit")
    store.append(_event())
    assert len(store) == 1


def test_invalid_table_name_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        SqliteLedgerStore(tmp_path / "ledger.db", table="bad; DROP TABLE")


def test_sql_injection_table_name_raises(tmp_path: Path) -> None:
    # A table name carrying a SQL-injection payload must be rejected at
    # construction, before it can be interpolated into any query.
    with pytest.raises(ValueError):
        SqliteLedgerStore(tmp_path / "ledger.db", table="x; DROP TABLE y")


def test_table_name_rejects_leading_digit_and_empty(tmp_path: Path) -> None:
    # The strict identifier regex rejects shapes the old isalnum() check let
    # through (leading digit) and the empty string.
    with pytest.raises(ValueError):
        SqliteLedgerStore(tmp_path / "ledger.db", table="1bad")
    with pytest.raises(ValueError):
        SqliteLedgerStore(tmp_path / "ledger.db", table="")
