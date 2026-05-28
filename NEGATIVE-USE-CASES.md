# NEGATIVE-USE-CASES.md — Statements this framework does NOT support

**Status:** v1.1.0 · Last reviewed: 2026-05-28.

This document exists because the BigLaw chamber of the council asked it to. Adopters under regulatory scrutiny will be asked, "what does this framework let you claim?" — and counsel will be asked, "what does this framework let your client claim?" The answer to both questions has limits. The list below is the deliberate enumeration of statements adopters and counsel should **not** make in reliance on this framework.

Each entry names the false statement, marks it FALSE, and explains why.

> Companion to [`DISCLAIMER.md`](DISCLAIMER.md) and [`LIMITATIONS.md`](LIMITATIONS.md).

---

## Statements this framework does NOT support

### 1. "Adopting this framework satisfies SR 11-7 model-validation requirements." — **FALSE**

SR 11-7 § V requires effective challenge by an independent second line, ongoing monitoring, outcomes analysis, conceptual-soundness review, benchmarking, and back-testing. This framework provides the **recordkeeping scaffolding** for that work — `ModelInventory` tracks status transitions, validation dates, and overdue queries. It does not perform validation. The model-risk-management function inside the adopter's institution performs validation; the framework records what they did.

### 2. "An audit-chain entry constitutes a SAR filing." — **FALSE**

`SARWorkflowAudit.record()` writes a chain entry capturing the workflow step a BSA officer took (alert reviewed, escalated, declined to file, filed). The system of record for filed SARs is the FinCEN BSA E-Filing System. An audit-chain entry is recordkeeping evidence about the workflow; it is not a regulatory submission, and it does not satisfy 31 CFR 1020.320(b)(3) filing requirements.

### 3. "Sovereign Veto absolves the human operator of the underlying decision." — **FALSE**

The Sovereign Veto pattern requires a human-only clearance with a recorded reason. The human operator who clears the veto is **still accountable** for the underlying decision — including its consequences, its fair-lending posture, its Reg-BI care-obligation analysis, its market-conduct implications. The pattern logs the clearance; it does not insulate the clearing operator from accountability for what was cleared.

### 4. "Hash-chain integrity proves the agent did not make a mistake." — **FALSE**

The hash chain proves the chain was not tampered with after entries were appended. It says nothing about whether the entries themselves capture good decisions. A chain of intact, correctly-hashed, tamper-detected entries documenting a series of bad decisions is still a chain of bad decisions. The chain is evidence of what happened, not evidence that what happened was correct.

### 5. "ProtectedClassProxyDetector detects all proxy discrimination." — **FALSE**

`ProtectedClassProxyDetector` ships the mutual-information arm in v1.2 (closing the v1.1 deferral per ADR-0019). It does NOT ship the SHAP attribution or conditional-demographic-disparity arms — those land in v1.3 with their own evidence discipline. The MI arm flags features whose joint information with the protected attribute AND with the decision both clear a configured threshold; it has known weaknesses against high-dimensional sparse features, non-linear conjunctive proxies, and binning-sensitive continuous inputs. Adopters who need broader proxy-detection coverage today must combine this detector with a third-party tool and / or qualified fair-lending analytics counsel.

### 6. "MIT license shields the adopter from regulatory liability." — **FALSE**

The MIT license is a contract between the author of this framework and the adopter. It governs the warranty-and-liability relationship between those two parties. It does not change the adopter's regulatory obligations to the OCC, Federal Reserve, FDIC, SEC, FINRA, CFPB, FinCEN, state regulators, or any foreign supervisor. The regulator is not a party to the MIT license; the adopter's compliance posture toward the regulator is unaffected by accepting the license.

### 7. "Writing to a WORMLedgerStore satisfies SEC 17a-4(f)." — **FALSE**

`WORMLedgerStore` is a best-effort within-OS-controls Python implementation. SEC 17a-4(f) requires storage media that physically prevents over-writing or erasure for the retention period. For production deployments where the rule applies, adopters pair this backend with **S3 Object Lock in COMPLIANCE mode** (not GOVERNANCE mode) or an equivalent storage substrate that meets the SEC's media requirement. See [`DEPLOY-CHECKLIST.md`](DEPLOY-CHECKLIST.md) Day -7.

### 8. "Witness anchoring to Sigstore Rekor satisfies any specific regulator's tamper-evidence requirement." — **FALSE**

Anchoring the chain head to Rekor produces a third-party inclusion proof that is independent of the deployer's substrate. Whether that inclusion proof satisfies a specific regulator's tamper-evidence expectation in a specific examination is a deployer-and-counsel determination. The framework provides the anchoring mechanism; the framework does not opine on whether that mechanism is sufficient evidence for any specific supervisory standard.

### 9. "VendorScoreGate satisfies SR 11-7's third-party model risk requirements." — **FALSE**

`VendorScoreGate` detects emission drift: same `(vendor_id, input_hash, model_version)` producing a different score. That is one of many SR 11-7 § VI third-party model controls. Conceptual review of the vendor model, evaluation of vendor validation evidence, ongoing performance monitoring, contingency planning for vendor failure, and oversight of vendor-provided model documentation are separate controls the deployer's institution maintains.

### 10. "The framework's regulatory mapping documents are legal opinions." — **FALSE**

The documents in `docs/` (SR 11-7 mapping, OCC 2011-12 mapping, SOX 404 ITGC mapping, etc.) are **reference mappings** that help adopters and their counsel point at relevant clauses. They are not legal opinions. They do not represent that the framework satisfies any specific clause. Applicability is a deployer-and-counsel determination.

### 11. "DEFCON HALT is a substitute for an incident-response procedure." — **FALSE**

`DEFCONMachine` ships a five-level risk-state machine. HALT raises a hard stop with no automatic de-escalation. The framework does not ship a runbook, a paging policy, a stakeholder-communication template, or a post-incident review process. The deployer's incident-response procedure is where the actual response lives.

### 12. "Autonomy Ladder A4 is achievable without a complete v1.1 substrate." — **FALSE**

`AutonomyLadder` tiers A0 → A4 are governance classifications, not autonomy entitlements. A4 (full autonomy in a tightly-bounded domain) requires the full set of v1.1 controls — Sovereign Veto, DEFCON, Shadow Mode pre-promotion, VendorScoreGate, witness anchoring, MIProxy attestation — and a deployer's institutional governance process that promotes the agent through the tiers. The classification is a label on what the agent is permitted to do today; the substrate is what makes that permission defensible.

---

## What this framework does support

For the affirmative list — what this framework actually claims to do — see [`README.md`](README.md), [`LIMITATIONS.md`](LIMITATIONS.md) § "What this framework DOES claim", and [`SHIP-RECEIPT.md`](SHIP-RECEIPT.md).

## Related

- [`DISCLAIMER.md`](DISCLAIMER.md)
- [`LIMITATIONS.md`](LIMITATIONS.md)
- [`FAILURE-MODES.md`](FAILURE-MODES.md)
- ADR-0017 (audit retention / privilege / discovery)
- ADR-0018 (adversarial agent threat model)
- ADR-0019 (ProtectedClassProxyDetector deferred)
