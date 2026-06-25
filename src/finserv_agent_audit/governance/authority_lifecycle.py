"""GRANT -> EXAMINE -> REVOKE authority lifecycle — ADR-0026.

The Autonomy Ladder's defensible contribution is not the A0->A4 taxonomy (a
known taxonomy: Morris "Levels of AGI", SAE J3016, Sheridan, SR 11-7). It is
the *demotion-gated, falsifiable-under-audit* control surface:

  - authority is GRANTED to an agent only against evidence,
  - a granted level is EXAMINED by an independent finding, and
  - a granted level is REVOCABLE, and the revocation is RECORDED against the
    grant and the finding that triggered it.

``autonomy_ladder.py`` codifies the A2->A3 promotion *gate* — the check on the
evidence. This module records the three lifecycle moments as first-class,
hash-chained audit events, so a claimed authority level becomes falsifiable: a
regulator (or an independent verifier) can walk the chain and confirm that
every granted level carries its evidence, and that any authority going *down*
is recorded against the examination that demoted it.

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

Regulatory anchors:
    - FRB SR 11-7 — effective challenge; the examination event is the
      independent finding, the revocation is the documented consequence.
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
    """
    canonical = json.dumps(evidence, sort_keys=True, default=str).encode()
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
        """Record an independent examination of a prior grant.

        The examination is the SR 11-7 effective-challenge artifact: a finding
        about whether the agent stayed inside the authority it was granted.
        ``passed=False`` is the trigger a revocation references.
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

      - an ``AUTHORITY_GRANTED`` event has no evidence;
      - an ``AUTHORITY_GRANTED`` event's evidence does not match its
        recorded ``evidence_digest``;
      - an ``AUTHORITY_EXAMINED`` event references a grant not present earlier;
      - an ``AUTHORITY_REVOKED`` event references a grant or examination not
        present earlier.

    Events are walked in order, so "present earlier" is enforced naturally.
    This is independent of, and complementary to, ``AuditChain.verify`` —
    run BOTH (hash-chain integrity AND semantic invariants) for a complete
    check. The semantic walk is what defeats a forged grant in a chain whose
    hashes were regenerated to pass ``verify()``.
    """
    grant_ids: set[str] = set()
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
            recomputed = evidence_digest(evidence)
            if recorded != recomputed:
                raise AuthorityInvariantError(
                    f"AUTHORITY_GRANTED event {event.event_id!r} evidence_digest "
                    f"mismatch: recorded={recorded!r}, recomputed={recomputed!r} "
                    "— the evidence was swapped after the grant was recorded"
                )
            grant_ids.add(event.event_id)
        elif etype is AuditEventType.AUTHORITY_EXAMINED:
            grant_ref = event.payload.get("grant_event_id")
            if grant_ref not in grant_ids:
                raise AuthorityInvariantError(
                    f"AUTHORITY_EXAMINED event {event.event_id!r} references "
                    f"grant {grant_ref!r} which is not present earlier in the chain"
                )
            examination_ids.add(event.event_id)
        elif etype is AuditEventType.AUTHORITY_REVOKED:
            grant_ref = event.payload.get("grant_event_id")
            exam_ref = event.payload.get("examination_event_id")
            if grant_ref not in grant_ids:
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
