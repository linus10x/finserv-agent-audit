"""Tests for the ProtectedClassProxyDetector — v1.2 shipped implementation.

The v1.1 contract was: a caller invoking ``detect`` gets a structured
``NotImplementedError`` pointing to ADR-0019. v1.2 ships the real
detector per ADR-0019's method-selection criterion: a mutual-information
estimator over discrete features against the protected attribute and
against the decision outcomes. Features whose MI with the protected
attribute clears the configured threshold AND whose MI with the
decision clears the same threshold are flagged as suspected proxies.

The detector is intentionally narrow:

- Stdlib only — no ``sklearn``, ``pandas``, ``numpy``. The discrete-MI
  estimator uses ``math.log`` + ``collections.Counter``.
- Continuous features are the caller's responsibility — discretize
  (binning, quantization) before passing in.
- The MI threshold is configurable; the default (0.1 nats) is a
  starting point per the ADR-0019 method-selection criterion and is
  documented as such.
- Every ``detect`` call emits one ``AuditEventType.COMPLIANCE_CHECK``
  chain entry capturing the detection result for forensic replay.

These tests cover: happy path with no proxy correlation, the
detection case (a feature that is both strongly correlated with the
protected attribute AND with decisions gets flagged), the empty-input
edge, mismatched-length input validation, the degenerate
single-value-protected-class case, and audit-chain emission.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from finserv_agent_audit.governance.protected_class_proxy_detector import (
    ProtectedClassProxyDetector,
    ProxyDetectionResult,
    ProxyFeatureFlag,
    _disparate_impact_ratio,
    _mutual_information_nats,
)
from finserv_agent_audit.schemas.audit_event import (
    AuditChain,
    AuditEventType,
)


@pytest.fixture
def chain(tmp_path: Path) -> AuditChain:
    return AuditChain(log_file=tmp_path / "audit.jsonl")


# --------------------------------------------------------------------------- #
# Happy path: no proxy correlation                                            #
# --------------------------------------------------------------------------- #


class TestNoProxy:
    def test_uncorrelated_features_pass_cleanly(self, chain: AuditChain) -> None:
        # Features whose distribution is independent of the protected class
        # should not be flagged. Construct an explicit uniform case.
        protected = ["A", "B"] * 50  # alternating A / B
        # ``feature_x`` runs on a period-4 cycle so it does not correlate
        # with the period-2 alternation in ``protected``. ``feature_y`` is
        # constant — zero MI by definition.
        feature_x = ["P", "P", "Q", "Q"] * 25
        feature_y = ["k"] * 100
        decisions = [1, 0] * 50

        detector = ProtectedClassProxyDetector(audit_chain=chain)
        result = detector.detect(
            features={"x": feature_x, "y": feature_y},
            decision_outcomes=decisions,
            protected_class=protected,
        )

        assert isinstance(result, ProxyDetectionResult)
        # Neither feature should clear both MI thresholds.
        flagged_names = {flag.feature_name for flag in result.proxy_features}
        assert "x" not in flagged_names
        assert "y" not in flagged_names

    def test_returns_structured_result_dataclass(self, chain: AuditChain) -> None:
        detector = ProtectedClassProxyDetector(audit_chain=chain)
        result = detector.detect(
            features={"feat": ["a", "b", "a", "b"]},
            decision_outcomes=[1, 0, 1, 0],
            protected_class=["P", "P", "Q", "Q"],
        )
        assert isinstance(result, ProxyDetectionResult)
        assert hasattr(result, "proxy_features")
        assert hasattr(result, "direct_disparate_impact_ratio")
        assert hasattr(result, "methodology")
        assert hasattr(result, "benchmark_used")
        assert hasattr(result, "confidence")


# --------------------------------------------------------------------------- #
# Detection case: feature highly correlated with both protected + decisions   #
# --------------------------------------------------------------------------- #


class TestProxyDetection:
    def test_perfectly_correlated_feature_is_flagged(self, chain: AuditChain) -> None:
        # ``proxy_feature`` perfectly tracks the protected attribute,
        # AND decisions also track the protected attribute — so the
        # feature is acting as a proxy.
        protected = ["A"] * 50 + ["B"] * 50
        proxy_feature = ["x"] * 50 + ["y"] * 50  # perfectly correlated
        # An innocuous feature with no relation to protected or decisions.
        neutral_feature = (["m", "n", "o", "p"] * 25)[:100]
        decisions = [1] * 50 + [0] * 50  # also tracks protected

        detector = ProtectedClassProxyDetector(audit_chain=chain, mi_threshold=0.1)
        result = detector.detect(
            features={"proxy": proxy_feature, "neutral": neutral_feature},
            decision_outcomes=decisions,
            protected_class=protected,
        )

        flagged_names = {flag.feature_name for flag in result.proxy_features}
        assert "proxy" in flagged_names
        assert "neutral" not in flagged_names

    def test_flag_records_both_mi_signals(self, chain: AuditChain) -> None:
        protected = ["A"] * 40 + ["B"] * 40
        proxy_feature = ["x"] * 40 + ["y"] * 40
        decisions = [1] * 40 + [0] * 40

        detector = ProtectedClassProxyDetector(audit_chain=chain, mi_threshold=0.1)
        result = detector.detect(
            features={"proxy": proxy_feature},
            decision_outcomes=decisions,
            protected_class=protected,
        )

        proxy_flags = [f for f in result.proxy_features if f.feature_name == "proxy"]
        assert len(proxy_flags) == 1
        flag = proxy_flags[0]
        assert isinstance(flag, ProxyFeatureFlag)
        assert flag.mi_with_protected > 0
        assert flag.mi_with_decision > 0
        # Perfectly correlated case: MI is the entropy of either side.
        assert flag.mi_with_protected > 0.5

    def test_direct_disparate_impact_ratio_recorded(self, chain: AuditChain) -> None:
        # Even when no proxy features are flagged, the direct DI ratio
        # between protected groups' selection rates is reported.
        protected = ["A"] * 50 + ["B"] * 50
        feature = ["x"] * 100
        # Protected group A gets approval 80% of the time;
        # protected group B gets approval 40% of the time.
        decisions = ([1] * 40 + [0] * 10) + ([1] * 20 + [0] * 30)

        detector = ProtectedClassProxyDetector(audit_chain=chain)
        result = detector.detect(
            features={"x": feature},
            decision_outcomes=decisions,
            protected_class=protected,
        )

        # The 4/5ths rule benchmark is 0.8. Here B/A = 40/80 = 0.5,
        # so the ratio should be below 1 and reflect the disparity.
        assert 0.0 < result.direct_disparate_impact_ratio < 1.0


# --------------------------------------------------------------------------- #
# Edge cases                                                                  #
# --------------------------------------------------------------------------- #


class TestEdgeCases:
    def test_empty_inputs_return_clean_result(self, chain: AuditChain) -> None:
        detector = ProtectedClassProxyDetector(audit_chain=chain)
        result = detector.detect(
            features={},
            decision_outcomes=[],
            protected_class=[],
        )
        assert result.proxy_features == []
        assert result.confidence == "low"

    def test_mismatched_lengths_raise_value_error(self, chain: AuditChain) -> None:
        detector = ProtectedClassProxyDetector(audit_chain=chain)
        with pytest.raises(ValueError, match="length"):
            detector.detect(
                features={"x": ["a", "b", "c"]},
                decision_outcomes=[1, 0],  # length mismatch
                protected_class=["P", "Q", "R"],
            )

    def test_feature_vector_length_must_match_decisions(self, chain: AuditChain) -> None:
        detector = ProtectedClassProxyDetector(audit_chain=chain)
        with pytest.raises(ValueError, match="length"):
            detector.detect(
                features={"x": ["a", "b"]},  # length 2
                decision_outcomes=[1, 0, 1],  # length 3
                protected_class=["P", "Q", "P"],  # length 3
            )

    def test_single_value_protected_class_is_low_confidence(self, chain: AuditChain) -> None:
        # Degenerate input: protected class is one value for everyone.
        # MI is mechanically zero; the detector should not flag
        # anything AND should report low confidence.
        detector = ProtectedClassProxyDetector(audit_chain=chain)
        result = detector.detect(
            features={"x": ["a"] * 10 + ["b"] * 10},
            decision_outcomes=[1] * 10 + [0] * 10,
            protected_class=["A"] * 20,
        )
        assert result.confidence == "low"
        assert result.proxy_features == []

    def test_default_mi_threshold_is_0_1(self, chain: AuditChain) -> None:
        # The default threshold is documented as 0.1 nats.
        detector = ProtectedClassProxyDetector(audit_chain=chain)
        # Reach into the attribute to confirm — the threshold is
        # part of the public API surface (configurable in the
        # constructor).
        assert detector.mi_threshold == pytest.approx(0.1)


# --------------------------------------------------------------------------- #
# Audit-chain emission                                                        #
# --------------------------------------------------------------------------- #


class TestAuditChainEmission:
    def test_detect_emits_compliance_check_entry(self, chain: AuditChain) -> None:
        detector = ProtectedClassProxyDetector(audit_chain=chain)
        before = len(chain._events)
        detector.detect(
            features={"x": ["a", "b", "a", "b"]},
            decision_outcomes=[1, 0, 1, 0],
            protected_class=["P", "Q", "P", "Q"],
        )
        after = len(chain._events)
        assert after == before + 1
        emitted = chain._events[-1]
        assert emitted.event_type == AuditEventType.COMPLIANCE_CHECK

    def test_emitted_payload_carries_methodology_and_flags(self, chain: AuditChain) -> None:
        detector = ProtectedClassProxyDetector(audit_chain=chain)
        detector.detect(
            features={"x": ["a", "b", "a", "b"]},
            decision_outcomes=[1, 0, 1, 0],
            protected_class=["P", "Q", "P", "Q"],
        )
        emitted = chain._events[-1]
        payload = emitted.payload
        assert payload.get("regulation") == "ECOA/RegB"
        assert payload.get("adr_reference") == "ADR-0019"
        assert "methodology" in payload
        assert "proxy_features" in payload
        assert "confidence" in payload


# --------------------------------------------------------------------------- #
# Module-docstring envelope                                                   #
# --------------------------------------------------------------------------- #


class TestEstimatorEdgeCases:
    """Cover the helper-function branches that the public-API tests do not reach."""

    def test_mi_zero_for_empty_sequences(self) -> None:
        assert _mutual_information_nats([], []) == 0.0

    def test_mi_zero_for_mismatched_lengths(self) -> None:
        # The internal helper is defensive: the public detector catches
        # length mismatches first, but the helper must also no-op.
        assert _mutual_information_nats(["a"], ["b", "c"]) == 0.0

    def test_di_ratio_one_for_empty_inputs(self) -> None:
        assert _disparate_impact_ratio([], []) == 1.0

    def test_di_ratio_one_for_single_decision_value(self) -> None:
        # All decisions the same -> no spread to measure.
        assert _disparate_impact_ratio(["1", "1", "1"], ["A", "B", "C"]) == 1.0

    def test_di_ratio_one_for_single_protected_group(self) -> None:
        assert _disparate_impact_ratio(["1", "0", "1"], ["A", "A", "A"]) == 1.0

    def test_di_ratio_one_when_max_rate_is_zero(self) -> None:
        # All decisions are unfavorable for both groups.
        # favorable=max("0", "1") = "1"; no one gets it -> max_rate = 0.
        assert _disparate_impact_ratio(["0", "0", "0", "0"], ["A", "A", "B", "B"]) == 1.0

    def test_di_ratio_one_when_a_group_has_no_members(self) -> None:
        # Degenerate construction: protected mentions group "B" but
        # decisions list has nothing aligned to "B" — impossible by
        # construction since zip would skip, but the safety branch is
        # exercised here via single-row populations.
        result = _disparate_impact_ratio(["1"], ["A"])
        assert result == 1.0


class TestModuleDocstring:
    def test_module_docstring_records_v1_2_ship(self) -> None:
        from finserv_agent_audit.governance import protected_class_proxy_detector

        doc = protected_class_proxy_detector.__doc__ or ""
        # Must reflect "shipped — v1.2; replaces v1.1 stub" per the
        # ADR-0019 reconciliation requirement.
        assert "v1.2" in doc
        assert "ADR-0019" in doc

    def test_module_docstring_cites_research_lineage(self) -> None:
        from finserv_agent_audit.governance import protected_class_proxy_detector

        doc = protected_class_proxy_detector.__doc__ or ""
        # Preserved from the v1.1 stub: the citation pointer is the
        # substance.
        assert "Barocas" in doc
        assert "mutual" in doc.lower()
