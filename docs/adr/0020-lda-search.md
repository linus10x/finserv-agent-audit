# ADR-0020 · LDA Search — Less Discriminatory Alternative Harness

**Status:** Accepted · v1.3 · ships with v1.3.0
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit v1.3

> **Reference pattern, not legal advice.** Fair-lending characterizations are summaries; readers must consult qualified counsel and qualified fair-lending statisticians. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

## Context

The Equal Credit Opportunity Act (ECOA, 15 U.S.C. § 1691) and Regulation B (12 C.F.R. Part 1002) prohibit credit discrimination on prohibited bases. The disparate-impact doctrine — reaffirmed in *Texas Department of Housing and Community Affairs v. Inclusive Communities Project, Inc.*, 576 U.S. 519 (2015) — reaches facially neutral models that produce disparate outcomes. The lender's defense under the doctrine is a two-step burden-shift: the lender must show a substantial legitimate business need served by the challenged practice, and the plaintiff (or the regulator) may rebut by showing a less discriminatory alternative (LDA) serves the same need.

The LDA prong is the operational gap regulated lenders have historically left to ad-hoc post-hoc analysis. The ACM-FAccT 2024 paper "Operationalizing the Search for Less Discriminatory Alternatives in Fair Lending" (Black, Gillis, Hall, Schrag, Singh, Yadav) names a tractable methodology: define a search space of candidate models, score each candidate's accuracy and disparate-impact ratio against the primary, and flag any candidate that dominates the primary on both criteria simultaneously (equal-or-better accuracy AND strictly better DI). A dominating candidate is the LDA the lender is on notice of and must consider before continuing to deploy the primary.

Three regulatory artifacts move LDA search from research methodology to regulator-expected diligence in 2026:

- **CFPB Circular 2023-09** [UNVERIFIED — confirm citation language against primary source] articulated that the CFPB considers the search for LDAs a relevant inquiry when supervising lenders using complex models, including AI underwriting models.
- **CFPB final rule (May 2026)** [UNVERIFIED — verify exact rule citation and publication date] formalized the expectation that lenders deploying AI underwriting models demonstrate they searched for less discriminatory alternatives, not merely that the primary passes a disparate-impact threshold.
- **Massachusetts AG settlement, July 10, 2025** [UNVERIFIED — confirm exact docket and settlement filing date] resolved the first state-AG fair-lending action against an AI underwriting model. Federal CFPB enforcement has scaled back; state AGs and private class actions now drive the floor of expected diligence. The Massachusetts AG fact pattern is the template plaintiff counsel will replicate.

