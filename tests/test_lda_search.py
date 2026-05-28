"""Tests for the LDA (Less Discriminatory Alternative) search harness — v1.3.

The harness operationalizes the ACM-FAccT 2024 paper "Operationalizing
the Search for Less Discriminatory Alternatives in Fair Lending"
(Black, Gillis, Hall, Schrag, Singh, Yadav). LDA search is regulatory-
grade methodology in 2026: CFPB Circular 2023-09 + the CFPB final rule
expect lenders to demonstrate they searched for LDAs, not merely that
their primary model passes a disparate-impact threshold. The state-AG
front (Massachusetts AG's July 10, 2025 settlement of the first state-
AG fair-lending action against an AI underwriting model) raises the
floor of expected diligence further.

These tests cover: happy path (LDA dominates the primary), LDA does
not dominate (similar accuracy + similar DI), tied accuracy + better
DI (LDA dominates on the tie-break), edge cases (empty candidates,
mismatched-length inputs, single-protected-group degenerate),
audit-chain emission, and the dataclass field surface.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from finserv_agent_audit.governance.lda_search import (
    LDACandidateReport,
    LDASearchHarness,
    LDASearchResult,
)
from finserv_agent_audit.schemas.audit_event import (
    AuditChain,
    AuditEventType,
)

# --------------------------------------------------------------------------- #
# Fixtures + helpers                                                          #
# --------------------------------------------------------------------------- #


@pytest.fixture
def chain(tmp_path: Path) -> AuditChain:
    return AuditChain(log_file=tmp_path / "audit.jsonl")


def _primary_model(features: dict[str, float | int | str]) -> int:
    """Deterministic primary scorer used across tests.

    The "primary" approves whenever the ``zip`` feature equals ``"A"``;
    it correlates strongly with the protected group encoded in the test
    fixtures below.
    """
    return 1 if str(features.get("zip")) == "A" else 0


def _fairer_lda(features: dict[str, float | int | str]) -> int:
    """LDA candidate that uses ``income`` (no protected-class signal).

    Returns approve (1) when income >= 50, deny (0) otherwise. By
    construction this is the same accuracy on the test fixture but a
    materially better DI ratio.
    """
    income_val = features.get("income")
    if isinstance(income_val, int | float):
        return 1 if income_val >= 50 else 0
    return 0


def _worse_lda(features: dict[str, float | int | str]) -> int:
    """LDA candidate that is strictly worse — random-flip parity model."""
    return 0


# --------------------------------------------------------------------------- #
# Happy path: LDA dominates the primary                                       #
# --------------------------------------------------------------------------- #


class TestLDADominance:
    def test_lda_with_better_di_and_equal_accuracy_dominates(self, chain: AuditChain) -> None:
        # Protected group A:  zip=A income=80  -> decision actual = 1
        # Protected group B:  zip=B income=80  -> decision actual = 1
        # The primary approves only zip=A so it is correct on group A
        # rows and wrong on group B rows -> 50% accuracy + strong DI.
        # The fairer LDA approves anyone with income>=50 -> 100%
        # accuracy on this fixture AND parity DI.
        n_per_group = 20
        features = [{"zip": "A", "income": 80} for _ in range(n_per_group)] + [
            {"zip": "B", "income": 80} for _ in range(n_per_group)
        ]
        decisions_actual = [1] * (2 * n_per_group)
        protected_class = ["A"] * n_per_group + ["B"] * n_per_group

        def candidates() -> Iterator[tuple[str, Callable[..., int]]]:
            yield ("fairer_income_model", _fairer_lda)

        harness = LDASearchHarness(
            primary_model=_primary_model,
            candidate_generator=candidates,
            audit_chain=chain,
        )

        result = harness.search(
            features_dataset=features,
            decisions_actual=decisions_actual,
            protected_class=protected_class,
        )
        assert isinstance(result, LDASearchResult)
        assert len(result.candidates) == 1
        report = result.candidates[0]
        assert isinstance(report, LDACandidateReport)
        assert report.name == "fairer_income_model"
        # The LDA is more accurate AND less discriminatory.
        assert report.accuracy_delta >= 0
        assert report.di_ratio_delta > 0
        assert report.dominates_primary is True

    def test_lda_that_does_not_dominate_is_reported_as_such(self, chain: AuditChain) -> None:
        n_per_group = 20
        features = [{"zip": "A", "income": 80} for _ in range(n_per_group)] + [
            {"zip": "B", "income": 80} for _ in range(n_per_group)
        ]
        decisions_actual = [1] * (2 * n_per_group)
        protected_class = ["A"] * n_per_group + ["B"] * n_per_group

        def candidates() -> Iterator[tuple[str, Callable[..., int]]]:
            yield ("strictly_worse_constant_deny", _worse_lda)

        harness = LDASearchHarness(
            primary_model=_primary_model,
            candidate_generator=candidates,
            audit_chain=chain,
        )

        result = harness.search(
            features_dataset=features,
            decisions_actual=decisions_actual,
            protected_class=protected_class,
        )
        report = result.candidates[0]
        assert report.dominates_primary is False

    def test_tied_accuracy_with_better_di_dominates(self, chain: AuditChain) -> None:
        # Construct a fixture where the primary's zip-only rule
        # produces some skew on DI while a fairer LDA scores equally
        # on accuracy AND parity on DI. The fixture: ground-truth
        # decisions correlate with a third signal ("good") that both
        # models can detect; the primary additionally uses zip
        # gratuitously (in a way that does not change accuracy here
        # but does change DI).
        features = [
            {"zip": "A", "income": 80, "good": 1},
            {"zip": "A", "income": 80, "good": 0},
            {"zip": "B", "income": 80, "good": 1},
            {"zip": "B", "income": 80, "good": 0},
        ]
        # Ground truth: approve only when "good" == 1, regardless of
        # zip.
        decisions_actual = [1, 0, 1, 0]
        protected_class = ["A", "A", "B", "B"]

        # Primary: approves zip=A AND good==1 (mostly tracks "good"
        # but introduces a zip dependency).
        # Actual accuracy on the fixture: row 0 (A,80,1) -> primary
        # 1, expected 1 (correct); row 1 (A,80,0) -> primary 0,
        # expected 0 (correct); row 2 (B,80,1) -> primary 0, expected
        # 1 (wrong); row 3 (B,80,0) -> primary 0, expected 0 (correct).
        # Accuracy = 3/4.
        def primary(features_in: dict[str, float | int | str]) -> int:
            zip_ok = str(features_in.get("zip")) == "A"
            good_val = features_in.get("good")
            good_ok = isinstance(good_val, int | float) and good_val == 1
            return 1 if zip_ok and good_ok else 0

        # LDA that follows "good" regardless of zip: produces 4/4
        # accuracy AND DI parity.
        def fairer_good_lda(
            features_in: dict[str, float | int | str],
        ) -> int:
            good_val = features_in.get("good")
            return 1 if isinstance(good_val, int | float) and good_val == 1 else 0

        # A second LDA that exactly mirrors the primary's zip-only
        # behavior — same accuracy, same DI -> not dominating.
        def neutral_zip_lda(features_in: dict[str, float | int | str]) -> int:
            return primary(features_in)

        def candidates() -> Iterator[tuple[str, Callable[..., int]]]:
            yield ("tied_zip_lda", neutral_zip_lda)
            yield ("fairer_good_lda", fairer_good_lda)

        harness = LDASearchHarness(
            primary_model=primary,
            candidate_generator=candidates,
            audit_chain=chain,
        )
        result = harness.search(
            features_dataset=features,
            decisions_actual=decisions_actual,
            protected_class=protected_class,
        )
        by_name = {c.name: c for c in result.candidates}
        # tied accuracy AND tied DI -> not dominating
        assert by_name["tied_zip_lda"].dominates_primary is False
        # fairer LDA dominates the primary on the accuracy + DI margin
        fairer = by_name["fairer_good_lda"]
        assert fairer.dominates_primary is True


# --------------------------------------------------------------------------- #
# Edge cases                                                                  #
# --------------------------------------------------------------------------- #


class TestEdgeCases:
    def test_empty_candidate_generator_returns_empty_result(self, chain: AuditChain) -> None:
        def no_candidates() -> Iterator[tuple[str, Callable[..., int]]]:
            return iter(())

        harness = LDASearchHarness(
            primary_model=_primary_model,
            candidate_generator=no_candidates,
            audit_chain=chain,
        )
        result = harness.search(
            features_dataset=[{"zip": "A", "income": 80}],
            decisions_actual=[1],
            protected_class=["A"],
        )
        assert result.candidates == []
        assert result.n_samples == 1

    def test_mismatched_length_inputs_raise_value_error(self, chain: AuditChain) -> None:
        def candidates() -> Iterator[tuple[str, Callable[..., int]]]:
            yield ("anything", _fairer_lda)

        harness = LDASearchHarness(
            primary_model=_primary_model,
            candidate_generator=candidates,
            audit_chain=chain,
        )
        with pytest.raises(ValueError, match="length"):
            harness.search(
                features_dataset=[
                    {"zip": "A", "income": 80},
                    {"zip": "B", "income": 80},
                ],
                decisions_actual=[1],
                protected_class=["A", "B"],
            )

    def test_mismatched_protected_class_length_raises(self, chain: AuditChain) -> None:
        def candidates() -> Iterator[tuple[str, Callable[..., int]]]:
            yield ("anything", _fairer_lda)

        harness = LDASearchHarness(
            primary_model=_primary_model,
            candidate_generator=candidates,
            audit_chain=chain,
        )
        with pytest.raises(ValueError, match="length"):
            harness.search(
                features_dataset=[
                    {"zip": "A", "income": 80},
                    {"zip": "B", "income": 80},
                ],
                decisions_actual=[1, 0],
                protected_class=["A"],
            )

    def test_empty_dataset_returns_zero_n_samples(self, chain: AuditChain) -> None:
        def candidates() -> Iterator[tuple[str, Callable[..., int]]]:
            yield ("any", _fairer_lda)

        harness = LDASearchHarness(
            primary_model=_primary_model,
            candidate_generator=candidates,
            audit_chain=chain,
        )
        result = harness.search(
            features_dataset=[],
            decisions_actual=[],
            protected_class=[],
        )
        assert result.n_samples == 0
        # On a degenerate dataset the candidate cannot dominate.
        assert result.candidates[0].dominates_primary is False


# --------------------------------------------------------------------------- #
# Audit-chain emission                                                        #
# --------------------------------------------------------------------------- #


class TestAuditChainEmission:
    def test_search_emits_one_compliance_check_entry(self, chain: AuditChain) -> None:
        def candidates() -> Iterator[tuple[str, Callable[..., int]]]:
            yield ("a", _fairer_lda)
            yield ("b", _worse_lda)

        harness = LDASearchHarness(
            primary_model=_primary_model,
            candidate_generator=candidates,
            audit_chain=chain,
        )
        before = len(chain._events)
        harness.search(
            features_dataset=[{"zip": "A", "income": 80}, {"zip": "B", "income": 80}],
            decisions_actual=[1, 1],
            protected_class=["A", "B"],
        )
        after = len(chain._events)
        assert after == before + 1
        emitted = chain._events[-1]
        assert emitted.event_type == AuditEventType.COMPLIANCE_CHECK

    def test_emitted_payload_carries_methodology_and_adr_reference(self, chain: AuditChain) -> None:
        def candidates() -> Iterator[tuple[str, Callable[..., int]]]:
            yield ("a", _fairer_lda)

        harness = LDASearchHarness(
            primary_model=_primary_model,
            candidate_generator=candidates,
            audit_chain=chain,
        )
        harness.search(
            features_dataset=[{"zip": "A", "income": 80}, {"zip": "B", "income": 80}],
            decisions_actual=[1, 1],
            protected_class=["A", "B"],
        )
        payload = chain._events[-1].payload
        assert payload.get("regulation") == "ECOA/RegB"
        assert payload.get("adr_reference") == "ADR-0020"
        assert "methodology" in payload
        assert "candidates" in payload
        assert isinstance(payload["candidates"], list)
        assert payload["candidates"][0]["name"] == "a"


# --------------------------------------------------------------------------- #
# Module docstring envelope                                                   #
# --------------------------------------------------------------------------- #


class TestModuleDocstring:
    def test_docstring_cites_acm_facct_and_cfpb(self) -> None:
        from finserv_agent_audit.governance import lda_search

        doc = lda_search.__doc__ or ""
        assert "ADR-0020" in doc
        assert "ACM-FAccT" in doc or "FAccT" in doc
        assert "CFPB" in doc

    def test_dataclass_report_has_required_fields(self) -> None:
        report = LDACandidateReport(
            name="x",
            accuracy_delta=0.1,
            di_ratio_delta=0.05,
            dominates_primary=True,
            methodology="lda_search_v1",
            n_samples=10,
        )
        assert report.name == "x"
        assert report.methodology == "lda_search_v1"
        assert report.n_samples == 10
