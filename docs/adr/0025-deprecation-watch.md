# ADR-0025 · Deprecation Watch — Foundation-Model Sunset Early-Warning Harness

**Status:** Accepted — Design + Reference Implementation (v1.3)
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit v1.3

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel. No attorney-client relationship is formed by use of this ADR. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

---

## Context

The foundation-model deprecation record across 2025 and into 2026 makes the operational risk concrete:

- **July 28, 2025** — OpenAI deprecated `o1-preview` with a short transition window.
- **November 11, 2025** — Google Cloud Vertex AI announced deprecation of Anthropic Claude 3.7 Sonnet on the Vertex surface; shutdown scheduled for May 11, 2026.
- **January 2026** — Novita issued a 14-day deprecation notice on a hosted model surface, the shortest cycle observed in the year and the floor banks must guard against.

A US-regulated financial institution running Reg-BI-relevant flows, BSA/AML transaction-monitoring augmentation, or FCRA-touched adverse-action narrative generation on these endpoints cannot survive a 14-day deprecation cycle. The SR 11-7 / OCC Bulletin 2026-13 change-management posture, the FFIEC IT Examination Handbook expectations on third-party model lifecycle, and DORA Article 28 exit-strategy obligations all assume the institution receives a deprecation signal early enough to qualify a replacement, validate the cutover, and run a parallel-run window. Fourteen days is not enough for any of those.

The signal exists — every named vendor publishes a changelog or deprecation page. The bank's gap is **systematic polling and chain-of-custody alerting** against those changelogs. Operations teams cannot reliably read every vendor's changelog every day; the institution needs a primitive that polls, parses, and emits an audit-chain alert with enough lead time to act.

## Decision

Define a `DeprecationWatch` polling harness that registers each foundation-model vendor against its changelog URL and a vendor-specific `ChangelogParser` callable. On `check()`, the harness fetches each registered changelog, parses it into `DeprecationAnnouncement` records, computes `days_until_sunset` for each, and emits a `DEPRECATION_ALERT` audit-chain event for any sunset inside the configured `alert_window_days` (default 60).

### Module surface

```python
from finserv_agent_audit.governance.deprecation_watch import (
    DeprecationWatch,
    DeprecationAnnouncement,
    ChangelogParser,
)

watch = DeprecationWatch(ledger_store=worm_store)
watch.register_vendor(
    vendor_id="openai",
    changelog_url="https://platform.openai.com/docs/deprecations",
    parser=openai_changelog_parser,
)
watch.register_vendor(
    vendor_id="anthropic",
    changelog_url="https://docs.anthropic.com/en/docs/about-claude/model-deprecations",
    parser=anthropic_changelog_parser,
)
alerts = watch.check(alert_window_days=60)
```

The harness ships no default parsers because every vendor's changelog format differs (HTML, JSON, RSS, markdown). Operators wire vendor-specific parsers as `ChangelogParser` callables; the parser Protocol is two methods (`__call__(payload: str) -> list[DeprecationAnnouncement]`).

### New audit-event type

`AuditEventType.DEPRECATION_ALERT` (`"vendor.deprecation_alert"`) is added to `schemas/audit_event.py` to carry the alert payload. Additive change; no existing events are renamed.

### Failure semantics

- **HTTP failure on one vendor's changelog** — swallowed for that vendor only. The next `check()` cron tick retries. Other registered vendors continue to be polled.
- **Parser raises on malformed payload** — swallowed for that vendor only. The bank's TPRM team learns about the parser failure through the missing-alert signal (no chain entry where one is expected) plus the vendor-side operational alerting the bank's substrate provides.
- **No `LedgerStore` configured** — `check()` still returns the alert list. Chain emission becomes silent. The configuration is the operator's call.

The HTTP-and-parser swallow posture is the deliberate one: a bad vendor must not block awareness of a good vendor's sunset.

## Alternatives Considered

1. **Stand up a third-party deprecation-tracker service.** Rejected — no existing service covers every foundation-model vendor with the cadence and parser fidelity the bank needs, and the third-party service adds another fourth-party-disclosure obligation under DORA RTS 2024/1773. The primitive is small enough to ship.
2. **Use a single regex against every vendor's page.** Rejected — vendor changelog formats vary too much for a single regex; a parser-per-vendor approach is the right factoring and is what every operator builds anyway. The Protocol seam is the value.
3. **Subscribe to vendor email lists and rely on inbox triage.** Rejected — email triage is not a control. The harness is the control; email is the human courtesy.
4. **Fail loud on HTTP / parser errors instead of swallowing.** Rejected — a single broken vendor would block the operator from learning about every other vendor's sunset. The swallow-per-vendor posture is the safer default.

