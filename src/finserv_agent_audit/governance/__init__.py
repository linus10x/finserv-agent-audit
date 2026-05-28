"""Governance patterns.

v1.0 (shipped):
    - DEFCONMachine (risk-state machine with hysteresis)
    - SovereignVeto (human-only kill switch)
    - AuditChain (tamper-detecting hash-chain logging within-trust-boundary)

v1.1 (Tranche 2 in progress):
    - ShadowMode (parallel dry-run before live execution)
    - LedgerStore Protocol + InMemory/Sqlite/Jsonl/WORM backends
    - TimestampSource Protocol + LocalClock + RFC3161 client
    - WitnessRegister Protocol + RekorWitness + OpenTimestampsWitness + anchor_to_witness()
    - MIProxy Protocol + LocalMIProxy + IntegrityVerificationError
    - VendorScoreGate + VendorScoreDriftDetected
    - FSI-specific: ModelInventory (SR 11-7), AdverseActionGate (FCRA/Reg V/CFPB Circular 2022-03),
      SARWorkflowAudit (BSA/AML), EquityAudit (ECOA/Reg B), BestInterestCheck (SEC Reg-BI),
      ProtectedClassProxyDetector (stub, see ADR-0019)
"""

from finserv_agent_audit.governance.defcon import DEFCON, DEFCONMachine, RiskMetrics
from finserv_agent_audit.governance.sovereign_veto import (
    SovereignVeto,
    VetoBlockedError,
    VetoReason,
    VetoRecord,
)

__all__ = [
    "DEFCON",
    "DEFCONMachine",
    "RiskMetrics",
    "SovereignVeto",
    "VetoBlockedError",
    "VetoReason",
    "VetoRecord",
]
