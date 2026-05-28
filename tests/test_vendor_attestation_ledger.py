"""Tests for the VendorAttestationLedger primitive (ADR-0023).

Covers attestation recording, query semantics (point-in-time + expiry +
missing), chain emission on every record, and edge cases (empty
registry, future-dated attestations, multiple versions for one vendor).

The audit-chain emission assertion is load-bearing: every recorded
attestation must produce an `AuditEventType.COMPLIANCE_CHECK` entry so
the third-line internal-audit trail attests that the bank's TPRM team
acted as designed. A silent record is worse than no record at all.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from finserv_agent_audit.governance.ledger_store import InMemoryLedgerStore
from finserv_agent_audit.governance.vendor_attestation_ledger import (
    AttestationGap,
    VendorAttestation,
    VendorAttestationLedger,
)
from finserv_agent_audit.schemas.audit_event import AuditEventType

# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #


@pytest.fixture
def now() -> datetime:
    return datetime.now(UTC)


@pytest.fixture
def store() -> InMemoryLedgerStore:
    return InMemoryLedgerStore()


@pytest.fixture
def ledger(store: InMemoryLedgerStore) -> VendorAttestationLedger:
    return VendorAttestationLedger(ledger_store=store)


# --------------------------------------------------------------------------- #
# Record + emit                                                               #
# --------------------------------------------------------------------------- #


class TestRecordAttestation:
    def test_record_returns_attestation(
        self, ledger: VendorAttestationLedger, now: datetime
    ) -> None:
        att = ledger.record_attestation(
            vendor_id="anthropic",
            attestation_type="SOC2_TYPE_II",
            attesting_entity="anthropic_pbc",
            version="2025-Q4",
            attestation_hash="a" * 64,
            valid_from=now - timedelta(days=30),
            valid_until=now + timedelta(days=335),
        )
        assert isinstance(att, VendorAttestation)
        assert att.vendor_id == "anthropic"
        assert att.attestation_type == "SOC2_TYPE_II"
        assert att.attesting_entity == "anthropic_pbc"
        assert att.evidence_url is None

    def test_record_emits_compliance_check_event(
        self,
        ledger: VendorAttestationLedger,
        store: InMemoryLedgerStore,
        now: datetime,
    ) -> None:
        ledger.record_attestation(
            vendor_id="openai",
            attestation_type="SOC2_TYPE_II",
            attesting_entity="openai_inc",
            version="2025-12",
            attestation_hash="b" * 64,
            valid_from=now,
            valid_until=now + timedelta(days=365),
            evidence_url="https://trust.openai.com/soc2",
        )
        events = list(store)
        assert len(events) == 1
        event = events[0]
        assert event.event_type == AuditEventType.COMPLIANCE_CHECK
        assert event.payload["vendor_id"] == "openai"
        assert event.payload["attestation_type"] == "SOC2_TYPE_II"
        assert event.payload["evidence_url"] == "https://trust.openai.com/soc2"

    def test_record_without_store_does_not_raise(self, now: datetime) -> None:
        ledger = VendorAttestationLedger()  # no store
        att = ledger.record_attestation(
            vendor_id="cohere",
            attestation_type="ISO_27001",
            attesting_entity="cohere_inc",
            version="v1",
            attestation_hash="c" * 64,
            valid_from=now,
            valid_until=now + timedelta(days=365),
        )
        assert att.vendor_id == "cohere"

    def test_record_rejects_inverted_validity_window(
        self, ledger: VendorAttestationLedger, now: datetime
    ) -> None:
        with pytest.raises(ValueError, match="valid_until"):
            ledger.record_attestation(
                vendor_id="x",
                attestation_type="SOC2_TYPE_II",
                attesting_entity="x",
                version="v1",
                attestation_hash="d" * 64,
                valid_from=now,
                valid_until=now - timedelta(days=1),
            )

    def test_record_rejects_empty_vendor_id(
        self, ledger: VendorAttestationLedger, now: datetime
    ) -> None:
        with pytest.raises(ValueError, match="vendor_id"):
            ledger.record_attestation(
                vendor_id="",
                attestation_type="SOC2_TYPE_II",
                attesting_entity="x",
                version="v1",
                attestation_hash="e" * 64,
                valid_from=now,
                valid_until=now + timedelta(days=1),
            )


# --------------------------------------------------------------------------- #
# Query                                                                       #
# --------------------------------------------------------------------------- #


class TestQuery:
    def test_query_returns_all_for_vendor(
        self, ledger: VendorAttestationLedger, now: datetime
    ) -> None:
        ledger.record_attestation(
            vendor_id="anthropic",
            attestation_type="SOC2_TYPE_II",
            attesting_entity="anthropic_pbc",
            version="2025-Q4",
            attestation_hash="a" * 64,
            valid_from=now - timedelta(days=30),
            valid_until=now + timedelta(days=335),
        )
        ledger.record_attestation(
            vendor_id="anthropic",
            attestation_type="ISO_42001",
            attesting_entity="bsi_independent_auditor",
            version="2025",
            attestation_hash="b" * 64,
            valid_from=now - timedelta(days=10),
            valid_until=now + timedelta(days=355),
        )
        ledger.record_attestation(
            vendor_id="openai",
            attestation_type="SOC2_TYPE_II",
            attesting_entity="openai_inc",
            version="2025-12",
            attestation_hash="c" * 64,
            valid_from=now,
            valid_until=now + timedelta(days=365),
        )
        results = ledger.query(vendor_id="anthropic")
        assert len(results) == 2
        assert {r.attestation_type for r in results} == {"SOC2_TYPE_II", "ISO_42001"}

    def test_query_filters_by_attestation_type(
        self, ledger: VendorAttestationLedger, now: datetime
    ) -> None:
        ledger.record_attestation(
            vendor_id="anthropic",
            attestation_type="SOC2_TYPE_II",
            attesting_entity="anthropic_pbc",
            version="2025-Q4",
            attestation_hash="a" * 64,
            valid_from=now - timedelta(days=30),
            valid_until=now + timedelta(days=335),
        )
        ledger.record_attestation(
            vendor_id="anthropic",
            attestation_type="ISO_42001",
            attesting_entity="bsi",
            version="2025",
            attestation_hash="b" * 64,
            valid_from=now,
            valid_until=now + timedelta(days=365),
        )
        results = ledger.query(vendor_id="anthropic", attestation_type="SOC2_TYPE_II")
        assert len(results) == 1
        assert results[0].attestation_type == "SOC2_TYPE_II"

    def test_query_with_valid_as_of_excludes_expired(
        self, ledger: VendorAttestationLedger, now: datetime
    ) -> None:
        ledger.record_attestation(
            vendor_id="vendor_x",
            attestation_type="SOC2_TYPE_II",
            attesting_entity="vx",
            version="2024",
            attestation_hash="a" * 64,
            valid_from=now - timedelta(days=400),
            valid_until=now - timedelta(days=35),
        )
        ledger.record_attestation(
            vendor_id="vendor_x",
            attestation_type="SOC2_TYPE_II",
            attesting_entity="vx",
            version="2025",
            attestation_hash="b" * 64,
            valid_from=now - timedelta(days=30),
            valid_until=now + timedelta(days=335),
        )
        # Past attestation is expired; current is valid.
        results = ledger.query(vendor_id="vendor_x", valid_as_of=now)
        assert len(results) == 1
        assert results[0].version == "2025"

    def test_query_with_valid_as_of_excludes_future_dated(
        self, ledger: VendorAttestationLedger, now: datetime
    ) -> None:
        ledger.record_attestation(
            vendor_id="vendor_x",
            attestation_type="SOC2_TYPE_II",
            attesting_entity="vx",
            version="future",
            attestation_hash="a" * 64,
            valid_from=now + timedelta(days=30),
            valid_until=now + timedelta(days=365),
        )
        # The attestation starts in the future; it is not valid "now".
        results = ledger.query(vendor_id="vendor_x", valid_as_of=now)
        assert results == []

    def test_query_empty_registry_returns_empty(self, ledger: VendorAttestationLedger) -> None:
        assert ledger.query(vendor_id="unknown") == []


# --------------------------------------------------------------------------- #
# Query expired / expiring soon                                               #
# --------------------------------------------------------------------------- #


class TestQueryExpired:
    def test_query_expired_returns_attestations_in_grace_window(
        self, ledger: VendorAttestationLedger, now: datetime
    ) -> None:
        # Expires in 15 days — inside default 30-day grace window.
        ledger.record_attestation(
            vendor_id="vendor_a",
            attestation_type="SOC2_TYPE_II",
            attesting_entity="va",
            version="2024",
            attestation_hash="a" * 64,
            valid_from=now - timedelta(days=350),
            valid_until=now + timedelta(days=15),
        )
        # Expires in 90 days — outside default grace window.
        ledger.record_attestation(
            vendor_id="vendor_b",
            attestation_type="ISO_27001",
            attesting_entity="vb",
            version="2025",
            attestation_hash="b" * 64,
            valid_from=now - timedelta(days=275),
            valid_until=now + timedelta(days=90),
        )
        expiring = ledger.query_expired(grace_period_days=30)
        assert len(expiring) == 1
        assert expiring[0].vendor_id == "vendor_a"

    def test_query_expired_includes_already_expired(
        self, ledger: VendorAttestationLedger, now: datetime
    ) -> None:
        ledger.record_attestation(
            vendor_id="vendor_a",
            attestation_type="SOC2_TYPE_II",
            attesting_entity="va",
            version="2024",
            attestation_hash="a" * 64,
            valid_from=now - timedelta(days=400),
            valid_until=now - timedelta(days=5),
        )
        expiring = ledger.query_expired(grace_period_days=30)
        assert len(expiring) == 1

    def test_query_expired_custom_grace_period(
        self, ledger: VendorAttestationLedger, now: datetime
    ) -> None:
        ledger.record_attestation(
            vendor_id="vendor_a",
            attestation_type="SOC2_TYPE_II",
            attesting_entity="va",
            version="2024",
            attestation_hash="a" * 64,
            valid_from=now - timedelta(days=180),
            valid_until=now + timedelta(days=120),
        )
        # 60-day window: not expiring soon.
        assert ledger.query_expired(grace_period_days=60) == []
        # 180-day window: now expiring soon.
        assert len(ledger.query_expired(grace_period_days=180)) == 1


# --------------------------------------------------------------------------- #
# Query missing                                                               #
# --------------------------------------------------------------------------- #


class TestQueryMissing:
    def test_query_missing_returns_unmet_requirements(
        self, ledger: VendorAttestationLedger, now: datetime
    ) -> None:
        ledger.record_attestation(
            vendor_id="anthropic",
            attestation_type="SOC2_TYPE_II",
            attesting_entity="anthropic_pbc",
            version="2025",
            attestation_hash="a" * 64,
            valid_from=now - timedelta(days=30),
            valid_until=now + timedelta(days=335),
        )
        requirements = [
            ("anthropic", "SOC2_TYPE_II"),
            ("anthropic", "ISO_42001"),
            ("openai", "SOC2_TYPE_II"),
        ]
        gaps = ledger.query_missing(requirements)
        assert len(gaps) == 2
        gap_keys = {(g.vendor_id, g.attestation_type) for g in gaps}
        assert gap_keys == {("anthropic", "ISO_42001"), ("openai", "SOC2_TYPE_II")}
        assert all(isinstance(g, AttestationGap) for g in gaps)

    def test_query_missing_empty_requirements(self, ledger: VendorAttestationLedger) -> None:
        assert ledger.query_missing([]) == []

    def test_query_missing_all_satisfied(
        self, ledger: VendorAttestationLedger, now: datetime
    ) -> None:
        ledger.record_attestation(
            vendor_id="anthropic",
            attestation_type="SOC2_TYPE_II",
            attesting_entity="anthropic_pbc",
            version="2025",
            attestation_hash="a" * 64,
            valid_from=now - timedelta(days=30),
            valid_until=now + timedelta(days=335),
        )
        gaps = ledger.query_missing([("anthropic", "SOC2_TYPE_II")])
        assert gaps == []

    def test_query_missing_treats_expired_as_missing(
        self, ledger: VendorAttestationLedger, now: datetime
    ) -> None:
        # Expired attestation should NOT satisfy a current requirement.
        ledger.record_attestation(
            vendor_id="anthropic",
            attestation_type="SOC2_TYPE_II",
            attesting_entity="anthropic_pbc",
            version="2023",
            attestation_hash="a" * 64,
            valid_from=now - timedelta(days=730),
            valid_until=now - timedelta(days=365),
        )
        gaps = ledger.query_missing([("anthropic", "SOC2_TYPE_II")])
        assert len(gaps) == 1


# --------------------------------------------------------------------------- #
# Sanity: the module lives at the documented path                             #
# --------------------------------------------------------------------------- #


def test_module_lives_at_documented_path() -> None:
    root = Path(__file__).resolve().parent.parent
    expected = root / "src" / "finserv_agent_audit" / "governance" / "vendor_attestation_ledger.py"
    assert expected.is_file()
