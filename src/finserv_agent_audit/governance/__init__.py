"""Governance patterns — v2.0.

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
        ProtectedClassProxyDetector (MI-arm shipped in v1.2; SHAP / CDD
        arms remain on the v1.3 roadmap per ADR-0019 § "v1.2 ship
        reconciliation")

    Operational patterns:
        ShadowMode (SR 11-7 pre-promotion parallel runs, ADR-0006)
        AutonomyLadder runtime helper (A2→A3 promotion gate, ADR-0004 + 0007)

v1.3 (ships 2026-XX-XX) — Discrimination-frontier patterns:

    Fair-lending discrimination frontier (ADRs 0020-0022):
        LDASearchHarness (ADR-0020) — Less Discriminatory Alternative
        search per ACM-FAccT 2024 + CFPB Circular 2023-09 + the May
        2026 CFPB final rule + Massachusetts AG July 2025 settlement
        LLMDisparateImpactHarness (ADR-0021) — DI testing for LLM
        outputs per EEOC 4/5ths rule + Mobley v. Workday May 2025
        EffectiveChallengeHarness (ADR-0022) — SR 11-7 effective
        challenge for frontier-API primaries; closes the OCC 2026-13
        scope-exclusion gap

    Customer-facing surface (ADR-0026):
        CustomerFacingChatbotGuardrail — three-layer interception for
        customer-facing banking chatbots; closes the Moffatt v. Air
        Canada (BC CRT, Feb 14, 2024) operator-liability precedent
        with policy-grounded RAG checking, money-movement /
        commitment-class human-handoff routing, and no-fabricated-
        policy assertion (PolicyCorpus + RAGSourceCheck Protocol seam
        + ActionClass enum + GuardrailResponse + RequiresHumanHandoff
        / FabricatedPolicyDetected exceptions)

v2.0 (ships 2026-XX-XX) — Platform surfaces:

    AIBOM dual emit (ADR-0031):
        AIBOMGenerator — one governance call yields a CycloneDX 1.7
        ML-BOM (machine-learning-model component type + modelCard
        extension) and an SPDX 3.0 AI Profile document
        (ai_AIPackage class + AI-specific properties). The class is
        re-exported here when `governance/aibom.py` is present;
        the v2.0 Tranche B subagent lands that module.
"""

# v1.0 core
# v1.1 FSI-specific (ADRs 0007-0011, 0013, 0019)
from finserv_agent_audit.governance.adverse_action_gate import (
    AdverseActionGate,
    AdverseActionViolation,
)

# v2.0 platform surface — AIBOM dual emit (ADR-0031)
try:  # pragma: no cover - module ships in v2.0 Tranche B
    from finserv_agent_audit.governance.aibom import (  # noqa: F401
        AIBOMGenerator,
        AIBOMModelRecord,
    )

    _HAS_AIBOM = True
except ImportError:  # pragma: no cover
    _HAS_AIBOM = False
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
from finserv_agent_audit.governance.customer_facing_chatbot_guardrail import (
    ActionClass,
    CustomerFacingChatbotGuardrail,
    FabricatedPolicyDetected,
    GuardrailDecision,
    GuardrailResponse,
    PolicyCorpus,
    PolicySource,
    RAGSourceCheck,
    RequiresHumanHandoff,
)
from finserv_agent_audit.governance.defcon import DEFCON, DEFCONMachine, RiskMetrics
from finserv_agent_audit.governance.deprecation_watch import (
    ChangelogParser,
    DeprecationAnnouncement,
    DeprecationWatch,
)
from finserv_agent_audit.governance.effective_challenge_harness import (
    ChallengeReport,
    EffectiveChallengeHarness,
)
from finserv_agent_audit.governance.equity_audit import (
    EquityAudit,
    EquityAuditViolation,
    ProtectedClass,
)
from finserv_agent_audit.governance.lda_search import (
    LDACandidateReport,
    LDASearchHarness,
    LDASearchResult,
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
from finserv_agent_audit.governance.llm_disparate_impact_harness import (
    LLMDisparateImpactHarness,
    LLMDisparateImpactResult,
    RubricScorer,
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
    ProxyDetectionResult,
    ProxyFeatureFlag,
)
from finserv_agent_audit.governance.retraining_cadence_monitor import (
    RetrainingCadenceMonitor,
    RetrainingCadenceReport,
    RetrainingClass,
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
from finserv_agent_audit.governance.vendor_attestation_ledger import (
    AttestationGap,
    VendorAttestation,
    VendorAttestationLedger,
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
    "ProxyDetectionResult",
    "ProxyFeatureFlag",
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
    # v1.3 Discrimination-frontier patterns (ADRs 0020-0022)
    "LDASearchHarness",
    "LDACandidateReport",
    "LDASearchResult",
    "LLMDisparateImpactHarness",
    "LLMDisparateImpactResult",
    "RubricScorer",
    "EffectiveChallengeHarness",
    "ChallengeReport",
    # v1.3 Customer-facing chatbot guardrail (ADR-0026)
    "ActionClass",
    "CustomerFacingChatbotGuardrail",
    "FabricatedPolicyDetected",
    "GuardrailDecision",
    "GuardrailResponse",
    "PolicyCorpus",
    "PolicySource",
    "RAGSourceCheck",
    "RequiresHumanHandoff",
    # v1.3 Vendor-surface patterns (ADRs 0023-0025)
    "VendorAttestationLedger",
    "VendorAttestation",
    "AttestationGap",
    "RetrainingCadenceMonitor",
    "RetrainingClass",
    "RetrainingCadenceReport",
    "DeprecationWatch",
    "DeprecationAnnouncement",
    "ChangelogParser",
]

# v2.0 platform surface — AIBOM dual emit (ADR-0031). The names are
# appended dynamically so the module gracefully no-ops if the v2.0
# Tranche B subagent has not yet landed `governance/aibom.py`.
if _HAS_AIBOM:  # pragma: no cover
    __all__.extend(["AIBOMGenerator", "AIBOMModelRecord"])