## Consequences

**Positive.** The bank gains an early-warning signal with configurable lead time and audit-chain evidence that the warning fired. Pairs cleanly with `VendorAttestationLedger` (ADR-0023) — a deprecation alert is a vendor-side material change that may invalidate an attestation — and with `RetrainingCadenceMonitor` (ADR-0024) — a sunset forces a class re-evaluation for the replacement model.

**Negative.** The harness depends on the quality of the parser the operator wires. A parser that misses a sunset announcement gives the bank false confidence. The mitigation is testing-side: every parser ships with a synthesized-changelog test against the vendor's known historical deprecation announcements; CI catches parser drift when the vendor changes the page structure.

**Architectural.** The harness is stdlib-only. The default `http_get` is `urllib.request.urlopen` so the base wheel stays dependency-free; operators who want async polling, retry budgets, or HTTP/2 wire those via the `http_get` injection seam without touching the harness.

## Regulatory Mapping

- **SR 11-7** (Federal Reserve, April 4, 2011) § V.4 (Model Implementation, Use, and Change) — vendor-side change events are material changes the bank's MRM must process.
- **OCC Bulletin 2026-13** (April 17, 2026) — model risk revised guidance; the deprecation signal is a vendor-side change-management event.
- **FFIEC IT Examination Handbook** § "Third-Party Model Risk" — examination expectations for vendor lifecycle monitoring.
- **DORA Article 28** (Regulation (EU) 2022/2554) — ICT third-party risk management; exit-strategy + contractual-transition requirements depend on early signal.
- **DORA RTS on subcontracting** (Commission Delegated Regulation 2024/1773) — fourth-party-disclosure cadence; a fourth-party deprecation is a third-party material change.
- **OCC Bulletin 2013-29** — original third-party risk management; superseded for AI workloads by the 2026 interagency RFI process, but vendor-lifecycle monitoring expectations carry forward.
- **Historical precedents:** OpenAI o1-preview deprecation (July 28, 2025) · Google Cloud Claude 3.7 Sonnet deprecation (November 11, 2025; shutdown May 11, 2026) · Novita January 2026 14-day deprecation notice.

## Pre-mortem

What fails:

1. **Vendor publishes a deprecation in an undocumented format the parser misses.** Mitigation: the bank's procurement clause (foundation-model API, Clause 5.iii) sets a 180-day notice minimum as the contractual floor. The harness is the technical safety-net; the contract is the legal one.
2. **Network outage during `check()`.** Mitigation: HTTP failures are swallowed per-vendor; the next cron tick retries. Deployer instruments the cron job's heartbeat in their alerting substrate.
3. **Two vendors announce simultaneous sunsets that compete for the same replacement.** Mitigation: the harness surfaces both alerts; the bank's TPRM + MRM functions decide on prioritization. The framework's job is awareness, not arbitration.
4. **Parser raises and the failure goes unnoticed.** Mitigation: parser-side test discipline (every parser ships with a synthesized-changelog test) plus operator-side observation that `check()` returned zero alerts on a vendor known to have a sunset. The chain entries on healthy vendors give the bank the comparative signal.
5. **Alert window is set too short.** Mitigation: `alert_window_days` defaults to 60; the bank's procurement clause sets the contractual floor at 180. Shortening the window to less than the notice period the bank can act on is a configuration error the second line catches at review.

## Reversibility

High. Removing the harness reverts the bank to vendor-email triage. The chain entries already written stand on their own as evidence the harness fired. Replacing the harness with a third-party service is straightforward — the chain emission can be wired from any source that produces `DEPRECATION_ALERT` events.

## Cross-references

- **Implementation:** `src/finserv_agent_audit/governance/deprecation_watch.py`
- **Tests:** `tests/test_deprecation_watch.py`
- **Audit event type:** `AuditEventType.DEPRECATION_ALERT` added to `src/finserv_agent_audit/schemas/audit_event.py` in v1.3.
- **Companion artifact:** `vendor-clauses/foundation_model_api_vendor_clauses.md` (v1.3 — Clause 5.iii covers the contractual 180-day notice floor).
- **Related ADRs:** ADR-0007 (SR 11-7 overlay — the second-line + third-line evidence framing) · ADR-0014 (Persistence + timestamp + witness seams — the chain substrate) · ADR-0016 (Vendor Score Gate — the runtime adapter; this ADR is the lifecycle adapter) · ADR-0023 (Vendor Attestation Ledger — attestations age out on deprecation events) · ADR-0024 (Retraining Cadence Monitor — class re-evaluation on sunset)
