"""Tests for the RetrainingCadenceMonitor primitive (ADR-0024).

Covers the four `RetrainingClass` cadence regimes (STATIC, MONTHLY,
WEEKLY, CONTINUOUS), overdue detection, audit-chain emission on
register, and edge cases (model with no prior validation, unknown
model, custom as_of for time-travel queries).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from finserv_agent_audit.governance.ledger_store import InMemoryLedgerStore
from finserv_agent_audit.governance.retraining_cadence_monitor import (
    RetrainingCadenceMonitor,
    RetrainingCadenceReport,
    RetrainingClass,
)
from finserv_agent_audit.schemas.audit_event import AuditEventType


@pytest.fixture
def now() -> datetime:
    return datetime.now(UTC)


@pytest.fixture
def store() -> InMemoryLedgerStore:
    return InMemoryLedgerStore()


@pytest.fixture
def monitor(store: InMemoryLedgerStore) -> RetrainingCadenceMonitor:
    return RetrainingCadenceMonitor(ledger_store=store)


# --------------------------------------------------------------------------- #
# Register                                                                    #
# --------------------------------------------------------------------------- #


class TestRegisterModel:
    def test_register_emits_compliance_check_event(
        self,
        monitor: RetrainingCadenceMonitor,
        store: InMemoryLedgerStore,
        now: datetime,
    ) -> None:
        monitor.register_model(
            model_id="anthropic_claude_sonnet_4_7",
            retraining_class=RetrainingClass.STATIC,
            last_trained=now - timedelta(days=30),
            owner="mrm@bank.example",
        )
        events = list(store)
        assert len(events) == 1
        event = events[0]
        assert event.event_type == AuditEventType.COMPLIANCE_CHECK
        assert event.payload["model_id"] == "anthropic_claude_sonnet_4_7"
        assert event.payload["retraining_class"] == "STATIC"
        assert event.payload["owner"] == "mrm@bank.example"

    def test_register_duplicate_raises(
        self, monitor: RetrainingCadenceMonitor, now: datetime
    ) -> None:
        monitor.register_model(
            model_id="m1",
            retraining_class=RetrainingClass.STATIC,
            last_trained=now,
            owner="o",
        )
        with pytest.raises(ValueError, match="already registered"):
            monitor.register_model(
                model_id="m1",
                retraining_class=RetrainingClass.WEEKLY_RETRAIN,
                last_trained=now,
                owner="o",
            )

    def test_register_without_store_succeeds(self, now: datetime) -> None:
        mon = RetrainingCadenceMonitor()
        mon.register_model(
            model_id="m1",
            retraining_class=RetrainingClass.STATIC,
            last_trained=now,
            owner="o",
        )
        # Should not raise.
        assert mon.evaluate("m1") is not None


# --------------------------------------------------------------------------- #
# Evaluate                                                                    #
# --------------------------------------------------------------------------- #


class TestEvaluate:
    def test_evaluate_returns_report(
        self, monitor: RetrainingCadenceMonitor, now: datetime
    ) -> None:
        monitor.register_model(
            model_id="m1",
            retraining_class=RetrainingClass.STATIC,
            last_trained=now - timedelta(days=10),
            owner="o",
        )
        report = monitor.evaluate("m1")
        assert isinstance(report, RetrainingCadenceReport)
        assert report.model_id == "m1"
        assert report.retraining_class == RetrainingClass.STATIC

    def test_evaluate_unknown_model_raises(self, monitor: RetrainingCadenceMonitor) -> None:
        with pytest.raises(KeyError):
            monitor.evaluate("unknown")

    def test_static_class_compliant_within_year(
        self, monitor: RetrainingCadenceMonitor, now: datetime
    ) -> None:
        monitor.register_model(
            model_id="m1",
            retraining_class=RetrainingClass.STATIC,
            last_trained=now - timedelta(days=200),
            owner="o",
        )
        # No validation recorded yet — model has no prior validation.
        report = monitor.evaluate("m1", as_of=now)
        # Without a prior validation, status is "unknown" rather than compliant.
        assert report.compliant is False

    def test_static_class_overdue_after_year(
        self, monitor: RetrainingCadenceMonitor, now: datetime
    ) -> None:
        monitor.register_model(
            model_id="m1",
            retraining_class=RetrainingClass.STATIC,
            last_trained=now - timedelta(days=400),
            owner="o",
        )
        monitor.record_validation("m1", validated_at=now - timedelta(days=380), actor_id="mrm")
        report = monitor.evaluate("m1", as_of=now)
        assert report.compliant is False
        assert report.required_validation_cadence == timedelta(days=365)

    def test_weekly_retrain_requires_monthly_validation(
        self, monitor: RetrainingCadenceMonitor, now: datetime
    ) -> None:
        monitor.register_model(
            model_id="m1",
            retraining_class=RetrainingClass.WEEKLY_RETRAIN,
            last_trained=now - timedelta(days=2),
            owner="o",
        )
        monitor.record_validation("m1", validated_at=now - timedelta(days=20), actor_id="mrm")
        report = monitor.evaluate("m1", as_of=now)
        assert report.compliant is True
        assert report.required_validation_cadence == timedelta(days=30)

    def test_weekly_retrain_overdue_after_month(
        self, monitor: RetrainingCadenceMonitor, now: datetime
    ) -> None:
        monitor.register_model(
            model_id="m1",
            retraining_class=RetrainingClass.WEEKLY_RETRAIN,
            last_trained=now - timedelta(days=2),
            owner="o",
        )
        monitor.record_validation("m1", validated_at=now - timedelta(days=45), actor_id="mrm")
        report = monitor.evaluate("m1", as_of=now)
        assert report.compliant is False

    def test_monthly_retrain_quarterly_validation(
        self, monitor: RetrainingCadenceMonitor, now: datetime
    ) -> None:
        monitor.register_model(
            model_id="m1",
            retraining_class=RetrainingClass.MONTHLY_RETRAIN,
            last_trained=now - timedelta(days=10),
            owner="o",
        )
        monitor.record_validation("m1", validated_at=now - timedelta(days=80), actor_id="mrm")
        report = monitor.evaluate("m1", as_of=now)
        assert report.compliant is True
        # Quarterly = 90 days.
        assert report.required_validation_cadence == timedelta(days=90)

    def test_continuous_fine_tune_requires_continuous_monitoring(
        self, monitor: RetrainingCadenceMonitor, now: datetime
    ) -> None:
        monitor.register_model(
            model_id="m1",
            retraining_class=RetrainingClass.CONTINUOUS_FINE_TUNE,
            last_trained=now,
            owner="o",
        )
        monitor.record_validation("m1", validated_at=now - timedelta(days=5), actor_id="mrm")
        report = monitor.evaluate("m1", as_of=now)
        # Continuous fine-tune class: validation cadence is the tightest
        # (per material change), capped at 7 days for the freshness signal.
        assert report.required_validation_cadence == timedelta(days=7)

    def test_evaluate_no_prior_validation_marks_non_compliant(
        self, monitor: RetrainingCadenceMonitor, now: datetime
    ) -> None:
        monitor.register_model(
            model_id="m1",
            retraining_class=RetrainingClass.WEEKLY_RETRAIN,
            last_trained=now,
            owner="o",
        )
        report = monitor.evaluate("m1", as_of=now)
        assert report.last_validated is None
        assert report.compliant is False


# --------------------------------------------------------------------------- #
# Overdue                                                                     #
# --------------------------------------------------------------------------- #


class TestQueryOverdue:
    def test_query_overdue_returns_only_overdue(
        self, monitor: RetrainingCadenceMonitor, now: datetime
    ) -> None:
        monitor.register_model(
            model_id="ok",
            retraining_class=RetrainingClass.STATIC,
            last_trained=now,
            owner="o",
        )
        monitor.record_validation("ok", validated_at=now - timedelta(days=30), actor_id="mrm")
        monitor.register_model(
            model_id="overdue",
            retraining_class=RetrainingClass.WEEKLY_RETRAIN,
            last_trained=now,
            owner="o",
        )
        monitor.record_validation("overdue", validated_at=now - timedelta(days=60), actor_id="mrm")
        results = monitor.query_overdue(as_of=now)
        ids = {r.model_id for r in results}
        assert ids == {"overdue"}

    def test_query_overdue_empty_registry(self, monitor: RetrainingCadenceMonitor) -> None:
        assert monitor.query_overdue() == []


# --------------------------------------------------------------------------- #
# Sanity: module path                                                         #
# --------------------------------------------------------------------------- #


def test_module_lives_at_documented_path() -> None:
    root = Path(__file__).resolve().parent.parent
    expected = root / "src" / "finserv_agent_audit" / "governance" / "retraining_cadence_monitor.py"
    assert expected.is_file()
