"""Reference agent surfaces — v1.1 (Tranche 2B).

AuditConsumer base accepts the 4 Protocol seams (LedgerStore,
TimestampSource, WitnessRegister, MIProxy) + optional VendorScoreGate
through one injection contract. Reference agents (AuditAgent,
MonitorAgent, OrchestratorAgent) demonstrate wiring.
"""

from finserv_agent_audit.agents.audit import AuditAgent
from finserv_agent_audit.agents.base import (
    Agent,
    AgentResult,
    AuditChainTamperError,
    AuditConsumer,
)
from finserv_agent_audit.agents.monitor import MonitorAgent
from finserv_agent_audit.agents.orchestrator import OrchestratorAgent

__all__ = [
    "Agent",
    "AgentResult",
    "AuditAgent",
    "AuditChainTamperError",
    "AuditConsumer",
    "MonitorAgent",
    "OrchestratorAgent",
]
