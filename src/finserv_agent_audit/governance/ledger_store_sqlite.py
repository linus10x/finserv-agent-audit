"""SQLite-backed LedgerStore — ADR-0012 § Persistence backends.

Uses stdlib `sqlite3`. Single-table schema; no UPDATE / DELETE codepath
(append-only is enforced by absence of methods, not by triggers — the
LedgerStore Protocol intentionally exposes no mutation surface).

For production deployments needing Postgres+WAL, S3+Object Lock, or
DynamoDB conditional writes (e.g. firm-wide model inventory under
SR 11-7 or customer NPI under GLBA): write a sibling backend in your
codebase implementing the `LedgerStore` Protocol. ADR-0012 documents
the integration shape; the repo does not pull driver libraries.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterator
from pathlib import Path

from finserv_agent_audit.governance.ledger_store import GENESIS_PREV_HASH
from finserv_agent_audit.schemas.audit_event import AuditEvent


class SqliteLedgerStore:
    """sqlite3-backed `LedgerStore`. One row per `AuditEvent`."""

    def __init__(self, db_path: Path | str, *, table: str = "audit_chain") -> None:
        # Table names cannot be passed as bound parameters, so the identifier
        # is validated to a strict ASCII SQL-identifier shape before it is ever
        # interpolated into a query string. This is the guard the `# nosec B608`
        # annotations below rely on.
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
            raise ValueError(f"invalid table name {table!r}")
        self._table = table
        self._conn = sqlite3.connect(str(db_path), isolation_level=None)
        self._conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._table} (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                event_type TEXT NOT NULL,
                autonomy_level TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                actor_id TEXT,
                prev_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL,
                schema_version TEXT NOT NULL
            )
            """
        )

    def append(self, event: AuditEvent) -> None:
        self._conn.execute(
            f"INSERT INTO {self._table} "  # nosec B608 — table name validated as a SQL identifier in __init__; values are parameterized
            f"(event_id, event_type, autonomy_level, agent_id, timestamp, "
            f"payload_json, actor_id, prev_hash, event_hash, schema_version) "
            f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event.event_id,
                event.event_type.value,
                event.autonomy_level.value,
                event.agent_id,
                event.timestamp,
                json.dumps(event.payload, sort_keys=True),
                event.actor_id,
                event.prev_hash,
                event.event_hash,
                event.schema_version,
            ),
        )

    def __iter__(self) -> Iterator[AuditEvent]:
        rows = self._conn.execute(
            f"SELECT event_id, event_type, autonomy_level, agent_id, timestamp, "  # nosec B608 — table name validated as a SQL identifier in __init__; values are parameterized
            f"payload_json, actor_id, prev_hash, event_hash, schema_version "
            f"FROM {self._table} ORDER BY sequence ASC"
        )
        for row in rows:
            yield self._row_to_event(row)

    def __len__(self) -> int:
        cur = self._conn.execute(f"SELECT COUNT(*) FROM {self._table}")  # nosec B608 — table name validated as a SQL identifier in __init__; values are parameterized
        result: int = cur.fetchone()[0]
        return result

    def get(self, sequence: int) -> AuditEvent:
        # sequence is 0-indexed externally; sqlite AUTOINCREMENT is 1-indexed.
        cur = self._conn.execute(
            f"SELECT event_id, event_type, autonomy_level, agent_id, timestamp, "  # nosec B608 — table name validated as a SQL identifier in __init__; values are parameterized
            f"payload_json, actor_id, prev_hash, event_hash, schema_version "
            f"FROM {self._table} WHERE sequence = ?",
            (sequence + 1,),
        )
        row = cur.fetchone()
        if row is None:
            raise IndexError(f"sequence {sequence} not found")
        return self._row_to_event(row)

    def head_sequence(self) -> int:
        cur = self._conn.execute(f"SELECT COUNT(*) FROM {self._table}")  # nosec B608 — table name validated as a SQL identifier in __init__; values are parameterized
        result = cur.fetchone()[0]
        return int(result) - 1

    def head_event_hash(self) -> str:
        cur = self._conn.execute(
            f"SELECT event_hash FROM {self._table} ORDER BY sequence DESC LIMIT 1"  # nosec B608 — table name validated as a SQL identifier in __init__; values are parameterized
        )
        row = cur.fetchone()
        if row is None:
            return GENESIS_PREV_HASH
        return str(row[0])

    @staticmethod
    def _row_to_event(row: tuple[object, ...]) -> AuditEvent:
        # CR-2 — replay through ``from_jsonl`` so the SQLite read path
        # is gated by the same hash-recomputation check as the JSONL
        # and WORM read paths. A row whose stored ``event_hash``
        # disagrees with its other columns raises
        # ``AuditChainTamperError``.
        data: dict[str, object] = {
            "event_id": str(row[0]),
            "event_type": str(row[1]),
            "autonomy_level": str(row[2]),
            "agent_id": str(row[3]),
            "timestamp": str(row[4]),
            "payload": json.loads(str(row[5])),
            "actor_id": None if row[6] is None else str(row[6]),
            "prev_hash": str(row[7]),
            "event_hash": str(row[8]),
            "schema_version": str(row[9]),
        }
        return AuditEvent.from_jsonl(data)
