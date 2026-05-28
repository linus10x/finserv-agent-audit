"""Tests for TimestampSource Protocol + LocalClock + RFC3161Source."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime

import pytest

from finserv_agent_audit.governance.timestamp_source import (
    LocalClock,
    RFC3161Source,
    TimestampSource,
    TrustedTimestamp,
)


def test_local_clock_returns_now() -> None:
    src: TimestampSource = LocalClock()
    before = datetime.now(UTC)
    ts = src.stamp(b"any-digest")
    after = datetime.now(UTC)
    assert before <= ts.asserted_at <= after
    assert ts.tsa_url is None
    assert ts.tsr_token_b64 is None
    assert ts.hash_algorithm == "sha256"


def test_trusted_timestamp_is_frozen() -> None:
    ts = TrustedTimestamp(
        asserted_at=datetime(2026, 5, 28, tzinfo=UTC),
        tsa_url=None,
        tsr_token_b64=None,
    )
    assert dataclasses.is_dataclass(ts)
    with pytest.raises(dataclasses.FrozenInstanceError):
        ts.tsa_url = "x"  # type: ignore[misc]


def test_rfc3161_source_falls_back_to_local_on_unreachable_host() -> None:
    callbacks: list[Exception] = []
    src = RFC3161Source(
        tsa_url="https://invalid.example.test.invalid./tsr",
        timeout_s=0.5,
        fallback_to_local_on_failure=True,
        on_fallback=callbacks.append,
    )
    before = datetime.now(UTC)
    ts = src.stamp(b"x" * 32)
    after = datetime.now(UTC)
    # Fallback path: local-clock-style result.
    assert ts.tsa_url is None
    assert ts.tsr_token_b64 is None
    assert before <= ts.asserted_at <= after
    assert len(callbacks) == 1


def test_rfc3161_source_raises_when_fallback_disabled() -> None:
    src = RFC3161Source(
        tsa_url="https://invalid.example.test.invalid./tsr",
        timeout_s=0.5,
        fallback_to_local_on_failure=False,
    )
    # Network failure surfaces as one of socket.gaierror, OSError, or
    # urllib.error.URLError — all OSError subclasses on CPython 3.10+.
    with pytest.raises(OSError):  # noqa: PT011
        src.stamp(b"x" * 32)


def test_rfc3161_source_rejects_unsupported_scheme() -> None:
    src = RFC3161Source(tsa_url="ftp://example/tsr", fallback_to_local_on_failure=False)
    with pytest.raises(ValueError):
        src.stamp(b"x" * 32)
