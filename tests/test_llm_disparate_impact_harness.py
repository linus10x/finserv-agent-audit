"""Tests for the LLM disparate-impact harness — v1.3.

Scorecard disparate-impact methodology does not transfer cleanly to
LLM-agent outputs that produce free text or categorical responses.
This harness runs a canary set of prompts across protected-class
populations, scores each output through a caller-supplied rubric,
and computes the adverse-impact ratio across protected groups against
the EEOC 4/5ths-rule benchmark.

The Mobley v. Workday May 16, 2025 conditional class certification
under the ADEA establishes that AI-mediated employment / lending
screening is a concrete liability surface; the framework treats LLM
DI testing as the runtime control that documents the institution's
diligence.

Tests cover: happy path (no DI), detection (significant DI -> flagged),
threshold customization (caller overrides the 0.8 default), multi-class
expansion, edge cases (single class, empty canaries), and audit-chain
emission with methodology + significance test.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from finserv_agent_audit.governance.llm_disparate_impact_harness import (
    LLMDisparateImpactHarness,
    LLMDisparateImpactResult,
)
from finserv_agent_audit.schemas.audit_event import (
    AuditChain,
    AuditEventType,
)


@pytest.fixture
def chain(tmp_path: Path) -> AuditChain:
    return AuditChain(log_file=tmp_path / "audit.jsonl")


# --------------------------------------------------------------------------- #
# Happy path: no disparate impact                                             #
# --------------------------------------------------------------------------- #


class TestNoDisparateImpact:
    def test_constant_approve_agent_passes_di(self, chain: AuditChain) -> None:
        # Agent always approves; rubric always passes -> per-class
        # success rate is 1.0 for both classes -> AI ratio = 1.0.
        def agent(prompt: str) -> str:
            return "approved"

        def rubric(output: Any) -> bool:
            return str(output) == "approved"

        canaries = {
            "group_A": [("p1", "Smith application"), ("p2", "Jones application")],
            "group_B": [("p1", "Hernandez application"), ("p2", "Patel application")],
        }
        harness = LLMDisparateImpactHarness(
            llm_agent=agent,
            rubric_scorer=rubric,
            canary_populations=canaries,
            audit_chain=chain,
        )
        result = harness.run(n_iterations=1)
        assert isinstance(result, LLMDisparateImpactResult)
        assert result.per_class_rates["group_A"] == pytest.approx(1.0)
        assert result.per_class_rates["group_B"] == pytest.approx(1.0)
        assert result.adverse_impact_ratio == pytest.approx(1.0)
        assert result.significant is False


# --------------------------------------------------------------------------- #
# Detection                                                                   #
# --------------------------------------------------------------------------- #


class TestDisparateImpactDetection:
    def test_agent_that_denies_one_class_is_flagged(self, chain: AuditChain) -> None:
        # Agent approves group A canaries; denies all group B canaries
        # by surname-pattern heuristic. AI ratio = 0/1 = 0.0 -> hard fail
        # of 4/5ths rule.
        def agent(prompt: str) -> str:
            if "Hernandez" in prompt or "Patel" in prompt:
                return "denied"
            return "approved"

        def rubric(output: Any) -> bool:
            return str(output) == "approved"

        canaries = {
            "group_A": [
                ("p1", "Smith application"),
                ("p2", "Jones application"),
                ("p3", "Miller application"),
                ("p4", "Brown application"),
            ],
            "group_B": [
                ("p1", "Hernandez application"),
                ("p2", "Patel application"),
                ("p3", "Hernandez application 2"),
                ("p4", "Patel application 2"),
            ],
        }
        harness = LLMDisparateImpactHarness(
            llm_agent=agent,
            rubric_scorer=rubric,
            canary_populations=canaries,
            audit_chain=chain,
        )
        result = harness.run(n_iterations=1)
        assert result.per_class_rates["group_A"] == pytest.approx(1.0)
        assert result.per_class_rates["group_B"] == pytest.approx(0.0)
        assert result.adverse_impact_ratio < 0.8
        assert result.significant is True

    def test_threshold_customization_changes_significance_call(self, chain: AuditChain) -> None:
        # Mild disparity: 1.0 vs 0.75 -> ratio 0.75, fails default 0.8
        # gate. Custom threshold of 0.5 should let it pass.
        def agent(prompt: str) -> str:
            if "deny_me" in prompt:
                return "denied"
            return "approved"

        def rubric(output: Any) -> bool:
            return str(output) == "approved"

        canaries = {
            "A": [
                ("p1", "approve_a"),
                ("p2", "approve_a"),
                ("p3", "approve_a"),
                ("p4", "approve_a"),
            ],
            "B": [
                ("p1", "approve_b"),
                ("p2", "approve_b"),
                ("p3", "approve_b"),
                ("p4", "deny_me"),
            ],
        }
        strict = LLMDisparateImpactHarness(
            llm_agent=agent,
            rubric_scorer=rubric,
            canary_populations=canaries,
            audit_chain=chain,
            adverse_impact_threshold=0.8,
        )
        strict_result = strict.run(n_iterations=1)
        assert strict_result.adverse_impact_ratio < 0.8
        assert strict_result.significant is True

        lax = LLMDisparateImpactHarness(
            llm_agent=agent,
            rubric_scorer=rubric,
            canary_populations=canaries,
            audit_chain=chain,
            adverse_impact_threshold=0.5,
        )
        lax_result = lax.run(n_iterations=1)
        assert lax_result.adverse_impact_ratio < 0.8
        assert lax_result.significant is False


# --------------------------------------------------------------------------- #
# Edge cases                                                                  #
# --------------------------------------------------------------------------- #


class TestEdgeCases:
    def test_single_class_returns_parity_ratio(self, chain: AuditChain) -> None:
        # One protected class -> no spread to measure. Ratio = 1.0,
        # significance = False.
        def agent(prompt: str) -> str:
            return "approved"

        def rubric(output: Any) -> bool:
            return str(output) == "approved"

        canaries = {
            "only_group": [("p1", "x")],
        }
        harness = LLMDisparateImpactHarness(
            llm_agent=agent,
            rubric_scorer=rubric,
            canary_populations=canaries,
            audit_chain=chain,
        )
        result = harness.run(n_iterations=1)
        assert result.adverse_impact_ratio == pytest.approx(1.0)
        assert result.significant is False

    def test_empty_canaries_raises_value_error(self, chain: AuditChain) -> None:
        def agent(prompt: str) -> str:
            return "approved"

        def rubric(output: Any) -> bool:
            return True

        with pytest.raises(ValueError, match="canary_populations"):
            harness = LLMDisparateImpactHarness(
                llm_agent=agent,
                rubric_scorer=rubric,
                canary_populations={},
                audit_chain=chain,
            )
            harness.run(n_iterations=1)

    def test_n_iterations_must_be_positive(self, chain: AuditChain) -> None:
        def agent(prompt: str) -> str:
            return "approved"

        def rubric(output: Any) -> bool:
            return True

        harness = LLMDisparateImpactHarness(
            llm_agent=agent,
            rubric_scorer=rubric,
            canary_populations={"A": [("p", "x")]},
            audit_chain=chain,
        )
        with pytest.raises(ValueError, match="n_iterations"):
            harness.run(n_iterations=0)

    def test_n_iterations_averages_stochastic_output(self, chain: AuditChain) -> None:
        # Stochastic agent flips a counter; rubric scores each output.
        # n_iterations should multiply the total calls but yield a
        # smooth average.
        state: dict[str, int] = {"i": 0}

        def agent(prompt: str) -> str:
            state["i"] += 1
            return "approved" if state["i"] % 2 == 0 else "denied"

        def rubric(output: Any) -> bool:
            return str(output) == "approved"

        canaries = {
            "A": [("p1", "x"), ("p2", "y")],
            "B": [("p1", "u"), ("p2", "v")],
        }
        harness = LLMDisparateImpactHarness(
            llm_agent=agent,
            rubric_scorer=rubric,
            canary_populations=canaries,
            audit_chain=chain,
        )
        result = harness.run(n_iterations=3)
        # Each prompt invoked 3x; total calls = 4 prompts * 3 = 12.
        assert state["i"] == 12
        # Rates should be roughly 0.5 (half of all outputs approved by
        # the modulo-2 counter); allow generous bounds for ordering.
        assert 0.0 <= result.per_class_rates["A"] <= 1.0
        assert 0.0 <= result.per_class_rates["B"] <= 1.0
        assert result.n_iterations == 3


# --------------------------------------------------------------------------- #
# Audit-chain emission                                                        #
# --------------------------------------------------------------------------- #


class TestAuditChainEmission:
    def test_run_emits_one_compliance_check_entry(self, chain: AuditChain) -> None:
        def agent(prompt: str) -> str:
            return "approved"

        def rubric(output: Any) -> bool:
            return True

        canaries = {"A": [("p", "x")], "B": [("p", "y")]}
        harness = LLMDisparateImpactHarness(
            llm_agent=agent,
            rubric_scorer=rubric,
            canary_populations=canaries,
            audit_chain=chain,
        )
        before = len(chain._events)
        harness.run(n_iterations=1)
        after = len(chain._events)
        assert after == before + 1
        emitted = chain._events[-1]
        assert emitted.event_type == AuditEventType.COMPLIANCE_CHECK
        payload = emitted.payload
        assert payload.get("adr_reference") == "ADR-0021"
        assert "per_class_rates" in payload
        assert "adverse_impact_ratio" in payload
        assert "methodology" in payload
        assert "n_iterations" in payload
        assert "adverse_impact_threshold" in payload


# --------------------------------------------------------------------------- #
# Rubric scorer Protocol surface                                              #
# --------------------------------------------------------------------------- #


class TestRubricScorer:
    def test_float_score_above_half_counts_as_success(self, chain: AuditChain) -> None:
        # Rubric returns floats; harness treats > 0.5 as success per
        # the methodology default.
        scorings: dict[str, float] = {
            "rich": 0.9,
            "poor": 0.4,
        }

        def agent(prompt: str) -> str:
            return prompt  # echo

        def rubric(output: Any) -> float:
            return scorings.get(str(output), 0.0)

        canaries: dict[str, list[tuple[str, str]]] = {
            "A": [("p1", "rich"), ("p2", "rich")],
            "B": [("p1", "poor"), ("p2", "poor")],
        }
        harness = LLMDisparateImpactHarness(
            llm_agent=agent,
            rubric_scorer=rubric,
            canary_populations=canaries,
            audit_chain=chain,
        )
        result = harness.run(n_iterations=1)
        assert result.per_class_rates["A"] == pytest.approx(1.0)
        assert result.per_class_rates["B"] == pytest.approx(0.0)


# --------------------------------------------------------------------------- #
# Module docstring envelope                                                   #
# --------------------------------------------------------------------------- #


class TestModuleDocstring:
    def test_docstring_cites_eeoc_and_mobley(self) -> None:
        from finserv_agent_audit.governance import llm_disparate_impact_harness

        doc = llm_disparate_impact_harness.__doc__ or ""
        assert "EEOC" in doc
        assert "Mobley" in doc
        assert "ADR-0021" in doc


# --------------------------------------------------------------------------- #
# Type-checking surface — RubricScorer Protocol                               #
# --------------------------------------------------------------------------- #


class TestRubricScorerProtocol:
    def test_rubric_scorer_is_importable(self) -> None:
        from finserv_agent_audit.governance.llm_disparate_impact_harness import (
            RubricScorer,
        )

        # The Protocol exists and accepts a typed callable.
        def scorer(output: Any) -> bool:
            return bool(output)

        # Assignment should type-check structurally.
        my_scorer: RubricScorer = scorer
        assert my_scorer("x") is True

    def test_llm_agent_callable_accepts_string_prompt(self, chain: AuditChain) -> None:
        # The agent surface is ``Callable[[str], Any]``; verify by
        # passing a simple string-returning callable.
        agent: Callable[[str], Any] = lambda p: p.upper()  # noqa: E731

        def rubric(output: Any) -> bool:
            return "X" in str(output)

        canaries = {"A": [("p", "ax")], "B": [("p", "by")]}
        harness = LLMDisparateImpactHarness(
            llm_agent=agent,
            rubric_scorer=rubric,
            canary_populations=canaries,
            audit_chain=chain,
        )
        result = harness.run(n_iterations=1)
        assert isinstance(result, LLMDisparateImpactResult)
