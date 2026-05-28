# ADR-0015: MI Proxy — Module Integrity Verifier Chain-of-Custody

**Status:** Accepted
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit v1.1
**Pairs with:** ADR-0014 (persistence / timestamps / witness anchor seams)

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel and the firm's model-risk-management function. No attorney-client relationship is formed by use of this ADR. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).
>
> **Citation update (April 17, 2026):** Where this ADR references SR 11-7 / OCC Bulletin 2011-12 as the prudential MRM citation, note that those instruments were superseded for new examinations / rescinded by the joint OCC / FRB / FDIC issuance of April 17, 2026 (OCC Bulletin 2026-13), which **excluded generative + agentic AI from scope** pending a forthcoming joint RFI. The model-implementation-integrity discipline described here is independent of the MRM citation lineage; the verifier-integrity control surface is the one most likely to be cited approvingly in whatever RFI outcome lands. See [`docs/interagency_mrm_2026_overlay.md`](../interagency_mrm_2026_overlay.md).

---

## Context

ADR-0014 introduced four Protocol seams that push the audit chain's trust boundary outward: the substrate (Postgres, S3, DynamoDB, WORM appliance), the TSA (FreeTSA, DigiCert, internal HSM-backed TSA), and the witness log (Rekor, OpenTimestamps). Three of the four seams (Persistence, Timestamps, Witness) are documented in ADR-0014.

There is one trust-boundary asset that ADR-0014 explicitly does not address: **the verifier itself.**

`AuditLedger.verify_chain()` is the function that internal audit, external audit, FINRA examiners, OCC examiners, and CFTC supervisors rely on to attest to chain integrity. If the verifier binary or its configuration is swapped — by a malicious operator, by a supply-chain attack on the package, by an undetected drift between the deployed verifier and the one approved through SDLC change management — then a compromised verifier returns false-positive `verify_chain()` across the entire audit chain. The hash chain itself remains internally consistent; the verifier is the lie.

This is the "verifier compromise" failure mode. SR 11-7 model risk management identifies it implicitly under "model implementation": a model can be sound on paper and compromised in implementation. The MI Proxy is the technical control behind that policy.

The internal audit named this gap under Finding D9.1 (Critical) on 2026-05-28; ADR-0014 closed three of the four required seams and named the fourth here.

The constraint that bounds every choice in this ADR is the same as ADR-0014: **the package's Zero-Runtime-Dependencies posture is load-bearing.** The default MI Proxy backend must work stdlib-only. External attestation (SLSA / in-toto / Sigstore cosign) is opt-in via `[project.optional-dependencies]` and is never imported by `finserv_agent_audit/__init__.py`.

### The recursive-verifier problem (named explicitly)

A natural objection to the MI Proxy: "who verifies the verifier of the verifier?" The objection is real and the ADR refuses to pretend it has a closed-form answer.

The recursion terminates somewhere — at the operator's signing key for the local backend, at the attestation service's root of trust for the opt-in backends, at a hardware root of trust (TPM, HSM) for the strongest deployments. There is no software-only solution that closes the regress. What the MI Proxy *does* provide is the artifact that makes the recursion visible: every `verify_chain()` call now emits a recordable attestation about the verifier's identity at the moment of the call. The regress moves from "implicit, undetectable" to "explicit, named at one level of indirection." That is the gain. The package does not claim more.

For FSI adopters, the practical guidance is: wire the default `LocalMIProxy` everywhere; wire an asymmetric-attestation backend (SLSA or Sigstore) when the verifier is consumed by an external auditor or by a regulator; document the root of trust in the firm's model-risk-management inventory under SR 11-7.

## Decision

Introduce an `MIProxy` Protocol with two methods, ship a stdlib-only default backend (`LocalMIProxy`), and add a `verify_chain` hook that fails closed when attestation fails.

### Protocol surface

```python
class MIProxy(Protocol):
    def attest(self, component_id: str) -> Attestation: ...
    def verify_attestation(self, attestation: Attestation) -> bool: ...
```

```python
@dataclass(frozen=True)
class Attestation:
    component_id: str          # e.g. "finserv_agent_audit.governance.audit_chain"
    sha256_hex: str            # hash over the verifier source + relevant config
    timestamp_iso: str         # UTC ISO 8601
    signature_b64: str         # signature over (component_id, sha256_hex, timestamp_iso)
    backend_id: str            # "local-hmac" | "slsa" | "in-toto" | "sigstore-cosign"
```

