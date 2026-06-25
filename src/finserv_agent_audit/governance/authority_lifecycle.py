"""GRANT -> EXAMINE -> REVOKE authority lifecycle — ADR-0026.

The Autonomy Ladder's defensible contribution is not the A0->A4 taxonomy (a
known taxonomy: Morris "Levels of AGI", SAE J3016, Sheridan, SR 11-7). It is
the *demotion-gated, falsifiable-under-audit* control surface:

  - authority is GRANTED to an agent only against RECORDED evidence,
  - a granted level is EXAMINED (a recorded examination finding), and
  - a granted level is REVOCABLE, and the revocation is RECORDED against the
    grant and the finding that triggered it.

SCOPE — what this module verifies, and what it does NOT (read before relying on
the regulatory mapping below):

  - It checks evidence is PRESENT and DIGEST-CONSISTENT (the recorded evidence
    is the evidence that was hashed). It does NOT check the evidence is
    sufficient, valid, or true — adequacy of evidence is the deployer's
    second-line responsibility (see ``autonomy_ladder.check_a2_to_a3_promotion``
    for the A2->A3 criteria gate). "Granted only against evidence" means
    *recorded* evidence, not *adequate* evidence.
  - It records WHO granted and WHO examined (``actor_id``) and, when both are
    present, ENFORCES that the examiner differs from the grantor
    (``verify_authority_invariants``). It does NOT otherwise verify the
    examiner's organizational independence — supplying distinct actor_ids is a
    deployer control. With actor_ids omitted, independence cannot be checked.
  - The EXAMINE event is the RECORD SLOT for an SR 11-7 effective challenge
    (a ``passed`` flag + a free-text finding); it is not itself the challenge,
    and the verifier does not inspect the finding's content.

``autonomy_ladder.py`` codifies the A2->A3 promotion *gate* — the check on the
evidence. For the A3+ regulator-visible boundary, a grant's evidence SHOULD be
the serialized output of ``check_a2_to_a3_promotion`` (see ``grant``); this
module records the lifecycle moments but does NOT itself re-run that gate
(hard coupling is tracked as an ADR-0026 follow-up). This module records the
three moments as first-class, hash-chained audit events, so a claimed authority
level becomes falsifiable: a regulator (or an independent verifier) can walk the
chain and confirm that every granted level carries recorded evidence, that the
examiner differed from the grantor where both are recorded, and that any
authority going *down* is recorded against the examination that demoted it.

``verify_authority_invariants`` is the SEMANTIC verification layer that sits
above hash-chain integrity (``AuditChain.verify`` / ``verify_strict``):

  - a hash-chain catches a record MUTATED after writing, and a record DELETED
    from the middle of the chain (the prev_hash link breaks);
  - the semantic layer catches a record that is internally well-formed and
    hash-consistent but VIOLATES the control's meaning — a grant inserted with
    no evidence, a grant whose evidence does not match its recorded digest, or
    a revocation that references a grant/examination that is not in the chain.

The forged-grant attack (an attacker with storage-layer write access who
regenerates the whole chain so ``verify()`` passes, then inserts a grant they
have no evidence for) passes hash-chain verification but is REJECTED here.

Regulatory anchors (these are where the lifecycle's records FIT; the module
records the artifacts, it does not perform the validation each regime requires):
    - FRB SR 11-7 — the examination event is the record slot for an effective
      challenge; the revocation is its documented consequence. (Independence of
      the challenge is a deployer control; this module enforces grantor !=
      examiner only when both actor_ids are recorded.)
    - EU AI Act Article 14 — human oversight; demotion is the oversight action
      made auditable.
    - NIST AI RMF (Govern/Manage) — the grant->examine->revoke loop is the
      accountability record for an autonomy change.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from finserv_agent_audit.schemas.audit_event import (
    AuditEventType,
    AutonomyLevel,
)

if TYPE_CHECKING:
    from finserv_agent_audit.governance.audit_chain import AuditChain
    from finserv_agent_audit.schemas.audit_event import AuditEvent


class AuthorityInvariantError(RuntimeError):
    """Raised when an authority-lifecycle event violates its structural meaning.

    Distinct from ``AuditChainTamperError`` (a hash-chain break): the chain can
    be cryptographically intact and still carry a semantically forged grant.
    This is the error a forged-grant attack trips.
    """


def evidence_digest(evidence: dict[str, Any]) -> str:
    """SHA-256 over the canonical JSON of an evidence object.

    Used both when recording a grant and when re-checking it during
    verification, so a forged grant cannot swap evidence for a record that
    claims a different (e.g. richer) evidence set than it carries.

    Evidence MUST be JSON-native (no ``default=`` coercion): the same
    constraint the audit-chain serializer enforces, so a digest computed when
    the grant is recorded re-computes byte-identically on any host (the
    cross-host SR 11-7 re-verification the chain advertises). Non-JSON-native
    evidence raises ``TypeError`` here, the same as it would at chain-append
    time.
    """
    canonical = json.dumps(evidence, sort_keys=True).encode()
    return hashlib.sha256(canonical).hexdigest()


class AuthorityLifecycle:
    """Records GRANT / EXAMINE / REVOKE events for one agent onto an AuditChain."""

    def __init__(self, chain: AuditChain, agent_id: str) -> None:
        self._chain = chain
        self._agent_id = agent_id

    def grant(
        self,
        *,
        level: AutonomyLevel,
        evidence: dict[str, Any],
        actor_id: str | None = None,
    ) -> AuditEvent:
        """Record that ``agent`` is granted ``level`` against ``evidence``.

        ``evidence`` MUST be non-empty — a grant with no evidence is the exact
        thing the control surface forbids, so it is refused at write time (and
        also caught at verification time, for grants forged past this method).

        Presence, not adequacy. This records and digests the evidence; it does
        NOT validate that the evidence is sufficient or true. For the A3+
        regulator-visible boundary, pass the SERIALIZED OUTPUT of
        ``autonomy_ladder.check_a2_to_a3_promotion`` (a passed
        ``PromotionGateReport`` and the ``PromotionRequirements`` it was derived
        from) as the evidence, so the recorded grant is provably the *output*
        of the enforced promotion gate rather than a free-text assertion.
        ``grant`` does not itself re-run that gate (hard coupling is an
        ADR-0026 follow-up); the deployer runs the gate and passes its result.

        ``actor_id`` records WHO granted. Pass it (and a DIFFERENT ``actor_id``
        to ``examine``) to get the enforced grantor-!=-examiner independence
        check in ``verify_authority_invariants``.
        """
        if not evidence:
            raise AuthorityInvariantError(
                "a grant must carry non-empty evidence; authority is granted "
                "only against evidence (refused at write time)"
            )
        payload: dict[str, Any] = {
            "granted_level": level.value,
            "evidence": evidence,
            "evidence_digest": evidence_digest(evidence),
        }
        return self._chain.append(
            event_type=AuditEventType.AUTHORITY_GRANTED,
            autonomy_level=level,
            agent_id=self._agent_id,
            payload=payload,
            actor_id=actor_id,
        )

    def examine(
        self,
        *,
        grant_event_id: str,
        at_level: AutonomyLevel,
        finding: str,
        passed: bool,
        actor_id: str | None = None,
    ) -> AuditEvent:
        """Record an examination of a prior grant.

        The examination is the RECORD SLOT for an SR 11-7 effective challenge: a
        ``passed`` flag plus a free-text finding about whether the agent stayed
        inside the authority it was granted. It is not itself the challenge, and
        the verifier does not inspect the finding's content. ``passed=False`` is
        the trigger a revocation references.

        ``actor_id`` records WHO examined. When both this and the grant's
        ``actor_id`` are set, ``verify_authority_invariants`` ENFORCES that they
        differ (an examination must not be performed by the grantor). Omitting
        actor_ids means independence cannot be verified — it is then a deployer
        control, not a checked one.
        """
        payload: dict[str, Any] = {
            "grant_event_id": grant_event_id,
            "finding": finding,
            "passed": passed,
        }
        return self._chain.append(
            event_type=AuditEventType.AUTHORITY_EXAMINED,
            autonomy_level=at_level,
            agent_id=self._agent_id,
            payload=payload,
            actor_id=actor_id,
        )

    def revoke(
        self,
        *,
        grant_event_id: str,
        examination_event_id: str,
        to_level: AutonomyLevel,
        reason: str,
        actor_id: str | None = None,
    ) -> AuditEvent:
        """Record authority going DOWN, chained to the grant + the finding.

        This is the under-told half of the ladder: a granted level is
        revocable and the revocation is recorded against its triggering
        evidence. ``autonomy_level`` on the event is the demoted-to level.
        """
        payload: dict[str, Any] = {
            "grant_event_id": grant_event_id,
            "examination_event_id": examination_event_id,
            "to_level": to_level.value,
            "reason": reason,
        }
        return self._chain.append(
            event_type=AuditEventType.AUTHORITY_REVOKED,
            autonomy_level=to_level,
            agent_id=self._agent_id,
            payload=payload,
            actor_id=actor_id,
        )


def verify_authority_invariants(chain: AuditChain) -> None:
    """Walk the chain and enforce the authority-lifecycle invariants.

    Raises ``AuthorityInvariantError`` (naming the offending event) when:

      - an ``AUTHORITY_GRANTED`` event has no evidence, or evidence that cannot
        be canonicalized (non-JSON-native);
      - an ``AUTHORITY_GRANTED`` event's evidence does not match its
        recorded ``evidence_digest``;
      - an ``AUTHORITY_EXAMINED`` event references a grant not present earlier;
      - an ``AUTHORITY_EXAMINED`` event's examiner ``actor_id`` equals the
        referenced grant's grantor ``actor_id`` (when both are recorded) — an
        examination must be independent of the grant it challenges;
      - an ``AUTHORITY_REVOKED`` event references a grant or examination not
        present earlier.

    Events are walked in order, so "present earlier" is enforced naturally.
    This is independent of, and complementary to, ``AuditChain.verify`` —
    run BOTH (hash-chain integrity AND semantic invariants) for a complete
    check. The semantic walk is what defeats a forged grant in a chain whose
    hashes were regenerated to pass ``verify()``.

    Independence is checked only when actor_ids are recorded on BOTH the grant
    and the examination; omitting them means independence is a deployer control
    this walk cannot verify (see the module docstring SCOPE note).
    """
    grant_actor: dict[str, str | None] = {}
    examination_ids: set[str] = set()

    for event in chain._events:  # noqa: SLF001 — verifier reads the ledger
        etype = event.event_type
        if etype is AuditEventType.AUTHORITY_GRANTED:
            evidence = event.payload.get("evidence")
            if not evidence:
                raise AuthorityInvariantError(
                    f"AUTHORITY_GRANTED event {event.event_id!r} carries no "
                    "evidence — authority granted without evidence is a forged "
                    "grant; rejected"
                )
            recorded = event.payload.get("evidence_digest")
            try:
                recomputed = evidence_digest(evidence)
            except TypeError as exc:
                raise AuthorityInvariantError(
                    f"AUTHORITY_GRANTED event {event.event_id!r} has evidence "
                    "that cannot be canonicalized to JSON — a valid grant's "
                    "evidence must be JSON-native; rejected"
                ) from exc
            if recorded != recomputed:
                raise AuthorityInvariantError(
                    f"AUTHORITY_GRANTED event {event.event_id!r} evidence_digest "
                    f"mismatch: recorded={recorded!r}, recomputed={recomputed!r} "
                    "— the evidence was swapped after the grant was recorded"
                )
            grant_actor[event.event_id] = event.actor_id
        elif etype is AuditEventType.AUTHORITY_EXAMINED:
            grant_ref = event.payload.get("grant_event_id")
            if grant_ref not in grant_actor:
                raise AuthorityInvariantError(
                    f"AUTHORITY_EXAMINED event {event.event_id!r} references "
                    f"grant {grant_ref!r} which is not present earlier in the chain"
                )
            grantor = grant_actor[grant_ref]
            if (
                event.actor_id is not None
                and grantor is not None
                and event.actor_id == grantor
            ):
                raise AuthorityInvariantError(
                    f"AUTHORITY_EXAMINED event {event.event_id!r} examiner "
                    f"actor_id {event.actor_id!r} is the SAME as the grantor of "
                    f"grant {grant_ref!r} — an examination must be independent of "
                    "the grant it challenges (SR 11-7 effective challenge)"
                )
            examination_ids.add(event.event_id)
        elif etype is AuditEventType.AUTHORITY_REVOKED:
            grant_ref = event.payload.get("grant_event_id")
            exam_ref = event.payload.get("examination_event_id")
            if grant_ref not in grant_actor:
                raise AuthorityInvariantError(
                    f"AUTHORITY_REVOKED event {event.event_id!r} references "
                    f"grant {grant_ref!r} which is not present earlier in the chain "
                    "— a revocation must be chained to the grant it revokes"
                )
            if exam_ref not in examination_ids:
                raise AuthorityInvariantError(
                    f"AUTHORITY_REVOKED event {event.event_id!r} references "
                    f"examination {exam_ref!r} which is not present earlier in the "
                    "chain — a revocation must be chained to its triggering finding"
                )


__all__ = [
    "AuthorityInvariantError",
    "AuthorityLifecycle",
    "evidence_digest",
    "verify_authority_invariants",
]
