# RESEARCH.md — Pattern-to-academic-source map

**Status:** v1.1.0 · Last reviewed: 2026-05-28.

Each pattern in this framework has academic and regulatory antecedents. This document is the explicit mapping. The intent is two-fold: to credit the prior art the framework stands on, and to give reviewers (AI-governance researchers, second-line model-risk teams, accreditation reviewers) a reading list for the design choices.

> Companion to the per-pattern ADRs in `docs/adr/`.

---

## Sovereign Veto / kill switch (ADR-0002)

- **Stuart Russell, *Human Compatible: Artificial Intelligence and the Problem of Control*** (Viking, 2019) — Russell's framing of provably-beneficial AI rests on the principle that the human's preferences are unknown to the agent and the agent must defer to a human's interruption signal. Sovereign Veto is the operational form of that principle: a human-only clearance, recorded, with reason, that no agent can self-clear.
- **Nick Bostrom, *Superintelligence: Paths, Dangers, Strategies*** (Oxford University Press, 2014) — Chapter 9 on capability-control methods enumerates kill-switch design under instrumental-convergence pressure. The framework's "no agent can clear its own veto" invariant is the practical answer to the corrigibility problem.
- **MiFID II algorithmic-trading requirements (Directive 2014/65/EU, Article 17; Commission Delegated Regulation 2017/589 RTS 6)** — the EU regime for algorithmic trading firms requires a "kill functionality" (RTS 6 Art. 12) that cancels orders and disables algorithms. Sovereign Veto generalizes the same control surface to non-trading agents.
- **Hadfield-Menell et al., "The Off-Switch Game"** (IJCAI, 2017) — game-theoretic treatment of when a rational agent will permit interruption.

## Hash-chain audit (ADR-0003)

- **Stuart Haber and W. Scott Stornetta, "How to Time-Stamp a Digital Document"** (*Journal of Cryptology*, 1991) — the foundational paper on linked timestamping. The original chain-of-hashes construction is the direct antecedent of the framework's `AuditChain`.
- **Dave Bayer, Stuart Haber, and W. Scott Stornetta, "Improving the Efficiency and Reliability of Digital Time-Stamping"** (*Sequences II: Methods in Communication, Security, and Computer Science*, 1993) — the tree-and-chain construction extending the 1991 paper. The witness-anchoring design (ADR-0014 Seam 3) follows the same publish-the-head pattern.
- **Ralph C. Merkle, "Secrecy, Authentication, and Public Key Systems"** (Stanford PhD thesis, 1979) — the Merkle tree construction underlying both Sigstore Rekor and OpenTimestamps witness backends.
- **SEC Rule 17a-4 (17 CFR 240.17a-4)** — the books-and-records rule for broker-dealers. The 1997 amendment introduced WORM media; subsequent amendments (most recently the 2022 amendment 17 CFR 240.17a-4(f)) define the audit-trail integrity expectation the framework's persistence layer maps to.

## Autonomy Ladder A0 → A4 (ADR-0004)

- **SAE J3016 *Taxonomy and Definitions for Terms Related to Driving Automation Systems for On-Road Motor Vehicles*** (Society of Automotive Engineers, revised 2021) — the J3016 Levels 0–5 framework is the closest analog for tiered-autonomy classification with explicit human-control fall-back at each level. The Autonomy Ladder applies the same shape to agentic AI in regulated contexts.
- **Stuart Russell, *Human Compatible*** (2019) — Russell's framing of A2 ("off switch") and the structural argument for why higher-autonomy tiers require correspondingly stronger control surfaces directly informs the A2 → A3 promotion gate.
- **NIST AI Risk Management Framework 1.0 (NIST AI 100-1, January 2023)** — the GOVERN / MAP / MEASURE / MANAGE functions provide the institutional context the ladder operationalizes.

## DEFCON state machine (ADR-0001)

- **U.S. military Defense Readiness Conditions (declassified history)** — the DEFCON 1–5 escalation framework, declassified portions of the operational doctrine. The framework adopts the five-level shape and the asymmetric-transition discipline (escalation is fast; de-escalation is slow and requires confirmation).
- **NYSE Rule 80B (market-wide circuit breakers)** — the three-level (7% / 13% / 20%) circuit breaker regime under SEC-approved exchange rules. The hysteresis discipline — once tripped, the market does not re-open on a 30-second rebound — is the direct analog to the framework's `HYSTERESIS_CONFIRMATIONS` requirement on DEFCON de-escalation.
- **Charles Perrow, *Normal Accidents: Living with High-Risk Technologies*** (Princeton University Press, revised 1999) — the tight-coupling / interactive-complexity analysis that motivates state-machine-based throttling under risk.

## Fair-lending proxy detection (ADR-0010, ADR-0019)

