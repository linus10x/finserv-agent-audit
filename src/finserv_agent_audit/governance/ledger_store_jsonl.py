"""Append-only JSONL LedgerStore — ADR-0012 § Persistence backends.

One JSON object per line. Survives crash mid-write only if `fsync=True`
(the default). For higher durability — e.g. firm-wide model inventory
records under SR 11-7 or customer NPI under GLBA Safeguards — deployers
should use an external append-only object store (S3 + Object Lock with
a retention period) and write a custom backend implementing
`LedgerStore` against the same Protocol.

CR-4 — concurrent ``append`` calls are serialized two ways:

  1. An in-process ``threading.Lock`` (``self._write_lock``)
     prevents two threads in the same Python process from racing
     through the open/write/flush/fsync critical section.

  2. Across processes, an advisory ``fcntl.flock(LOCK_EX)`` is
     taken on the open fd for the duration of the write. Python's
     buffered ``f.write()`` may emit multiple syscalls under the
     hood, so the kernel's O_APPEND atomicity for a single
     ``write(2)`` is not sufficient on its own.

``fcntl`` is POSIX-only. On Windows (``sys.platform == "win32"``)
the module is unavailable and we fall back to the in-process Lock
alone — a deployer who runs multi-process writers on Windows
should use ``msvcrt.locking`` or constrain the writer to a single
process. The platform-detect path is documented and lint-clean.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from collections.abc import Iterator
from pathlib import Path

from finserv_agent_audit.governance.ledger_store import GENESIS_PREV_HASH
from finserv_agent_audit.schemas.audit_event import AuditEvent

# CR-4 — POSIX-only file-lock import. On Windows ``fcntl`` is
# unavailable; we fall back to the in-process threading.Lock and
# leave the cross-process race documented as a Windows caveat.
if sys.platform != "win32":
    import fcntl
else:  # pragma: no cover - exercised on Windows hosts only
    fcntl = None  # type: ignore[assignment]


class JsonlLedgerStore:
    """JSONL file-backed `LedgerStore`."""

    def __init__(self, path: Path | str, *, fsync: bool = True) -> None:
        self._path = Path(path)
        self._fsync = fsync
        self._path.touch(exist_ok=True)
        # CR-4 — in-process critical section guard. Cross-process is
        # handled per-append by ``fcntl.flock(LOCK_EX)``.
        self._write_lock = threading.Lock()

    def append(self, event: AuditEvent) -> None:
        line = json.dumps(event.to_dict(), sort_keys=True, separators=(",", ":")) + "\n"
        # CR-4 — in-process Lock keeps two threads in the same
        # process from interleaving syscalls. Cross-process is
        # serialized by ``fcntl.flock`` (POSIX only; see module
        # docstring for the Windows caveat).
        with self._write_lock, open(self._path, "a", encoding="utf-8") as f:
            if fcntl is not None:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(line)
                f.flush()
                if self._fsync:
                    os.fsync(f.fileno())
            finally:
                if fcntl is not None:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

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
        # CR-2 — ``from_jsonl`` recomputes the hash and raises
        # ``AuditChainTamperError`` when the stored ``event_hash``
        # disagrees with the reconstructed fields. The store is now
        # self-verifying on read, not only on explicit chain replay.
        d = json.loads(line)
        return AuditEvent.from_jsonl(d)