The 2026-05-28 council debate (BigLaw chamber, Plaintiff's chamber, MRM chamber) named LDA search as the discrimination-frontier control that is most likely to be cited in the next state-AG action and most likely to be missing from the bank's existing MRM playbook. v1.3 ships the LDA search harness as the framework-level answer.

## Decision

Ship `LDASearchHarness` in `src/finserv_agent_audit/governance/lda_search.py`. The harness takes a primary scoring model and a generator of LDA candidates; per candidate it computes accuracy_delta vs primary, DI ratio delta vs primary, and a dominance verdict; emits one `AuditEventType.COMPLIANCE_CHECK` chain entry per `search` call carrying the methodology + per-candidate report for forensic replay.

### Dominance criterion

A candidate dominates the primary iff:
- `accuracy_delta >= 0` (the candidate is at least as accurate)
- AND `di_ratio_delta > 0` (the candidate has a strictly larger 4/5ths-rule selection-rate ratio — i.e., is strictly less discriminatory)

This is the FAccT-2024 weak-dominance criterion. ADR-0020 explicitly does not encode the FAccT-2024 significance tests on the accuracy delta; institutions applying this harness for regulatory diligence should pair it with the significance-test arm in their MRM playbook, per the operator-side calibration discipline of ADR-0010.

### Candidate generation is the caller's responsibility

The framework does not enumerate the FAccT-2024 search-space construction (model-class sweeps, feature-subset sweeps, regularization sweeps). Those are operator-specific and depend on the lender's model-development toolchain. The harness's contract is to score and report what the caller supplies; the candidate-generation discipline lives in the MRM playbook.

### Chain emission

Every `search` call emits one `AuditEventType.COMPLIANCE_CHECK` entry. Payload: `regulation = "ECOA/RegB"`, `adr_reference = "ADR-0020"`, `methodology = "lda_search_v1"`, `n_samples`, `primary_accuracy`, `primary_di_ratio`, per-candidate `[{name, accuracy_delta, di_ratio_delta, dominates_primary}]`. The regulator-side question "Did you search for an LDA?" now has an answer with a hash-chained receipt.

## Alternatives Considered

- **Defer LDA search to v1.4 or beyond.** Rejected: the state-AG enforcement floor is rising now; deferring leaves adopters exposed during the v1.3 deployment window.
- **Wrap a vendor LDA library.** Rejected: vendor LDA tools embed search-space and dominance choices that may not match the FAccT-2024 methodology; the framework's contract is auditability of the dominance criterion, not opacity behind a vendor SDK.
- **Ship a full FAccT-2024 search-space generator alongside the harness.** Rejected: search-space construction is operator-specific (model class, feature engineering toolchain, regularization policy). A built-in generator would either be too narrow to be useful or too broad to be auditable. The MRM function curates the search space; the framework scores it.
- **Encode the FAccT-2024 statistical-significance tests in the dominance verdict.** Rejected for v1.3: the significance-test family (paired bootstrap, McNemar's test, sample-size correction) is its own design discussion. v1.3 ships the weak-dominance verdict; significance testing is the operator's MRM-playbook addition. Reversible — v1.4 may ship a `significance_test` constructor knob.

## Consequences

**Positive.** Adopters get a framework-level answer to the LDA-search regulatory question with a hash-chained receipt per `search` call. The receipt is forensic-replayable under ADR-0003; a regulator-facing investigation can reconstruct the methodology, the search-space breadth, and the dominance verdicts per candidate.

**Negative.** A weak-dominance verdict without significance testing can over-flag candidates that beat the primary on tiny samples. Mitigation: callers pair the harness with significance testing in their MRM playbook; the harness records `n_samples` so a downstream review can apply the operator's sample-size policy.

**Architectural.** The harness consumes the same `AuditChain` Protocol the rest of the v1.1+ governance modules use. No new persistence seams; no new runtime dependencies. Stdlib-only.

## Regulatory Mapping

- **ECOA, 15 U.S.C. § 1691** — prohibition on discrimination in any aspect of a credit transaction
- **Regulation B, 12 C.F.R. § 1002** — § 1002.4(a) general rule against discrimination
- ***Texas Department of Housing and Community Affairs v. Inclusive Communities Project, Inc.*, 576 U.S. 519 (2015)** — disparate-impact doctrine; LDA prong of the burden-shift
- **CFPB Circular 2023-09** — LDA search as relevant inquiry [UNVERIFIED — citation language not confirmed against primary source]
- **CFPB final rule (May 2026)** — formal expectation that lenders demonstrate LDA search for AI underwriting [UNVERIFIED — verify exact rule citation and publication date]
- **Massachusetts AG settlement, July 10, 2025** — first state-AG fair-lending action against an AI underwriting model [UNVERIFIED — confirm exact docket]
- **SR 11-7 (Federal Reserve, 2011) / OCC 2011-12** — model risk management; LDA search is a validation-time expectation under "effective challenge"
- **ACM-FAccT 2024 paper** — Black, Gillis, Hall, Schrag, Singh, Yadav, "Operationalizing the Search for Less Discriminatory Alternatives in Fair Lending"

## Pre-mortem

The way this harness fails is **search-space malpractice**: an adopter supplies a search space narrow enough that no candidate could plausibly dominate the primary, runs the harness, gets a clean "no LDA found" record, and treats the chain entry as a regulator-facing shield. Mitigation: ADR-0020 names this in the docstring; the MRM playbook is where the search-space breadth discipline lives. The harness records the candidate count + per-candidate names in the chain payload so a regulator-facing reviewer can inspect the breadth of the search.

The other failure mode is **weak-dominance over-flagging**: a tiny-sample candidate beats the primary on noise alone, the harness marks it dominating, and the MRM function spends review cycles on a false positive. Mitigation: the harness records `n_samples`; the operator-side MRM playbook applies the institution's sample-size + significance discipline.

## Reversibility

Reversible. The harness is a wrapper over caller-supplied callables; removing it from the governance package surface is a one-line `__all__` edit. The dominance criterion is encoded in `LDASearchHarness._recommend`-equivalent logic (inlined in `search`); a v1.4 may add a constructor `dominance_policy` knob without breaking the v1.3 contract.

## Cross-references

- ADR-0003 (Hash-chain Audit) — LDA-search receipts land on the chain
- ADR-0010 (ECOA / Reg B EquityAudit) — LDA-search results feed the disparate-impact-monitor cohort review
- ADR-0019 (ProtectedClassProxyDetector) — MI-arm detector flags proxy features; LDA search proposes the model-level remediation
- ADR-0021 (LLM Disparate Impact Harness) — the LLM-output analog of LDA search
- ADR-0022 (Effective Challenge Harness) — the broader SR 11-7 effective-challenge frame

## Implementation status

**Shipped in v1.3.** Module: `src/finserv_agent_audit/governance/lda_search.py`. Tests: `tests/test_lda_search.py`. Exports: `LDASearchHarness`, `LDACandidateReport`, `LDASearchResult`.
