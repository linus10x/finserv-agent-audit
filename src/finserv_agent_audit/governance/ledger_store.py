"""Pluggable persistence layer for the audit ledger — ADR-0012.

The original `AuditChain` stored events in a single in-memory list and a
JSONL file. v1.1 factors storage behind a Protocol so deployers can plug
in SQLite (this repo), JSONL (this repo), WORM (this repo, SEC 17a-4
broker-dealer compliance), or downstream backends (Postgres+WAL,
S3+Object Lock with retention period, DynamoDB conditional writes)
without touching `AuditChain` or hash semantics.

This module ships the Protocol + the in-memory reference implementation.
Backends live in `ledger_store_sqlite.py`, `ledger_store_jsonl.py`, and
`ledger_store_worm.py`.

Regulatory anchors:
    - SEC Rule 17a-4 (17 C.F.R. § 240.17a-4) — broker-dealer electronic
      record retention; WORM is the canonical compliant backend
    - SR 11-7 — model risk management; the audit trail evidences the
      effective challenge documented in the model inventory
    - GLBA Safeguards Rule — customer NPI handling; the ledger is the
      tamper-detecting record for any decision touching protected data
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

from finserv_agent_audit.schemas.audit_event import AuditEvent

GENESIS_PREV_HASH = "0" * 64


class LedgerStore(Protocol):
    """Storage Protocol for the audit ledger. Append-only; never mutates."""

    def append(self, event: AuditEvent) -> None: ...
    def __iter__(self) -> Iterator[AuditEvent]: ...
    def __len__(self) -> int: ...
    def get(self, sequence: int) -> AuditEvent: ...
    def head_sequence(self) -> int: ...
    def head_event_hash(self) -> str: ...


class InMemoryLedgerStore:
    """Reference in-memory store — preserves v1.0 behavior."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:
        self._events.append(event)

    def __iter__(self) -> Iterator[AuditEvent]:
        return iter(self._events)

    def __len__(self) -> int:
        return len(self._events)

    def get(self, sequence: int) -> AuditEvent:
        if sequence < 0 or sequence >= len(self._events):
            raise IndexError(f"sequence {sequence} out of range [0, {len(self._events)})")
        return self._events[sequence]

    def head_sequence(self) -> int:
        return len(self._events) - 1

    def head_event_hash(self) -> str:
        if not self._events:
            return GENESIS_PREV_HASH
        return self._events[-1].event_hash
