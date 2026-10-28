"""Tests for the DeprecationWatch primitive (ADR-0025).

Covers vendor changelog registration, parser plug-in (Protocol), alert
emission when a sunset date falls within `alert_window_days`, HTTP
failure handling (logs and continues), and the no-deprecation happy
path. The audit-chain emission test is load-bearing: a registered
vendor with a sunset inside the window MUST emit a
`DEPRECATION_ALERT` chain entry.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from finserv_agent_audit.governance.deprecation_watch import (
    DeprecationAnnouncement,
    DeprecationWatch,
)
from finserv_agent_audit.governance.ledger_store import InMemoryLedgerStore
from finserv_agent_audit.schemas.audit_event import AuditEventType


@pytest.fixture
def now() -> datetime:
    return datetime.now(UTC)


@pytest.fixture
def store() -> InMemoryLedgerStore:
    return InMemoryLedgerStore()


def _http_get_returning(payload: str) -> object:
    """Build a fake http_get callable that returns the same payload."""

    def fake(url: str, *, timeout: float = 10.0) -> str:
        return payload

    return fake


def _http_get_failing() -> object:
    """Build a fake http_get that always raises."""

    def fake(url: str, *, timeout: float = 10.0) -> str:
        raise OSError("network down")

    return fake


# --------------------------------------------------------------------------- #
# Register                                                                    #
# --------------------------------------------------------------------------- #


class TestRegisterVendor:
    def test_register_persists_vendor(self, store: InMemoryLedgerStore) -> None:
        watch = DeprecationWatch(ledger_store=store, http_get=_http_get_returning(""))

        def parser(_: str) -> list[DeprecationAnnouncement]:
            return []

        watch.register_vendor(
            vendor_id="openai",
            changelog_url="https://platform.openai.com/docs/deprecations",
            parser=parser,
        )
        # Verifying registration via the public surface — `check()` runs
        # against registered vendors only.
        assert watch.check(now=datetime.now(UTC)) == []

    def test_register_duplicate_raises(self, store: InMemoryLedgerStore) -> None:
        watch = DeprecationWatch(ledger_store=store, http_get=_http_get_returning(""))

        def parser(_: str) -> list[DeprecationAnnouncement]:
            return []

        watch.register_vendor(vendor_id="openai", changelog_url="https://x", parser=parser)
        with pytest.raises(ValueError, match="already registered"):
            watch.register_vendor(vendor_id="openai", changelog_url="https://y", parser=parser)


# --------------------------------------------------------------------------- #
# Check — happy paths                                                         #
# --------------------------------------------------------------------------- #


class TestCheckNoAlerts:
    def test_check_no_announcements_emits_nothing(
        self, store: InMemoryLedgerStore, now: datetime
    ) -> None:
        watch = DeprecationWatch(ledger_store=store, http_get=_http_get_returning("{}"))

        def parser(_: str) -> list[DeprecationAnnouncement]:
            return []

        watch.register_vendor(vendor_id="openai", changelog_url="https://x", parser=parser)
        alerts = watch.check(now=now)
        assert alerts == []
        assert list(store) == []

    def test_check_sunset_outside_window_emits_nothing(
        self, store: InMemoryLedgerStore, now: datetime
    ) -> None:
        sunset_far_off = now + timedelta(days=180)
        ann = DeprecationAnnouncement(
            vendor_id="openai",
            model_id="o1-preview",
            sunset_date=sunset_far_off,
            deprecation_date=now,
            replacement_model_id="o1",
            source_url="https://x",
        )
        watch = DeprecationWatch(ledger_store=store, http_get=_http_get_returning("payload"))

        def parser(_: str) -> list[DeprecationAnnouncement]:
            return [ann]

        watch.register_vendor(vendor_id="openai", changelog_url="https://x", parser=parser)
        # Default alert window is 60 days; sunset is 180 days out.
        alerts = watch.check(now=now)
        assert alerts == []


# --------------------------------------------------------------------------- #
# Check — alert emission                                                      #
# --------------------------------------------------------------------------- #


class TestCheckAlertEmission:
    def test_sunset_inside_window_emits_alert(
        self, store: InMemoryLedgerStore, now: datetime
    ) -> None:
        sunset_soon = now + timedelta(days=30)
        ann = DeprecationAnnouncement(
            vendor_id="openai",
            model_id="o1-preview",
            sunset_date=sunset_soon,
            deprecation_date=now,
            replacement_model_id="o1",
            source_url="https://platform.openai.com/docs/deprecations",
        )
        watch = DeprecationWatch(ledger_store=store, http_get=_http_get_returning("payload"))

        def parser(_: str) -> list[DeprecationAnnouncement]:
            return [ann]

        watch.register_vendor(vendor_id="openai", changelog_url="https://x", parser=parser)
        alerts = watch.check(now=now, alert_window_days=60)
        assert len(alerts) == 1
        assert alerts[0].model_id == "o1-preview"

        events = list(store)
        assert len(events) == 1
        event = events[0]
        assert event.event_type == AuditEventType.DEPRECATION_ALERT
        assert event.payload["vendor_id"] == "openai"
        assert event.payload["model_id"] == "o1-preview"
        assert event.payload["replacement_model_id"] == "o1"
        assert "days_until_sunset" in event.payload

    def test_sunset_already_past_still_emits(
        self, store: InMemoryLedgerStore, now: datetime
    ) -> None:
        # If a model was already sunset (the bank missed it), the watch
        # should still surface it loudly.
        ann = DeprecationAnnouncement(
            vendor_id="novita",
            model_id="some-model",
            sunset_date=now - timedelta(days=5),
            deprecation_date=now - timedelta(days=19),
            replacement_model_id=None,
            source_url="https://novita",
        )
        watch = DeprecationWatch(ledger_store=store, http_get=_http_get_returning("payload"))

        def parser(_: str) -> list[DeprecationAnnouncement]:
            return [ann]

        watch.register_vendor(vendor_id="novita", changelog_url="https://x", parser=parser)
        alerts = watch.check(now=now)
        assert len(alerts) == 1
        assert alerts[0].sunset_date < now

    def test_check_without_ledger_store_still_returns_alerts(self, now: datetime) -> None:
        ann = DeprecationAnnouncement(
            vendor_id="anthropic",
            model_id="claude-3.7-sonnet",
            sunset_date=now + timedelta(days=14),
            deprecation_date=now - timedelta(days=180),
            replacement_model_id="claude-4-sonnet",
            source_url="https://x",
        )
        watch = DeprecationWatch(http_get=_http_get_returning("p"))

        def parser(_: str) -> list[DeprecationAnnouncement]:
            return [ann]

        watch.register_vendor(vendor_id="anthropic", changelog_url="https://x", parser=parser)
        alerts = watch.check(now=now)
        assert len(alerts) == 1


# --------------------------------------------------------------------------- #
# Check — failure modes                                                       #
# --------------------------------------------------------------------------- #


class TestCheckFailureModes:
    def test_http_failure_does_not_raise(self, store: InMemoryLedgerStore, now: datetime) -> None:
        watch = DeprecationWatch(ledger_store=store, http_get=_http_get_failing())

        def parser(_: str) -> list[DeprecationAnnouncement]:
            return []

        watch.register_vendor(vendor_id="openai", changelog_url="https://x", parser=parser)
        # The vendor's changelog is unreachable; check() should swallow
        # the error and return an empty alert list for this vendor.
        # Other registered vendors must continue to be polled.
        alerts = watch.check(now=now)
        assert alerts == []

    def test_parser_raising_does_not_block_other_vendors(
        self, store: InMemoryLedgerStore, now: datetime
    ) -> None:
        watch = DeprecationWatch(ledger_store=store, http_get=_http_get_returning("payload"))

        def bad_parser(_: str) -> list[DeprecationAnnouncement]:
            raise ValueError("malformed changelog")

        def good_parser(_: str) -> list[DeprecationAnnouncement]:
            return [
                DeprecationAnnouncement(
                    vendor_id="good_vendor",
                    model_id="m1",
                    sunset_date=now + timedelta(days=10),
                    deprecation_date=now,
                    replacement_model_id="m2",
                    source_url="https://x",
                )
            ]

        watch.register_vendor(vendor_id="bad_vendor", changelog_url="https://x", parser=bad_parser)
        watch.register_vendor(
            vendor_id="good_vendor", changelog_url="https://y", parser=good_parser
        )
        alerts = watch.check(now=now, alert_window_days=60)
        # bad_vendor's parser raised; good_vendor still emitted an alert.
        assert len(alerts) == 1
        assert alerts[0].vendor_id == "good_vendor"


# --------------------------------------------------------------------------- #
# Sanity                                                                      #
# --------------------------------------------------------------------------- #


def test_module_lives_at_documented_path() -> None:
    root = Path(__file__).resolve().parent.parent
    expected = root / "src" / "finserv_agent_audit" / "governance" / "deprecation_watch.py"
    assert expected.is_file()


@pytest.mark.parametrize("bad_url", ["file:///etc/passwd", "ftp://host/x", "gopher://x"])
def test_default_http_get_rejects_non_http_scheme(bad_url: str) -> None:
    # The stdlib urlopen wrapper must refuse non-http(s) schemes before the
    # URL ever reaches urlopen (urllib.request can open file:// / ftp://).
    from finserv_agent_audit.governance.deprecation_watch import _default_http_get

    with pytest.raises(ValueError):
        _default_http_get(bad_url)
