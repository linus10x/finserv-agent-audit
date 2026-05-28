"""Append-only JSONL LedgerStore — ADR-0012 § Persistence backends.

One JSON object per line. Survives crash mid-write only if `fsync=True`
(the default). For higher durability — e.g. firm-wide model inventory
records under SR 11-7 or customer NPI under GLBA Safeguards — deployers
should use an external append-only object store (S3 + Object Lock with
a retention period) and write a custom backend implementing
`LedgerStore` against the same Protocol.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path

from finserv_agent_audit.governance.ledger_store import GENESIS_PREV_HASH
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)


class JsonlLedgerStore:
    """JSONL file-backed `LedgerStore`."""

    def __init__(self, path: Path | str, *, fsync: bool = True) -> None:
        self._path = Path(path)
        self._fsync = fsync
        self._path.touch(exist_ok=True)

    def append(self, event: AuditEvent) -> None:
        line = json.dumps(event.to_dict(), sort_keys=True, separators=(",", ":")) + "\n"
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            if self._fsync:
                os.fsync(f.fileno())

    def __iter__(self) -> Iterator[AuditEvent]:
        with open(self._path, encoding="utf-8") as f:
            for raw in f:
                stripped = raw.strip()
                if not stripped:
                    continue
                yield self._decode(stripped)

    def __len__(self) -> int:
        with open(self._path, encoding="utf-8") as f:
            return sum(1 for ln in f if ln.strip())

    def get(self, sequence: int) -> AuditEvent:
        for i, event in enumerate(self):
            if i == sequence:
                return event
        raise IndexError(f"sequence {sequence} not found")

    def head_sequence(self) -> int:
        return len(self) - 1

    def head_event_hash(self) -> str:
        head = GENESIS_PREV_HASH
        for event in self:
            head = event.event_hash
        return head

    @staticmethod
    def _decode(line: str) -> AuditEvent:
        d = json.loads(line)
        event = AuditEvent(
            event_type=AuditEventType(d["event_type"]),
            autonomy_level=AutonomyLevel(d["autonomy_level"]),
            agent_id=d["agent_id"],
            payload=d["payload"],
            prev_hash=d["prev_hash"],
            event_id=d["event_id"],
            timestamp=d["timestamp"],
            actor_id=d.get("actor_id"),
            schema_version=d.get("schema_version", "1.0.0"),
        )
        # Preserve stored hash (round-trip yields the same value when
        # fields are deterministic, but we explicitly restore for fidelity).
        event.event_hash = d["event_hash"]
        return event
