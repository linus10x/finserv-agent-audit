# ARCHITECTURE.md — System-level architecture

**Status:** v1.1.0 · Last reviewed: 2026-05-28.

This document is the one-page view of how the v1.1 modules compose. ADRs hold the per-decision rationale; this document holds the layering.

> Companion to [`FAILURE-MODES.md`](FAILURE-MODES.md), [`LIMITATIONS.md`](LIMITATIONS.md), and the per-decision ADRs in `docs/adr/`.

---

## System diagram

```mermaid
flowchart TB
    subgraph PRE["Pre-decision control plane"]
        SV[SovereignVeto<br/>ADR-0002<br/>human-only kill switch]
        DEF[DEFCONMachine<br/>ADR-0001<br/>5-level risk state machine<br/>hysteresis-controlled]
        AL[AutonomyLadder<br/>ADR-0004<br/>A0..A4 promotion gate]
    end

    subgraph AGENT["Agent surface"]
        A[Agent<br/>+ AuditConsumer base<br/>agents/base.py]
        A1[AuditAgent]
        A2[MonitorAgent]
        A3[OrchestratorAgent]
        A --> A1
        A --> A2
        A --> A3
    end

    subgraph FSI["FSI gates (composable, ADR-0007..0011, 0019)"]
        MI[ModelInventory<br/>SR 11-7]
        AAG[AdverseActionGate<br/>FCRA / Reg-V + CFPB 2022-03]
        SAR[SARWorkflowAudit<br/>BSA/AML 5318g/h]
        EQ[EquityAudit<br/>ECOA / Reg-B]
        BI[BestInterestCheck<br/>SEC Reg-BI]
        PCP[ProtectedClassProxyDetector<br/>MI arm shipped v1.2 · ADR-0019]
    end

    subgraph BOUNDARY["Trust boundary (in-process verifier)"]
        AC[AuditChain<br/>ADR-0003<br/>SHA-256 hash chain<br/>verify / verify_strict]
        VSG[VendorScoreGate<br/>ADR-0016<br/>drift detection]
    end

    subgraph SEAMS["Protocol seams (ADR-0014, ADR-0015)"]
        LS[LedgerStore<br/>InMemory / JSONL / SQLite / WORM]
        TS[TimestampSource<br/>LocalClock / RFC3161Source]
        WR[WitnessRegister<br/>Rekor / OpenTimestamps]
        MIP[MIProxy<br/>LocalMIProxy HMAC-SHA256]
    end

    subgraph EXTERNAL["Across trust boundary (external attestation)"]
        TSA[(RFC 3161 TSA<br/>FreeTSA / Sectigo / DigiCert)]
        REK[(Sigstore Rekor<br/>public-good or private)]
        OTS[(OpenTimestamps<br/>calendar + Bitcoin)]
        SLSA[(SLSA / in-toto<br/>build-provenance attestor)]
    end

    SV -. blocks .-> A
    DEF -. gates .-> A
    AL -. gates .-> A

    A --> MI
    A --> AAG
    A --> SAR
    A --> EQ
    A --> BI
    A --> PCP

    MI --> AC
    AAG --> AC
    SAR --> AC
    EQ --> AC
    BI --> AC
    A --> VSG
    VSG --> AC

    AC --> LS
    AC --> TS
    AC -. opt-in attestation .-> MIP
    AC -. anchor_to_witness .-> WR

    TS -.->|sign| TSA
    WR -.->|inclusion proof| REK
    WR -.->|calendar commitment| OTS
    MIP -.->|optional substrate| SLSA

    classDef boundary stroke:#900,stroke-width:3px,stroke-dasharray: 4 4
    class BOUNDARY boundary
```

The dashed boundary box is the trust boundary the framework defends by default. Anchoring to a witness crosses the boundary; that is the design intent of ADR-0014.

---

## Layering

1. **Pre-decision control plane** — `SovereignVeto`, `DEFCONMachine`, `AutonomyLadder`. These three gate whether the agent gets to run at all. They are the architecture's "no" mechanisms: a clear veto stops the call; a state above ALERT throttles or halts; an autonomy tier above the configured ceiling refuses the action.

