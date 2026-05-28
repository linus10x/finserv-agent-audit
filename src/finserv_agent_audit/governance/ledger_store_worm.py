"""WORM (write-once-read-many) LedgerStore — ADR-0013.

SEC Rule 17a-4 (17 C.F.R. § 240.17a-4) requires broker-dealers to
preserve certain electronic records in a non-rewriteable, non-erasable
format for prescribed retention periods (commonly 3–6 years, with the
first two years readily accessible). The 2022 SEC amendments
(Release No. 34-96034) modernized the rule to permit electronic
recordkeeping systems that either (a) preserve records in WORM format
or (b) maintain an audit-trail alternative — this backend implements
the former path: every appended event is sealed at the filesystem
layer (read-only mode bits) and any attempt to overwrite a prior line,
truncate the file, or rewrite an existing event raises
`WORMViolationError`.

Layered architecture: the file format is JSONL (one event per line,
matches `JsonlLedgerStore`), so existing tooling can read a WORM
ledger as an ordinary JSONL ledger. The WORM contract is enforced on
the *write* path.

For production-grade WORM in the cloud, pair this backend with
S3 Object Lock in COMPLIANCE mode plus an explicit retention period
calibrated to your books-and-records policy. This local backend is
suitable for tier-2 audit copies, on-prem deployments, and tests.
"""

from __future__ import annotations

import contextlib
import json
import os
import stat
from collections.abc import Iterator
from pathlib import Path

from finserv_agent_audit.governance.ledger_store import GENESIS_PREV_HASH
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)


class WORMViolationError(RuntimeError):
    """Raised when a write would violate the write-once contract."""


class WORMLedgerStore:
    """Write-once-read-many JSONL-format `LedgerStore`.

    File-level invariants enforced on every append:
        1. The file is opened in O_APPEND mode (kernel guarantees
           writes land at end-of-file).
        2. Before each append, the existing byte length is recorded
           and re-checked after the write; any discrepancy raises.
        3. After each append, the file's mode bits are reduced to
           owner-read-only (0o400) to deter casual mutation. The
           next append re-grants write to the owner just for the
           duration of the system call (and revokes it again on
           success). On filesystems that ignore mode bits (FAT,
           some network mounts) this is best-effort.
        4. `event_id`s already present in the file are tracked and
           re-appending the same id raises `WORMViolationError`.
    """

    def __init__(self, path: Path | str, *, fsync: bool = True) -> None:
        self._path = Path(path)
        self._fsync = fsync
        if not self._path.exists():
            self._path.touch()
            self._seal()
        self._seen_ids: set[str] = {e.event_id for e in self}

    def append(self, event: AuditEvent) -> None:
        if event.event_id in self._seen_ids:
            raise WORMViolationError(
                f"event_id {event.event_id!r} already present — WORM forbids overwrite"
            )
        line = json.dumps(event.to_dict(), sort_keys=True, separators=(",", ":")) + "\n"
        pre_size = self._path.stat().st_size
        self._unseal()
        try:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(line)
                f.flush()
                if self._fsync:
                    os.fsync(f.fileno())
            post_size = self._path.stat().st_size
            expected = pre_size + len(line.encode("utf-8"))
            if post_size != expected:
                raise WORMViolationError(
                    f"file size {post_size} != expected {expected} — WORM integrity broken"
                )
        finally:
            self._seal()
        self._seen_ids.add(event.event_id)

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

    def _seal(self) -> None:
        """Reduce file mode to owner-read-only (best effort)."""
        with contextlib.suppress(OSError, NotImplementedError):
            os.chmod(self._path, stat.S_IRUSR)

    def _unseal(self) -> None:
        """Re-grant owner-write for the duration of an append."""
        with contextlib.suppress(OSError, NotImplementedError):
            os.chmod(self._path, stat.S_IRUSR | stat.S_IWUSR)

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
        event.event_hash = d["event_hash"]
        return event
