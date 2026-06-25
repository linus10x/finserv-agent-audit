"""verify() / verify_strict() must be genesis-aware (CR-7 consistency fix).

CR-7 seeds a deployer-keyed genesis event whose ``prev_hash`` is
``_compute_genesis_hash(deployer_id, chain_creation_iso)`` — NOT the legacy
``"0"*64`` sentinel. But ``verify`` / ``verify_strict`` hard-coded the walk to
start at the sentinel, so an HONEST deployer-keyed chain failed verification
(``verify()`` returned False; ``verify_strict`` raised "prev_hash mismatch at
index 0"). That is a false tamper-alarm on a clean chain — and it silently
disabled the very anti-regeneration mode the library promotes.

The fix makes the walk start from the chain's actual seed:
  - legacy / empty chain  -> the GENESIS sentinel (unchanged behavior);
  - deployer-keyed chain   -> the seed RECOMPUTED from the genesis event's
    declared ``deployer_id`` + ``chain_creation_iso``, so a genesis whose
    ``prev_hash`` was altered to not match its declared deployer identity is
    CAUGHT (an added integrity check, not a relaxation).
"""

from __future__ import annotations

import pytest

from finserv_agent_audit.governance.audit_chain import (
    GENESIS_AGENT_ID,
    AuditChain,
    AuditChainTamperError,
)
from finserv_agent_audit.governance.ledger_store import InMemoryLedgerStore
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)


def _deployer_chain() -> AuditChain:
    return AuditChain(
        ledger_store=InMemoryLedgerStore(),
        deployer_id="acme-bank-prod",
        chain_creation_iso="2026-06-24T00:00:00+00:00",
    )


class TestHonestChainsVerify:
    def test_honest_deployer_keyed_chain_verifies_true(self) -> None:
        chain = _deployer_chain()
        chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="zeus",
            payload={"action": "buy"},
        )
        assert chain.verify() is True  # was False before the fix

    def test_honest_deployer_keyed_chain_passes_verify_strict(self) -> None:
        chain = _deployer_chain()
        chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="zeus",
            payload={"action": "buy"},
        )
        chain.verify_strict()  # must not raise

    def test_legacy_in_memory_chain_still_verifies_true(self) -> None:
        chain = AuditChain(ledger_store=InMemoryLedgerStore())
        chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="zeus",
            payload={"action": "buy"},
        )
        assert chain.verify() is True


class TestTamperedGenesisIsCaught:
    def test_genesis_with_wrong_seed_is_caught(self) -> None:
        """A genesis event whose prev_hash does not match the seed derived from
        its OWN declared deployer_id/creation_iso is rejected at index 0."""
        chain = _deployer_chain()
        genesis = chain._events[0]
        # Forge a genesis with a tampered seed but an otherwise valid (recomputed)
        # event_hash, so only the seed-derivation check can catch it.
        forged_genesis = AuditEvent.create(
            event_type=AuditEventType.AGENT_STARTED,
            autonomy_level=AutonomyLevel.A0,
            agent_id=GENESIS_AGENT_ID,
            payload=dict(genesis.payload),  # same declared deployer_id/creation_iso
            prev_hash="f" * 64,  # <-- wrong seed
            event_id=genesis.event_id,
            timestamp=genesis.timestamp,
        )
        chain._store._events[0] = forged_genesis  # noqa: SLF001
        assert chain.verify() is False
        with pytest.raises(AuditChainTamperError):
            chain.verify_strict()

    def test_genesis_with_swapped_deployer_id_is_caught(self) -> None:
        """Swapping the declared deployer_id while keeping the original seed
        makes the recomputed seed disagree with prev_hash -> caught."""
        chain = _deployer_chain()
        genesis = chain._events[0]
        swapped_payload = dict(genesis.payload)
        swapped_payload["deployer_id"] = "evil-corp"
        forged_genesis = AuditEvent.create(
            event_type=AuditEventType.AGENT_STARTED,
            autonomy_level=AutonomyLevel.A0,
            agent_id=GENESIS_AGENT_ID,
            payload=swapped_payload,
            prev_hash=genesis.prev_hash,  # original seed, now inconsistent with deployer_id
            event_id=genesis.event_id,
            timestamp=genesis.timestamp,
        )
        chain._store._events[0] = forged_genesis  # noqa: SLF001
        assert chain.verify() is False
