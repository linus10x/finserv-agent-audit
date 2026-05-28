"""Shared base types for the FSI agent topology.

Agents are roles, not microservices — the same process can host multiple
agents in a small deployment, separated only by the orchestrator's routing
logic. Each role has one clear responsibility.

``AuditConsumer`` is the consolidated v1.1 contract for agents that read
or write the audit chain. It accepts the four v1.1 Protocol seams in one
place — ``ledger_store`` (ADR-0012), ``timestamp_source`` (ADR-0014),
``witness_register`` (ADR-0014 external anchor), ``mi_proxy`` (ADR-0015
verifier chain-of-custody) — plus the optional vendor-mediated AI seam
``vendor_score_gate`` (ADR-0016). Production deployers wire all five
through one constructor; the same consumer instance can verify chain
integrity end-to-end without reaching past the interface.

``verify_integrity()`` is the consolidated read-side check that wraps
``AuditChain.verify()`` and, when an MI Proxy is wired, attests the
verifier's identity out-of-band before returning. ``record_vendor_score()``
delegates to the injected gate or raises if absent — never silently
no-ops a vendor signal.

Regulatory framing:
    - SR 11-7 (Federal Reserve / OCC) — model risk management; the audit
      consumer is the seam where second-line validation evidence lives
    - SEC Rule 17a-4 — broker-dealer electronic record retention; the
      ledger_store seam is where WORM compliance is enforced
    - SOX 404 ITGC — verifier change-management; mi_proxy is the evidence
      the deployed verifier matches the approved binary
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from finserv_agent_audit.governance.ledger_store import LedgerStore
    from finserv_agent_audit.governance.mi_proxy import MIProxy
    from finserv_agent_audit.governance.timestamp_source import TimestampSource
    from finserv_agent_audit.governance.vendor_score_gate import (
        VendorClass,
        VendorScoreEntry,
        VendorScoreGate,
    )
    from finserv_agent_audit.governance.witness_anchor import WitnessRegister
    from finserv_agent_audit.schemas.audit_event import AuditChain


class Agent[InputT, OutputT](ABC):
    """Base agent interface — typed input, typed output, no shared state.

    Production implementations swap in their own subclass per role. The
    reference stubs here exist so the orchestrator can be wired against a
    stable interface and so consumers see the canonical role signatures.
    """

    role: str
    """Short identifier used by the audit chain and the orchestrator."""

    @abstractmethod
    def process(self, input_data: InputT) -> OutputT: ...


@dataclass(frozen=True)
class AgentResult[OutputT]:
    """Wrapper for an agent's output that carries the role + outcome together."""

    role: str
    output: OutputT


class AuditConsumer:
    """Mixin for agents that read or write the audit chain.

    Captures the v1.1 dependency-injection contract in one place. The
    required seam is ``audit_chain`` (the in-process chain object); the
    four Protocol seams are optional and wired through one constructor:

        ledger_store      — ADR-0012, pluggable persistence
        timestamp_source  — ADR-0014, trusted-timestamp Protocol
        witness_register  — ADR-0014, external transparency-log anchor
        mi_proxy          — ADR-0015, verifier chain-of-custody
        vendor_score_gate — ADR-0016, third-party AI scoring capture

    ``verify_integrity()`` is the consolidated read-side check —
    ``AuditChain.verify()`` (returns False on tamper) and, when an MI Proxy
    is wired, ``enforce_attestation`` of the verifier component before the
    bool result is converted to a raise. Tamper detection raises
    ``AuditChainTamperError``; verifier compromise raises
    ``IntegrityVerificationError``.

    ``record_vendor_score()`` delegates to the injected gate or raises if
    absent — the consumer cannot silently no-op a vendor signal.
    """

    audit_chain: AuditChain
    ledger_store: LedgerStore | None
    timestamp_source: TimestampSource | None
    witness_register: WitnessRegister | None
    mi_proxy: MIProxy | None
    vendor_score_gate: VendorScoreGate | None

    def verify_integrity(self) -> None:
        """Verify the chain end-to-end, including verifier integrity if
        MI Proxy is wired.

        Raises ``AuditChainTamperError`` on in-chain inconsistency or
        ``IntegrityVerificationError`` on MI Proxy attestation failure.
        Fail-closed: never returns a verified result while either check
        fails.
        """
        if not self.audit_chain.verify():
            raise AuditChainTamperError(
                "AuditChain.verify() returned False; chain integrity has been "
                "compromised. Quarantine the chain, investigate the divergence."
            )
        if self.mi_proxy is not None:
            # Local import keeps the symbol resolution at call time so the
            # base module imports cleanly even when an opt-in MI-Proxy
            # backend is not installed.
            from finserv_agent_audit.governance.mi_proxy import enforce_attestation

            enforce_attestation(
                self.mi_proxy,
                "finserv_agent_audit.schemas.audit_event",
            )

    def record_vendor_score(
        self,
        *,
        vendor_id: str,
        vendor_class: VendorClass,
        input_hash: str,
        score: float,
        model_version: str,
    ) -> VendorScoreEntry:
        """Record a vendor-scoring event via the injected gate.

        Raises ``RuntimeError`` when no gate was injected — the consumer
        cannot silently no-op a vendor signal; the deployer either wires
        a gate or calls ``VendorScoreGate.emit()`` directly.
        """
        if self.vendor_score_gate is None:
            raise RuntimeError(
                "record_vendor_score requires an injected VendorScoreGate; "
                "construct this consumer with vendor_score_gate=... or call "
                "VendorScoreGate.emit() directly"
            )
        return self.vendor_score_gate.emit(
            vendor_id=vendor_id,
            vendor_class=vendor_class,
            input_hash=input_hash,
            score=score,
            model_version=model_version,
        )


class AuditChainTamperError(RuntimeError):
    """Raised by ``AuditConsumer.verify_integrity`` on chain-tamper detection.

    ``AuditChain.verify()`` returns False when the hash-chain replay finds
    a mismatched event_hash or prev_hash. The AuditConsumer converts that
    bool into a fail-closed exception so callers cannot accidentally
    proceed against a compromised chain.
    """


__all__ = [
    "Agent",
    "AgentResult",
    "AuditChainTamperError",
    "AuditConsumer",
]
