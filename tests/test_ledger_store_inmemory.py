"""Tests for the in-memory reference LedgerStore."""

from __future__ import annotations

import pytest

from finserv_agent_audit.governance.ledger_store import (
    GENESIS_PREV_HASH,
    InMemoryLedgerStore,
    LedgerStore,
)
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)


def _make_event(prev: str = GENESIS_PREV_HASH) -> AuditEvent:
    return AuditEvent(
        event_type=AuditEventType.DECISION_MADE,
        autonomy_level=AutonomyLevel.A2,
        agent_id="test-agent",
        payload={"action": "enter_position", "ticker": "SPY"},
        prev_hash=prev,
    )


def test_empty_store_head_returns_genesis() -> None:
    store: LedgerStore = InMemoryLedgerStore()
    assert store.head_event_hash() == GENESIS_PREV_HASH
    assert store.head_sequence() == -1
    assert len(store) == 0


def test_append_then_get() -> None:
    store: LedgerStore = InMemoryLedgerStore()
    e0 = _make_event()
    store.append(e0)
    assert len(store) == 1
    assert store.get(0) == e0
    assert store.head_sequence() == 0
    assert store.head_event_hash() == e0.event_hash


def test_iter_returns_events_in_order() -> None:
    store: LedgerStore = InMemoryLedgerStore()
    prev = GENESIS_PREV_HASH
    appended = []
    for _ in range(3):
        e = _make_event(prev=prev)
        store.append(e)
        appended.append(e)
        prev = e.event_hash
    assert [e.event_id for e in store] == [e.event_id for e in appended]


def test_get_out_of_range_raises() -> None:
    store: LedgerStore = InMemoryLedgerStore()
    store.append(_make_event())
    with pytest.raises(IndexError):
        store.get(5)


def test_protocol_conformance_via_method_set() -> None:
    store = InMemoryLedgerStore()
    for method in (
        "append",
        "__iter__",
        "__len__",
        "get",
        "head_sequence",
        "head_event_hash",
    ):
        assert hasattr(store, method)
