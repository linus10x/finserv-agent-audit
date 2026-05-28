"""BestInterestCheck — SEC Reg-BI fail-closed pre-recommendation gate.

Every agent that surfaces, ranks, or systematically influences a
securities recommendation to a retail customer routes through this
gate before the recommendation reaches the customer. The gate
**fails closed**: absent documented consideration of (a) costs,
(b) risks, (c) alternatives, and (d) the customer profile, the
recommendation is vetoed and the violation is recorded on the
hash-chain audit ledger.

The four required fields map directly to the SEC Reg-BI Care
Obligation under 17 C.F.R. § 240.15l-1(a)(2)(ii): "reasonable
diligence, care, and skill" to understand the recommendation's
risks, rewards, and costs and to have a reasonable basis to
believe it is in the retail customer's best interest. The April 26,
2023 SEC Division of Examinations risk alert and the July 2023
predictive-data-analytics proposed rule (Release No. 34-97990)
confirmed the obligation reaches algorithmically generated
recommendations.

Regulatory framing:
    - SEC Regulation Best Interest, 17 C.F.R. § 240.15l-1
    - SEC Release No. 34-86031 (June 5, 2019) — adopting release
    - SEC Division of Examinations Risk Alert (April 26, 2023) —
      *Observations from Broker-Dealer Examinations Related to Reg BI*
    - SEC Release No. 34-97990 (July 26, 2023) — PDA proposed rule
    - FINRA Rule 2111 — legacy suitability rule (institutional carve-out)

Gap notes (out of scope here, documented in
``docs/sec_reg_bi_mapping.md``): Form CRS, pre-/post-trade reporting
under Rule 605/606, books-and-records retention under SEC Rule 17a-4,
the annual CEO certification of compliance. The gate covers the
agent-decision-layer Care Obligation; the other arms of Reg BI live
upstream and downstream.

> Patterns are software, not legal advice. Regulatory citations live
> in ``docs/sec_reg_bi_mapping.md``; consult counsel for applicability
> to your control environment.
"""

from __future__ import annotations

from dataclasses import dataclass

from finserv_agent_audit.schemas.audit_event import (
    AuditChain,
    AuditEventType,
    AutonomyLevel,
)


class BestInterestViolation(RuntimeError):  # noqa: N818  # name fixed by sec_reg_bi_mapping
    """Raised when a recommendation lacks documented Care-Obligation evidence.

    The violation is recorded on the audit chain BEFORE this exception
    propagates, so the regulator inquiring about the suppressed
    recommendation can still reconstruct the gate verdict even if the
    caller swallows the error. Recovery is operator-driven: complete
    the missing documentation, escalate to compliance, or suppress
    the recommendation.
    """


@dataclass
class RecommendationProfile:
    """The four documented-consideration fields the Care Obligation requires.

    Each field is a free-text narrative; the gate enforces presence,
    not a specific structure. Operators that want richer schemas can
    wrap this dataclass with their own validators.

    Fields:
        costs: Documented consideration of total cost to the customer —
            commissions, expense ratios, spread, financing, tax drag.
        risks: Documented consideration of the risks of the
            recommendation — market, credit, liquidity, sequence,
            concentration, product-specific.
        alternatives: Documented consideration of reasonably available
            alternatives — the SEC has been explicit that the absence
            of any alternatives review is a Reg-BI failure mode.
        customer_profile: Documented consideration of the customer's
            investment profile — objectives, time horizon, liquidity
            needs, risk tolerance, financial situation, tax status.
    """

    costs: str
    risks: str
    alternatives: str
    customer_profile: str


@dataclass(frozen=True)
class BestInterestResult:
    """The outcome of one ``BestInterestCheck.check`` call.

    ``passed`` is True if the gate allowed the recommendation through;
    the ``event_id`` references the audit-chain entry written by the
    check (which is always written — even on violation).
    """

    passed: bool
    recommendation_id: str
    event_id: str
    reason_code: str | None = None


_REQUIRED_FIELDS: tuple[str, ...] = (
    "costs",
    "risks",
    "alternatives",
    "customer_profile",
)


