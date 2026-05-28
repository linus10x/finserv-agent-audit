"""Tests for the BestInterestCheck SEC Reg-BI pre-recommendation gate.

Test surface: happy path (a fully-documented recommendation passes and emits
the BEST_INTEREST_CHECKED event), fail-closed posture (any of the four
required documented-consideration fields absent raises
BestInterestViolation), chain-entry-before-raise.

Regulatory anchor:
    - SEC Reg BI 17 C.F.R. § 240.15l-1(a)(2)(ii) — Care Obligation
    - sec_reg_bi_mapping.md — pattern mapping
"""

from __future__ import annotations

from pathlib import Path

import pytest

from finserv_agent_audit.governance.best_interest_check import (
    BestInterestCheck,
    BestInterestViolation,
    RecommendationProfile,
)
from finserv_agent_audit.schemas.audit_event import (
    AuditChain,
    AuditEventType,
    AutonomyLevel,
)


@pytest.fixture
def chain(tmp_path: Path) -> AuditChain:
    return AuditChain(log_file=tmp_path / "audit.jsonl")


def _full_profile() -> RecommendationProfile:
    return RecommendationProfile(
        costs="Front-load 1.0%; expense ratio 0.45%; turnover-related drag estimated 8 bps.",
        risks=(
            "Leveraged ETF — daily-rebalance decay; sequence-of-returns risk over 12-month hold."
        ),
        alternatives=(
            "Plain S&P 500 ETF (cheaper, unleveraged); cash sweep; "
            "customer's current target-date fund."
        ),
        customer_profile=(
            "Retail customer; age 58; retirement horizon 7 years; moderate risk tolerance per "
            "the most recent suitability questionnaire dated 2026-03-14."
        ),
    )


# --------------------------------------------------------------------------- #
# Happy path                                                                  #
# --------------------------------------------------------------------------- #


class TestHappyPath:
    def test_fully_documented_recommendation_passes(self, chain: AuditChain) -> None:
        gate = BestInterestCheck(audit_chain=chain)
        result = gate.check(
            recommendation_id="rec-001",
            customer_id="cust-77",
            agent_id="advisor_bot",
            profile=_full_profile(),
        )
        assert result.passed is True
        assert result.event_id is not None
        assert len(chain._events) == 1

    def test_emits_best_interest_checked_event(self, chain: AuditChain) -> None:
        gate = BestInterestCheck(audit_chain=chain)
        gate.check(
            recommendation_id="rec-002",
            customer_id="cust-77",
            agent_id="advisor_bot",
            profile=_full_profile(),
        )
        assert chain._events[0].event_type == AuditEventType.BEST_INTEREST_CHECKED

    def test_default_autonomy_level_is_a2(self, chain: AuditChain) -> None:
        gate = BestInterestCheck(audit_chain=chain)
        gate.check(
            recommendation_id="rec-003",
            customer_id="cust-77",
            agent_id="advisor_bot",
            profile=_full_profile(),
        )
        assert chain._events[0].autonomy_level == AutonomyLevel.A2

    def test_payload_contains_all_four_consideration_fields(self, chain: AuditChain) -> None:
        gate = BestInterestCheck(audit_chain=chain)
        gate.check(
            recommendation_id="rec-004",
            customer_id="cust-77",
            agent_id="advisor_bot",
            profile=_full_profile(),
        )
        payload = chain._events[0].payload
        for field in ("costs", "risks", "alternatives", "customer_profile"):
            assert field in payload
            assert payload[field]  # non-empty


# --------------------------------------------------------------------------- #
# Fail-closed posture                                                         #
# --------------------------------------------------------------------------- #


class TestFailClosed:
    @pytest.mark.parametrize(
        "missing_field",
        ["costs", "risks", "alternatives", "customer_profile"],
    )
    def test_missing_any_required_consideration_raises(
        self, chain: AuditChain, missing_field: str
    ) -> None:
        profile = _full_profile()
        # Blank the field to simulate "not documented".
        object.__setattr__(profile, missing_field, "")
        gate = BestInterestCheck(audit_chain=chain)

        with pytest.raises(BestInterestViolation) as exc:
            gate.check(
                recommendation_id="rec-bad",
                customer_id="cust-77",
                agent_id="advisor_bot",
                profile=profile,
            )
        assert "REG-BI-CARE-UNDOCUMENTED" in str(exc.value)
        assert missing_field in str(exc.value)

    def test_violation_records_chain_entry_before_raising(self, chain: AuditChain) -> None:
        profile = _full_profile()
        object.__setattr__(profile, "costs", "")
        gate = BestInterestCheck(audit_chain=chain)

        with pytest.raises(BestInterestViolation):
            gate.check(
                recommendation_id="rec-bad",
                customer_id="cust-77",
                agent_id="advisor_bot",
                profile=profile,
            )
        # Violation must be on the chain before the exception propagates —
        # the regulator gets the audit entry even if the caller swallows.
        assert len(chain._events) == 1
        assert chain._events[0].payload["gate_verdict"] == "violation"
        assert chain._events[0].payload["reason_code"] == "REG-BI-CARE-UNDOCUMENTED"
        assert "costs" in chain._events[0].payload["missing_fields"]

    def test_whitespace_only_consideration_counts_as_missing(self, chain: AuditChain) -> None:
        profile = _full_profile()
        object.__setattr__(profile, "risks", "   \n\t  ")
        gate = BestInterestCheck(audit_chain=chain)

        with pytest.raises(BestInterestViolation) as exc:
            gate.check(
                recommendation_id="rec-bad",
                customer_id="cust-77",
                agent_id="advisor_bot",
                profile=profile,
            )
        assert "risks" in str(exc.value)

    def test_all_four_missing_lists_all_four(self, chain: AuditChain) -> None:
        profile = RecommendationProfile(
            costs="",
            risks="",
            alternatives="",
            customer_profile="",
        )
        gate = BestInterestCheck(audit_chain=chain)

        with pytest.raises(BestInterestViolation):
            gate.check(
                recommendation_id="rec-empty",
                customer_id="cust-77",
                agent_id="advisor_bot",
                profile=profile,
            )
        missing = chain._events[0].payload["missing_fields"]
        assert set(missing) == {"costs", "risks", "alternatives", "customer_profile"}


# --------------------------------------------------------------------------- #
# Input validation                                                            #
# --------------------------------------------------------------------------- #


class TestInputValidation:
    def test_empty_recommendation_id_rejected(self, chain: AuditChain) -> None:
        gate = BestInterestCheck(audit_chain=chain)
        with pytest.raises(ValueError):
            gate.check(
                recommendation_id="",
                customer_id="cust-77",
                agent_id="advisor_bot",
                profile=_full_profile(),
            )

    def test_empty_customer_id_rejected(self, chain: AuditChain) -> None:
        gate = BestInterestCheck(audit_chain=chain)
        with pytest.raises(ValueError):
            gate.check(
                recommendation_id="rec-001",
                customer_id="",
                agent_id="advisor_bot",
                profile=_full_profile(),
            )
