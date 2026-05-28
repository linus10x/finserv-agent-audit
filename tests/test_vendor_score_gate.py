"""Tests for VendorScoreGate (third-party AI scoring with audit-chain emit).

Implements the test surface named in ADR-0016: round-trip emit + read-back
per FSI vendor class (KYC, fraud-score, credit-decision, robo-advisor signal,
AML transaction monitoring), score-drift detection on same (input_hash,
model_version), model-version change recorded not absorbed, and chain-verify
parity for vendor entries.

Score drift is the load-bearing assertion. A vendor silently shipping a
patched model is the exact failure ADR-0016 names — and the operator carries
the regulatory exposure under FCRA, ECOA, BSA, SR 11-7, and CFPB UDAAP.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from finserv_agent_audit.governance.vendor_score_gate import (
    InMemoryVendorScoreGate,
    VendorClass,
    VendorScoreDriftDetected,
    VendorScoreEntry,
    VendorScoreGate,
)
from finserv_agent_audit.schemas.audit_event import (
    AuditChain,
    AuditEventType,
    AutonomyLevel,
)


def _input_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@pytest.fixture
def tmp_chain(tmp_path: Path) -> AuditChain:
    """Fresh AuditChain backed by a per-test tmp log file."""
    return AuditChain(log_file=tmp_path / "audit_chain.jsonl")


# --------------------------------------------------------------------------- #
# 1. Protocol conformance                                                     #
# --------------------------------------------------------------------------- #


def test_in_memory_vendor_score_gate_is_a_vendor_score_gate(tmp_chain: AuditChain) -> None:
    gate: VendorScoreGate = InMemoryVendorScoreGate(audit_chain=tmp_chain)
    assert hasattr(gate, "emit")
    assert hasattr(gate, "history_for")


# --------------------------------------------------------------------------- #
# 2. Round-trip emit + read-back                                              #
# --------------------------------------------------------------------------- #


def test_emit_records_kyc_vendor_score_to_audit_chain(tmp_chain: AuditChain) -> None:
    gate = InMemoryVendorScoreGate(audit_chain=tmp_chain)
    entry = gate.emit(
        vendor_id="persona-class",
        vendor_class=VendorClass.KYC,
        input_hash=_input_hash(b"applicant-1"),
        score=0.82,
        model_version="v3.1.0",
    )
    assert isinstance(entry, VendorScoreEntry)
    assert entry.vendor_id == "persona-class"
    assert entry.vendor_class is VendorClass.KYC
    assert entry.score == pytest.approx(0.82)
    assert entry.model_version == "v3.1.0"
    # Chain has exactly one entry; event_type is the v1.1 enum value.
    assert len(tmp_chain._events) == 1
    chain_event = tmp_chain._events[0]
    assert chain_event.event_type is AuditEventType.VENDOR_SCORE_RECORDED
    assert chain_event.agent_id == "persona-class"
    assert chain_event.payload["vendor_class"] == "kyc"


def test_history_for_returns_entries_in_emit_order(tmp_chain: AuditChain) -> None:
    gate = InMemoryVendorScoreGate(audit_chain=tmp_chain)
    input_hash = _input_hash(b"applicant-2")
    gate.emit(
        vendor_id="alloy-class",
        vendor_class=VendorClass.KYC,
        input_hash=input_hash,
        score=0.50,
        model_version="v3.1.0",
    )
    gate.emit(
        vendor_id="alloy-class",
        vendor_class=VendorClass.KYC,
        input_hash=input_hash,
        score=0.50,
        model_version="v3.2.0",
    )
    history = gate.history_for(vendor_id="alloy-class", input_hash=input_hash)
    assert [h.model_version for h in history] == ["v3.1.0", "v3.2.0"]
    assert all(h.vendor_class is VendorClass.KYC for h in history)


@pytest.mark.parametrize(
    "vendor_class",
    [
        VendorClass.KYC,
        VendorClass.FRAUD_SCORE,
        VendorClass.CREDIT_DECISION,
        VendorClass.ROBO_ADVISOR_SIGNAL,
        VendorClass.AML_TRANSACTION_MONITORING,
    ],
)
def test_emit_round_trip_for_every_fsi_vendor_class(
    tmp_chain: AuditChain, vendor_class: VendorClass
) -> None:
    """ADR-0016 enumerates five FSI vendor classes — each round-trips."""
    gate = InMemoryVendorScoreGate(audit_chain=tmp_chain)
    input_hash = _input_hash(f"applicant-{vendor_class.value}".encode())
    entry = gate.emit(
        vendor_id=f"vendor-{vendor_class.value}",
        vendor_class=vendor_class,
        input_hash=input_hash,
        score=0.42,
        model_version="v1.0.0",
    )
    assert entry.vendor_class is vendor_class
    chain_event = tmp_chain._events[-1]
    assert chain_event.payload["vendor_class"] == vendor_class.value
    history = gate.history_for(vendor_id=f"vendor-{vendor_class.value}", input_hash=input_hash)
    assert len(history) == 1
    assert history[0].vendor_class is vendor_class


# --------------------------------------------------------------------------- #
# 3. Score-drift detection                                                    #
# --------------------------------------------------------------------------- #


def test_same_input_same_model_different_score_raises_drift(tmp_chain: AuditChain) -> None:
    """The exact silent-vendor-patch failure: same input + same model_version,
    score moves. Must be detected, not absorbed.
    """
    gate = InMemoryVendorScoreGate(audit_chain=tmp_chain)
    input_hash = _input_hash(b"applicant-3")
    gate.emit(
        vendor_id="zest-class",
        vendor_class=VendorClass.CREDIT_DECISION,
        input_hash=input_hash,
        score=0.50,
        model_version="v3.1.0",
    )
    with pytest.raises(VendorScoreDriftDetected) as excinfo:
        gate.emit(
            vendor_id="zest-class",
            vendor_class=VendorClass.CREDIT_DECISION,
            input_hash=input_hash,
            score=0.65,
            model_version="v3.1.0",
        )
    msg = str(excinfo.value)
    assert "zest-class" in msg
    assert "v3.1.0" in msg
    assert "credit_decision" in msg


def test_drift_entry_recorded_to_chain_even_when_raising(tmp_chain: AuditChain) -> None:
    """The drift detection itself is an auditable event; the flagged entry
    must hit the chain before the exception propagates.
    """
    gate = InMemoryVendorScoreGate(audit_chain=tmp_chain)
    input_hash = _input_hash(b"applicant-4")
    gate.emit(
        vendor_id="sift-class",
        vendor_class=VendorClass.FRAUD_SCORE,
        input_hash=input_hash,
        score=0.50,
        model_version="v3.1.0",
    )
    with pytest.raises(VendorScoreDriftDetected):
        gate.emit(
            vendor_id="sift-class",
            vendor_class=VendorClass.FRAUD_SCORE,
            input_hash=input_hash,
            score=0.65,
            model_version="v3.1.0",
        )
    # Two chain events: original recorded + drift detected.
    assert len(tmp_chain._events) == 2
    drift_event = tmp_chain._events[1]
    assert drift_event.event_type is AuditEventType.VENDOR_SCORE_DRIFT_DETECTED
    assert drift_event.agent_id == "sift-class"
    assert drift_event.payload["gate_verdict"] == "drift_flagged"
    assert drift_event.payload["previous_score"] == pytest.approx(0.50)


def test_strict_drift_mode_can_be_disabled(tmp_chain: AuditChain) -> None:
    """When raise_on_drift=False (shadow-mode rollouts), drift is recorded
    but does not raise — required for staged production cutovers.
    """
    gate = InMemoryVendorScoreGate(audit_chain=tmp_chain, raise_on_drift=False)
    input_hash = _input_hash(b"applicant-5")
    gate.emit(
        vendor_id="actimize-class",
        vendor_class=VendorClass.AML_TRANSACTION_MONITORING,
        input_hash=input_hash,
        score=0.50,
        model_version="v3.1.0",
    )
    entry = gate.emit(
        vendor_id="actimize-class",
        vendor_class=VendorClass.AML_TRANSACTION_MONITORING,
        input_hash=input_hash,
        score=0.65,
        model_version="v3.1.0",
    )
    assert entry.drift_detected is True
    assert entry.previous_score == pytest.approx(0.50)
    # Chain still records both events.
    assert len(tmp_chain._events) == 2


# --------------------------------------------------------------------------- #
# 4. Model-version change recorded, not absorbed                              #
# --------------------------------------------------------------------------- #


def test_same_input_different_model_version_is_not_drift(tmp_chain: AuditChain) -> None:
    """A new model_version is a legitimate vendor change. The new score is
    recorded in the chain as its own entry; no drift exception.
    """
    gate = InMemoryVendorScoreGate(audit_chain=tmp_chain)
    input_hash = _input_hash(b"applicant-6")
    gate.emit(
        vendor_id="robo-advisor-class",
        vendor_class=VendorClass.ROBO_ADVISOR_SIGNAL,
        input_hash=input_hash,
        score=0.50,
        model_version="v3.1.0",
    )
    second = gate.emit(
        vendor_id="robo-advisor-class",
        vendor_class=VendorClass.ROBO_ADVISOR_SIGNAL,
        input_hash=input_hash,
        score=0.65,
        model_version="v3.2.0",
    )
    assert second.drift_detected is False
    assert len(tmp_chain._events) == 2
    assert tmp_chain._events[1].event_type is AuditEventType.VENDOR_SCORE_RECORDED


# --------------------------------------------------------------------------- #
# 5. Vendor entries pass standard verify                                      #
# --------------------------------------------------------------------------- #


def test_vendor_entries_pass_standard_audit_chain_verify(tmp_chain: AuditChain) -> None:
    gate = InMemoryVendorScoreGate(audit_chain=tmp_chain)
    for i in range(3):
        gate.emit(
            vendor_id="persona-class",
            vendor_class=VendorClass.KYC,
            input_hash=_input_hash(f"applicant-{i}".encode()),
            score=0.5 + i * 0.1,
            model_version="v3.1.0",
        )
    assert tmp_chain.verify() is True


def test_vendor_drift_entries_pass_standard_audit_chain_verify(tmp_chain: AuditChain) -> None:
    gate = InMemoryVendorScoreGate(audit_chain=tmp_chain, raise_on_drift=False)
    input_hash = _input_hash(b"applicant-X")
    gate.emit(
        vendor_id="persona-class",
        vendor_class=VendorClass.KYC,
        input_hash=input_hash,
        score=0.50,
        model_version="v3.1.0",
    )
    gate.emit(
        vendor_id="persona-class",
        vendor_class=VendorClass.KYC,
        input_hash=input_hash,
        score=0.99,
        model_version="v3.1.0",
    )
    assert len(tmp_chain._events) == 2
    assert tmp_chain.verify() is True


# --------------------------------------------------------------------------- #
# 6. Score range validation at gate level                                     #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("bad_score", [-0.01, 1.01, float("nan"), float("inf")])
def test_emit_rejects_out_of_range_score(tmp_chain: AuditChain, bad_score: float) -> None:
    gate = InMemoryVendorScoreGate(audit_chain=tmp_chain)
    with pytest.raises(ValueError):
        gate.emit(
            vendor_id="persona-class",
            vendor_class=VendorClass.KYC,
            input_hash=_input_hash(b"applicant-x"),
            score=bad_score,
            model_version="v3.1.0",
        )


def test_emit_rejects_empty_input_hash(tmp_chain: AuditChain) -> None:
    gate = InMemoryVendorScoreGate(audit_chain=tmp_chain)
    with pytest.raises(ValueError):
        gate.emit(
            vendor_id="persona-class",
            vendor_class=VendorClass.KYC,
            input_hash="",
            score=0.5,
            model_version="v3.1.0",
        )


def test_emit_rejects_empty_vendor_id(tmp_chain: AuditChain) -> None:
    gate = InMemoryVendorScoreGate(audit_chain=tmp_chain)
    with pytest.raises(ValueError):
        gate.emit(
            vendor_id="",
            vendor_class=VendorClass.KYC,
            input_hash=_input_hash(b"applicant-x"),
            score=0.5,
            model_version="v3.1.0",
        )


def test_emit_rejects_empty_model_version(tmp_chain: AuditChain) -> None:
    gate = InMemoryVendorScoreGate(audit_chain=tmp_chain)
    with pytest.raises(ValueError):
        gate.emit(
            vendor_id="persona-class",
            vendor_class=VendorClass.KYC,
            input_hash=_input_hash(b"applicant-x"),
            score=0.5,
            model_version="",
        )


# --------------------------------------------------------------------------- #
# 7. Autonomy-level threading                                                 #
# --------------------------------------------------------------------------- #


def test_emit_defaults_to_a2_autonomy_level(tmp_chain: AuditChain) -> None:
    """Vendor-mediated decisions default to A2 (human on the loop)."""
    gate = InMemoryVendorScoreGate(audit_chain=tmp_chain)
    gate.emit(
        vendor_id="persona-class",
        vendor_class=VendorClass.KYC,
        input_hash=_input_hash(b"applicant-default"),
        score=0.7,
        model_version="v1",
    )
    assert tmp_chain._events[0].autonomy_level is AutonomyLevel.A2


def test_emit_respects_overridden_autonomy_level(tmp_chain: AuditChain) -> None:
    gate = InMemoryVendorScoreGate(audit_chain=tmp_chain, autonomy_level=AutonomyLevel.A1)
    gate.emit(
        vendor_id="persona-class",
        vendor_class=VendorClass.KYC,
        input_hash=_input_hash(b"applicant-override"),
        score=0.7,
        model_version="v1",
    )
    assert tmp_chain._events[0].autonomy_level is AutonomyLevel.A1