- **Solon Barocas and Andrew D. Selbst, "Big Data's Disparate Impact"** (*California Law Review*, 2016) — the foundational law-review treatment of how facially-neutral data can produce ECOA / Title VII-relevant disparate impact through proxy variables. The deferral reasoning in ADR-0019 (a bad proxy detector is more dangerous than an absent one) traces to this paper's argument that the proxy problem is not solvable by post-hoc auditing alone.
- **Sorelle A. Friedler, Carlos Scheidegger, and Suresh Venkatasubramanian, "On the (im)possibility of fairness"** (arXiv:1609.07236, 2016) — the impossibility argument linking observational fairness criteria. Informs the EquityAudit design choice to surface metrics rather than declare a fairness verdict.
- **Moritz Hardt, Eric Price, and Nathan Srebro, "Equality of Opportunity in Supervised Learning"** (NeurIPS, 2016) — the equal-opportunity criterion; the framework's `EquityAudit` records the inputs needed for this analysis without performing it.
- **CFPB Circular 2022-03** — Consumer Financial Protection Bureau guidance on adverse-action notices when a creditor uses "complex algorithms." The framework's `AdverseActionGate` operationalizes the "specific and accurate" requirement (FCRA § 615 + Reg-B § 1002.9).
- **DOJ + 8 state AGs, *United States v. RealPage Inc.*** (D. Md., filed August 23, 2024) — Sherman § 1 antitrust complaint, a contemporaneous regulatory-of-record marker for how algorithmic systems are now litigated even outside the credit context.

## Witness anchoring (ADR-0014 Seam 3)

- **Linux Foundation Sigstore project** — `rekor.sigstore.dev` is the public-good transparency log the framework's `RekorWitness` posts to. The Sigstore SLSA (Supply-chain Levels for Software Artifacts) framework provides the substrate model for attestation as separate from execution.
- **Peter Todd, "OpenTimestamps: A Standard for Distributed Trust Timestamps"** (OpenTimestamps protocol specification, 2016) — the calendar-server-plus-Bitcoin-anchor design the framework's `OpenTimestampsWitness` interoperates with.
- **Ben Laurie, Adam Langley, and Emilia Käsper, "Certificate Transparency"** (RFC 6962, 2013) — the Merkle-log-with-public-auditing pattern that underlies both Rekor and the broader CT ecosystem.
- **Internet Engineering Task Force, "Internet X.509 Public Key Infrastructure Time-Stamp Protocol (TSP)"** (RFC 3161, 2001) — the trusted-timestamp authority protocol the framework's `RFC3161Source` and `rfc3161_codec` module implement.

## SR 11-7 three-lines-of-defense (ADR-0007)

- **Board of Governors of the Federal Reserve System, "Supervisory Guidance on Model Risk Management" (SR 11-7)** (April 4, 2011, jointly issued with OCC Bulletin 2011-12) — the foundational U.S. model-risk-management guidance. The framework's `ModelInventory` status state machine (`PRE_VALIDATION` → `IN_VALIDATION` → `APPROVED_FOR_PRODUCTION` → `RETIRED`) is the operational form of the SR 11-7 § V model-validation lifecycle.
- **Institute of Internal Auditors, *The IIA's Three Lines Model: An update of the Three Lines of Defense*** (July 2020 revision) — the contemporary articulation of the three-lines model the framework's gates (first-line decision, second-line validation surfaced via `ModelInventory.query_overdue()`, third-line independent assurance via the audit chain) operationalize.
- **OCC Bulletin 2011-12** — the OCC's parallel issuance of the model-risk guidance; the framework's `docs/occ_2011_12_mapping.md` references it directly.
- **OCC, Federal Reserve, and FDIC, *Sound Practices to Strengthen the Resilience of the U.S. Financial System (FRB SR 11-7 supplement on third-party model risk, 2017 update)*** — extends the third-party model-risk discipline that `VendorScoreGate` (ADR-0016) and the Vendor Score Drift signal address.

## Vendor-mediated AI scoring drift (ADR-0016)

- **Federal Reserve, OCC, FDIC, CFPB, NCUA, *Interagency Guidance on Third-Party Relationships: Risk Management*** (June 6, 2023, 88 Fed. Reg. 37920) — the contemporary U.S. interagency guidance on third-party relationships, including third-party AI / models. The framework's `VendorScoreGate` records the emission diff signal the third-party guidance presumes the institution can produce.
- **ISO/IEC 42001:2023, *Artificial intelligence — Management system*** — § 8 operational controls including third-party AI components; the framework's `docs/iso_42001_mapping.md` references it.

## NIST AI RMF and EU AI Act crosswalks

- **NIST AI Risk Management Framework 1.0 (NIST AI 100-1, January 2023)** and **NIST AI RMF Generative AI Profile (NIST AI 600-1, July 2024)** — referenced in `docs/nist_ai_rmf_mapping.md`.
- **Regulation (EU) 2024/1689 of the European Parliament and of the Council laying down harmonised rules on artificial intelligence (Artificial Intelligence Act)** — referenced in `docs/eu_ai_act_mapping.md`; Annex IV § 1(g) (third-party component records) maps to `VendorScoreGate`; Articles 9–15 high-risk-system controls map to the framework's primitives broadly.

---

## How to use this document

Reviewers preparing an internal model-risk review, an external accreditation review, or an academic citation should pull both the listed source and the corresponding ADR in `docs/adr/`. The ADR records the design decision; this document records the prior art the decision builds on.

Adopters preparing a regulator-facing artifact (examination response, supervisory letter, internal model risk committee memo) should pair this document with [`ASSURANCE-GUIDE.md`](ASSURANCE-GUIDE.md), which walks the audit-evidence trail from the same primitives.

## Related

- All ADRs in `docs/adr/`
- All mapping documents in `docs/`
- [`ASSURANCE-GUIDE.md`](ASSURANCE-GUIDE.md)
