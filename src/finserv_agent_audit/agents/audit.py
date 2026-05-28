"""Audit agent — reconstructs prior decisions for regulators, model-risk
reviewers, and internal-audit teams by reading the hash-chain audit ledger.

Reference implementation. v1.1 extends ``AuditConsumer`` so the four
v1.1 Protocol seams (LedgerStore, TimestampSource, WitnessRegister,
MIProxy) plus the optional VendorScoreGate are injectable through one
constructor.

Regulatory framing:
    - SR 11-7 — the audit agent is the read-side surface model-risk
      validators reach for during effective-challenge reviews
    - SEC Rule 17a-4 — the broker-dealer record-retention path; the
      audit agent's ``process`` returns the events second-line auditors
      review during cycle testing
    - GLBA Safeguards Rule — when the query reaches NPI-touching
      decisions, the audit agent is the chain-of-custody seam
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from finserv_agent_audit.agents.base import Agent, AuditConsumer
from finserv_agent_audit.schemas.audit_event import AuditChain, AuditEvent

if TYPE_CHECKING:
    from finserv_agent_audit.governance.ledger_store import LedgerStore
    from finserv_agent_audit.governance.mi_proxy import MIProxy
    from finserv_agent_audit.governance.timestamp_source import TimestampSource
    from finserv_agent_audit.governance.vendor_score_gate import VendorScoreGate
    from finserv_agent_audit.governance.witness_anchor import WitnessRegister


@dataclass(frozen=True)
class AuditQuery:
    """A regulator-facing audit query — by event type, agent, or sequence range."""

    event_type: str | None = None
    agent_id: str | None = None
    since_index: int | None = None


class AuditAgent(Agent[AuditQuery, tuple[AuditEvent, ...]], AuditConsumer):
    role = "audit"

    def __init__(
        self,
        audit_chain: AuditChain,
        *,
        ledger_store: LedgerStore | None = None,
        timestamp_source: TimestampSource | None = None,
        witness_register: WitnessRegister | None = None,
        mi_proxy: MIProxy | None = None,
        vendor_score_gate: VendorScoreGate | None = None,
    ) -> None:
        self.audit_chain = audit_chain
        self.ledger_store = ledger_store
        self.timestamp_source = timestamp_source
        self.witness_register = witness_register
        self.mi_proxy = mi_proxy
        self.vendor_score_gate = vendor_score_gate

    def process(self, input_data: AuditQuery) -> tuple[AuditEvent, ...]:
        """Filter chain events against the query.

        Reference implementation: supports event_type, agent_id, and
        since_index filters. Production deployers typically extend this
        with time-window queries, actor-kind filters, and pagination.
        """
        events = list(self.audit_chain._events)  # noqa: SLF001
        if input_data.since_index is not None:
            events = events[input_data.since_index :]
        if input_data.event_type is not None:
            events = [e for e in events if e.event_type.value == input_data.event_type]
        if input_data.agent_id is not None:
            events = [e for e in events if e.agent_id == input_data.agent_id]
        return tuple(events)
