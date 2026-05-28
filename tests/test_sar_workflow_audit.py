"""Tests for the BSA/AML SARWorkflowAudit module (ADR-0011).

Covers per-surface SAR_FILED chain emissions, the audit-emit-mandatory
contract, narrative-hash + flagged-entity scoring evidence capture, and
the § 5318(g)(2) safe-harbor metadata field.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from finserv_agent_audit.governance.ledger_store import InMemoryLedgerStore
from finserv_agent_audit.governance.sar_workflow_audit import (
    SARActionTaken,
    SARAuditError,
    SARDecisionSurface,
    SARWorkflowAudit,
    SARWorkflowEntry,
)
from finserv_agent_audit.schemas.audit_event import AuditEventType

# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #


def _entry(**overrides: object) -> SARWorkflowEntry:
    base: dict[str, object] = {
        "entry_id": "entry-001",
        "surface": SARDecisionSurface.ALERT_DISPOSITION,
        "action": SARActionTaken.ESCALATE_TO_ANALYST,
        "case_id": "case-789",
        "alert_ids": ("alert-1", "alert-2"),
        "suspect_party_ids": ("party-001",),
        "model_id": "tm_engine",
        "model_version": "5.2.0",
        "model_validation_id": "mrm-bsa-2026-Q1-003",
        "detection_anchor_timestamp": datetime.now(UTC) - timedelta(days=2),
        "decision_timestamp": datetime.now(UTC),
        "human_reviewer": "analyst-007",
        "narrative_hash": None,
        "score_value": 0.82,
        "score_factors": ("feature.txn_velocity", "feature.geo_risk"),
        "rationale": (
            "Velocity over the 30-day window exceeded the typology threshold "
            "for cash-intensive small-business accounts."
        ),
        "safe_harbor_claimed": True,
    }
    base.update(overrides)
    return SARWorkflowEntry(**base)  # type: ignore[arg-type]


@pytest.fixture
def store() -> InMemoryLedgerStore:
    return InMemoryLedgerStore()


@pytest.fixture
def audit(store: InMemoryLedgerStore) -> SARWorkflowAudit:
    return SARWorkflowAudit(ledger_store=store, agent_id="aml-agent")


# --------------------------------------------------------------------------- #
# Happy path                                                                  #
# --------------------------------------------------------------------------- #


class TestRecordHappyPath:
    def test_record_emits_sar_filed_event(
        self, audit: SARWorkflowAudit, store: InMemoryLedgerStore
    ) -> None:
        audit.record(_entry())
        events = list(store)
        assert len(events) == 1
        event = events[0]
        assert event.event_type == AuditEventType.SAR_FILED
        assert event.payload["entry_id"] == "entry-001"
        assert event.payload["surface"] == SARDecisionSurface.ALERT_DISPOSITION.value
        assert event.payload["action"] == SARActionTaken.ESCALATE_TO_ANALYST.value
        assert event.payload["case_id"] == "case-789"
        assert event.actor_id == "analyst-007"

    def test_score_and_factors_captured(
        self, audit: SARWorkflowAudit, store: InMemoryLedgerStore
    ) -> None:
        audit.record(_entry())
        event = list(store)[0]
        assert event.payload["score_value"] == 0.82
        assert event.payload["score_factors"] == [
            "feature.txn_velocity",
            "feature.geo_risk",
        ]

    def test_safe_harbor_metadata_persisted(
        self, audit: SARWorkflowAudit, store: InMemoryLedgerStore
    ) -> None:
        audit.record(_entry(safe_harbor_claimed=True))
        event = list(store)[0]
        assert event.payload["safe_harbor_claimed"] is True
        assert event.payload["safe_harbor_citation"] == "31 U.S.C. 5318(g)(2)"

    def test_record_file_decision(
        self, audit: SARWorkflowAudit, store: InMemoryLedgerStore
    ) -> None:
        audit.record(
            _entry(
                surface=SARDecisionSurface.FILE_DECISION,
                action=SARActionTaken.RECOMMEND_FILE,
            )
        )
        event = list(store)[0]
        assert event.payload["surface"] == SARDecisionSurface.FILE_DECISION.value
        assert event.payload["action"] == SARActionTaken.RECOMMEND_FILE.value

    def test_narrative_auto_population_with_hash(
        self, audit: SARWorkflowAudit, store: InMemoryLedgerStore
    ) -> None:
        audit.record(
            _entry(
                surface=SARDecisionSurface.NARRATIVE_AUTO_POPULATION,
                action=SARActionTaken.NARRATIVE_DRAFTED,
                narrative_hash="a" * 64,
            )
        )
        event = list(store)[0]
        assert event.payload["narrative_hash"] == "a" * 64

    def test_narrative_indicator_in_payload(
        self, audit: SARWorkflowAudit, store: InMemoryLedgerStore
    ) -> None:
        audit.record(
            _entry(
                surface=SARDecisionSurface.NARRATIVE_AUTO_POPULATION,
                action=SARActionTaken.NARRATIVE_DRAFTED,
                narrative_hash="b" * 64,
            )
        )
        event = list(store)[0]
        assert event.payload["narrative_auto_populated"] is True

    def test_non_narrative_records_indicator_false(
        self, audit: SARWorkflowAudit, store: InMemoryLedgerStore
    ) -> None:
        audit.record(_entry())  # default ALERT_DISPOSITION
        event = list(store)[0]
        assert event.payload["narrative_auto_populated"] is False


# --------------------------------------------------------------------------- #
# Audit-emit-mandatory: validation failures                                   #
# --------------------------------------------------------------------------- #


class TestVetoes:
    def test_narrative_without_hash_blocked(self, audit: SARWorkflowAudit) -> None:
        with pytest.raises(SARAuditError) as exc_info:
            audit.record(
                _entry(
                    surface=SARDecisionSurface.NARRATIVE_AUTO_POPULATION,
                    action=SARActionTaken.NARRATIVE_DRAFTED,
                    narrative_hash=None,
                )
            )
        assert "BSA-NARRATIVE-UNHASHED" in str(exc_info.value)

    def test_missing_validation_id_blocked(self, audit: SARWorkflowAudit) -> None:
        with pytest.raises(SARAuditError) as exc_info:
            audit.record(_entry(model_validation_id=""))
        assert "BSA-VALIDATION-MISSING" in str(exc_info.value)

    def test_generic_rationale_blocked(self, audit: SARWorkflowAudit) -> None:
        with pytest.raises(SARAuditError) as exc_info:
            audit.record(_entry(rationale="model decision"))
        assert "BSA-RATIONALE-VAGUE" in str(exc_info.value)

    def test_no_further_action_warranted_blocked(self, audit: SARWorkflowAudit) -> None:
        with pytest.raises(SARAuditError):
            audit.record(_entry(rationale="no further action warranted"))

    def test_extension_decision_requires_named_reason(self, audit: SARWorkflowAudit) -> None:
        with pytest.raises(SARAuditError) as exc_info:
            audit.record(
                _entry(
                    surface=SARDecisionSurface.EXTENSION_DECISION,
                    action=SARActionTaken.ESCALATE_TO_ANALYST,
                    # rationale does not name "suspect" or "identification" —
                    # the regulatory predicate for the 30-to-60-day extension.
                    rationale="More time is required to finish the review.",
                )
            )
        assert "BSA-EXTENSION-UNJUSTIFIED" in str(exc_info.value)

    def test_extension_with_named_predicate_passes(
        self, audit: SARWorkflowAudit, store: InMemoryLedgerStore
    ) -> None:
        audit.record(
            _entry(
                surface=SARDecisionSurface.EXTENSION_DECISION,
                action=SARActionTaken.ESCALATE_TO_ANALYST,
                rationale=(
                    "No suspect has been identified across the connected "
                    "account network; extending under 31 C.F.R. 1020.320(b)(3)."
                ),
            )
        )
        assert len(list(store)) == 1


# --------------------------------------------------------------------------- #
# Audit-emit-mandatory: store failure propagation                             #
# --------------------------------------------------------------------------- #


class _FailingStore:
    """Ledger store that raises on append to simulate write failure."""

    def append(self, event: object) -> None:  # noqa: ARG002
        raise OSError("disk full")

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(())

    def __len__(self) -> int:
        return 0

    def get(self, sequence: int):  # type: ignore[no-untyped-def]
        raise IndexError(sequence)

    def head_sequence(self) -> int:
        return -1

    def head_event_hash(self) -> str:
        return "0" * 64


def test_write_failure_raises_bsa_audit_write_failed() -> None:
    audit = SARWorkflowAudit(ledger_store=_FailingStore(), agent_id="aml-agent")
    with pytest.raises(SARAuditError) as exc_info:
        audit.record(_entry())
    assert "BSA-AUDIT-WRITE-FAILED" in str(exc_info.value)


# --------------------------------------------------------------------------- #
# Module path stability                                                       #
# --------------------------------------------------------------------------- #


def test_module_lives_at_documented_path() -> None:
    root = Path(__file__).resolve().parent.parent
    expected = root / "src" / "finserv_agent_audit" / "governance" / "sar_workflow_audit.py"
    assert expected.is_file()
