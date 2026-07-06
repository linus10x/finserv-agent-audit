# Security Policy

## Supported versions

| Version | Supported (security fixes) |
|---|---|
| 2.x | ✅ current |
| 1.x | ❌ superseded — upgrade to 2.x |

"Supported" = security fixes land on the latest 2.x minor. Older 2.x minors are not separately backported;
pin and upgrade forward.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Preferred: **GitHub private vulnerability reporting** — the "Report a vulnerability" button under this repo's
**Security** tab (Security Advisories). It gives us a private, durable, GitHub-native channel. If that is not
available to you, send a direct message via LinkedIn (https://linkedin.com/in/kunjarbhaduri) as a fallback.

This is a solo-maintained research library: expect a **best-effort acknowledgment, typically within 48
hours**, and a resolution timeline once the report is triaged. Coordinated disclosure is welcome; reporters
who want credit will get it once a fix ships.

---

## Adversary model

This is a **reference implementation of a control surface**, published to be attacked. It ships to attackers
by design — the demo runs from a cold clone with no install and no network. The guarantees do **not** depend
on the secrecy of the mechanism; they are meant to hold against an adversary who has read every line. There
are no secrets, credentials, or keys in the repository (a `gitleaks` scan runs in CI).

**Trust boundaries considered** (not just runtime ops):
1. **The audit-log store** — an attacker with write access to the `*.jsonl` chain (e.g. a compromised admin).
2. **The external witness** — the independent register the chain head is anchored to.
3. **The evidence supplied to a grant** — the inputs an agent presents to claim authority.
4. **The veto's own decision inputs** — what the sovereign veto reads to decide.

### Three verifiers, three jobs

The demo (`examples/demotion_gate_demo.py`) is self-verifying — it asserts each expected catch fires and exits
non-zero if any does not, so a green run *is* the proof. It runs **three distinct verifiers**, and the split
is the point:

| Verifier | Call | Catches |
|---|---|---|
| **Hash-chain** | `chain.verify()` / `verify_strict()` | In-place mutation of a recorded event, *within* the trust boundary |
| **Authority-invariant (semantic)** | `verify_authority_invariants()` | A grant not backed by bound evidence, and structural violations such as grantor = examiner (independence) |
| **External-anchor** | `verify_against_external_anchors()` | Tampering that a chain rewrite would hide from a hash check — truncation and full regeneration — by comparing against a witness the attacker does not control |

**The four attacks the demo runs, and which verifier catches each:**

| # | Attack | Caught by |
|---|---|---|
| 1 | A **forged grant** with no bound evidence (chain hashes regenerated so `chain.verify()` still passes) | **authority-invariant (semantic)** verifier — `AuthorityInvariantError` |
| 2 | A **deleted revocation / head-truncation** (agent appears to still hold A3) | **external-anchor** verifier — `WitnessContradictionError` |
| 3 | An **in-place mutation** of a recorded event | **hash-chain** verifier |
| 4 | A **backdated regeneration** of the whole history that drops the revocation | **external-anchor** verifier (the witnessed head is absent) |

A hash chain alone survives none of attacks 1, 2, or 4 — an attacker who controls the log store rewrites it
from genesis. The semantic verifier is what catches authority that was never evidence-backed (attack 1); the
external anchor is what catches a coherent rewrite that drops a witnessed head (attacks 2 and 4). Note that
attacks 2 and 4 share one detection mechanism — *a previously witnessed head is missing* — reached by two
different routes (truncation vs. regeneration); the check is head-presence against the witness, not a
timestamp comparison.

---

## Assurance boundary — the theorem and where it stops being true

Each invariant holds **only under an explicit assumption set.** Stated so a reviewer can see where the
guarantee ends rather than trusting a slogan:

**Ledger integrity** — *"no undetected tampering of the recorded history."*
- Holds **given:** the external-anchor verifier runs against a witness the attacker does **not** control, and
  that witness's record of the chain head is authentic.
- **Stops being true if:** the attacker controls *both* the log store *and* the witness. A coherent forged
  history plus a matching forged anchor then passes. Independence of the witness is load-bearing.
- **Demo caveat (read this):** the runnable demo anchors to an in-process **`RecordingWitness`** — it proves
  the *algorithm* offline with no network, but provides **no external independence** by itself. The library
  ships **write-side reference clients** (`RekorWitness`, `OpenTimestampsWitness`) that submit a digest and
  return a receipt; it does **not** ship — and the demo does **not** exercise — the networked **read-back**
  of an inclusion proof into an `ExternalAnchorRecord`, which is what closes the loop in production.
  Additionally, `RekorWitness` submits a `hashedrekord` with a placeholder (empty) signature for
  transparency-log-only use; a real Rekor instance may require signing. **Before relying on external
  anchoring in your environment, wire (a) signing appropriate to your register and (b) the read-back +
  compare, and validate the loop against your own instance.** Do not read a green offline demo as "externally
  anchored in your environment."
- **Anchors are unsigned digest commitments** by default: the witness attests the head *existed at a time*,
  not *who committed it*. If you need authorship, sign the head with a KMS-held key and record the key id.

**Sovereign veto / demotion gate** — *"no action executes at an elevated autonomy level while the veto is
engaged or the gate is blocked."*
- Holds **given:** every authority-bearing action routes through the gate (no bypass path in the integrating
  application), and the veto/gate inputs are themselves trustworthy.
- **Stops being true if:** the integrating system has a code path that acts without consulting the gate, or if
  the **veto's decision inputs are compromised** (a poisoned signal that says "all clear"). The ledger records
  what the veto decided; it does not attest that the veto's *inputs* were sound.

**Authority lifecycle (grant → examine → revoke)** — *"authority is granted only against bound evidence, and
revoked the moment that evidence fails."*
- Holds **given:** the evidence presented at grant time is *semantically* valid.
- **Stops being true if:** the upstream evidence is itself fabricated. The gate checks that evidence **exists
  and is bound** to the grant (and that grantor ≠ examiner) — not that the underlying claim is true.
  Garbage-in still binds. Semantic validation of the evidence is the integrator's responsibility, and is where
  model/data-layer attacks (prompt injection, evidence poisoning) live.

---

## What this does NOT protect against (scope honesty)

- **Confidentiality** — the audit chain is **tamper-detecting, not encrypting.** Encrypt `*.jsonl` at rest per
  your data classification; never log secrets/PII/strategy in `AuditEvent.payload` (strip at the app layer).
- **A fully compromised witness** — independence is an assumption the code cannot enforce (see above).
- **Time-source trust** — detection uses witnessed-head presence, not clock comparison; the local
  `witnessed_at` is not a trusted time. A trusted time requires a production witness that provides one
  (OpenTimestamps' Bitcoin attestation, a Rekor log time, or an RFC-3161 authority).
- **Semantically false but well-formed evidence** — model/data-layer attacks that produce a "valid" grant.
- **Replay** — re-appending a previously valid event is bounded by the `prev_hash` chaining; verify this
  holds for your integration rather than assuming it.
- **Availability / denial of service** — out of scope; this is an integrity/authority surface.
- **The threshold values themselves** — those in `defcon_state_machine.py` are illustrative; calibrate.

---

## Supply chain of this library

- **Zero third-party runtime dependencies (Python stdlib only)** — there is no transitive dependency surface
  to compromise in the runtime path. (Dev/test tooling is separate and pinned.)
- **Verify what you pulled.** Releases are tagged and DOI-archived on Zenodo; confirm the artifact you install
  matches a published release digest / the archived version before deploying a control library into a
  regulated environment.
- CI runs `gitleaks`, `bandit`, CodeQL, `pip-audit`, and OSV-Scanner on every change.

---

## Deployment hardening (before using any pattern in a regulated environment)

1. **Wire a real external witness end-to-end** (Rekor / OpenTimestamps / RFC-3161): signing + inclusion-proof
   read-back + compare — the offline `RecordingWitness` is for the demo, not production (see assurance boundary).
2. **Review all threshold values** in `defcon_state_machine.py` — calibrate to your risk tolerance.
3. **Implement access controls** — only authorized agents/operators may call `manual_override()` and
   `SovereignVeto.clear()`; use read-only IAM boundaries for agent roles.
4. **Encrypt audit logs at rest** — tamper detection ≠ confidentiality.
5. **Verify on a schedule** — run `AuditChain.verify()` and `verify_against_external_anchors()` periodically;
   alert on failure or on a `WitnessContradictionError`.
6. **Never log secrets in payloads** — strip credentials, PII, and strategy from `AuditEvent.payload` at the
   application layer before logging.

*This is independent research, not legal advice. The regulatory mappings in this repository are reference
mapping, not a certification or an attestation of record.*
