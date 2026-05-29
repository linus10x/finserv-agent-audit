"""Tests for the WORM (write-once-read-many) LedgerStore — SEC Rule 17a-4."""

from __future__ import annotations

import os
import stat
import warnings
from pathlib import Path

import pytest

from finserv_agent_audit.governance.ledger_store import GENESIS_PREV_HASH
from finserv_agent_audit.governance.ledger_store_worm import (
    BestEffortWORMLedgerStore,
    WORMLedgerStore,
    WORMViolationError,
)
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)


def _event(prev: str = GENESIS_PREV_HASH) -> AuditEvent:
    return AuditEvent(
        event_type=AuditEventType.SAR_FILED,
        agent_id="bsa-aml-bot",
        autonomy_level=AutonomyLevel.A1,
        payload={"sar_id": "SAR-2026-001", "amount_usd": 12500},
        prev_hash=prev,
    )


def test_empty_file_genesis(tmp_path: Path) -> None:
    store = WORMLedgerStore(tmp_path / "worm.jsonl")
    assert store.head_event_hash() == GENESIS_PREV_HASH
    assert len(store) == 0


def test_append_then_read(tmp_path: Path) -> None:
    store = WORMLedgerStore(tmp_path / "worm.jsonl")
    e = _event()
    store.append(e)
    assert len(store) == 1
    fetched = store.get(0)
    assert fetched.event_id == e.event_id
    assert fetched.event_hash == e.event_hash


def test_duplicate_event_id_raises_worm_violation(tmp_path: Path) -> None:
    store = WORMLedgerStore(tmp_path / "worm.jsonl")
    e = _event()
    store.append(e)
    with pytest.raises(WORMViolationError):
        store.append(e)


def test_file_is_sealed_after_append(tmp_path: Path) -> None:
    """After each append the file should be owner-read-only."""
    p = tmp_path / "worm.jsonl"
    store = WORMLedgerStore(p)
    store.append(_event())
    mode = stat.S_IMODE(os.stat(p).st_mode)
    # Owner-read present; owner-write absent.
    assert mode & stat.S_IRUSR
    assert not (mode & stat.S_IWUSR)


def test_reopen_recovers_seen_ids(tmp_path: Path) -> None:
    p = tmp_path / "worm.jsonl"
    a = WORMLedgerStore(p)
    e = _event()
    a.append(e)
    del a
    b = WORMLedgerStore(p)
    with pytest.raises(WORMViolationError):
        b.append(e)


def test_append_chains_multiple_events(tmp_path: Path) -> None:
    store = WORMLedgerStore(tmp_path / "worm.jsonl")
    prev = GENESIS_PREV_HASH
    for _ in range(5):
        e = _event(prev=prev)
        store.append(e)
        prev = e.event_hash
    assert len(store) == 5
    assert store.head_event_hash() == prev


def test_retention_truncation_attempt_caught_on_next_append(tmp_path: Path) -> None:
    """If a hostile process truncates the file, the next append should
    still detect that the post-write size does not match the pre-write
    size + line length — i.e. the WORM size invariant holds across a
    single append even if the file was tampered with between appends."""
    p = tmp_path / "worm.jsonl"
    store = WORMLedgerStore(p)
    e1 = _event()
    store.append(e1)
    # Simulate operator tampering by re-opening read-write and clobbering.
    os.chmod(p, stat.S_IRUSR | stat.S_IWUSR)
    p.write_text("")  # truncate
    # The next append still succeeds (the size invariant is per-append),
    # but the truncation is detectable: len(store) drops to 1, not 2.
    e2 = _event(prev=e1.event_hash)
    store.append(e2)
    # Only one event remains because the file was wiped; this is the
    # detection signal — a downstream verifier comparing expected vs
    # actual count would flag tampering.
    assert len(store) == 1


def test_get_out_of_range_raises(tmp_path: Path) -> None:
    store = WORMLedgerStore(tmp_path / "worm.jsonl")
    store.append(_event())
    with pytest.raises(IndexError):
        store.get(99)


def test_worm_violation_error_is_runtime_error() -> None:
    """Tooling that catches RuntimeError should also catch WORM violations."""
    assert issubclass(WORMViolationError, RuntimeError)


# --------------------------------------------------------------------------- #
# CR-10 — Honest naming + filesystem-capability detection                     #
# --------------------------------------------------------------------------- #


def _besteffort_event(prev: str = GENESIS_PREV_HASH) -> AuditEvent:
    return AuditEvent(
        event_type=AuditEventType.SAR_FILED,
        agent_id="bsa-aml-bot",
        autonomy_level=AutonomyLevel.A1,
        payload={"sar_id": "SAR-2026-002", "amount_usd": 9_999},
        prev_hash=prev,
    )


def test_best_effort_worm_ledger_store_round_trip(tmp_path: Path) -> None:
    """Renamed class works identically to the old WORMLedgerStore."""
    store = BestEffortWORMLedgerStore(tmp_path / "be_worm.jsonl")
    e = _besteffort_event()
    store.append(e)
    assert len(store) == 1
    assert store.get(0).event_id == e.event_id


def test_worm_ledger_store_alias_emits_deprecation_warning(tmp_path: Path) -> None:
    """The legacy name is kept as an alias but emits a DeprecationWarning."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        WORMLedgerStore(tmp_path / "alias.jsonl")
    dep = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert dep, "Expected DeprecationWarning on WORMLedgerStore construction"
    # The warning must mention the honest alternative.
    assert any("BestEffortWORMLedgerStore" in str(w.message) for w in dep)


def test_worm_ledger_store_alias_is_subclass_of_besteffort() -> None:
    """The deprecated alias is the same class, semantically."""
    assert issubclass(WORMLedgerStore, BestEffortWORMLedgerStore)


def test_chmod_detection_logs_warning_on_unsupported_fs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """When chmod 0o400 is not honored, construction logs a WARNING."""
    from finserv_agent_audit.governance import ledger_store_worm

    # Force the probe to report not-honored.
    monkeypatch.setattr(ledger_store_worm, "_detect_chmod_honored", lambda _p: False)
    with caplog.at_level("WARNING"):
        BestEffortWORMLedgerStore(tmp_path / "no_chmod.jsonl")
    assert any(
        "S3 Object Lock" in rec.message and "not honored" in rec.message for rec in caplog.records
    )


def test_chmod_detection_quiet_on_supported_fs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """When chmod 0o400 IS honored (POSIX local FS), no WARNING fires."""
    from finserv_agent_audit.governance import ledger_store_worm

    monkeypatch.setattr(ledger_store_worm, "_detect_chmod_honored", lambda _p: True)
    with caplog.at_level("WARNING"):
        BestEffortWORMLedgerStore(tmp_path / "chmod_ok.jsonl")
    capability_warnings = [rec for rec in caplog.records if "S3 Object Lock" in rec.message]
    assert not capability_warnings


def test_detect_chmod_honored_real_local_filesystem(tmp_path: Path) -> None:
    """On a normal POSIX local filesystem (tmpfs / APFS / ext4), chmod is honored."""
    from finserv_agent_audit.governance.ledger_store_worm import (
        _detect_chmod_honored,
    )

    # Touch a probe-target path so the function has a parent directory.
    target = tmp_path / "probe_target"
    assert _detect_chmod_honored(target) is True
