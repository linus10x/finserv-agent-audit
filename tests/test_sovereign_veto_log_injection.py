"""Regression test: untrusted fields cannot inject forged log lines.

CR/LF in agent-controlled values (triggered_by, description, operator_id,
reason) must be neutralized by ``_scrub`` before interpolation so an attacker
cannot smuggle a second, forged log record into the stream.
"""

from __future__ import annotations

import logging

import pytest

from finserv_agent_audit.governance.sovereign_veto import (
    SovereignVeto,
    VetoBlockedError,
    VetoReason,
)

FORGED = "real_value\nCRITICAL:root:FORGED LOG LINE injected by attacker"


def _assert_no_embedded_newline(records: list[logging.LogRecord]) -> None:
    for rec in records:
        rendered = rec.getMessage()
        assert "\n" not in rendered, f"embedded newline in: {rendered!r}"
        assert "\r" not in rendered, f"embedded carriage return in: {rendered!r}"


def test_trigger_scrubs_crlf_in_untrusted_fields(caplog) -> None:
    veto = SovereignVeto(agent_id="zeus")
    with caplog.at_level(logging.CRITICAL):
        veto.trigger(VetoReason.RISK_LIMIT_BREACH, FORGED, FORGED)
    # The forged content is still present (scrubbed), but on a single line.
    triggered = [r for r in caplog.records if "SOVEREIGN VETO triggered" in r.getMessage()]
    assert triggered, "expected the veto-trigger log record"
    _assert_no_embedded_newline(triggered)
    assert "FORGED LOG LINE" in triggered[0].getMessage()


def test_clear_scrubs_crlf_in_operator_and_reason(caplog) -> None:
    veto = SovereignVeto(agent_id="zeus")
    veto.trigger(VetoReason.MANUAL_OPERATOR, "operator_001", "initial")
    with caplog.at_level(logging.INFO):
        veto.clear(operator_id="operator_002", reason=FORGED)
    cleared = [r for r in caplog.records if "VETO CLEARED" in r.getMessage()]
    assert cleared, "expected the veto-cleared log record"
    _assert_no_embedded_newline(cleared)


def test_self_clear_rejection_scrubs_crlf(caplog) -> None:
    # agent_id carries the CR/LF; the rejection log must stay single-line.
    veto = SovereignVeto(agent_id="agent\ninjected")
    veto.trigger(VetoReason.MANUAL_OPERATOR, "x", "y")
    with caplog.at_level(logging.CRITICAL), pytest.raises(VetoBlockedError):
        veto.clear(operator_id="agent\ninjected", reason="self")
    rejected = [r for r in caplog.records if "REJECTED self-clearing" in r.getMessage()]
    assert rejected, "expected the self-clear rejection log record"
    _assert_no_embedded_newline(rejected)
