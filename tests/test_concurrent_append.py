"""CR-4 regression — concurrent ``AuditChain.append`` and ``JsonlLedgerStore.append``.

These tests fail on the pre-fix code because:

  1. ``AuditChain.append`` reads ``self._store.head_event_hash()``,
     constructs an event with that ``prev_hash``, then calls
     ``self._store.append(event)``. Two threads racing through this
     window both observe the same head, both construct events with the
     same ``prev_hash``, and the chain forks silently — ``verify()``
     returns False on at least one branch.

  2. ``JsonlLedgerStore.append`` writes to the JSONL file without an
     advisory lock. Two concurrent writers (separate processes) can
     interleave bytes within a single line, corrupting JSON parse.

  3. Concurrent readers + writers can hit ``RuntimeError: dictionary
     changed size during iteration`` (or list-equivalent) when
     ``verify()`` walks the store while another thread appends.

TDD discipline: these tests live alongside the fix in
``governance/audit_chain.py`` (RLock) and
``governance/ledger_store_jsonl.py`` (``fcntl.flock``). On Windows the
``fcntl`` paths skip — see the per-test ``skipif`` marker.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import sys
import threading
from pathlib import Path

import pytest

from finserv_agent_audit.governance.audit_chain import AuditChain
from finserv_agent_audit.governance.ledger_store_jsonl import JsonlLedgerStore
from finserv_agent_audit.schemas.audit_event import (
    AuditEventType,
    AutonomyLevel,
)

# --------------------------------------------------------------------------- #
# Test 1 — thread-safe AuditChain.append                                      #
# --------------------------------------------------------------------------- #


class TestThreadSafeAppend:
    """16 threads x 50 events each must produce exactly 800 events.

    Without the RLock fix two threads both read the same head_event_hash,
    both call ``AuditEvent.create(prev_hash=head, ...)``, and both call
    ``store.append(event)`` — the chain forks silently and ``verify()``
    fails on the second branch.
    """

    def test_concurrent_append_no_fork(self, tmp_path: Path) -> None:
        # Use legacy-mode (no deployer_id) so ``AuditChain.verify()``
        # walks from the legacy ``GENESIS_HASH`` sentinel. The
        # deployer-keyed genesis path is exercised in
        # ``test_concurrent_append_no_fork_with_deployer_id`` below
        # via direct chain-link checking.
        chain = AuditChain(log_file=tmp_path / "concurrent.jsonl")

        num_threads = 16
        events_per_thread = 50

        def worker(thread_id: int) -> None:
            for i in range(events_per_thread):
                chain.append(
                    event_type=AuditEventType.DECISION_MADE,
                    autonomy_level=AutonomyLevel.A2,
                    agent_id=f"agent-{thread_id}",
                    payload={"thread_id": thread_id, "seq": i},
                )

        threads = [threading.Thread(target=worker, args=(tid,)) for tid in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Legacy mode: no genesis event #0 is prepended, so we expect
        # exactly num_threads * events_per_thread events. No silent fork.
        expected = num_threads * events_per_thread
        assert len(chain._events) == expected, (
            f"Expected {expected} events ({num_threads} threads x "
            f"{events_per_thread}); got {len(chain._events)} — "
            "indicates dropped writes or a forked chain"
        )
        # And the chain must verify end-to-end.
        assert chain.verify(), (
            "Chain failed verify() after concurrent append — "
            "likely a silent fork caused by TOCTOU on head_event_hash"
        )

    def test_concurrent_append_no_fork_with_deployer_id(self, tmp_path: Path) -> None:
        """Same race, exercised under the deployer-keyed genesis path.

        ``verify()`` walks from the legacy GENESIS_HASH sentinel and
        will not handle a deployer-keyed genesis event. We instead
        check chain integrity directly by walking the prev_hash
        links from event #0 (the genesis) through every appended
        event — equivalent contract to ``verify()`` for this case.
        """
        chain = AuditChain(
            log_file=tmp_path / "concurrent_deployer.jsonl",
            deployer_id="test-deployer-concurrent",
            chain_creation_iso="2026-05-28T00:00:00+00:00",
        )

        num_threads = 16
        events_per_thread = 50

        def worker(thread_id: int) -> None:
            for i in range(events_per_thread):
                chain.append(
                    event_type=AuditEventType.DECISION_MADE,
                    autonomy_level=AutonomyLevel.A2,
                    agent_id=f"agent-{thread_id}",
                    payload={"thread_id": thread_id, "seq": i},
                )

        threads = [threading.Thread(target=worker, args=(tid,)) for tid in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 1 genesis + 16 * 50 = 801 events. No silent fork.
        expected = 1 + num_threads * events_per_thread
        assert len(chain._events) == expected, (
            f"Expected {expected} events (genesis + "
            f"{num_threads} threads x {events_per_thread}); "
            f"got {len(chain._events)} — indicates dropped writes "
            "or a forked chain"
        )

        # Walk the chain links manually: every event must (a) re-hash
        # to its stored event_hash and (b) its prev_hash must equal
        # the previous event's event_hash. The genesis event seeds
        # from the deployer-keyed prev_hash, not from GENESIS_HASH.
        events = chain._events
        prev = events[0].prev_hash  # the deployer-keyed seed
        for index, event in enumerate(events):
            assert event.event_hash == event._compute_hash(), (
                f"event_hash mismatch at index {index} (event_id={event.event_id!r})"
            )
            assert event.prev_hash == prev, (
                f"prev_hash mismatch at index {index} "
                f"(event_id={event.event_id!r}): "
                f"expected {prev!r}, got {event.prev_hash!r} — "
                "indicates a forked chain from concurrent append"
            )
            prev = event.event_hash


# --------------------------------------------------------------------------- #
# Test 2 — per-file lock for JsonlLedgerStore (multi-process)                 #
# --------------------------------------------------------------------------- #


def _mp_writer(args: tuple[str, int, int]) -> None:
    """Worker for the multi-process test (module-level so pickle works).

    Each process writes pre-built events directly to a shared
    ``JsonlLedgerStore`` — we exercise the ``fcntl.flock(LOCK_EX)``
    critical section, not chain semantics (which would require a
    cross-process append lock that ``fcntl`` cannot provide on its own
    for the prev_hash read-then-write sequence). The chain-link
    integrity under multi-process writers is a *deployer concern*,
    documented in the JsonlLedgerStore module docstring; this test
    only proves that the file-write region is line-atomic.
    """
    path_str, proc_id, count = args

    from finserv_agent_audit.governance.ledger_store import GENESIS_PREV_HASH
    from finserv_agent_audit.governance.ledger_store_jsonl import (
        JsonlLedgerStore,
    )
    from finserv_agent_audit.schemas.audit_event import AuditEvent

    store = JsonlLedgerStore(Path(path_str))
    for i in range(count):
        evt = AuditEvent.create(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id=f"proc-{proc_id}",
            payload={
                "proc_id": proc_id,
                "seq": i,
                # Large filler so each event spans multiple write
                # syscalls — increases the byte-interleaving window
                # without the fcntl lock.
                "filler": "x" * 500,
            },
            prev_hash=GENESIS_PREV_HASH,
            event_id=f"proc-{proc_id:02d}-evt-{i:06d}",
            timestamp="2026-05-28T00:00:00+00:00",
        )
        store.append(evt)


class TestMultiProcessAppend:
    """4 processes x 100 events each must produce 400 well-formed JSONL lines.

    Without ``fcntl.flock`` two processes can interleave bytes within a
    single ``fh.write()`` (Python's buffered I/O issues multiple
    syscalls under the hood; even O_APPEND atomicity at the kernel
    level doesn't guarantee atomicity across multiple writes).
    """

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="fcntl-based file locking is POSIX-only; Windows uses msvcrt.locking",
    )
    def test_multi_process_append_no_byte_interleaving(self, tmp_path: Path) -> None:
        log_file = tmp_path / "mp_concurrent.jsonl"

        num_procs = 4
        events_per_proc = 100

        ctx = mp.get_context("spawn")
        with ctx.Pool(num_procs) as pool:
            pool.map(
                _mp_writer,
                [(str(log_file), pid, events_per_proc) for pid in range(num_procs)],
            )

        # Each line must be valid JSON. If two processes interleaved
        # bytes within a single line the JSON parse fails.
        lines = log_file.read_text(encoding="utf-8").splitlines()
        nonblank = [ln for ln in lines if ln.strip()]
        parsed = []
        for ln in nonblank:
            # If bytes interleaved within a line this raises.
            parsed.append(json.loads(ln))

        # 4 processes * 100 events = 400 total lines
        expected = num_procs * events_per_proc
        assert len(parsed) == expected, (
            f"Expected {expected} JSONL lines "
            f"({num_procs} processes x {events_per_proc} events); "
            f"got {len(parsed)} — indicates dropped writes or "
            "lock contention"
        )

        # Each event_id must be unique — proves we got all rows
        # without truncation. (Hashes coincide here because all
        # processes used GENESIS_PREV_HASH as prev_hash; the
        # event_id differs per process+seq.)
        event_ids = [ev["event_id"] for ev in parsed]
        assert len(set(event_ids)) == len(event_ids), (
            "Duplicate event_id detected — indicates a write got lost or corrupted"
        )


# --------------------------------------------------------------------------- #
# Test 3 — concurrent verify + append must not raise mid-iteration            #
# --------------------------------------------------------------------------- #


class TestConcurrentVerifyAndAppend:
    """8 threads appending while a verifier thread walks the chain.

    Without synchronization the verifier hits ``RuntimeError: list
    modified during iteration`` (Python's list iterator) or returns
    a stale-tail False positive. With the RLock the verifier holds
    the lock for the duration of the walk and sees a consistent
    snapshot.
    """

    def test_concurrent_verify_and_append(self, tmp_path: Path) -> None:
        # Legacy mode so ``verify()`` walks from GENESIS_HASH.
        chain = AuditChain(log_file=tmp_path / "verify_concurrent.jsonl")

        # Seed with some events so verify has something to walk.
        for i in range(10):
            chain.append(
                event_type=AuditEventType.DECISION_MADE,
                autonomy_level=AutonomyLevel.A2,
                agent_id="seed-agent",
                payload={"seq": i},
            )

        stop_flag = threading.Event()
        errors: list[BaseException] = []
        verify_results: list[bool] = []

        def appender(tid: int) -> None:
            try:
                for i in range(50):
                    if stop_flag.is_set():
                        break
                    chain.append(
                        event_type=AuditEventType.DECISION_MADE,
                        autonomy_level=AutonomyLevel.A2,
                        agent_id=f"appender-{tid}",
                        payload={"tid": tid, "seq": i},
                    )
            except BaseException as e:  # noqa: BLE001 - we re-raise via collected list
                errors.append(e)

        def verifier() -> None:
            try:
                for _ in range(20):
                    if stop_flag.is_set():
                        break
                    verify_results.append(chain.verify())
            except BaseException as e:  # noqa: BLE001 - we re-raise via collected list
                errors.append(e)

        appender_threads = [threading.Thread(target=appender, args=(tid,)) for tid in range(8)]
        verifier_thread = threading.Thread(target=verifier)

        for t in appender_threads:
            t.start()
        verifier_thread.start()

        for t in appender_threads:
            t.join()
        stop_flag.set()
        verifier_thread.join()

        # No "list modified during iteration" or similar runtime errors.
        assert not errors, f"Got runtime errors during concurrent verify+append: {errors!r}"

        # Every verify call must have returned True — no false-positive
        # tamper detection from a stale-tail walk.
        assert all(verify_results), (
            f"verify() returned False during concurrent append: "
            f"{verify_results!r} — indicates the walk read a partially "
            "appended state"
        )

        # Final chain must verify cleanly.
        assert chain.verify()


# --------------------------------------------------------------------------- #
# Direct JsonlLedgerStore.append concurrency — single-process threads         #
# --------------------------------------------------------------------------- #


class TestJsonlLedgerStoreThreadAppend:
    """Direct concurrent appends to a single JsonlLedgerStore from threads.

    Even within one process, two threads racing through ``open(...)`` +
    ``f.write(...)`` can interleave bytes. The fcntl LOCK_EX serializes
    the append region.
    """

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="fcntl-based file locking is POSIX-only",
    )
    def test_threaded_jsonl_append_well_formed(self, tmp_path: Path) -> None:
        # Build a free-standing store (no chain wrapping) and append
        # pre-constructed events from multiple threads. We exercise
        # the file-write critical section, not the chain logic.
        store = JsonlLedgerStore(tmp_path / "store_threaded.jsonl")

        # Pre-build 100 unique events sharing a common genesis prev_hash.
        # (We are NOT testing chain integrity here — only that the file
        # lock keeps lines well-formed.)
        from finserv_agent_audit.governance.ledger_store import GENESIS_PREV_HASH
        from finserv_agent_audit.schemas.audit_event import AuditEvent

        events = [
            AuditEvent.create(
                event_type=AuditEventType.DECISION_MADE,
                autonomy_level=AutonomyLevel.A2,
                agent_id=f"agent-{i}",
                # large enough to span multiple write syscalls
                payload={"seq": i, "filler": "x" * 200},
                prev_hash=GENESIS_PREV_HASH,
                event_id=f"evt-{i:06d}",
                timestamp="2026-05-28T00:00:00+00:00",
            )
            for i in range(400)
        ]

        def worker(start: int, stop: int) -> None:
            for i in range(start, stop):
                store.append(events[i])

        threads = [threading.Thread(target=worker, args=(i * 100, (i + 1) * 100)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        lines = (tmp_path / "store_threaded.jsonl").read_text(encoding="utf-8").splitlines()
        nonblank = [ln for ln in lines if ln.strip()]
        assert len(nonblank) == 400, (
            f"Expected 400 lines, got {len(nonblank)} — possible dropped writes"
        )
        # Every line must parse — no byte interleaving.
        for ln in nonblank:
            parsed = json.loads(ln)
            assert "event_hash" in parsed
