# Sample MIProxy Attestation Receipt

**Status:** Sample artifact for training. Synthetic data; do not rely on the receipt below as a verifiable attestation.
**Last reviewed:** 2026-05-28.

> See [`ADR-0015`](../../docs/adr/0015-mi-proxy-module-integrity.md) for the MI Proxy design, and [`finserv_agent_audit.governance.mi_proxy`](../../src/finserv_agent_audit/governance/mi_proxy.py) for the implementation.

---

## Receipt body

```json
{
  "attestation_format": "finserv-agent-audit/mi-proxy/v1",
  "issued_at": "2026-05-28T17:42:11.224Z",
  "issuer": {
    "backend": "LocalMIProxy",
    "backend_version": "finserv-agent-audit==1.1.0",
    "operator_principal": "ops.attestation-signer@bank.northriver.example",
    "key_id": "mi-proxy-key-2026Q2"
  },
  "claim": {
    "component_id": "finserv_agent_audit.governance.audit_chain.AuditChain",
    "component_version_pin": "1.1.0",
    "canonical_source_sha256": "0e5fae217bd64823a91ce0a0b09cd1e6dccaef72ec3a47b09ed5f2b0ac1b21d3",
    "canonical_config_sha256": "f1248a3c95eb02c4e29d8a01f5b3e90c1be7ec46aab92a55810cdf1b30ec0a4c",
    "runtime_environment": {
      "python": "3.12.7",
      "platform": "linux-x86_64",
      "container_image_digest": "sha256:8f4e2c1d093b27ec05fd9114b8c2ab90ec5e7afd1c92e3b4081d2a9c5f6a7b8e"
    }
  },
  "signature": {
    "algorithm": "HMAC-SHA256",
    "value": "b7c4e0a8d2f5614c9b3e7a01f2d8c5e9b7f4a1d8e3c0a7f4b1e8d5c2a9f6c3d0"
  },
  "verifier_self_attestation": {
    "verifier_callable": "finserv_agent_audit.governance.audit_chain.AuditChain.verify_strict",
    "callable_invocation_ref": "verify-run-20260528T174211Z-NRB-AUDIT-001",
    "callable_returned": true,
    "mi_proxy_called": "finserv_agent_audit.governance.mi_proxy.LocalMIProxy.verify_integrity",
    "mi_proxy_result": "verified"
  }
}
```

## How an auditor reads this receipt

1. **Identify the backend.** `issuer.backend` is the named MIProxy implementation in production. For `LocalMIProxy`, confirm the deployer's documentation names the HMAC-SHA256 key custody (KMS, HSM, in-process file). For substrate-pluggable backends (`SLSA`, `in-toto`), confirm the corresponding attestation framework's provenance file is on hand.

2. **Verify the claim.** `claim.canonical_source_sha256` is the SHA-256 of the verifier callable's source as of attestation time. The auditor cross-checks this hash against the source the client has under change-management — if it disagrees, the verifier has been swapped under the operator's feet.

3. **Verify the signature.** Re-run `MIProxy.verify_integrity(claim, attestation)` in the client's environment; expect a no-raise result. Induce a failure on a sandbox by mutating one byte of the source; expect `IntegrityVerificationError`.

4. **Tie to the chain.** `verifier_self_attestation.callable_invocation_ref` points to the run identifier captured in the operational log. Tie to the `AuditChain.verify_strict()` output for that run; confirm the strict-verify returned `True` and that no `IntegrityVerificationError` was raised.

5. **Test the failure mode.** Ask the deployer to demonstrate the failure path: swap the verifier source on a sandbox, re-run the attestation, observe `IntegrityVerificationError`. This is the auditor's evidence that the control operates as designed, not just that it exists.

## Cross-references

- [`ADR-0014`](../../docs/adr/0014-persistence-witness-timestamp-pattern.md) — the four Protocol seams (LedgerStore, TimestampSource, WitnessRegister, MIProxy)
- [`ADR-0015`](../../docs/adr/0015-mi-proxy-module-integrity.md) — MIProxy detailed rationale + backend pluggability
- [`ASSURANCE-GUIDE.md`](../../ASSURANCE-GUIDE.md) — Part 1, "Chain attestation" — the auditor walk-through for MIProxy
- [`FAILURE-MODES.md`](../../FAILURE-MODES.md) — row 7 (verifier compromise) — what this receipt addresses

---

*Patterns are software, not legal advice. The receipt above is illustrative; production receipts depend on the deployer's chosen MIProxy backend, key-custody substrate, and verifier callable.*
