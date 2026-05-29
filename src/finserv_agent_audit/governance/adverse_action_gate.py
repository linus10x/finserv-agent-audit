"""FCRA / Reg V / CFPB Circular 2022-03 AdverseActionGate — ADR-0009.

When an autonomous agent issues, recommends, or materially influences an
adverse credit decision, the resulting notice owes the consumer specific
principal reasons under FCRA § 615 (15 U.S.C. § 1681m) and Reg B
§ 1002.9(a)(2)(i). CFPB Circular 2022-03 (May 26, 2022) forecloses the
"the model is too complex to explain" defense. The gate enforces those
requirements at decision-emit time: a packet that cannot defend itself
is rejected before the decision reaches the consumer.

The gate fails closed. A missing or generic reason set, a missing
consumer-reporting-agency identifier on an FCRA-trigger decision, or an
absent model-validation reference each raises `AdverseActionViolation`
under a named violation code. Every gate evaluation (pass or block) emits
`AuditEventType.ADVERSE_ACTION_TAKEN` to the wired ledger store.

The reference reason-code dictionary at the bottom of this module covers
the canonical Reg B principal-reason set; institutions extend it to match
their decision-engine taxonomy.

Regulatory anchors:
    - FCRA § 615, 15 U.S.C. § 1681m
    - FCRA § 607(b), 15 U.S.C. § 1681e(b)
    - Reg V, 12 C.F.R. § 1022.74
    - Reg B (ECOA), 12 C.F.R. § 1002.9(a)(1) and (a)(2)(i)
    - CFPB Circular 2022-03 (May 26, 2022)
    - Reader-friendly mapping: `docs/fcra_reg_v_mapping.md` and
      `docs/cfpb_circular_2022_03_mapping.md`

> Reference pattern, not legal advice. Regulatory characterizations are
> summaries; engage qualified counsel for compliance determinations. See
> repo-root `DISCLAIMER.md`.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from types import MappingProxyType

from finserv_agent_audit.governance.ledger_store import LedgerStore
from finserv_agent_audit.governance.subject_id import SubjectIdHasher
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)

logger = logging.getLogger(__name__)

MAX_PRINCIPAL_REASONS = 4
"""Reg B convention: notices carry up to four principal reasons."""

_GENERIC_REASON_FRAGMENTS: tuple[str, ...] = (
    "model decision",
    "score below threshold",
    "score too low",
    "credit score too low",
    "algorithm decision",
)


class AdverseActionKind(Enum):
    """Categorization of adverse-action triggers."""

    CREDIT_DENIED = "credit_denied"
    CREDIT_TERMINATED = "credit_terminated"
    UNFAVORABLE_CHANGE = "unfavorable_change"
    COUNTEROFFER_LESS_FAVORABLE = "counteroffer_less_favorable"
    INSURANCE_DENIED_OR_PRICED_UP = "insurance_decline_or_priced_up"


@dataclass(frozen=True)
class ReasonCode:
    """One principal reason tied to upstream feature provenance.

    Fields:
        code: institution-scoped reason-code identifier.
        plain_language: consumer-facing wording.
        factor_contribution: non-negative normalized weight within the decision.
        upstream_feature_ids: traceable input features for the explainability harness.
    """

    code: str
    plain_language: str
    factor_contribution: float
    upstream_feature_ids: tuple[str, ...]


@dataclass(frozen=True)
class AdverseActionPacket:
    """Decision-time payload presented to the gate."""

    decision_id: str
    consumer_id: str
    action_kind: AdverseActionKind
    primary_reasons: tuple[ReasonCode, ...]
    model_id: str
    model_version: str
    model_validation_id: str
    cra_used: str | None
    decision_timestamp: datetime


class AdverseActionViolation(RuntimeError):  # noqa: N818  # name fixed by ADR-0009
    """Raised when a packet does not satisfy the gate's preconditions.

    The message lists every triggered violation code so the caller can
    address the full set rather than fix-and-retry one at a time.
    """

    def __init__(self, codes: tuple[str, ...]) -> None:
        self.codes = codes
        super().__init__("; ".join(codes))


@dataclass
class AdverseActionGate:
    """Fail-closed gate for adverse credit decisions.

    Wire a `LedgerStore` to receive `ADVERSE_ACTION_TAKEN` events on every
    gate evaluation (pass or block). The audit chain entry carries the full
    violation list so a downstream supervisory inquiry returns a defensible
    answer from the chain itself.

    When ``subject_id_hasher`` is supplied, raw ``consumer_id`` values are
    hashed before being written to the chain payload — required for GLBA /
    GDPR-safe operation (see ``governance.subject_id``). When ``None`` (the
    default), the gate emits a ``WARNING``-level log on every emit naming
    the GLBA Safeguards Rule / GDPR Art. 17 risk; operators wiring the gate
    in production MUST pass a hasher.
    """

    ledger_store: LedgerStore | None = None
    agent_id: str = "system:adverse_action_gate"
    subject_id_hasher: SubjectIdHasher | None = None
    _generic_fragments: tuple[str, ...] = field(
        default=_GENERIC_REASON_FRAGMENTS, init=False, repr=False
    )

    def evaluate(self, packet: AdverseActionPacket) -> None:
        """Run every precondition. Raise on any failure; emit audit on every call."""
        violations = self._collect_violations(packet)
        if violations:
            self._emit_event(packet, outcome="blocked", violations=violations)
            raise AdverseActionViolation(violations)
        self._emit_event(packet, outcome="passed", violations=())

    # ------------------------------------------------------------------ #
    # Internals                                                          #
    # ------------------------------------------------------------------ #

    def _collect_violations(self, packet: AdverseActionPacket) -> tuple[str, ...]:
        violations: list[str] = []

        if not packet.primary_reasons or self._all_reasons_generic(packet.primary_reasons):
            violations.append("FCRA-REASONS-MISSING")

        if len(packet.primary_reasons) > MAX_PRINCIPAL_REASONS:
            violations.append("FCRA-REASONS-OVERLOAD")

        if packet.primary_reasons and not self._has_factor_traceability(packet.primary_reasons):
            violations.append("FCRA-FACTOR-TRACE-MISSING")

        if packet.primary_reasons and self._has_negative_contribution(packet.primary_reasons):
            violations.append("FCRA-FACTOR-CONTRIB-INVALID")

        if not packet.cra_used:
            violations.append("FCRA-CRA-UNNAMED")

        if not packet.model_validation_id:
            violations.append("FCRA-VALIDATION-MISSING")

        return tuple(violations)

    def _all_reasons_generic(self, reasons: tuple[ReasonCode, ...]) -> bool:
        if not reasons:
            return False
        return all(self._is_generic(r) for r in reasons)

    def _is_generic(self, reason: ReasonCode) -> bool:
        haystack = reason.plain_language.strip().lower()
        if not haystack:
            return True
        return any(fragment in haystack for fragment in self._generic_fragments)

    @staticmethod
    def _has_factor_traceability(reasons: tuple[ReasonCode, ...]) -> bool:
        return all(len(r.upstream_feature_ids) > 0 for r in reasons)

    @staticmethod
    def _has_negative_contribution(reasons: tuple[ReasonCode, ...]) -> bool:
        return any(r.factor_contribution < 0 for r in reasons)

    def _emit_event(
        self,
        packet: AdverseActionPacket,
        *,
        outcome: str,
        violations: tuple[str, ...],
    ) -> None:
        if self.ledger_store is None:
            return
        prev_hash = self.ledger_store.head_event_hash()
        payload: dict[str, object] = {
            "decision_id": packet.decision_id,
            "action_kind": packet.action_kind.value,
            "model_id": packet.model_id,
            "model_version": packet.model_version,
            "model_validation_id": packet.model_validation_id,
            "cra_used": packet.cra_used,
            "decision_timestamp": packet.decision_timestamp.isoformat(),
            "reason_codes": [r.code for r in packet.primary_reasons],
            "outcome": outcome,
            "violations": list(violations),
        }
        if self.subject_id_hasher is not None:
            hashed = self.subject_id_hasher.hash_subject(packet.consumer_id)
            payload["consumer_id_hash_b64"] = hashed.hash_b64
            payload["consumer_id_pepper_version"] = hashed.pepper_version
            payload["consumer_id_algorithm"] = hashed.algorithm
        else:
            logger.warning(
                "AdverseActionGate emitting ADVERSE_ACTION_TAKEN with cleartext "
                "consumer_id=%r — GLBA Safeguards Rule (NPI at rest) and "
                "GDPR Art. 17 (right to erasure) risk. Inject a "
                "SubjectIdHasher to hash the consumer_id before payload write.",
                packet.consumer_id,
            )
            payload["consumer_id"] = packet.consumer_id
        event = AuditEvent(
            event_type=AuditEventType.ADVERSE_ACTION_TAKEN,
            autonomy_level=AutonomyLevel.A2,
            agent_id=self.agent_id,
            payload=payload,
            prev_hash=prev_hash,
        )
        self.ledger_store.append(event)


# --------------------------------------------------------------------------- #
# Reference reason-code dictionary                                            #
# --------------------------------------------------------------------------- #

_REFERENCE_REASON_CODES: dict[str, str] = {
    "DTI_TOO_HIGH": "Debt-to-income ratio exceeds policy threshold.",
    "LIMITED_CREDIT_HISTORY": "Length and depth of credit file insufficient.",
    "DELINQUENT_PAYMENT_HISTORY": "Delinquencies present on tradelines.",
    "INSUFFICIENT_INCOME": "Verified income insufficient for requested credit.",
    "EXCESSIVE_OBLIGATIONS": "Total monthly obligations exceed policy threshold.",
    "RECENT_INQUIRIES": "Pattern of recent credit-seeking activity.",
    "HIGH_UTILIZATION": "Revolving-credit utilization exceeds policy threshold.",
    "PUBLIC_RECORD_DEROGATORY": "Public record (bankruptcy, judgment, lien) present.",
    "INSUFFICIENT_COLLATERAL": "Collateral value insufficient relative to requested amount.",
    "EMPLOYMENT_TENURE_SHORT": "Verified employment tenure below policy threshold.",
}

REFERENCE_REASON_CODES: Mapping[str, str] = MappingProxyType(_REFERENCE_REASON_CODES)
"""Canonical Reg B principal-reason set. Extend per institution taxonomy."""


__all__ = [
    "MAX_PRINCIPAL_REASONS",
    "REFERENCE_REASON_CODES",
    "AdverseActionGate",
    "AdverseActionKind",
    "AdverseActionPacket",
    "AdverseActionViolation",
    "ReasonCode",
]
