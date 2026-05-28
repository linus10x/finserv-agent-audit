"""Governance patterns — v1.1.

v1.0 (shipped 2026-05-15):
    - DEFCONMachine (risk-state machine with hysteresis)
    - SovereignVeto (human-only kill switch)
    - AuditChain (tamper-detecting hash-chain logging within-trust-boundary;
      extracted from schemas/audit_event.py in v1.1 to consume Protocol seams)

v1.1 (shipped 2026-XX-XX) — Tranche 2 ports + FSI overlay:

    Protocol seams (audit-chain layer, ADR-0014 + ADR-0015):
        LedgerStore Protocol + InMemoryLedgerStore + SqliteLedgerStore +
        JsonlLedgerStore + WORMLedgerStore (SEC 17a-4 compliant)
        TimestampSource Protocol + LocalClock + RFC3161Source
        WitnessRegister Protocol + RekorWitness + OpenTimestampsWitness
        + anchor_to_witness() helper
        MIProxy Protocol + LocalMIProxy + IntegrityVerificationError

    Vendor-mediated AI (ADR-0016):
        VendorScoreGate + VendorScoreDriftDetected + 5 FSI VendorClass values

    FSI-specific governance (ADRs 0007-0011, 0013, 0019):
        ModelInventory (SR 11-7 model-risk three-lines-of-defense)
        AdverseActionGate (FCRA § 615 + CFPB Circular 2022-03)
        SARWorkflowAudit (BSA/AML § 5318(g)/(h))
        EquityAudit (ECOA / Reg-B fair-lending pre-flight)
        BestInterestCheck (SEC Reg-BI)
        ProtectedClassProxyDetector (STUB per ADR-0019; v1.2 ship-gate)

    Operational patterns:
        ShadowMode (SR 11-7 pre-promotion parallel runs, ADR-0006)
        AutonomyLadder runtime helper (A2→A3 promotion gate, ADR-0004 + 0007)
"""

# v1.0 core
# v1.1 FSI-specific (ADRs 0007-0011, 0013, 0019)
from finserv_agent_audit.governance.adverse_action_gate import (
    AdverseActionGate,
    AdverseActionViolation,
)
from finserv_agent_audit.governance.audit_chain import AuditChain, AuditChainTamperError

# v1.1 Operational (ADR-0004, ADR-0006)
from finserv_agent_audit.governance.autonomy_ladder import (
    AutonomyTier,
    PromotionGateNotMet,
    PromotionGateReport,
    PromotionRequirements,
    check_a2_to_a3_promotion,
)
from finserv_agent_audit.governance.best_interest_check import (
    BestInterestCheck,
    BestInterestViolation,
    RecommendationProfile,
)
from finserv_agent_audit.governance.defcon import DEFCON, DEFCONMachine, RiskMetrics
from finserv_agent_audit.governance.equity_audit import (
    EquityAudit,
    EquityAuditViolation,
    ProtectedClass,
)

# v1.1 Protocol seams (ADR-0014, ADR-0015)
from finserv_agent_audit.governance.ledger_store import (
    InMemoryLedgerStore,
    LedgerStore,
)
from finserv_agent_audit.governance.ledger_store_jsonl import JsonlLedgerStore
from finserv_agent_audit.governance.ledger_store_sqlite import SqliteLedgerStore
from finserv_agent_audit.governance.ledger_store_worm import (
    WORMLedgerStore,
    WORMViolationError,
)
from finserv_agent_audit.governance.mi_proxy import (
    IntegrityVerificationError,
    LocalMIProxy,
    MIProxy,
    enforce_attestation,
)
from finserv_agent_audit.governance.model_inventory import (
    ImplementationStatus,
    Model,
    ModelInventory,
)
from finserv_agent_audit.governance.protected_class_proxy_detector import (
    ProtectedClassProxyDetector,
)
from finserv_agent_audit.governance.rfc3161_codec import (
    build_timestamp_request,
    parse_timestamp_response,
)
from finserv_agent_audit.governance.sar_workflow_audit import SARWorkflowAudit
from finserv_agent_audit.governance.shadow_mode import (
    DecisionClass,
    DecisionOutcome,
    PromotionVerdict,
    ShadowRouter,
    VetoDirection,
)
from finserv_agent_audit.governance.sovereign_veto import (
    SovereignVeto,
    VetoBlockedError,
    VetoReason,
    VetoRecord,
)
from finserv_agent_audit.governance.timestamp_source import (
    LocalClock,
    RFC3161Source,
    TimestampSource,
)

# v1.1 Vendor-mediated AI (ADR-0016)
from finserv_agent_audit.governance.vendor_score_gate import (
    InMemoryVendorScoreGate,
    VendorClass,
    VendorScoreDriftDetected,
    VendorScoreEntry,
    VendorScoreGate,
)
from finserv_agent_audit.governance.witness_anchor import (
    OpenTimestampsWitness,
    RekorWitness,
    WitnessRegister,
    anchor_to_witness,
)

__all__ = [
    # v1.0
    "AuditChain",
    "AuditChainTamperError",
    "DEFCON",
    "DEFCONMachine",
    "RiskMetrics",
    "SovereignVeto",
    "VetoBlockedError",
    "VetoReason",
    "VetoRecord",
    # Protocol seams
    "InMemoryLedgerStore",
    "LedgerStore",
    "JsonlLedgerStore",
    "SqliteLedgerStore",
    "WORMLedgerStore",
    "WORMViolationError",
    "LocalClock",
    "RFC3161Source",
    "TimestampSource",
    "build_timestamp_request",
    "parse_timestamp_response",
    "OpenTimestampsWitness",
    "RekorWitness",
    "WitnessRegister",
    "anchor_to_witness",
    "IntegrityVerificationError",
    "LocalMIProxy",
    "MIProxy",
    "enforce_attestation",
    # Vendor-mediated AI
    "InMemoryVendorScoreGate",
    "VendorClass",
    "VendorScoreDriftDetected",
    "VendorScoreEntry",
    "VendorScoreGate",
    # FSI-specific
    "AdverseActionGate",
    "AdverseActionViolation",
    "BestInterestCheck",
    "BestInterestViolation",
    "RecommendationProfile",
    "EquityAudit",
    "EquityAuditViolation",
    "ProtectedClass",
    "ImplementationStatus",
    "Model",
    "ModelInventory",
    "ProtectedClassProxyDetector",
    "SARWorkflowAudit",
    # Operational
    "AutonomyTier",
    "PromotionGateNotMet",
    "PromotionGateReport",
    "PromotionRequirements",
    "check_a2_to_a3_promotion",
    "DecisionClass",
    "DecisionOutcome",
    "PromotionVerdict",
    "ShadowRouter",
    "VetoDirection",
]
