"""Tests for the JSONL-backed LedgerStore."""

from __future__ import annotations

from pathlib import Path

import pytest

from finserv_agent_audit.governance.ledger_store import GENESIS_PREV_HASH
from finserv_agent_audit.governance.ledger_store_jsonl import JsonlLedgerStore
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)


def _event(prev: str = GENESIS_PREV_HASH) -> AuditEvent:
    return AuditEvent(
        event_type=AuditEventType.HUMAN_OVERRIDE,
        autonomy_level=AutonomyLevel.A0,
        agent_id="zeus",
        payload={"override": "halt_cleared"},
        prev_hash=prev,
        actor_id="risk_officer_001",
    )


def test_empty_file_genesis(tmp_path: Path) -> None:
    store = JsonlLedgerStore(tmp_path / "ledger.jsonl")
    assert store.head_event_hash() == GENESIS_PREV_HASH
    assert len(store) == 0


def test_append_and_persist(tmp_path: Path) -> None:
    p = tmp_path / "ledger.jsonl"
    store = JsonlLedgerStore(p)
    e = _event()
    store.append(e)
    assert p.exists()
    assert len(store) == 1
    fetched = store.get(0)
    assert fetched.event_id == e.event_id
    assert fetched.event_hash == e.event_hash


def test_reopen_reads_existing(tmp_path: Path) -> None:
    p = tmp_path / "ledger.jsonl"
    a = JsonlLedgerStore(p)
    e1 = _event()
    a.append(e1)
    a.append(_event(prev=e1.event_hash))
    del a
    b = JsonlLedgerStore(p)
    assert len(b) == 2


def test_corrupted_line_raises(tmp_path: Path) -> None:
    p = tmp_path / "ledger.jsonl"
    p.write_text('{"event_type": "not-a-valid-enum-value"}\n')
    with pytest.raises((ValueError, KeyError)):
        list(JsonlLedgerStore(p))


def test_fsync_can_be_disabled(tmp_path: Path) -> None:
    p = tmp_path / "ledger.jsonl"
    store = JsonlLedgerStore(p, fsync=False)
    store.append(_event())
    assert len(store) == 1


def test_get_not_found_raises(tmp_path: Path) -> None:
    store = JsonlLedgerStore(tmp_path / "ledger.jsonl")
    store.append(_event())
    with pytest.raises(IndexError):
        store.get(99)