The Protocol carries two methods on purpose. `attest()` produces a signed assertion about *this* verifier at *this* moment. `verify_attestation()` re-validates an assertion at verify time. Splitting the two lets downstream backends produce attestations out-of-band (CI build pipeline, SLSA provenance generator, firm-internal signing service) and lets the runtime only carry the re-validation path.

### Default backend — `LocalMIProxy`

Shipped in `src/finserv_agent_audit/governance/mi_proxy.py`:

- Reads the verifier module's source bytes via `importlib.resources` (avoids `inspect.getsource` brittleness across packaging tooling).
- Computes SHA-256 over `(source_bytes + canonical_config_bytes)`.
- Signs `(component_id, sha256_hex, timestamp_iso)` with HMAC-SHA256 using a static key loaded from the environment variable `FINSERV_AUDIT_MI_PROXY_KEY` (32+ bytes, base64 or hex).
- If the key is absent: emits a non-suppressible `MIProxyKeyMissingWarning`, signs with a zeroed key, and any subsequent `verify_attestation()` against a real key fails closed. The verifier refuses to silently degrade.
- Attestations are time-bounded: `verify_attestation()` rejects attestations older than `max_age_seconds` (default 86_400 — one day). Override per deployer policy. FSI deployers operating under tighter change-window controls reduce this to the duration of a single trading day or shorter.
- `backend_id="local-hmac"`.

The default is symmetric-HMAC, not asymmetric. The reason: HMAC stays stdlib; asymmetric signatures pull in `cryptography`, which violates Zero-Deps. Deployers needing asymmetric attestation (non-repudiation by a third party, third-party auditor verification, regulator-facing verification) wire the opt-in backend.

### Opt-in backend — external attestation

A second backend family (not shipped in v1.1; documented for the integration shape) delegates to an external attestation service:

- **SLSA provenance** — read `provenance.json` from a known-location artifact registry; verify against the build pipeline's signing certificate.
- **in-toto** — verify a layout against the deployed verifier binary.
- **Sigstore cosign** — verify a `cosign sign-blob` signature against the Fulcio-issued certificate, with Rekor inclusion proof.

These backends ship under the `[project.optional-dependencies] attestation` extra in a forthcoming release; the core package never imports them.

### Hook into `verify_chain`

`AuditLedger.verify_chain()` accepts an optional `mi_proxy: MIProxy | None = None` parameter:

- If `mi_proxy is None`: default behavior is preserved (v1.0 / ADR-0014 semantics). Existing callers see no change.
- If `mi_proxy is not None`: before walking the chain, the verifier calls `mi_proxy.attest(component_id="finserv_agent_audit.governance.audit_chain")` and `mi_proxy.verify_attestation(...)`. If attestation fails, raise `IntegrityVerificationError` and **refuse to return a verified result**. Fail-closed.

The hook is opt-in to preserve v1.0 backward compatibility. The recommended posture in deployment documentation is to wire `mi_proxy` whenever the audit chain is consumed by an external auditor, an FSI regulator, or a downstream financial-reporting flow under SOX 404 scope.

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Trust the verifier implicitly | Assumes a trust boundary the framework cannot enforce. The whole point of v1.1's audit-hardening pass is to make that boundary explicit and testable. SR 11-7 model-implementation risk is a documented examination focus. |
| Require external attestation (SLSA / cosign) as the default | Forces an infra dependency on every adopter. Breaks Zero-Deps. A v1.1 deployer on a single VM should be able to use the framework end-to-end with stdlib only. Asymmetric backends remain opt-in. |
| Merkle tree of verifier state over time | Gives the *history* of verifier identities, not the answer to "is THIS binary the one we approved." The MI Proxy answers the question; a Merkle log of attestations is a derivative artifact and can be built on top. |
| Embed the verifier hash directly in `AuditEntry` | Couples every chain entry to a verifier-state artifact. Forces re-attestation per entry instead of per verify. Inflates the chain. The MI Proxy fires per `verify_chain()` call, which is the right cadence — verify is the action that matters. |
| Sign the chain head with an asymmetric key at append time | A different pattern (signed-log, à la Certificate Transparency). Useful, but orthogonal: it attests to the *chain*, not the *verifier*. The witness anchor in ADR-0014 covers the signed-log direction. |
| Require the deployer to wire OS-level integrity measurement (Linux IMA, Secure Boot, TPM remote attestation) | The right answer in regulated environments, but the package cannot ship it; OS-level integrity is the deployer's substrate, not the library's. The MI Proxy is the layer the library can own. |
| Use the firm's enterprise PKI as the signing root | Considered. The Protocol surface supports it: a deployer-side backend that signs against an enterprise CA-issued key is straightforward (~60 LOC). It does not become the default because not every adopter operates an enterprise PKI; HMAC is the universal lowest-friction default. |

