"""Tests for the ProtectedClassProxyDetector stub (ADR-0019 deferred).

The stub's contract is: a caller invoking ``detect`` gets a structured
``NotImplementedError`` pointing to ADR-0019 within thirty seconds of
reading the docs. The stub signals engagement; the runtime answer ships
in v1.2 with evaluated false-positive and false-negative rates against
the HMDA benchmark.
"""

from __future__ import annotations

import pytest

from finserv_agent_audit.governance.protected_class_proxy_detector import (
    ProtectedClassProxyDetector,
)


class TestStubContract:
    def test_detect_raises_not_implemented(self) -> None:
        detector = ProtectedClassProxyDetector()
        with pytest.raises(NotImplementedError):
            detector.detect(
                features={"zip_code": "75201", "surname": "Bhaduri"},
                decision_outcomes=[1, 0, 1, 1, 0],
            )

    def test_error_message_references_adr_0019(self) -> None:
        detector = ProtectedClassProxyDetector()
        with pytest.raises(NotImplementedError) as exc:
            detector.detect(features={}, decision_outcomes=[])
        message = str(exc.value)
        assert "ADR-0019" in message

    def test_error_message_references_v1_2(self) -> None:
        detector = ProtectedClassProxyDetector()
        with pytest.raises(NotImplementedError) as exc:
            detector.detect(features={}, decision_outcomes=[])
        assert "v1.2" in str(exc.value)

    def test_detect_callable_on_empty_inputs(self) -> None:
        # The stub raises before any computation — empty inputs are valid call.
        detector = ProtectedClassProxyDetector()
        with pytest.raises(NotImplementedError):
            detector.detect(features={}, decision_outcomes=[])

    def test_module_docstring_cites_research_lineage(self) -> None:
        from finserv_agent_audit.governance import protected_class_proxy_detector

        doc = protected_class_proxy_detector.__doc__ or ""
        # The docstring is the substance of the stub.
        assert "Barocas" in doc
        assert "ADR-0019" in doc
        assert "mutual" in doc.lower()
