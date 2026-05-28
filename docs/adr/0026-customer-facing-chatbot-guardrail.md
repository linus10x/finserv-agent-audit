# ADR-0026 · Customer-Facing Chatbot Guardrail

**Status:** Accepted (shipped in v1.3)
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit v1.3

> **Reference pattern, not legal advice.** Precedent characterizations are summaries; readers must consult qualified counsel for jurisdiction-specific applicability. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

## Context

Banking chatbots sit at the point of action. A wrong answer can trigger a money movement, a security change, or a customer commitment the institution is then liable for. The customer-facing surface compresses three failure shapes the agent literature has tracked separately into one operational moment: a fabricated policy promise, an unauthorized commitment, and an off-corpus citation.

The settled-liability anchor of record is **Moffatt v. Air Canada**, British Columbia Civil Resolution Tribunal, February 14, 2024. Air Canada's customer-facing chatbot told a grieving customer that the carrier offered a retroactive bereavement-fare refund — a policy that did not exist in any approved source. The tribunal awarded CA$812.02 against the carrier, expressly rejecting the carrier's argument that the chatbot was a separate legal entity ("a separate legal entity that is responsible for its own actions"). The carrier was liable for what the chatbot represented to the customer.

Subsequent incidents on the financial-services adjacency reinforced the pattern. The Microsoft Bing launch demo misreported Gap's quarterly margins from a live financial filing; the Google Bard launch demo misstated which telescope took the first picture of an exoplanet, with intraday market-cap pressure on the parent reportedly in the tens of billions [UNVERIFIED — composite industry-press figures, not a primary-source statistic]. Industry-press composite figures for chatbot fabrication impact on financial services in 2024 cluster in the tens of billions globally with hallucination rates up to approximately 41% on finance-domain queries [UNVERIFIED — composite, not a primary source].

The legal and regulatory frame around the precedent is consolidating in parallel:

- **NIST AI 600-1** (Generative AI Profile, July 2024) explicitly names **Confabulation** as a tracked risk category for generative AI in deployment, with mitigations centered on grounding, citation, and human escalation pathways.
- **EU AI Act Article 13** imposes transparency obligations toward customer-facing users of high-risk AI systems; Article 14 mandates human-oversight architecture for high-risk systems including the ability for a human to override or interrupt the system.
- **CFPB Circular 2022-03** forces adverse-action notice obligations for any AI-derived consumer credit decision back onto the operator, regardless of the customer-facing surface that issued the notice.
- **ADR-0009** (FCRA / Reg V adverse-action gate) is the upstream counterpart to this ADR for adverse-action notice issuance; the guardrail's `REGULATORY_DISCLOSURE` action class routes Reg-V-adjacent statements through the same human-handoff pathway.
- **ADR-0017** (audit-chain retention, privilege, and discovery posture) governs the operator-side evidentiary record this guardrail produces; the audit-chain entries the guardrail emits sit inside the retention schedule and privilege-classification framework ADR-0017 specifies.

The patterns shipped through v1.2 did not address the customer-facing surface. `BestInterestCheck` (ADR-0013) handles SEC Reg-BI recommendations to retail customers, but does not handle the broader chatbot-fabrication surface. `AdverseActionGate` (ADR-0009) handles the FCRA notice, not the upstream chatbot promise that the notice will not be issued. The customer-facing chatbot has been an unguarded boundary on the framework's perimeter; ADR-0026 closes it.

## Decision

Ship `CustomerFacingChatbotGuardrail` in v1.3 as a three-layered interception wrapping every customer-facing chatbot response before it reaches the customer.

The three arms run in a fixed decision order. The order is itself the design — a money-movement attempt stops the pipeline before any RAG check runs because the chatbot is not authorized to make the commitment in the first place.

### Arm 1 — Action-class human-handoff routing

Five action classes route through a mandatory human handoff. The chatbot does not autonomously commit any of them; the guardrail returns `REQUIRES_HUMAN_HANDOFF` and the chatbot routes the customer to a human agent.

| `ActionClass` | Covers |
|---|---|
| `MONEY_MOVEMENT` | Transfer, payment, withdrawal, wire issuance |
| `COMMITMENT` | Account open / close, rate change, limit change, term modification |
| `SECURITY_CHANGE` | Password reset, MFA change, beneficiary change |
| `LEGAL_REPRESENTATION` | Statements that could be construed as legal advice or eligibility opinions |
| `REGULATORY_DISCLOSURE` | Privacy notice, adverse-action notice, fee disclosure |

The deployer narrows or widens the set on construction via `handoff_action_classes=`. The default ships all five enabled — the right side of the cost / risk trade-off for a v1.3 reference pattern.

### Arm 2 — Policy-grounded RAG citation check

Every response carrying a factual claim cites at least one `PolicySource` from the deployer's `PolicyCorpus`. The guardrail validates:

