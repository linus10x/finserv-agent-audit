"""BSA / AML SARWorkflowAudit — ADR-0011.

Every agent contribution to a SAR-workflow decision (alert disposition,
file / no-file recommendation, narrative auto-population, flagged-entity
scoring, 30-to-60-day extension) routes through this module before the
decision is recorded. The module emits one
`AuditEventType.SAR_FILED` chain entry per evaluated decision; the chain
is the program's evidentiary backbone for AI-influenced SAR activity.

The audit is emit-mandatory. If the wired ledger store cannot accept the
entry, `SARAuditError` fires with `BSA-AUDIT-WRITE-FAILED` so the calling
agent must block the underlying decision (the sovereign-veto pattern,
ADR-0002). Five additional vetoes fire on missing or generic inputs:
`BSA-VALIDATION-MISSING`, `BSA-RATIONALE-VAGUE`,
`BSA-NARRATIVE-UNHASHED`, `BSA-EXTENSION-UNJUSTIFIED`, and
`BSA-DETECTION-ANCHOR-MISSING`.

The 31 U.S.C. § 5318(g)(2) safe-harbor metadata field travels with every
filed entry; the chain documents that the filing was made in good faith,
which is the predicate for the statutory civil-liability protection.

Regulatory anchors:
    - BSA, 31 U.S.C. § 5318(g) and § 5318(h)
    - SAR rule, 31 C.F.R. § 1020.320 (banks) plus parallel rules
      § 1023.320, § 1024.320, § 1025.320, § 1026.320
    - FFIEC BSA/AML Examination Manual
    - 31 U.S.C. § 5318(g)(2) safe harbor
    - Interagency statement on MRM for BSA/AML compliance (April 9, 2021)
    - Reader-friendly mapping: `docs/bsa_aml_mapping.md`

> Reference pattern, not legal advice. Regulatory characterizations are
> summaries; engage qualified BSA/AML counsel and the firm's BSA Officer
> for compliance determinations. See repo-root `DISCLAIMER.md`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from finserv_agent_audit.governance.ledger_store import LedgerStore
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)

SAFE_HARBOR_CITATION = "31 U.S.C. 5318(g)(2)"

_VAGUE_RATIONALE_FRAGMENTS: tuple[str, ...] = (
    "model decision",
    "score below threshold",
    "no further action warranted",
    "see attached",
    "as discussed",
)

# Extension-decision rationales must name a regulatory predicate. The
# 30-to-60-day extension is permitted when no suspect has been identified;
# the rationale text must articulate that predicate (or an equivalent one
# tied to suspect identification) to satisfy the supervisory expectation.
_EXTENSION_PREDICATE_TOKENS: tuple[str, ...] = (
    "suspect",
    "identification",
    "identify",
    "1020.320(b)(3)",
    "no subject",
)


class SARDecisionSurface(Enum):
    """The five AI-influenced surfaces within the SAR workflow."""

    ALERT_DISPOSITION = "alert_disposition"
    FILE_DECISION = "file_decision"
    NARRATIVE_AUTO_POPULATION = "narrative_auto"
    FLAGGED_ENTITY_SCORE = "flagged_entity_score"
    EXTENSION_DECISION = "extension_decision"


class SARActionTaken(Enum):
    """Discrete actions an AI-influenced decision can record."""

    CLOSE = "close"
    ESCALATE_TO_ANALYST = "escalate_to_analyst"
    OPEN_CASE = "open_case"
    RECOMMEND_FILE = "recommend_file"
    RECOMMEND_NO_FILE = "recommend_no_file"
    AMENDED_FILE = "amended_file"
    NARRATIVE_DRAFTED = "narrative_drafted"
    SCORE_EMITTED = "score_emitted"


@dataclass(frozen=True)
class SARWorkflowEntry:
    """Single AI-influenced SAR-workflow decision payload."""

    entry_id: str
    surface: SARDecisionSurface
    action: SARActionTaken
    case_id: str
    alert_ids: tuple[str, ...]
    suspect_party_ids: tuple[str, ...]
    model_id: str
    model_version: str
    model_validation_id: str
    detection_anchor_timestamp: datetime
    decision_timestamp: datetime
    human_reviewer: str | None
    narrative_hash: str | None
    score_value: float | None
    score_factors: tuple[str, ...]
    rationale: str
    safe_harbor_claimed: bool = False


class SARAuditError(RuntimeError):
    """Raised on any audit-emission failure or precondition violation."""

    def __init__(self, codes: tuple[str, ...], *, cause: Exception | None = None) -> None:
        self.codes = codes
        super().__init__("; ".join(codes))
        if cause is not None:
            self.__cause__ = cause


@dataclass
class SARWorkflowAudit:
    """Audit-emit-mandatory ledger writer for the SAR workflow.

    Construct with the institution's wired `LedgerStore`. Each call to
    `record(entry)` validates the entry against the BSA-AML veto list,
    then writes one `SAR_FILED` event to the chain. A store-side write
    failure surfaces as `BSA-AUDIT-WRITE-FAILED` so the calling agent
    can block the underlying decision under the sovereign veto.
    """

    ledger_store: LedgerStore
    agent_id: str = "system:sar_workflow_audit"
    _vague_fragments: tuple[str, ...] = field(
        default=_VAGUE_RATIONALE_FRAGMENTS, init=False, repr=False
    )

    def record(self, entry: SARWorkflowEntry) -> AuditEvent:
        """Validate `entry` and emit a SAR_FILED chain event.

        Raises `SARAuditError` on precondition violation or store-write
        failure. Returns the appended event on success.
        """
        violations = self._collect_violations(entry)
        if violations:
            raise SARAuditError(violations)

        prev_hash = self.ledger_store.head_event_hash()
        event = AuditEvent(
            event_type=AuditEventType.SAR_FILED,
            autonomy_level=AutonomyLevel.A2,
            agent_id=self.agent_id,
            payload=self._build_payload(entry),
            prev_hash=prev_hash,
            actor_id=entry.human_reviewer,
        )
        try:
            self.ledger_store.append(event)
        except Exception as exc:
            raise SARAuditError(("BSA-AUDIT-WRITE-FAILED",), cause=exc) from exc
        return event

    # ------------------------------------------------------------------ #
    # Internals                                                          #
    # ------------------------------------------------------------------ #

    def _collect_violations(self, entry: SARWorkflowEntry) -> tuple[str, ...]:
        violations: list[str] = []

        if entry.detection_anchor_timestamp is None:
            violations.append("BSA-DETECTION-ANCHOR-MISSING")

        if not entry.model_validation_id:
            violations.append("BSA-VALIDATION-MISSING")

        if self._is_vague(entry.rationale):
            violations.append("BSA-RATIONALE-VAGUE")

        if (
            entry.surface == SARDecisionSurface.NARRATIVE_AUTO_POPULATION
            and not entry.narrative_hash
        ):
            violations.append("BSA-NARRATIVE-UNHASHED")

        if (
            entry.surface == SARDecisionSurface.EXTENSION_DECISION
            and not self._extension_predicate_named(entry.rationale)
        ):
            violations.append("BSA-EXTENSION-UNJUSTIFIED")

        return tuple(violations)

    def _is_vague(self, rationale: str) -> bool:
        text = rationale.strip().lower()
        if not text:
            return True
        return any(fragment in text for fragment in self._vague_fragments)

    @staticmethod
    def _extension_predicate_named(rationale: str) -> bool:
        text = rationale.lower()
        return any(token in text for token in _EXTENSION_PREDICATE_TOKENS)

    def _build_payload(self, entry: SARWorkflowEntry) -> dict[str, object]:
        return {
            "entry_id": entry.entry_id,
            "surface": entry.surface.value,
            "action": entry.action.value,
            "case_id": entry.case_id,
            "alert_ids": list(entry.alert_ids),
            "suspect_party_ids": list(entry.suspect_party_ids),
            "model_id": entry.model_id,
            "model_version": entry.model_version,
            "model_validation_id": entry.model_validation_id,
            "detection_anchor_timestamp": entry.detection_anchor_timestamp.isoformat(),
            "decision_timestamp": entry.decision_timestamp.isoformat(),
            "narrative_hash": entry.narrative_hash,
            "narrative_auto_populated": entry.surface
            == SARDecisionSurface.NARRATIVE_AUTO_POPULATION,
            "score_value": entry.score_value,
            "score_factors": list(entry.score_factors),
            "rationale": entry.rationale,
            "safe_harbor_claimed": entry.safe_harbor_claimed,
            "safe_harbor_citation": SAFE_HARBOR_CITATION,
        }


__all__ = [
    "SAFE_HARBOR_CITATION",
    "SARActionTaken",
    "SARAuditError",
    "SARDecisionSurface",
    "SARWorkflowAudit",
    "SARWorkflowEntry",
]
