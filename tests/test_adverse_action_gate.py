"""Tests for the FCRA / Reg V AdverseActionGate (ADR-0009).

Covers the fail-closed gate behavior on missing / generic / overloaded
reason codes, the audit-emission contract for every gate evaluation,
and the reference reason-code dictionary.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from finserv_agent_audit.governance.adverse_action_gate import (
    REFERENCE_REASON_CODES,
    AdverseActionGate,
    AdverseActionKind,
    AdverseActionPacket,
    AdverseActionViolation,
    ReasonCode,
)
from finserv_agent_audit.governance.ledger_store import InMemoryLedgerStore
from finserv_agent_audit.schemas.audit_event import AuditEventType

# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #


def _well_formed_reasons() -> tuple[ReasonCode, ...]:
    return (
        ReasonCode(
            code="DTI_TOO_HIGH",
            plain_language="Debt-to-income ratio exceeds policy threshold.",
            factor_contribution=0.45,
            upstream_feature_ids=("feature.dti_ratio",),
        ),
        ReasonCode(
            code="LIMITED_CREDIT_HISTORY",
            plain_language="Credit file too thin for confident scoring.",
            factor_contribution=0.30,
            upstream_feature_ids=("feature.tradeline_count",),
        ),
    )


def _packet(**overrides: object) -> AdverseActionPacket:
    base: dict[str, object] = {
        "decision_id": "dec-001",
        "consumer_id": "consumer-abc",
        "action_kind": AdverseActionKind.CREDIT_DENIED,
        "primary_reasons": _well_formed_reasons(),
        "model_id": "credit_scorer_v3",
        "model_version": "3.0.1",
        "model_validation_id": "mrm-2026-Q1-007",
        "cra_used": "Equifax",
        "decision_timestamp": datetime.now(UTC),
    }
    base.update(overrides)
    return AdverseActionPacket(**base)  # type: ignore[arg-type]


@pytest.fixture
def gate() -> AdverseActionGate:
    return AdverseActionGate()


@pytest.fixture
def audited_gate() -> tuple[AdverseActionGate, InMemoryLedgerStore]:
    store = InMemoryLedgerStore()
    return AdverseActionGate(ledger_store=store), store


# --------------------------------------------------------------------------- #
# Happy path                                                                  #
# --------------------------------------------------------------------------- #


class TestEvaluateHappyPath:
    def test_well_formed_packet_passes(self, gate: AdverseActionGate) -> None:
        # No exception means the gate cleared the packet.
        gate.evaluate(_packet())

    def test_gate_emits_event_on_pass(
        self, audited_gate: tuple[AdverseActionGate, InMemoryLedgerStore]
    ) -> None:
        gate, store = audited_gate
        gate.evaluate(_packet())
        events = list(store)
        assert len(events) == 1
        event = events[0]
        assert event.event_type == AuditEventType.ADVERSE_ACTION_TAKEN
        assert event.payload["decision_id"] == "dec-001"
        assert event.payload["outcome"] == "passed"
        assert event.payload["action_kind"] == AdverseActionKind.CREDIT_DENIED.value


# --------------------------------------------------------------------------- #
# Fail-closed behavior                                                        #
# --------------------------------------------------------------------------- #


class TestFailClosed:
    def test_empty_reasons_blocked(self, gate: AdverseActionGate) -> None:
        packet = _packet(primary_reasons=())
        with pytest.raises(AdverseActionViolation) as exc_info:
            gate.evaluate(packet)
        assert "FCRA-REASONS-MISSING" in str(exc_info.value)

    def test_too_many_reasons_blocked(self, gate: AdverseActionGate) -> None:
        many = tuple(
            ReasonCode(
                code=f"CODE_{i}",
                plain_language=f"Reason {i}.",
                factor_contribution=0.1,
                upstream_feature_ids=(f"feature.x_{i}",),
            )
            for i in range(5)
        )
        packet = _packet(primary_reasons=many)
        with pytest.raises(AdverseActionViolation) as exc_info:
            gate.evaluate(packet)
        assert "FCRA-REASONS-OVERLOAD" in str(exc_info.value)

    def test_generic_reason_text_blocked(self, gate: AdverseActionGate) -> None:
        generic = (
            ReasonCode(
                code="MODEL_DECISION",
                plain_language="Model decision",
                factor_contribution=1.0,
                upstream_feature_ids=("feature.model_output",),
            ),
        )
        packet = _packet(primary_reasons=generic)
        with pytest.raises(AdverseActionViolation) as exc_info:
            gate.evaluate(packet)
        assert "FCRA-REASONS-MISSING" in str(exc_info.value)

    def test_score_below_threshold_blocked(self, gate: AdverseActionGate) -> None:
        generic = (
            ReasonCode(
                code="SCORE",
                plain_language="Score below threshold",
                factor_contribution=1.0,
                upstream_feature_ids=("feature.score",),
            ),
        )
        packet = _packet(primary_reasons=generic)
        with pytest.raises(AdverseActionViolation):
            gate.evaluate(packet)

    def test_missing_upstream_features_blocked(self, gate: AdverseActionGate) -> None:
        untraceable = (
            ReasonCode(
                code="DTI_TOO_HIGH",
                plain_language="DTI exceeds threshold.",
                factor_contribution=0.5,
                upstream_feature_ids=(),
            ),
        )
        packet = _packet(primary_reasons=untraceable)
        with pytest.raises(AdverseActionViolation) as exc_info:
            gate.evaluate(packet)
        assert "FCRA-FACTOR-TRACE-MISSING" in str(exc_info.value)

    def test_missing_cra_blocked(self, gate: AdverseActionGate) -> None:
        packet = _packet(cra_used=None)
        with pytest.raises(AdverseActionViolation) as exc_info:
            gate.evaluate(packet)
        assert "FCRA-CRA-UNNAMED" in str(exc_info.value)

    def test_missing_validation_id_blocked(self, gate: AdverseActionGate) -> None:
        packet = _packet(model_validation_id="")
        with pytest.raises(AdverseActionViolation) as exc_info:
            gate.evaluate(packet)
        assert "FCRA-VALIDATION-MISSING" in str(exc_info.value)

    def test_negative_factor_contribution_blocked(self, gate: AdverseActionGate) -> None:
        bad_contrib = (
            ReasonCode(
                code="DTI_TOO_HIGH",
                plain_language="DTI exceeds threshold.",
                factor_contribution=-0.1,
                upstream_feature_ids=("feature.dti_ratio",),
            ),
        )
        packet = _packet(primary_reasons=bad_contrib)
        with pytest.raises(AdverseActionViolation):
            gate.evaluate(packet)


class TestAuditOnFailure:
    def test_violation_emits_event(
        self, audited_gate: tuple[AdverseActionGate, InMemoryLedgerStore]
    ) -> None:
        gate, store = audited_gate
        with pytest.raises(AdverseActionViolation):
            gate.evaluate(_packet(primary_reasons=()))
        events = list(store)
        assert len(events) == 1
        event = events[0]
        assert event.event_type == AuditEventType.ADVERSE_ACTION_TAKEN
        assert event.payload["outcome"] == "blocked"
        assert "FCRA-REASONS-MISSING" in event.payload["violations"]


# --------------------------------------------------------------------------- #
# Reference reason-code dictionary                                            #
# --------------------------------------------------------------------------- #


class TestReferenceReasonCodes:
    def test_reference_dictionary_is_non_empty(self) -> None:
        assert len(REFERENCE_REASON_CODES) >= 8

    def test_reference_codes_include_common_credit_factors(self) -> None:
        codes = set(REFERENCE_REASON_CODES.keys())
        # The dictionary should cover the canonical Reg B principal-reason set.
        for expected in (
            "DTI_TOO_HIGH",
            "LIMITED_CREDIT_HISTORY",
            "DELINQUENT_PAYMENT_HISTORY",
            "INSUFFICIENT_INCOME",
        ):
            assert expected in codes

    def test_reference_entries_have_plain_language(self) -> None:
        for code, plain in REFERENCE_REASON_CODES.items():
            assert isinstance(code, str) and code
            assert isinstance(plain, str) and plain


# --------------------------------------------------------------------------- #
# Module path stability                                                       #
# --------------------------------------------------------------------------- #


def test_module_lives_at_documented_path() -> None:
    root = Path(__file__).resolve().parent.parent
    expected = root / "src" / "finserv_agent_audit" / "governance" / "adverse_action_gate.py"
    assert expected.is_file()
