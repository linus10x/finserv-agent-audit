"""Best-effort WORM (write-once-read-many) LedgerStore — ADR-0013.

SEC Rule 17a-4 (17 C.F.R. § 240.17a-4) requires broker-dealers to
preserve certain electronic records in a non-rewriteable, non-erasable
format for prescribed retention periods (commonly 3-6 years, with the
first two years readily accessible). The 2022 SEC amendments
(Release No. 34-96034) modernized the rule to permit electronic
recordkeeping systems that either (a) preserve records in WORM format
or (b) maintain an audit-trail alternative — this backend implements
the former path on a best-effort basis: every appended event is sealed
at the filesystem layer (read-only mode bits) and any attempt to
overwrite a prior line, truncate the file, or rewrite an existing
event raises `WORMViolationError`.

CR-10 honesty note: the chmod-based seal is reversible by any
same-uid process in one syscall, and is silently ignored on FAT,
NFS, SMB/CIFS, S3-FUSE, EFS, and most container overlay filesystems.
The class was renamed from ``WORMLedgerStore`` to
``BestEffortWORMLedgerStore`` so deployers do not mistake the backend
for hardware/cloud-enforced WORM. The legacy name is retained as a
deprecation alias.

For production-grade WORM in the cloud, pair this backend with
S3 Object Lock in COMPLIANCE mode plus an explicit retention period
calibrated to your books-and-records policy, or use AWS QLDB / Azure
Confidential Ledger. This local backend is suitable for tier-2 audit
copies, on-prem deployments, and tests.

Layered architecture: the file format is JSONL (one event per line,
matches `JsonlLedgerStore`), so existing tooling can read a WORM
ledger as an ordinary JSONL ledger. The WORM contract is enforced on
the *write* path.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import stat
from collections.abc import Iterator
from pathlib import Path

from finserv_agent_audit.governance.ledger_store import GENESIS_PREV_HASH
from finserv_agent_audit.schemas.audit_event import AuditEvent

logger = logging.getLogger(__name__)


class WORMViolationError(RuntimeError):
    """Raised when a write would violate the write-once contract."""


def _detect_chmod_honored(path: Path) -> bool:
    """Probe whether the filesystem actually enforces chmod 0o400 on writes.

    Returns True iff a write to a 0o400 probe-file raises
    PermissionError / OSError. Some filesystems (FAT, NFS without
    root-squash, SMB/CIFS, S3-FUSE, EFS, overlay) silently allow the
    write through; in that case this function returns False and the
    BestEffortWORMLedgerStore constructor emits a WARNING naming the
    S3-Object-Lock fallback. The probe file is removed on exit.
    """
    parent = path.parent if path.parent.exists() else Path.cwd()
    probe = parent / f".finserv_chmod_probe.{os.getpid()}"
    try:
        probe.write_text("test", encoding="utf-8")
        try:
            os.chmod(probe, 0o400)
        except (OSError, NotImplementedError):
            return False
        try:
            with open(probe, "a", encoding="utf-8") as fh:
                fh.write("retry")  # should fail if chmod is honored
            # The write succeeded — chmod NOT enforced on this filesystem.
            return False
        except (PermissionError, OSError):
            return True
    finally:
        with contextlib.suppress(OSError, FileNotFoundError):
            os.chmod(probe, 0o600)
            probe.unlink()


class BestEffortWORMLedgerStore:
    """Best-effort write-once-read-many JSONL-format `LedgerStore`.

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
           NFS, SMB, S3-FUSE, EFS, overlay) this is best-effort
           and the constructor logs a WARNING naming the
           S3-Object-Lock fallback (CR-10).
        4. `event_id`s already present in the file are tracked and
           re-appending the same id raises `WORMViolationError`.

    For SEC 17a-4 compliance pair with S3 Object Lock COMPLIANCE mode
    plus a configured retention period, or use AWS QLDB / Azure
    Confidential Ledger.
    """

    def __init__(self, path: Path | str, *, fsync: bool = True) -> None:
        self._path = Path(path)
        self._fsync = fsync
        if not self._path.exists():
            self._path.touch()
            self._seal()
        self._seen_ids: set[str] = {e.event_id for e in self}
        # CR-10: detect whether chmod-based sealing is honored. The probe
        # writes to the parent directory (not the chain file itself) so it
        # does not perturb the chain.
        if not _detect_chmod_honored(self._path):
            logger.warning(
                "chmod-based WORM enforcement is not honored on this "
                "filesystem (%s). The chmod 0o400 seal is advisory only. "
                "Pair with S3 Object Lock COMPLIANCE mode (or AWS QLDB / "
                "Azure Confidential Ledger) for SEC 17a-4 compliance.",
                self._path.parent,
            )

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
        # CR-2 — ``from_jsonl`` recomputes the hash and raises
        # ``AuditChainTamperError`` when the stored ``event_hash``
        # disagrees with the reconstructed fields. Pair this with the
        # WORM file-mode guards above for a defense-in-depth read path.
        d = json.loads(line)
        return AuditEvent.from_jsonl(d)


class WORMLedgerStore(BestEffortWORMLedgerStore):
    """DEPRECATED in CR-10: prefer ``BestEffortWORMLedgerStore`` for clarity.

    The legacy class name implied actual hardware-enforced WORM, which the
    chmod-based seal does not deliver on NFS / SMB / S3-FUSE / EFS / overlay
    filesystems. The honest name is ``BestEffortWORMLedgerStore``; the
    semantics are identical.
    """

    def __init__(self, path: Path | str, *, fsync: bool = True) -> None:
        import warnings

        warnings.warn(
            "WORMLedgerStore is best-effort only (chmod-based; not actual "
            "WORM on NFS / SMB / S3-FUSE / EFS / overlay filesystems). Use "
            "BestEffortWORMLedgerStore for the same semantics with an honest "
            "name. For SEC 17a-4 compliance, pair with S3 Object Lock "
            "COMPLIANCE mode or AWS QLDB / Azure Confidential Ledger.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(path, fsync=fsync)


__all__ = [
    "BestEffortWORMLedgerStore",
    "WORMLedgerStore",
    "WORMViolationError",
]
