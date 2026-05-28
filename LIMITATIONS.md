# LIMITATIONS.md — Bounded claims for finserv-agent-audit v1.1

**Status:** v1.1.0 · Last reviewed: 2026-05-28.

This document is the explicit non-coverage list. If a property is not stated as in-scope below, assume it is **out of scope** for this framework and the deployer's responsibility.

> Companion to [`DISCLAIMER.md`](DISCLAIMER.md) (legal) and [`FAILURE-MODES.md`](FAILURE-MODES.md) (adversarial matrix).

---

## What this framework does NOT do

### Legal and regulatory

1. **This is not legal advice.** Nothing in this repository — code, documentation, ADRs, regulatory mapping docs — constitutes legal advice. The mapping documents in `docs/` (SR 11-7, OCC 2011-12, SOX 404 ITGC, SEC 17a-4, SEC Reg-BI, FCRA / Reg-V, ECOA / Reg-B, BSA/AML, GLBA Safeguards, EU AI Act, NIST AI RMF, ISO/IEC 42001, COSO ICAIR, CFPB Circular 2022-03) are reference mappings to help adopters point qualified counsel at relevant clauses. Applicability is a deployer-and-counsel determination.

2. **This framework does not absolve adopters of SR 11-7 model-validation obligations.** `ModelInventory` provides the recordkeeping surface (status state machine, validation-date tracking, overdue query). It does not perform model validation. Second-line validation — backtesting, benchmarking, conceptual-soundness review, ongoing monitoring per SR 11-7 § V — remains the deployer's institutional responsibility.

3. **This framework does not constitute a SAR filing.** `SARWorkflowAudit` records the workflow steps a BSA officer takes (alert review, escalation, filing decision). The FinCEN BSA E-Filing System is the system of record for filed SARs. An audit-chain entry is recordkeeping evidence, not a regulatory submission.

4. **MIT license does not shield adopters from regulatory liability.** The license is a contract between author and adopter. The adopter's regulatory obligations to the OCC, Federal Reserve, FDIC, SEC, FINRA, CFPB, FinCEN, state regulators, and foreign supervisors are unaffected by accepting MIT-licensed software.

### Trust boundary and threat model

5. **This framework does not defend against sovereign-agent intentional veto bypass.** See ADR-0018 for the explicit scope. The Sovereign Veto pattern assumes the operator population is not the adversary; an operator with credential, signing key, and runtime access who chooses to clear the veto for an undocumented reason is outside the framework's threat model.

