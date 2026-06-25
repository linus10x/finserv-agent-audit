"""Tests for the GRANT -> EXAMINE -> REVOKE authority lifecycle primitive.

The lifecycle records, as first-class hash-chained events, the three moments
that make a *demotion-gated* control surface falsifiable under audit:

  1. authority is GRANTED to an agent only against evidence,
  2. the grant is EXAMINED (an independent finding), and
  3. authority is REVOKED/demoted, recorded against the grant + the finding
     that triggered it.

The ``verify_authority_invariants`` walk is the SEMANTIC layer above hash-chain
integrity: it catches a grant inserted with no evidence even when the hash
chain itself has been regenerated to pass ``verify()``. That is the forged-grant
attack the panel asked the demo to defeat.
"""

from __future__ import annotations

import pytest

from finserv_agent_audit.governance.audit_chain import AuditChain
from finserv_agent_audit.governance.authority_lifecycle import (
    AuthorityInvariantError,
    AuthorityLifecycle,
    verify_authority_invariants,
)
from finserv_agent_audit.governance.ledger_store import InMemoryLedgerStore
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)


def _fresh_chain() -> AuditChain:
    # Hermetic in-memory store, deployer-keyed (engages the genesis event #0).
    # An explicit store avoids the default JSONL log path so the test never
    # picks up a stale ``output/audit_chain.jsonl`` from the working tree.
    return AuditChain(
        ledger_store=InMemoryLedgerStore(),
        deployer_id="test-bank-prod",
        chain_creation_iso="2026-06-24T00:00:00+00:00",
    )


def _grant_exam_revoke(chain: AuditChain) -> tuple[AuditEvent, AuditEvent, AuditEvent]:
    lc = AuthorityLifecycle(chain, agent_id="rebalancer-agent")
    grant = lc.grant(
        level=AutonomyLevel.A3,
        evidence={
            "sovereign_veto_load_tested": True,
            "audit_ledger_running_days": 120,
            "shadow_mode_running_days": 45,
            "circuit_breaker_test_recent": True,
        },
    )
    exam = lc.examine(
        grant_event_id=grant.event_id,
        at_level=AutonomyLevel.A3,
        finding="2 out-of-envelope writes exceeded the drift band threshold",
        passed=False,
    )
    revoke = lc.revoke(
        grant_event_id=grant.event_id,
        examination_event_id=exam.event_id,
        to_level=AutonomyLevel.A1,
        reason="examination failed: out-of-envelope drift",
    )
    return grant, exam, revoke


class TestLifecycleRecording:
    def test_grant_examine_revoke_are_appended_as_typed_events(self) -> None:
        chain = _fresh_chain()
        grant, exam, revoke = _grant_exam_revoke(chain)
        assert grant.event_type is AuditEventType.AUTHORITY_GRANTED
        assert exam.event_type is AuditEventType.AUTHORITY_EXAMINED
        assert revoke.event_type is AuditEventType.AUTHORITY_REVOKED
        # The whole chain still verifies cryptographically.
        assert chain.verify() is True

    def test_grant_records_evidence_and_a_matching_digest(self) -> None:
        chain = _fresh_chain()
        grant, _, _ = _grant_exam_revoke(chain)
        assert grant.payload["evidence"]  # non-empty
        assert grant.payload["granted_level"] == "A3"
        assert len(grant.payload["evidence_digest"]) == 64

    def test_revocation_references_the_grant_and_the_examination(self) -> None:
        chain = _fresh_chain()
        grant, exam, revoke = _grant_exam_revoke(chain)
        # authority going DOWN, recorded against its triggering evidence.
        assert revoke.payload["grant_event_id"] == grant.event_id
        assert revoke.payload["examination_event_id"] == exam.event_id
        assert revoke.payload["to_level"] == "A1"
        assert revoke.autonomy_level is AutonomyLevel.A1

    def test_grant_with_empty_evidence_is_refused_at_write_time(self) -> None:
        chain = _fresh_chain()
        lc = AuthorityLifecycle(chain, agent_id="rebalancer-agent")
        with pytest.raises(AuthorityInvariantError):
            lc.grant(level=AutonomyLevel.A3, evidence={})


class TestInvariantVerifier:
    def test_clean_lifecycle_passes_invariants(self) -> None:
        chain = _fresh_chain()
        _grant_exam_revoke(chain)
        # Must not raise.
        verify_authority_invariants(chain)

    def test_forged_grant_with_no_evidence_is_caught(self) -> None:
        """A grant inserted with no evidence, in a chain whose hashes were
        regenerated so ``verify()`` passes, is still REJECTED by the semantic
        verifier. This is the forged-grant attack the panel named.

        Polarity: the assertion checks for the PRESENCE of the catch (the
        forged grant is rejected), not merely the absence of an error.
        """
        chain = _fresh_chain()
        # Forge directly into the store: a well-formed AUTHORITY_GRANTED whose
        # payload carries NO evidence. Hash is recomputed on construction, so
        # the cryptographic chain is internally consistent.
        head = chain.chain_head()
        forged = AuditEvent.create(
            event_type=AuditEventType.AUTHORITY_GRANTED,
            autonomy_level=AutonomyLevel.A4,
            agent_id="attacker-agent",
            payload={"granted_level": "A4"},  # <-- no "evidence" key
            prev_hash=head,
        )
        chain._store.append(forged)  # noqa: SLF001 — simulating a storage-layer attacker
        # Cryptographic verify is happy — the forgery is internally consistent.
        assert chain.verify() is True
        # The SEMANTIC verifier catches it.
        with pytest.raises(AuthorityInvariantError) as exc:
            verify_authority_invariants(chain)
        assert "evidence" in str(exc.value).lower()
        assert forged.event_id in str(exc.value)

    def test_forged_grant_with_mismatched_evidence_digest_is_caught(self) -> None:
        chain = _fresh_chain()
        head = chain.chain_head()
        forged = AuditEvent.create(
            event_type=AuditEventType.AUTHORITY_GRANTED,
            autonomy_level=AutonomyLevel.A4,
            agent_id="attacker-agent",
            payload={
                "granted_level": "A4",
                "evidence": {"fabricated": True},
                "evidence_digest": "0" * 64,  # does not match the evidence
            },
            prev_hash=head,
        )
        chain._store.append(forged)  # noqa: SLF001
        assert chain.verify() is True
        with pytest.raises(AuthorityInvariantError) as exc:
            verify_authority_invariants(chain)
        assert "digest" in str(exc.value).lower()

    def test_revocation_referencing_an_absent_grant_is_caught(self) -> None:
        chain = _fresh_chain()
        head = chain.chain_head()
        forged = AuditEvent.create(
            event_type=AuditEventType.AUTHORITY_REVOKED,
            autonomy_level=AutonomyLevel.A1,
            agent_id="attacker-agent",
            payload={
                "grant_event_id": "does-not-exist",
                "examination_event_id": "also-missing",
                "to_level": "A1",
            },
            prev_hash=head,
        )
        chain._store.append(forged)  # noqa: SLF001
        assert chain.verify() is True
        with pytest.raises(AuthorityInvariantError):
            verify_authority_invariants(chain)
