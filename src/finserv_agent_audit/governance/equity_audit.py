"""EquityAudit — ECOA / Reg B fail-closed pre-flight gate for lending decisions.

Every agent action that touches a protected lending surface (credit
underwriting, credit-limit assignment, risk-based pricing, line-size
changes, account termination on credit grounds, pre-screened marketing,
loss-mitigation offer assignment) routes through this gate before
execution. The gate **fails closed**: absent a current model-validation
artifact, the action is vetoed and the violation is recorded on the
hash-chain audit ledger.

The check sequence implemented here is the first arm of ADR-0010:
``ECOA-VALIDATION-MISSING``. The remaining four arms (lexical proxy
blocklist, disparate-treatment fenceposts, disparate-impact monitor,
notice-timing handle) are operator-specific and ship as separate
modules or configuration in v1.2; this module is the framework anchor.

The protected-class proxy detector (``protected_class_proxy_detector``)
ships as an ADR-0019 stub and raises ``NotImplementedError`` until v1.2;
this gate documents the gap rather than silently passing.

Regulatory framing:
    - ECOA, 15 U.S.C. § 1691 — prohibition on discrimination in any
      aspect of a credit transaction on prohibited bases
    - Regulation B, 12 C.F.R. Part 1002 — protected-class enumeration
      (race, color, religion, national origin, sex, marital status,
      age), § 1002.4(a) general rule, § 1002.4(b) discouragement,
      § 1002.6(b) age limits, § 1002.9(a)(1) 30-day notice timing
    - SR 11-7 (Federal Reserve, 2011) / OCC 2011-12 — model risk
      management; pre-deployment validation, ongoing monitoring,
      challenger testing are expectations not options
    - CFPB / DOJ / OCC / FTC / EEOC joint statement on AI and
      discrimination in credit underwriting (April 25, 2023)
      [UNVERIFIED — confirm full agency list before publication]
    - CFPB Circular 2022-03 (May 26, 2022) — algorithmic complexity
      is not a defense for failing to provide specific reasons

The gate consults a model inventory protocol (``ModelInventory``)
provided by Tranche 2C.a. To avoid a hard import dependency at module
load time, the type is imported under ``TYPE_CHECKING``; at runtime
the gate accepts any object exposing ``has_current_validation(
model_id, model_version) -> bool``.

There is no ECOA-specific ``AuditEventType`` member in the v1.1 enum;
this module emits ``AuditEventType.COMPLIANCE_CHECK`` and namespaces
the payload with ``regulation="ECOA/RegB"``. A dedicated enum member
is a v1.2 follow-up.

> Patterns are software, not legal advice. Regulatory citations live
> in ADR-0010; consult counsel for applicability to your control
> environment.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from finserv_agent_audit.schemas.audit_event import (
    AuditChain,
    AuditEventType,
    AutonomyLevel,
)

if TYPE_CHECKING:
    # Tranche 2C.a contract. Kept under TYPE_CHECKING so this module
    # loads even if 2C.a has not landed yet.
    from finserv_agent_audit.governance.model_inventory import (  # noqa: F401
        ModelInventory,
    )


class ProtectedClass(Enum):
    """ECOA / Reg B § 1002.2 protected-class enumeration.

    Receipt of public assistance and good-faith exercise of consumer-
    credit-protection rights are also protected bases under ECOA;
    they are included for completeness even though they are less
    commonly modeled at the feature level.
    """

    RACE = "race"
    COLOR = "color"
    RELIGION = "religion"
    NATIONAL_ORIGIN = "national_origin"
    SEX = "sex"
    MARITAL_STATUS = "marital_status"
    AGE = "age"
    PUBLIC_ASSISTANCE = "public_assistance"
    CONSUMER_CREDIT_RIGHTS = "consumer_credit_rights"


# The protected lending surfaces enumerated in ADR-0010. A surface is
# protected if a decision on it falls within ECOA's "any aspect of a
# credit transaction" or is an ECOA-adjacent pre-decision step. The
# canonical list moves to ``config/compliance_rules.yaml`` in v1.2;
# the in-module set is the v1.1 default.
PROTECTED_LENDING_SURFACES: frozenset[str] = frozenset(
    {
        "credit_underwriting_decision",
        "credit_limit_assignment",
        "risk_based_pricing",
        "renewal_repricing",
        "line_increase_decision",
        "line_decrease_decision",
        "account_termination_credit",
        "marketing_audience_pre_screen",
        "loss_mitigation_offer_assignment",
    }
)


class EquityAuditViolation(RuntimeError):  # noqa: N818  # name fixed by ADR-0010
    """Raised when a lending-decision check fails closed.

    The violation is recorded on the audit chain BEFORE this exception
    propagates, so the chain remains the source of truth even if the
    caller swallows the error. Recovery is operator-driven: file a
    documented exception per ADR-0010, escalate to the Fair-Lending
    function, or refuse to emit the decision.
    """


@runtime_checkable
class _ModelInventoryLike(Protocol):
    """Structural typing for the Tranche 2C.a ``ModelInventory`` surface.

    Any object that exposes ``has_current_validation`` satisfies the
    gate's runtime contract. The concrete 2C.a implementation will be
    interchangeable with this Protocol once committed.
    """

    def has_current_validation(self, model_id: str, model_version: str) -> bool: ...


@dataclass(frozen=True)
class EquityAuditResult:
    """The outcome of one ``EquityAudit.check`` call.

    ``passed`` is True if the gate allowed the action through; the
    ``event_id`` references the audit-chain entry written by the
    check (which is always written — even on violation).
    """

    passed: bool
    surface: str
    event_id: str
    reason_code: str | None = None


@dataclass
class EquityAudit:
    """Fail-closed pre-flight gate for ECOA / Reg B lending decisions.

    Wire the gate at the agent boundary: every lending-decision-shaped
    action calls ``check`` before execution. On a protected surface the
    gate requires (a) a non-empty ``model_id`` + ``model_version`` and
    (b) a current validation in the supplied ``ModelInventory``. On
    failure the gate writes a violation entry to the chain and raises
    ``EquityAuditViolation``.

    The autonomy-level default is A2 (human on the loop); deployers may
    override per ADR-0004 if the deployment context warrants.
    """

    audit_chain: AuditChain
    model_inventory: _ModelInventoryLike
    autonomy_level: AutonomyLevel = AutonomyLevel.A2

    def check(
        self,
        *,
        surface: str,
        protected_classes: set[ProtectedClass],
        model_id: str | None,
        model_version: str | None,
        agent_id: str,
        actor_id: str | None = None,
    ) -> EquityAuditResult:
        """Run the pre-flight check. Raises on a fail-closed violation.

        Args:
            surface: The named decision surface (e.g.
                ``"credit_underwriting_decision"``). Surfaces in
                ``PROTECTED_LENDING_SURFACES`` trigger the
                model-validation requirement.
            protected_classes: ECOA-protected dimensions the caller
                knows the decision touches. Recorded in the chain
                payload for forensic replay; the gate does not branch
                on this set in v1.1 (any protected lending surface is
                gated).
            model_id: Identifier of the model that produced the
                decision. Required on protected surfaces.
            model_version: Version pin of the model. Required on
                protected surfaces.
            agent_id: The agent emitting the decision.
            actor_id: Optional human actor (e.g. for human-override
                paths). Passed through to the audit chain.

        Returns:
            ``EquityAuditResult`` with ``passed=True`` on success.

        Raises:
            EquityAuditViolation: When the surface is protected and a
                current model-validation artifact is not available.
        """
        if not surface:
            raise ValueError("surface must be a non-empty string")
        if not agent_id:
            raise ValueError("agent_id must be a non-empty string")

        is_protected = surface in PROTECTED_LENDING_SURFACES

        if not is_protected:
            return self._emit_pass(
                surface=surface,
                protected_classes=protected_classes,
                model_id=model_id,
                model_version=model_version,
                agent_id=agent_id,
                actor_id=actor_id,
                note="non_protected_surface",
            )

        # Protected surface — model validation is required.
        if not model_id or not model_version:
            return self._emit_violation(
                surface=surface,
                protected_classes=protected_classes,
                model_id=model_id,
                model_version=model_version,
                agent_id=agent_id,
                actor_id=actor_id,
                detail="model_id and model_version are required on a protected lending surface",
            )

        if not self.model_inventory.has_current_validation(model_id, model_version):
            return self._emit_violation(
                surface=surface,
                protected_classes=protected_classes,
                model_id=model_id,
                model_version=model_version,
                agent_id=agent_id,
                actor_id=actor_id,
                detail=(
                    f"no current model-validation artifact for "
                    f"model_id={model_id!r} model_version={model_version!r}"
                ),
            )

        return self._emit_pass(
            surface=surface,
            protected_classes=protected_classes,
            model_id=model_id,
            model_version=model_version,
            agent_id=agent_id,
            actor_id=actor_id,
            note="validated",
        )

    def _emit_pass(
        self,
        *,
        surface: str,
        protected_classes: set[ProtectedClass],
        model_id: str | None,
        model_version: str | None,
        agent_id: str,
        actor_id: str | None,
        note: str,
    ) -> EquityAuditResult:
        event = self.audit_chain.append(
            event_type=AuditEventType.COMPLIANCE_CHECK,
            autonomy_level=self.autonomy_level,
            agent_id=agent_id,
            payload={
                "regulation": "ECOA/RegB",
                "adr_reference": "ADR-0010",
                "surface": surface,
                "protected_classes": sorted(pc.value for pc in protected_classes),
                "model_id": model_id,
                "model_version": model_version,
                "gate_verdict": "pass",
                "note": note,
            },
            actor_id=actor_id,
        )
        return EquityAuditResult(
            passed=True,
            surface=surface,
            event_id=event.event_id,
        )

    def _emit_violation(
        self,
        *,
        surface: str,
        protected_classes: set[ProtectedClass],
        model_id: str | None,
        model_version: str | None,
        agent_id: str,
        actor_id: str | None,
        detail: str,
    ) -> EquityAuditResult:
        reason_code = "ECOA-VALIDATION-MISSING"
        event = self.audit_chain.append(
            event_type=AuditEventType.COMPLIANCE_CHECK,
            autonomy_level=self.autonomy_level,
            agent_id=agent_id,
            payload={
                "regulation": "ECOA/RegB",
                "adr_reference": "ADR-0010",
                "surface": surface,
                "protected_classes": sorted(pc.value for pc in protected_classes),
                "model_id": model_id,
                "model_version": model_version,
                "gate_verdict": "violation",
                "reason_code": reason_code,
                "detail": detail,
            },
            actor_id=actor_id,
        )
        raise EquityAuditViolation(
            f"{reason_code}: {detail} (surface={surface!r}, agent_id={agent_id!r}); "
            f"violation recorded at event_id={event.event_id}."
        )


__all__ = [
    "PROTECTED_LENDING_SURFACES",
    "EquityAudit",
    "EquityAuditResult",
    "EquityAuditViolation",
    "ProtectedClass",
]
