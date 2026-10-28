"""External-anchor verification — defeats head-truncation AND backdating.

A hash-chain alone cannot detect that its TAIL was removed: deleting the last
event(s) and re-reading the chain re-links cleanly, so ``verify()`` returns
True on a truncated chain. Likewise a storage-layer attacker can REGENERATE the
whole chain to a backdated history with a different head, and ``verify()`` is
again happy. The defense is an EXTERNAL witness that recorded what the head was
at time T: an honest chain only grows, so every externally-witnessed head MUST
still be present in the chain. If a witnessed head is gone, the chain was
truncated below it or regenerated away from it.

``verify_against_external_anchors`` is that check. It needs no network — the
witnessed (head, time) records are held OUTSIDE the chain (in production: read
back from Rekor / OpenTimestamps / a regulator's log; here: retained by a
``RecordingWitness`` that simulates the external log).
"""

from __future__ import annotations

import pytest

from finserv_agent_audit.governance.audit_chain import (
    AuditChain,
    AuditChainTamperError,
)
from finserv_agent_audit.governance.authority_lifecycle import AuthorityLifecycle
from finserv_agent_audit.governance.ledger_store import InMemoryLedgerStore
from finserv_agent_audit.governance.witness_anchor import (
    RecordingWitness,
    WitnessContradictionError,
    anchor_to_witness,
    verify_against_external_anchors,
)
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)


def _chain_with_revocation() -> tuple[AuditChain, RecordingWitness, str]:
    """Build grant->examine->revoke, anchor the revoked head externally.

    Returns (chain, witness, revoked_head_hex). The witness has recorded the
    revocation's event_hash as an external anchor.
    """
    chain = AuditChain(
        ledger_store=InMemoryLedgerStore(),
        deployer_id="acme-bank-prod",
        chain_creation_iso="2026-06-24T00:00:00+00:00",
    )
    lc = AuthorityLifecycle(chain, agent_id="rebalancer-agent")
    grant = lc.grant(level=AutonomyLevel.A3, evidence={"shadow_days": 45})
    exam = lc.examine(
        grant_event_id=grant.event_id,
        at_level=AutonomyLevel.A3,
        finding="out-of-envelope drift",
        passed=False,
    )
    revoke = lc.revoke(
        grant_event_id=grant.event_id,
        examination_event_id=exam.event_id,
        to_level=AutonomyLevel.A1,
        reason="examination failed",
    )
    revoked_head = revoke.event_hash
    witness = RecordingWitness()
    # Anchor the revoked head to the external witness register.
    anchor_to_witness(audit_chain=chain, witness=witness)
    return chain, witness, revoked_head


class TestRecordingWitness:
    def test_anchor_records_the_head(self) -> None:
        chain, witness, revoked_head = _chain_with_revocation()
        assert len(witness.records) == 1
        assert witness.records[0].chain_head_hex == revoked_head
        assert witness.records[0].register_name == "recording-witness"

    def test_anchor_rejects_non_sha256(self) -> None:
        witness = RecordingWitness()
        with pytest.raises(ValueError):
            witness.anchor("tooshort")


class TestVerifyAgainstAnchors:
    def test_honest_chain_passes(self) -> None:
        chain, witness, _ = _chain_with_revocation()
        # The revoked head is still present in the (grown) chain -> no contradiction.
        verify_against_external_anchors(chain, witness.records)

    def test_head_truncation_removing_the_revocation_is_caught(self) -> None:
        """Attacker deletes the revocation (and the anchor event after it) so the
        agent appears to still hold A3. verify() is fooled; the external anchor
        is not."""
        chain, witness, revoked_head = _chain_with_revocation()
        # Truncate the tail: drop the WITNESS_ANCHOR event and the revocation.
        store = chain._store  # noqa: SLF001
        del store._events[-2:]  # noqa: SLF001 — simulate a storage-layer truncation
        # The truncated chain still passes hash-chain verification (re-links cleanly).
        assert chain.verify() is True
        # But the externally-witnessed revoked head is now ABSENT -> caught.
        with pytest.raises(WitnessContradictionError) as exc:
            verify_against_external_anchors(chain, witness.records)
        assert revoked_head[:12] in str(exc.value)

    def test_backdated_regeneration_is_caught(self) -> None:
        """Attacker regenerates a different (backdated) history with a different
        head. The witnessed head from the real chain is absent -> caught."""
        _, witness, _ = _chain_with_revocation()
        # A wholly regenerated chain the attacker built from scratch — internally
        # consistent, passes verify(), but does NOT contain the witnessed head.
        regenerated = AuditChain(
            ledger_store=InMemoryLedgerStore(),
            deployer_id="acme-bank-prod",
            chain_creation_iso="2026-06-24T00:00:00+00:00",
        )
        lc = AuthorityLifecycle(regenerated, agent_id="rebalancer-agent")
        # Backdated story: a grant with NO subsequent revocation.
        lc.grant(level=AutonomyLevel.A3, evidence={"shadow_days": 45})
        assert regenerated.verify() is True
        with pytest.raises(WitnessContradictionError):
            verify_against_external_anchors(regenerated, witness.records)

    def test_no_anchors_is_a_noop(self) -> None:
        chain, _, _ = _chain_with_revocation()
        # An empty anchor set cannot contradict anything.
        verify_against_external_anchors(chain, [])

    def test_fail_closed_when_chain_is_not_hash_consistent(self) -> None:
        """Called on a hash-broken chain, the anchor verifier must NOT silently
        pass — it runs verify() first and raises. This closes the "called alone"
        ghost-event bypass the security review flagged."""
        chain, witness, _ = _chain_with_revocation()
        # Break the hash chain in place (mutate a payload, keep its stored hash).
        target = chain._store._events[1]  # noqa: SLF001
        mutated = AuditEvent(
            event_type=target.event_type,
            autonomy_level=target.autonomy_level,
            agent_id=target.agent_id,
            payload={**target.payload, "tampered": True},
            prev_hash=target.prev_hash,
            event_id=target.event_id,
            timestamp=target.timestamp,
            actor_id=target.actor_id,
            schema_version=target.schema_version,
            event_hash=target.event_hash,  # stale hash -> verify() False
        )
        chain._store._events[1] = mutated  # noqa: SLF001
        assert chain.verify() is False
        with pytest.raises(AuditChainTamperError):
            verify_against_external_anchors(chain, witness.records)

    def test_empty_chain_anchor_does_not_false_positive(self) -> None:
        """Anchoring an empty (legacy) chain records the GENESIS sentinel; a
        later verify must SKIP it rather than false-positive on an honest chain."""
        chain = AuditChain(ledger_store=InMemoryLedgerStore())
        witness = RecordingWitness()
        anchor_to_witness(audit_chain=chain, witness=witness)  # anchors the sentinel
        chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="a",
            payload={"k": 1},
        )
        verify_against_external_anchors(chain, witness.records)  # must not raise
