"""Allow-list for ``tests/test_doc_staleness.py``.

The staleness test walks every public-doc surface and flags any
co-occurrence of an exported ``__all__`` name with a deferral marker
(``stub`` · ``deferred`` · ``forthcoming`` · ``TBD`` · ``v0.X candidate``
· ``coming soon`` · ``future work`` · ``not yet shipped`` ·
``NOT YET IMPLEMENTED`` · ``design only``) inside the 400-character
proximity window.

A handful of co-occurrences are legitimate historical meta-prose: the
SHIP-RECEIPT classification key, ROADMAP's released-version checklists,
CHANGELOG references that document prior deferrals now closed, etc.
This file lists the legitimate cases as ``(exported_name, file_relative,
marker)`` tuples. An entry suppresses one specific co-occurrence —
nothing wildcard.

When a deferral closes (e.g. v1.2 ships
``ProtectedClassProxyDetector``), the test author SHOULD remove the
corresponding entries here rather than leave them lurking; the test's
failure on real drift is the value, and a stale allow-list erodes it.
"""

from __future__ import annotations

from typing import Final

# Each entry: (exported_name, repo-relative path with forward slashes, marker substring).
# The marker substring is the literal text the test detects in the proximity window.
ALLOW_LIST: Final[frozenset[tuple[str, str, str]]] = frozenset(
    {
        # --- SHIP-RECEIPT classification-key meta-prose ----------------------
        # The receipt itself defines what "stub-with-tracking" means; the
        # name appears as the exemplar in the key row. After the v1.2
        # ship the row description still cites "stub" to record the
        # historical posture.
        ("ProtectedClassProxyDetector", "SHIP-RECEIPT.md", "stub"),
        ("ProtectedClassProxyDetector", "SHIP-RECEIPT.md", "deferred"),
        # MonitorAgent + OrchestratorAgent ship as classes whose method
        # bodies are reference stubs — this is a deliberate, documented
        # ship posture (not a deferral). The receipt names them so
        # adopters know to subclass.
        ("MonitorAgent", "SHIP-RECEIPT.md", "stub"),
        ("OrchestratorAgent", "SHIP-RECEIPT.md", "stub"),
        ("OrchestratorAgent", "SHIP-RECEIPT.md", "deferred"),
        # The RFC 3161 codec is shipped; the verify-side cross-check
        # against the TSA cert chain is the only NOT-YET-IMPLEMENTED
        # piece, tracked under ADR-0014-A1. The receipt names this
        # explicitly in the row's "Notes" cell.
        ("parse_timestamp_response", "SHIP-RECEIPT.md", "NOT YET IMPLEMENTED"),
        # --- VERSIONING.md historical reconciliation line --------------------
        # The v1.1 versioning record names the stub posture as historical
        # fact; the v1.2 reconciliation is appended to the same line.
        ("ProtectedClassProxyDetector", "VERSIONING.md", "stub"),
        # --- CHANGELOG.md — the v1.1 ADR list cites the ADR's title:
        # "Protected-Class Proxy Detector — Deferred-Implementation".
        # That historical title is a real ADR file and is correctly
        # cited here; the word "Deferred" sits in the title, not in a
        # status assertion against the listed names.
        ("Agent", "CHANGELOG.md", "Deferred"),
        ("DEFCON", "CHANGELOG.md", "Deferred"),
        ("Model", "CHANGELOG.md", "Deferred"),
        # --- NEGATIVE-USE-CASES.md — the "deferred" word in the v1.2
        # rewrite refers to the SHAP/CDD arms still on the v1.3
        # roadmap, which the prose explicitly notes. The MI arm IS
        # shipped; the proximity test fires anyway because "v1.3"
        # appears within window.
        ("ProtectedClassProxyDetector", "NEGATIVE-USE-CASES.md", "deferred"),
        # --- ASSURANCE-GUIDE.md — the v1.2 rewrite explicitly cites
        # "not yet shipped" arms for the compensating-control question.
        # This is the correct posture, not stale documentation.
        ("ProtectedClassProxyDetector", "ASSURANCE-GUIDE.md", "not yet shipped"),
        # --- FAILURE-MODES.md — the matrix table has rows that
        # legitimately combine an `(F)` callable in one cell with a
        # NOT-YET-IMPLEMENTED marker in an adjacent cell for the SAME
        # row. The names below are real callables; the marker covers
        # a different, named-and-tracked sub-amendment (ADR-0014-A1
        # / A2) on the same row.
        ("AuditChain", "FAILURE-MODES.md", "NOT YET IMPLEMENTED"),
        ("TimestampSource", "FAILURE-MODES.md", "NOT YET IMPLEMENTED"),
        ("anchor_to_witness", "FAILURE-MODES.md", "NOT YET IMPLEMENTED"),
        # --- docs/iso_42001_mapping.md — the mapping row at A.6.2.7
        # names "Explainability Stub" (a v1.2-planned feature) on the
        # same line as `AuditEvent`. The prose talks about the future
        # feature; the name `AuditEvent` is shipped.
        ("AuditEvent", "docs/iso_42001_mapping.md", "stub"),
        # --- ARCHITECTURE.md — bullet listing "ADR-0019 —
        # ProtectedClassProxyDetector deferred" is the historical ADR
        # title. The ADR is real; the deferral was real; v1.2 closed
        # it (recorded in the ADR's "v1.2 ship reconciliation"
        # section). Title preserved for historical traceability.
        ("ProtectedClassProxyDetector", "ARCHITECTURE.md", "deferred"),
        # --- CHANGELOG.md — the v1.2 release notes legitimately
        # describe what changed by referencing the v1.1 "stub" that
        # the v1.2 implementation replaces.
        ("ProtectedClassProxyDetector", "CHANGELOG.md", "stub"),
        # --- docs/caio_first_90_days_playbook.md — the v1.2 rewrite
        # explicitly cites "not yet shipped" arms (SHAP, CDD) that
        # remain on the v1.3 roadmap; this is current posture, not
        # stale documentation.
        ("ProtectedClassProxyDetector", "docs/caio_first_90_days_playbook.md", "not yet shipped"),
        # --- v1.3 deferred-arm reconciliations -------------------------------
        # `LDASearchHarness` IS shipped in v1.3. Both CHANGELOG.md and
        # ROADMAP.md cite the "deferred" word in proximity to the name
        # because the prose names the continuous-feature quantile-binning
        # helper as still on the v1.4 roadmap. The proximity test fires
        # on the legitimate v1.4-deferral mention.
        ("LDASearchHarness", "CHANGELOG.md", "deferred"),
        ("LDASearchHarness", "ROADMAP.md", "deferred"),
        # `ProtectedClassProxyDetector` MI arm shipped in v1.2; LDA arm
        # shipped via `LDASearchHarness` in v1.3; the v1.3 CHANGELOG and
        # ROADMAP both cite the v1.4 "deferred" SHAP / CDD arms in
        # proximity to the name. This is current posture, not stale.
        ("ProtectedClassProxyDetector", "CHANGELOG.md", "deferred"),
        ("ProtectedClassProxyDetector", "ROADMAP.md", "deferred"),
    }
)