1. Each cited `source_id` exists in the corpus. Off-corpus citation -> `BLOCK` with reason code `RAG-OFF-CORPUS-CITATION`.
2. The response is semantically consistent with each cited source. Inconsistency -> `REVISE` with reason code `RAG-CITATION-INCONSISTENT` and a `suggested_revision` field pointing back at the corpus source.
3. A factual claim (regex: `$N`, fee, rate, hours, policy, APY, APR, refund, deposit, withdrawal, transfer, waive, offer, entitled, eligible, interest, overdraft, minimum) emitted without any citation -> `BLOCK` with reason code `RAG-NO-CITATION-WITH-CLAIM` or `FABRICATED-POLICY-PATTERN`.

The semantic-consistency check ships as a keyword-overlap heuristic (Jaccard with stopwords removed, default minimum overlap ratio 0.30). The `RAGSourceCheck` Protocol is the seam: a production deployer with an embedding backend plugs in an `is_consistent(response, source) -> bool` callable and replaces the reference check without touching the guardrail.

### Arm 3 — No-fabricated-policy assertion

Two regex banks ride over Arm 2:

- **Fabrication-signal patterns** ("our policy states", "we offer", "you can receive", "we will waive", "retroactive refund", "entitled to a", "we guarantee") flagged only when the response carries no in-corpus citation. These are the Air-Canada-shaped fabrication signals.
- **Known-bad patterns** ("bereavement refund", "late-payment forgiveness", "fee waived" without a `human agent` / `specialist` / `representative` qualifier) blocked **regardless of citation** because the deployer-side discipline is that the chatbot does not promise refunds, waivers, or forgiveness autonomously — those flow through the handoff arm by policy.

A `known_good_responses: frozenset[str]` short-circuits the pattern check for vetted responses. For corpora large enough to justify the memory profile, the deployer swaps the frozenset for a Bloom filter without changing the guardrail's interface.

### Audit-chain emission

Every `evaluate` call emits exactly one `AuditEventType.COMPLIANCE_CHECK` entry to the optional `audit_chain` carrying the decision, the reason code, the cited source IDs, the session id, the customer id, and the action class. The audit entry is written **before** any exception is raised so a regulator inquiring about a blocked response can still reconstruct what the chatbot tried to say.

## TRUST BOUNDARY

The guardrail is the bank's last line of defense before the customer sees the chatbot's output. The trust boundary is explicit:

- **Bank side (inside the boundary):** the policy corpus authoritative for what the bank says, the action-class taxonomy authoritative for what the chatbot may commit, the audit chain authoritative for what the chatbot tried to say. Money-movement, commitment, and regulatory-disclosure decisions stay on the bank side; the guardrail blocks the agent from issuing them autonomously.
- **Agent side (outside the boundary):** the agent's intended response is treated as untrusted input. The guardrail does not negotiate with the agent; it decides ALLOW / BLOCK / REVISE / REQUIRES_HUMAN_HANDOFF and the calling layer routes accordingly.

This is the Air Canada precedent operationalized as software architecture. The carrier's failed argument — "the chatbot is a separate legal entity" — is rejected at the trust boundary: the guardrail enforces that the chatbot speaks **only** what the bank's policy corpus has authorized, and **never** commits a money movement, security change, or regulatory disclosure on the bank's behalf.

## Alternatives Considered

- **Ship the RAG arm alone.** Rejected: the Air Canada chatbot would have passed a RAG-only check if it had cited any plausible source. Without the action-class arm, the chatbot still makes commitments the bank is liable for. Without the fabrication-pattern arm, the chatbot still emits "we offer" / "we will waive" outside of any cited source.
- **Ship the action-class arm alone.** Rejected: a chatbot blocked from money movement can still misstate fees, branch hours, or rate terms. The customer relies on the misstatement; the bank is liable. The Air Canada precedent expressly covers misstatements that do not themselves move money.
- **Ship the fabrication-pattern arm alone.** Rejected: pattern banks are a porous defense against a generative model. The model will paraphrase around any finite pattern set. Patterns are useful as a fast-fail surface on top of the structural arms, not as a substitute for them.
- **Use embedding-based RAG as the default.** Rejected for v1.3: introduces a runtime dependency (sentence-transformers or similar), a model-asset distribution problem, and a performance profile that varies by deployer hardware. The keyword-overlap reference plus the `RAGSourceCheck` Protocol seam preserves the stdlib-only discipline and gives deployers a clean upgrade path.
- **Treat all chatbot output as `LEGAL_REPRESENTATION` and route everything through human handoff.** Rejected: collapses the chatbot's value proposition. The guardrail is a precision instrument, not a kill switch — `SovereignVeto` (ADR-0002) is the kill switch when the failure mode warrants it.

## Consequences