2. **Agent surface** — `Agent` and `AuditConsumer` in `finserv_agent_audit.agents.base`. The `AuditConsumer` base accepts the four Protocol seams + an optional `VendorScoreGate` through one injection contract. Reference agents (`AuditAgent`, `MonitorAgent`, `OrchestratorAgent`) demonstrate wiring; production deployers subclass `Agent` and reuse the consumer surface.

3. **FSI gates** — six modules (`ModelInventory`, `AdverseActionGate`, `SARWorkflowAudit`, `EquityAudit`, `BestInterestCheck`, `ProtectedClassProxyDetector`) that emit structured `AuditEvent`s into the chain. They are composable: an agent that issues credit calls `AdverseActionGate` and `EquityAudit`; an agent that recommends securities calls `BestInterestCheck`; an agent supporting the BSA function calls `SARWorkflowAudit`. `ProtectedClassProxyDetector` shipped the mutual-information arm in v1.2 (closing the v1.1 deferral per ADR-0019); SHAP and conditional-demographic-disparity arms remain on the v1.3 roadmap.

4. **Trust boundary** — `AuditChain` and `VendorScoreGate` operate inside the in-process trust boundary. `AuditChain.verify()` confirms hash-chain integrity; `verify_strict()` adds sequence-monotonicity and optional MIProxy attestation. `VendorScoreGate.record_score()` writes per-call entries and raises `VendorScoreDriftDetected` on the `(vendor_id, input_hash, model_version)` collision.

5. **Protocol seams** — four Protocols (`LedgerStore`, `TimestampSource`, `WitnessRegister`, `MIProxy`) let the deployer wire the substrate their compliance posture requires. Defaults are in-process (InMemory + LocalClock + no witness + LocalMIProxy) so test suites and demos run with zero infrastructure. Production deployers wire SQLite / JSONL / WORM ledger backends, RFC 3161 timestamps, Rekor / OpenTimestamps witnesses, and substrate-attested MIProxy backends.

6. **Across the trust boundary** — external attestation services. The framework does not ship clients for these; the seam contract is the interface, and reference adapter shapes are in `examples/`. The TSA, Rekor, OpenTimestamps calendar, and a SLSA / in-toto attestor live outside the in-process trust boundary by design.

---

## Data-flow paragraph

A typical FSI agent call flows: pre-decision gates (`SovereignVeto.is_clear()` → `DEFCONMachine.current_level()` → `AutonomyLadder.check_a2_to_a3_promotion()`) → agent reasoning → FSI gate(s) appropriate to the decision class (e.g. credit decline calls `AdverseActionGate.evaluate()` and `EquityAudit.check()`; security recommendation calls `BestInterestCheck.check()`; BSA escalation calls `SARWorkflowAudit.record()`) → each gate emits a structured `AuditEvent` via the agent's `AuditConsumer` → `AuditChain.append()` hashes the event with the prior-hash, calls `TimestampSource.now()` for the timestamp, and persists through `LedgerStore.append()`. Asynchronously, a cron job calls `anchor_to_witness(audit_chain, witness)` to write the chain head to Rekor / OpenTimestamps and append a `WITNESS_ANCHOR` entry back into the chain. On verify (operator-triggered or scheduled), `AuditChain.verify_strict(mi_proxy=...)` re-hashes the chain, checks sequence monotonicity, and calls `MIProxy.verify_integrity()` to attest the verifier itself. If any check fails, the verifier raises (`AuditChainTamperError` or `IntegrityVerificationError`) and refuses to return a verified result — the framework is fail-closed on the verify side.

---

## Cross-references

- ADR-0001 — DEFCON state machine
- ADR-0002 — Sovereign Veto
- ADR-0003 — Hash-chain audit
- ADR-0004 — Autonomy Ladder A0–A4
- ADR-0006 — Shadow Mode rollout
- ADR-0007 — SR 11-7 overlay
- ADR-0013 — SEC 17a-4 WORM
- ADR-0014 — Persistence + timestamp + witness pattern
- ADR-0015 — MI Proxy
- ADR-0016 — VendorScoreGate
- ADR-0017 — Audit retention / privilege / discovery
- ADR-0018 — Adversarial agent threat model
- ADR-0019 — ProtectedClassProxyDetector deferred
- [`FAILURE-MODES.md`](FAILURE-MODES.md), [`LIMITATIONS.md`](LIMITATIONS.md), [`ASSURANCE-GUIDE.md`](ASSURANCE-GUIDE.md)