## Consequences

**Positive.**
- Closes the verifier-compromise failure mode with a real, fail-closed detection mechanism.
- Zero-Deps badge intact. Default backend uses `hashlib`, `hmac`, `base64`, `importlib.resources` — all stdlib.
- The Protocol surface is small enough that downstream deployers wire SLSA / in-toto / cosign backends in ~80 LOC against the same interface.
- Existing `AuditLedger.verify_chain()` callers are unaffected. The hook is opt-in.
- The recursive-verifier problem is named explicitly in the ADR. Adopters cannot reasonably claim the pattern solves it; they can claim it makes the trust assumption one level more explicit, which is the honest claim.

**Negative.**
- HMAC keys must be managed by the deployer. The package does not ship key-rotation tooling; that is a deployment concern. The `MIProxyKeyMissingWarning` and fail-closed-on-mismatch posture surface the problem loudly when keys are misconfigured, but the deployer owns the lifecycle. FSI deployers typically integrate with an enterprise key-management service (AWS KMS, HashiCorp Vault, on-prem HSM); the integration is wired at the env-var population layer.
- The default backend protects against in-process verifier swap but not against an attacker with read-access to the HMAC key. Asymmetric signatures (SLSA / cosign) close that gap; the deployer pays the dependency cost on their side, not in the core package.
- The verifier's `component_id` is a string; the default backend hashes the module's source file. If the deployer monkey-patches `verify_chain` at runtime via `setattr(module, ...)`, the hash will not change. This is a documented limitation; defending against runtime monkey-patching requires a different posture (sandboxed verifier process, kernel-level integrity measurement) that is out of scope for a Python package.
- Adds approximately 5ms per `verify_chain()` call with the local backend. Measured on Apple Silicon; reproducible via `tests/test_mi_proxy.py::test_attest_latency_local_backend`. For audit pipelines that call `verify_chain()` once per audit cycle, the cost is irrelevant; for hot-path callers, the deployer should cache the attestation result for the duration of a known-stable window.

**Architectural.**
- The MI Proxy is the **second** out-of-band trust seam in the audit stack. The first is the witness anchor (ADR-0014 Seam 3), which makes the chain history tamper-evident (witness-anchored hash-chain mechanism). The MI Proxy makes the verifier itself tamper-detecting. Together they close the loop on "is the chain real and is the function reading it real."
- The Protocol-with-default-backend pattern matches ADR-0014's three seams. The same downstream-deployer story applies: small Protocol surface, stdlib reference, opt-in stronger backends. This consistency across the four seams is intentional — adopters learn one pattern and apply it four times.

## What this ADR does NOT cover

- **Asymmetric default.** The default backend is HMAC. Deployers requiring non-repudiation wire the opt-in backend.
- **Key rotation.** The deployer owns the HMAC key lifecycle. The package only requires the key be present and at least 32 bytes; it does not rotate, escrow, or manage keys.
- **Runtime monkey-patching defense.** A deployer with code-execution privilege on the verifier host can replace `verify_chain` at runtime in ways the source-hash backend does not detect. Defending against this requires OS-level integrity measurement (Linux IMA, macOS Endpoint Security, Windows VBS) — out of scope for the package.
- **Verifier-of-the-verifier.** The MI Proxy attests to the verifier. The MI Proxy itself is part of the trust boundary. Recursion stops at the operator's signing key for the local backend, and at the attestation service's root of trust for the opt-in backends. The package documents this and does not pretend to close infinite regress.
- **Integration with the witness anchor.** A future ADR-0015-A1 may write the MI Proxy attestation result as a `decision_type="verifier_attestation"` entry in the audit chain, binding the verifier's identity into the chain it verifies. Out of scope for the v1.1 deliverable.

## Regulatory Mapping