@dataclass
class BestInterestCheck:
    """Fail-closed pre-recommendation gate for SEC Reg-BI Care Obligation.

    Wire the gate at the recommendation-emission boundary: every
    prospective recommendation calls ``check`` before reaching the
    customer. The gate emits ``AuditEventType.BEST_INTEREST_CHECKED``
    on every call (pass or violation) — the audit chain becomes the
    Care-Obligation evidence record.

    The autonomy-level default is A2 (human on the loop); deployers
    of A3 or A4 autonomy should layer additional supervisory review
    per their Compliance Obligation under § 240.15l-1(a)(2)(iv).
    """

    audit_chain: AuditChain
    autonomy_level: AutonomyLevel = AutonomyLevel.A2

    def check(
        self,
        *,
        recommendation_id: str,
        customer_id: str,
        agent_id: str,
        profile: RecommendationProfile,
        actor_id: str | None = None,
    ) -> BestInterestResult:
        """Run the pre-recommendation gate. Raises on a fail-closed violation.

        Args:
            recommendation_id: Stable identifier for the prospective
                recommendation. Used as the join key for downstream
                forensic replay.
            customer_id: Retail-customer identifier. Stored in the
                chain payload; persistence of customer-PII linkage is
                a deployer responsibility (see ADR-0008 GLBA).
            agent_id: The agent emitting the recommendation.
            profile: Documented consideration across the four required
                Care-Obligation fields. Empty or whitespace-only field
                values trigger a violation.
            actor_id: Optional human actor (e.g. for human-in-the-loop
                paths). Passed through to the audit chain.

        Returns:
            ``BestInterestResult`` with ``passed=True`` on success.

        Raises:
            BestInterestViolation: When one or more of the four
                required documented-consideration fields is absent.
            ValueError: When ``recommendation_id`` or ``customer_id``
                is empty.
        """
        if not recommendation_id:
            raise ValueError("recommendation_id must be a non-empty string")
        if not customer_id:
            raise ValueError("customer_id must be a non-empty string")
        if not agent_id:
            raise ValueError("agent_id must be a non-empty string")

        missing = [name for name in _REQUIRED_FIELDS if not getattr(profile, name).strip()]

        if missing:
            return self._emit_violation(
                recommendation_id=recommendation_id,
                customer_id=customer_id,
                agent_id=agent_id,
                profile=profile,
                missing=missing,
                actor_id=actor_id,
            )

        return self._emit_pass(
            recommendation_id=recommendation_id,
            customer_id=customer_id,
            agent_id=agent_id,
            profile=profile,
            actor_id=actor_id,
        )

    def _emit_pass(
        self,
        *,
        recommendation_id: str,
        customer_id: str,
        agent_id: str,
        profile: RecommendationProfile,
        actor_id: str | None,
    ) -> BestInterestResult:
        event = self.audit_chain.append(
            event_type=AuditEventType.BEST_INTEREST_CHECKED,
            autonomy_level=self.autonomy_level,
            agent_id=agent_id,
            payload={
                "regulation": "SEC/RegBI",
                "obligation": "care",
                "citation": "17 CFR 240.15l-1(a)(2)(ii)",
                "recommendation_id": recommendation_id,
                "customer_id": customer_id,
                "costs": profile.costs,
                "risks": profile.risks,
                "alternatives": profile.alternatives,
                "customer_profile": profile.customer_profile,
                "gate_verdict": "pass",
            },
            actor_id=actor_id,
        )
        return BestInterestResult(
            passed=True,
            recommendation_id=recommendation_id,
            event_id=event.event_id,
        )

    def _emit_violation(
        self,
        *,
        recommendation_id: str,
        customer_id: str,
        agent_id: str,
        profile: RecommendationProfile,
        missing: list[str],
        actor_id: str | None,
    ) -> BestInterestResult:
        reason_code = "REG-BI-CARE-UNDOCUMENTED"
        event = self.audit_chain.append(
            event_type=AuditEventType.BEST_INTEREST_CHECKED,
            autonomy_level=self.autonomy_level,
            agent_id=agent_id,
            payload={
                "regulation": "SEC/RegBI",
                "obligation": "care",
                "citation": "17 CFR 240.15l-1(a)(2)(ii)",
                "recommendation_id": recommendation_id,
                "customer_id": customer_id,
                "costs": profile.costs,
                "risks": profile.risks,
                "alternatives": profile.alternatives,
                "customer_profile": profile.customer_profile,
                "gate_verdict": "violation",
                "reason_code": reason_code,
                "missing_fields": missing,
            },
            actor_id=actor_id,
        )
        raise BestInterestViolation(
            f"{reason_code}: undocumented Care-Obligation consideration on "
            f"fields={missing} (recommendation_id={recommendation_id!r}, "
            f"customer_id={customer_id!r}); violation recorded at "
            f"event_id={event.event_id}."
        )


__all__ = [
    "BestInterestCheck",
    "BestInterestResult",
    "BestInterestViolation",
    "RecommendationProfile",
]