**Positive.** A v1.3 deployment closes the Air Canada precedent on the operator side. The chatbot can speak from the policy corpus, the action-class taxonomy prevents the chatbot from making commitments the bank has not approved, and the audit chain becomes the evidentiary record the next tribunal inquiry will demand. The Protocol seam keeps the stdlib-only discipline while letting production deployments plug stronger checks in.

**Negative.** The keyword-overlap default RAG check is weak. A deployer running the guardrail unchanged in production is relying on a heuristic that can be paraphrased around. The module docstring and this ADR are explicit about that. A deployer that does not configure an embedding-based check is accepting a known-weak default — the framework signals it loudly and stops short of fixing it for them.

The known-bad pattern bank requires deployer-side care: the bank's legitimate offers ("we offer a 4.5% APY on our premium savings account") will trigger `FABRICATED-POLICY-PATTERN` if the chatbot emits them without an in-corpus citation. This is the correct behavior — the legitimate offer should be in the policy corpus and cited — but the deployer must seed the corpus before the chatbot goes live.

**Architectural.** The guardrail introduces no new persistence, no new network call, and no new runtime dependency. It composes onto the existing `AuditChain` (ADR-0003 + ADR-0014) and consumes the same `AuditEventType.COMPLIANCE_CHECK` event class the rest of the v1.x patterns use. The `RAGSourceCheck` Protocol is the only new Protocol seam this ADR introduces.

## Regulatory Mapping

- *Moffatt v. Air Canada*, 2024 BCCRT 149 (BC Civil Resolution Tribunal, February 14, 2024) — operator liable for chatbot-fabricated policy; CA$812.02 award; rejected the "chatbot is a separate legal entity" defense.
- NIST AI 600-1 (Generative AI Profile, July 2024) — Confabulation risk category, grounding and citation mitigations.
- EU AI Act, Regulation (EU) 2024/1689, Article 13 — transparency to deployers and end users; Article 14 — human oversight of high-risk systems.
- CFPB Circular 2022-03 — adverse-action notice obligations for AI-driven consumer credit decisions [UNVERIFIED — primary-source language not re-fetched in this session].
- finserv-agent-audit ADR-0009 — FCRA / Regulation V adverse-action gate (upstream pairing for `REGULATORY_DISCLOSURE` action class).
- finserv-agent-audit ADR-0017 — audit-chain retention, privilege, and discovery posture (governs the evidentiary record this guardrail produces).
- finserv-agent-audit ADR-0003 — hash-chained audit ledger (the substrate the guardrail emits to).
- finserv-agent-audit ADR-0026 (this ADR).

## Pre-mortem

The failure mode this ADR prevents: a buyer reads the v1.3 README, looks for the customer-facing surface, sees the guardrail named, wires it in at the chatbot-response-emission boundary, and the next Moffatt-shaped tribunal inquiry can be answered with an audit-chain replay showing the chatbot was blocked from fabricating the policy.

The failure mode this ADR creates if mishandled: a deployer ships the v1.3 default keyword-overlap RAG check into production, ignores the docstring's instruction to plug in an embedding-based check, the chatbot paraphrases around the keyword overlap and emits a fabricated policy that nonetheless co-occurs enough with corpus tokens to pass the heuristic, the customer relies on it, the bank is liable. Mitigation: the module docstring is explicit that the keyword overlap is a reference, not a production check; the Protocol seam is in place; this ADR names the deferral; and the test suite exercises the inconsistency path against a deliberately off-topic response so the deployer sees the heuristic at work before shipping.

## Reversibility

Reversible. The three-arm decision order is the contract. A future ADR could supersede this one by, for example, collapsing the fabrication-pattern arm into the RAG arm when an embedding-based RAG check is mandatory rather than optional, or by widening the action-class taxonomy to cover account-level operations the v1.3 set does not name. The pattern's audit-chain emission contract (`AuditEventType.COMPLIANCE_CHECK` with payload schema named above) is the load-bearing piece; replacing the arms while preserving the emission contract is a non-breaking change.

## Cross-references

- ADR-0002 (Sovereign Veto) — the kill switch when the chatbot itself must be stopped; the guardrail is the per-response gate, the veto is the per-system halt.
- ADR-0003 (Hash-chained Audit Ledger) — the substrate this guardrail's audit-chain entries land on.
- ADR-0009 (FCRA / Regulation V Adverse Action) — upstream pairing for the `REGULATORY_DISCLOSURE` action class.
- ADR-0013 (SEC Reg-BI Best Interest Check) — adjacent customer-facing surface for securities recommendations; the recommendation gate and the chatbot guardrail are parallel intercepts on the same trust boundary.
- ADR-0017 (Audit-Chain Retention, Privilege & Discovery) — retention schedule and privilege-classification framework for the audit entries this guardrail produces.

---

*Patterns are software, not legal advice. Regulatory citations are reference mappings; consult counsel for applicability to your control environment.*