- **SOX 404 ITGC — Change Management category** — the verifier is privileged software; changes to it must go through approved change. The MI Proxy fails closed when the deployed verifier diverges from the attested one. See ADR-0012. [UNVERIFIED — primary source not fetched]
- **SR 11-7 — Federal Reserve Guidance on Model Risk Management (2011)** — model-implementation risk; the verifier is a privileged component whose implementation soundness is in scope. The MI Proxy is the integrity control behind the model-implementation expectation. (SR 11-7 superseded for new examinations by the April 17, 2026 joint issuance — OCC counterpart OCC Bulletin 2026-13, which excluded generative + agentic AI from scope; see [`docs/interagency_mrm_2026_overlay.md`](../interagency_mrm_2026_overlay.md).) [UNVERIFIED — primary source not fetched]
- **SOC 2 Type 2 CC7.2** — *System Monitoring*. The verifier is a privileged component in the audit-trail pipeline; its integrity is a CC7.2 expectation.
- **FFIEC IT Handbook, Outsourcing Booklet** — when the opt-in backend delegates to an external attestation service (SLSA, cosign + Fulcio), third-party-attestation expectations apply to that service. The package documents the integration; the deployer owns the third-party risk assessment.
- **ISO/IEC 42001:2023** — *AI Management System*. § 8.4 (Operational Controls) expects integrity controls on the AI system's operational software. The verifier qualifies; the MI Proxy is the integrity control.
- **EU AI Act (Regulation (EU) 2024/1689), Annex IV § 1(g)** — record-keeping for third-party components. The opt-in backend's attestation chain is the record. [UNVERIFIED — primary OJ text not fetched]
- **NYDFS 23 NYCRR Part 500** — § 500.06 audit-trail integrity; the verifier's integrity is part of the trail's integrity. [UNVERIFIED — primary source not fetched]
- **RFC 6962** — *Certificate Transparency*. The opt-in Sigstore backend uses Rekor (a CT-style log). The trust model is identical: an external append-only log records what was attested at time T; later attempts to claim a different attestation contradict the log.

## Pre-mortem

What fails:

1. **Deployer ships without setting `FINSERV_AUDIT_MI_PROXY_KEY`.** Mitigation — `MIProxyKeyMissingWarning` is non-suppressible; `verify_attestation()` against a real key fails closed; the production-readiness check (forthcoming `make production-ready` target in Tranche 3) refuses to pass with an unset key.
2. **HMAC key leaks via environment-variable dump in a CI log.** Mitigation — operator-side hygiene; the package documents the risk and recommends KMS-backed env-var injection rather than static config files.
3. **External attestation backend is wired but the attestation service is offline at verify time.** Mitigation — fail-closed semantics; `verify_chain()` raises `IntegrityVerificationError` rather than degrading silently. Deployers running in an air-gapped environment use the local backend or wire a private attestation service.
4. **Verifier source is hashed correctly but a malicious operator patches a downstream-imported helper.** Mitigation — `component_id` can be parameterized to include the helper's source bytes; the deployer extends the hash scope per their risk model. Default scope is the `audit_chain` module; extending it is a deployer decision.

## Reversibility

High at the wiring level — the hook is opt-in, and a deployer can remove the `mi_proxy=` parameter and revert to v1.0 behavior. Historical attestations remain valid against the historical key. Switching backends (local-HMAC to SLSA) requires a clean cutover with a documented transition window; attestations produced under the previous backend remain verifiable as long as the key (or certificate) material is preserved.

## Cross-references

- **Implementation:** `src/finserv_agent_audit/governance/mi_proxy.py` — `MIProxy` Protocol + `Attestation` dataclass + `LocalMIProxy` default backend + `IntegrityVerificationError` + `MIProxyKeyMissingWarning`
- **Hook:** `src/finserv_agent_audit/governance/audit_chain.py` — `verify_chain(mi_proxy=None)` parameter; fail-closed when attestation fails
- **Tests:** `tests/test_mi_proxy.py` — round-trip, tampered binary, missing key, stale attestation, verifier-hook integration
- **Related ADRs:** ADR-0003 (Hash-chained audit ledger — the function this ADR protects) · ADR-0014 (Persistence / timestamps / witness anchor seams — companion ADR; same Protocol-with-stdlib-default pattern) · ADR-0012 (SOX 404 ITGC — change-management category)
- **Companion frameworks:** SLSA (Supply-chain Levels for Software Artifacts) · in-toto (supply-chain attestation framework) · Sigstore (signing + Rekor transparency log)

---

*Patterns are software, not legal advice. Regulatory citations are reference mappings; consult counsel for applicability to your control environment.*
