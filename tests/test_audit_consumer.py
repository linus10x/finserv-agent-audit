"""Tests for the consolidated AuditConsumer base — the four v1.1 Protocol
seams (ADR-0012 LedgerStore, ADR-0014 TimestampSource + WitnessRegister,
ADR-0015 MIProxy) plus the optional ADR-0016 VendorScoreGate, all
injected through one interface and used by AuditAgent / MonitorAgent.
"""

from __future__ import annotations

import hashlib
import secrets
from pathlib import Path

import pytest

from finserv_agent_audit.agents.audit import AuditAgent, AuditQuery
from finserv_agent_audit.agents.base import AuditChainTamperError, AuditConsumer
from finserv_agent_audit.agents.monitor import MonitorAgent
from finserv_agent_audit.agents.orchestrator import OrchestratorAgent
from finserv_agent_audit.governance.mi_proxy import (
    IntegrityVerificationError,
    LocalMIProxy,
)
from finserv_agent_audit.governance.vendor_score_gate import (
    InMemoryVendorScoreGate,
    VendorClass,
    VendorScoreDriftDetected,
)
from finserv_agent_audit.schemas.audit_event import (
    AuditChain,
    AuditEventType,
    AutonomyLevel,
)


def _chain(tmp_path: Path) -> AuditChain:
    return AuditChain(log_file=tmp_path / "audit.jsonl")


# --------------------------------------------------------------------------- #
# 1. AuditConsumer base — required surface                                    #
# --------------------------------------------------------------------------- #


def test_audit_agent_is_an_audit_consumer(tmp_path: Path) -> None:
    agent = AuditAgent(audit_chain=_chain(tmp_path))
    assert isinstance(agent, AuditConsumer)


def test_monitor_agent_is_an_audit_consumer(tmp_path: Path) -> None:
    assert isinstance(MonitorAgent(audit_chain=_chain(tmp_path)), AuditConsumer)


# --------------------------------------------------------------------------- #
# 2. Injection of the v1.1 seams                                              #
# --------------------------------------------------------------------------- #


def test_audit_consumer_accepts_mi_proxy_injection(tmp_path: Path) -> None:
    proxy = LocalMIProxy(signing_key=secrets.token_bytes(32))
    agent = AuditAgent(audit_chain=_chain(tmp_path), mi_proxy=proxy)
    assert agent.mi_proxy is proxy


def test_audit_consumer_accepts_vendor_score_gate_injection(tmp_path: Path) -> None:
    chain = _chain(tmp_path)
    gate = InMemoryVendorScoreGate(audit_chain=chain)
    agent = MonitorAgent(audit_chain=chain, vendor_score_gate=gate)
    assert agent.vendor_score_gate is gate


def test_audit_consumer_accepts_all_four_protocol_seams(tmp_path: Path) -> None:
    """The four v1.1 Protocol seams + vendor_score_gate land in one ctor."""
    from finserv_agent_audit.governance.ledger_store import InMemoryLedgerStore
    from finserv_agent_audit.governance.timestamp_source import LocalClock
    from finserv_agent_audit.governance.witness_anchor import RekorWitness

    chain = _chain(tmp_path)
    store = InMemoryLedgerStore()
    clock = LocalClock()
    witness = RekorWitness()
    proxy = LocalMIProxy(signing_key=secrets.token_bytes(32))
    gate = InMemoryVendorScoreGate(audit_chain=chain)

    agent = AuditAgent(
        audit_chain=chain,
        ledger_store=store,
        timestamp_source=clock,
        witness_register=witness,
        mi_proxy=proxy,
        vendor_score_gate=gate,
    )
    assert agent.ledger_store is store
    assert agent.timestamp_source is clock
    assert agent.witness_register is witness
    assert agent.mi_proxy is proxy
    assert agent.vendor_score_gate is gate


# --------------------------------------------------------------------------- #
# 3. verify_integrity — convenience that wraps verify() + MI Proxy            #
# --------------------------------------------------------------------------- #


def test_verify_integrity_passes_when_proxy_absent(tmp_path: Path) -> None:
    chain = _chain(tmp_path)
    chain.append(
        event_type=AuditEventType.AGENT_STARTED,
        autonomy_level=AutonomyLevel.A0,
        agent_id="test",
        payload={"v": 1},
    )
    AuditAgent(audit_chain=chain).verify_integrity()  # must not raise


def test_verify_integrity_uses_injected_mi_proxy(tmp_path: Path) -> None:
    chain = _chain(tmp_path)
    chain.append(
        event_type=AuditEventType.DECISION_MADE,
        autonomy_level=AutonomyLevel.A2,
        agent_id="test",
        payload={"k": "v"},
    )
    proxy = LocalMIProxy(signing_key=secrets.token_bytes(32))
    agent = AuditAgent(audit_chain=chain, mi_proxy=proxy)
    agent.verify_integrity()  # must not raise — proxy attestation valid


