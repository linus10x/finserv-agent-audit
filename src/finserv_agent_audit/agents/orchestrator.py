"""Orchestrator agent (reference stub) — routes work between agents per
the compose order documented in ARCHITECTURE.md:

    DEFCON -> Domain pre-flight -> Sovereign Veto -> Autonomy Ladder
    -> Shadow Mode -> Hash-chain Audit write -> ACTION

Reference implementation ships the role + a minimal ``process`` that
demonstrates the compose order can be wired end-to-end. Production
implementations swap in their own subclass with the specific agent
wiring for the deployment (KYC pipeline, fraud-decisioning pipeline,
underwriting pipeline, robo-advisor signal pipeline, AML transaction
monitoring pipeline — see ADR-0016 for the FSI vendor-class enumeration).

Regulatory framing:
    - SR 11-7 — the orchestrator is the system boundary at which model
      risk management evaluates the end-to-end decision pipeline; the
      compose order IS the documented effective-challenge artifact
    - SEC Reg-BI / FINRA Rule 2111 — for the robo-advisor signal class,
      the orchestrator is where the best-interest gate sits between
      strategy output and customer-facing action
"""

from __future__ import annotations

from dataclasses import dataclass

from finserv_agent_audit.agents.audit import AuditAgent
from finserv_agent_audit.agents.base import Agent
from finserv_agent_audit.agents.monitor import MonitorAgent
from finserv_agent_audit.governance.defcon import DEFCONMachine
from finserv_agent_audit.governance.sovereign_veto import SovereignVeto
from finserv_agent_audit.schemas.audit_event import AuditChain


@dataclass
class OrchestratorAgent(Agent[object, object]):
    """Composes the other roles into one decision pipeline.

    All sub-agents and governance hooks are optional so the reference
    stub can be instantiated bare; production deployers wire the full
    compose order per ARCHITECTURE.md.
    """

    role: str = "orchestrator"
    audit: AuditAgent | None = None
    monitor: MonitorAgent | None = None
    defcon: DEFCONMachine | None = None
    sovereign_veto: SovereignVeto | None = None
    audit_chain: AuditChain | None = None

    def process(self, input_data: object) -> object:
        """Reference stub — returns None. Production implementations wire
        the full compose order: domain pre-flight -> strategy proposal ->
        risk assessment -> defcon gate -> sovereign-veto check -> shadow
        mode -> audit-chain write -> return outcome."""
        return None