6. **WORMLedgerStore is best-effort within OS-level controls.** The Python implementation uses `chmod 0o444` plus an in-process guard. A privileged user (root, `CAP_DAC_OVERRIDE`, the deployer's IAM operator) can reset permissions and overwrite the file. For production deployments where WORM is a regulatory requirement under SEC 17a-4(f), pair this backend with **S3 Object Lock in COMPLIANCE mode** (not GOVERNANCE mode) at the storage layer — see ADR-0013 and [`DEPLOY-CHECKLIST.md`](DEPLOY-CHECKLIST.md).

7. **MIProxy's local backend protects against in-process verifier substitution; it does not protect against host-level substitution.** `LocalMIProxy` hashes the verifier source + canonical config and signs with HMAC-SHA256 using a deployer-supplied key. If the attacker controls the host and can replace the key material, the attestation can be re-minted. ADR-0015 documents the substrate-pluggable path (SLSA provenance, in-toto attestations) for the higher-assurance posture.

### Detection vs prevention

8. **ProtectedClassProxyDetector ships the mutual-information arm only (v1.2).** ADR-0019 named three method arms: mutual information, SHAP attribution audits, and conditional-demographic-disparity measures. v1.2 ships the MI arm with the synthetic-benchmark FPR/FNR documented in ADR-0019 § "v1.2 ship reconciliation"; the other two arms remain on the v1.3 roadmap. Known weaknesses of the MI arm: high-dimensional sparse features (estimator variance), non-linear conjunctive proxies (the detector treats each feature independently), and binning sensitivity for discretized continuous inputs.

9. **The audit chain detects tampering; it does not prevent it.** A hash-chain invariant violation means a previously-valid chain has been mutated. Recovery is operator-driven. The chain is the evidence, not the enforcement mechanism.

10. **The Vendor Score Gate detects emission diff; it does not validate the vendor's underlying model.** Same `(vendor_id, input_hash, model_version)` producing a different score is the drift signal. Whether the vendor's new score is more accurate, less accurate, or differently biased is outside the framework's signal.

### Infrastructure dependencies

11. **Network-dependent backends require external service availability.** `RFC3161Source` requires the configured TSA (e.g. FreeTSA, Sectigo, DigiCert) to be reachable; `RekorWitness` requires the configured Rekor instance (public-good `rekor.sigstore.dev` or a private instance) to be reachable; `OpenTimestampsWitness` requires the configured calendar server. Default fallback behavior is documented in [`FAILURE-MODES.md`](FAILURE-MODES.md) § Defaults.

12. **Zero runtime dependencies means deployers implement integrations themselves.** The package depends only on the Python ≥ 3.12 standard library by design. Deployers integrating with their substrate (S3, DynamoDB, Postgres, Datadog, Splunk, ServiceNow, Jira, ArcSight, internal SIEM) write the integration glue. Reference adapter shapes are in `examples/`.

### Data lifecycle

13. **No GDPR right-to-erasure handling.** The hash chain is append-only by design. Removing an entry would invalidate every subsequent hash. For deployments where Article 17 erasure or Reg-S-P deletion is required, the deployer's pattern is **key-rotation + envelope encryption at the payload layer** (encrypt PII fields with a per-subject key; rotate / destroy the key on erasure request; the chain remains valid but the payload is cryptographically unreadable). This is a deployer-implemented pattern; the framework does not ship it.

14. **No automatic retention enforcement.** ADR-0017 documents the seven-year default per SEC 17a-4(b)(4) for broker-dealer records and the comparable retention windows for SOX (seven years), BSA (five years), FCRA (twenty-five months for credit reports, longer for adverse-action records). The framework records; the deployer schedules cold-storage migration and end-of-retention destruction per their counsel's guidance.

### Coverage scope

15. **U.S. FSI overlay is primary; EU / UK / SG mappings are partial.** v1.1 ships EU AI Act, ISO/IEC 42001, and NIST AI RMF mapping docs as reference. UK FCA SS1/23 and Singapore MAS Veritas mapping are on the roadmap (see [`ROADMAP.md`](ROADMAP.md)); deployers in those jurisdictions retain qualified counsel.

16. **Insurance-specific overlays (NAIC Model Bulletin AI, state DOI requirements, MCAS reporting) are out of scope for v1.1.** The framework's primitives compose; an insurance-overlay sister package is a community contribution candidate.

---

## What this framework DOES claim

- A tested set of governance primitives (DEFCON, Sovereign Veto, Autonomy Ladder, hash-chain audit, Shadow Mode) with a published ADR rationale.
- Four substrate-pluggable Protocol seams (LedgerStore, TimestampSource, WitnessRegister, MIProxy) so the deployer wires the backends their compliance posture requires.
- FSI-specific gates (AdverseActionGate, SARWorkflowAudit, EquityAudit, BestInterestCheck, ModelInventory) that emit structured chain entries tied to the named regulatory clauses.
- Vendor-mediated-AI scoring drift detection (VendorScoreGate) with five FSI vendor classes pre-registered.
- 273 tests on Python 3.12 + 3.13 in CI.
- Zero runtime dependencies.

The combination is the framework. The deployer's substrate is the production deployment.

---

## Related

- [`DISCLAIMER.md`](DISCLAIMER.md)
- [`FAILURE-MODES.md`](FAILURE-MODES.md)
- [`NEGATIVE-USE-CASES.md`](NEGATIVE-USE-CASES.md)
- [`DEPLOY-CHECKLIST.md`](DEPLOY-CHECKLIST.md)
- ADR-0013 (WORM persistence), ADR-0017 (retention), ADR-0018 (threat model), ADR-0019 (proxy detector deferral)
