"""Monitor agent — observes the audit ledger for anomalies and emits
structured alerts. Read-only with respect to the chain.

Reference implementation. v1.1 extends ``AuditConsumer`` so the four
v1.1 Protocol seams plus the optional VendorScoreGate are injectable
through one constructor. ``process`` returns an empty alert tuple by
default; production implementations scan the chain for statistical
anomalies (veto-rate spikes, vendor-score drift bursts, shadow-mode
time-in-state limits, model-risk thresholds per SR 11-7) and emit
appropriately-typed alerts.

Regulatory framing:
    - SR 11-7 — monitoring is the ongoing-monitoring leg of the model
      risk management lifecycle; alerts here are the upstream signal
      validators reach for during annual review
    - NYDFS 23 NYCRR 500 / Part 504 — continuous monitoring of AML
      transaction surveillance is the regulator-named obligation;
      monitor alerts on VENDOR_SCORE_DRIFT_DETECTED in the AML class
      are first-line evidence
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from finserv_agent_audit.agents.base import Agent, AuditConsumer
from finserv_agent_audit.schemas.audit_event import AuditChain

if TYPE_CHECKING:
    from finserv_agent_audit.governance.ledger_store import LedgerStore
    from finserv_agent_audit.governance.mi_proxy import MIProxy
    from finserv_agent_audit.governance.timestamp_source import TimestampSource
    from finserv_agent_audit.governance.vendor_score_gate import VendorScoreGate
    from finserv_agent_audit.governance.witness_anchor import WitnessRegister


@dataclass(frozen=True)
class MonitorAlert:
    severity: str  # 'INFO' | 'WARNING' | 'CRITICAL'
    code: str
    message: str


class MonitorAgent(Agent[AuditChain, tuple[MonitorAlert, ...]], AuditConsumer):
    role = "monitor"

    def __init__(
        self,
        audit_chain: AuditChain | None = None,
        *,
        ledger_store: LedgerStore | None = None,
        timestamp_source: TimestampSource | None = None,
        witness_register: WitnessRegister | None = None,
        mi_proxy: MIProxy | None = None,
        vendor_score_gate: VendorScoreGate | None = None,
    ) -> None:
        self.audit_chain = audit_chain if audit_chain is not None else AuditChain()
        self.ledger_store = ledger_store
        self.timestamp_source = timestamp_source
        self.witness_register = witness_register
        self.mi_proxy = mi_proxy
        self.vendor_score_gate = vendor_score_gate

    def process(self, input_data: AuditChain) -> tuple[MonitorAlert, ...]:
        """Reference stub — production implementations scan the chain for
        statistical anomalies (veto-rate spikes, cohort-specific divergence,
        shadow-mode time-in-state limits, vendor-score drift) and emit
        alerts. Returns an empty tuple at the reference level."""
        return ()