def test_verify_integrity_fails_closed_with_bad_proxy(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from finserv_agent_audit.governance.mi_proxy import Attestation

    class AlwaysFailMIProxy:
        def attest(self, component_id: str) -> Attestation:
            return Attestation(
                component_id=component_id,
                sha256_hex="f" * 64,
                timestamp_iso=datetime.now(UTC).isoformat(),
                signature_b64="x",
                backend_id="x",
            )

        def verify_attestation(self, attestation: Attestation) -> bool:
            return False

    chain = _chain(tmp_path)
    agent = AuditAgent(audit_chain=chain, mi_proxy=AlwaysFailMIProxy())
    with pytest.raises(IntegrityVerificationError):
        agent.verify_integrity()


def test_verify_integrity_raises_on_chain_tamper(tmp_path: Path) -> None:
    """verify_integrity() converts AuditChain.verify()==False into a raise."""
    chain = _chain(tmp_path)
    chain.append(
        event_type=AuditEventType.DECISION_MADE,
        autonomy_level=AutonomyLevel.A2,
        agent_id="test",
        payload={"k": "v"},
    )
    # Tamper: mutate the dict-typed payload so verify() returns False.
    # CR-2 — ``AuditEvent`` is frozen, but the ``payload`` dict
    # contents remain mutable. Editing them invalidates the stored
    # event_hash without raising ``FrozenInstanceError``.
    chain._events[0].payload["k"] = "tampered"
    agent = AuditAgent(audit_chain=chain)
    with pytest.raises(AuditChainTamperError):
        agent.verify_integrity()


# --------------------------------------------------------------------------- #
# 4. record_vendor_score — delegates to the injected gate                     #
# --------------------------------------------------------------------------- #


def test_record_vendor_score_delegates_to_gate(tmp_path: Path) -> None:
    chain = _chain(tmp_path)
    gate = InMemoryVendorScoreGate(audit_chain=chain)
    agent = MonitorAgent(audit_chain=chain, vendor_score_gate=gate)
    entry = agent.record_vendor_score(
        vendor_id="acme",
        vendor_class=VendorClass.KYC,
        input_hash=hashlib.sha256(b"x").hexdigest(),
        score=0.5,
        model_version="v1",
    )
    assert entry.vendor_id == "acme"
    assert entry.vendor_class is VendorClass.KYC
    assert len(chain._events) == 1


def test_record_vendor_score_without_gate_raises(tmp_path: Path) -> None:
    agent = MonitorAgent(audit_chain=_chain(tmp_path))  # no gate
    with pytest.raises(RuntimeError):
        agent.record_vendor_score(
            vendor_id="acme",
            vendor_class=VendorClass.KYC,
            input_hash=hashlib.sha256(b"x").hexdigest(),
            score=0.5,
            model_version="v1",
        )


def test_record_vendor_score_propagates_drift(tmp_path: Path) -> None:
    chain = _chain(tmp_path)
    gate = InMemoryVendorScoreGate(audit_chain=chain)
    agent = MonitorAgent(audit_chain=chain, vendor_score_gate=gate)
    input_hash = hashlib.sha256(b"x").hexdigest()
    agent.record_vendor_score(
        vendor_id="acme",
        vendor_class=VendorClass.FRAUD_SCORE,
        input_hash=input_hash,
        score=0.5,
        model_version="v1",
    )
    with pytest.raises(VendorScoreDriftDetected):
        agent.record_vendor_score(
            vendor_id="acme",
            vendor_class=VendorClass.FRAUD_SCORE,
            input_hash=input_hash,
            score=0.8,
            model_version="v1",
        )


# --------------------------------------------------------------------------- #
# 5. Public-signature backward compatibility                                  #
# --------------------------------------------------------------------------- #


def test_audit_agent_filter_signature_preserved(tmp_path: Path) -> None:
    """AuditAgent.process(AuditQuery(...)) returns tuple[AuditEvent, ...]."""
    chain = _chain(tmp_path)
    chain.append(
        event_type=AuditEventType.DECISION_MADE,
        autonomy_level=AutonomyLevel.A2,
        agent_id="strategy",
        payload={"action": "buy"},
    )
    agent = AuditAgent(audit_chain=chain)
    result = agent.process(AuditQuery(event_type=AuditEventType.DECISION_MADE.value))
    assert isinstance(result, tuple)
    assert len(result) == 1


def test_monitor_agent_process_signature_preserved(tmp_path: Path) -> None:
    """MonitorAgent.process(chain) returns tuple[MonitorAlert, ...]."""
    agent = MonitorAgent(audit_chain=_chain(tmp_path))
    result = agent.process(AuditChain(log_file=tmp_path / "other.jsonl"))
    assert isinstance(result, tuple)


def test_orchestrator_accepts_audit_and_monitor_with_seams(tmp_path: Path) -> None:
    """Orchestrator wires injected consumers with their v1.1 seams."""
    chain = _chain(tmp_path)
    proxy = LocalMIProxy(signing_key=secrets.token_bytes(32))
    gate = InMemoryVendorScoreGate(audit_chain=chain)
    orch = OrchestratorAgent(
        audit=AuditAgent(audit_chain=chain, mi_proxy=proxy),
        monitor=MonitorAgent(audit_chain=chain, vendor_score_gate=gate),
        audit_chain=chain,
    )
    assert orch.process({}) is None  # reference stub preserved
