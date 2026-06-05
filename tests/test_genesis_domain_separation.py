"""CR-7 — Genesis hash MUST be deployer-keyed, not a shared sentinel.

The v1.x impl used ``GENESIS_HASH = "0" * 64`` as the initial
``prev_hash`` for every chain in every deployment. An attacker who
could write the storage layer could trivially replace a chain
end-to-end — there was no per-deployer secret in the chain seed, so
the regenerated chain would pass ``verify()`` against the same
genesis sentinel.

The fix:

  * ``AuditChain.__init__`` accepts ``deployer_id: str``. New chains
    derive a genesis hash from
    ``SHA-256(domain_separator/deployer_id/chain_creation_iso)``.

  * The genesis is persisted as event #0 — a
    ``AuditEventType.AGENT_STARTED`` event with
    ``agent_id="finserv-audit-chain"`` and
    ``payload={"deployer_id", "chain_creation_iso", "genesis_version"}``.

  * Subsequent events derive ``prev_hash`` from the genesis event's
    ``event_hash``. Two chains with different ``deployer_id`` values
    produce different genesis events even at empty state.

  * Backward compat: a chain loaded from an existing log with the
    legacy ``"0"*64`` genesis is accepted with a deprecation warning
    recommending re-creation with an explicit ``deployer_id``.
"""

from __future__ import annotations

import warnings
from pathlib import Path

from finserv_agent_audit.governance.audit_chain import AuditChain
from finserv_agent_audit.schemas.audit_event import (
    AuditEventType,
    AutonomyLevel,
)


class TestGenesisDifferentiation:
    """Two deployers MUST produce two different genesis events."""

    def test_two_deployers_produce_different_genesis_event_hashes(
        self,
        tmp_path: Path,
    ) -> None:
        chain_a = AuditChain(
            log_file=tmp_path / "a.jsonl",
            deployer_id="deployer-A",
        )
        chain_b = AuditChain(
            log_file=tmp_path / "b.jsonl",
            deployer_id="deployer-B",
        )
        # Both chains have exactly one event — the genesis event #0.
        assert len(chain_a._events) == 1
        assert len(chain_b._events) == 1

        genesis_a = chain_a._events[0]
        genesis_b = chain_b._events[0]
        # Different deployer ids MUST produce different genesis hashes.
        assert genesis_a.event_hash != genesis_b.event_hash

    def test_two_deployers_have_different_chain_heads_at_empty_state(
        self,
        tmp_path: Path,
    ) -> None:
        chain_a = AuditChain(
            log_file=tmp_path / "a.jsonl",
            deployer_id="deployer-A",
        )
        chain_b = AuditChain(
            log_file=tmp_path / "b.jsonl",
            deployer_id="deployer-B",
        )
        # Even at "empty" (genesis-only) state the heads MUST differ —
        # the prior sentinel-based design had them identical.
        assert chain_a.chain_head() != chain_b.chain_head()


class TestGenesisEventStructure:
    """The genesis event MUST be a canonical AGENT_STARTED with the deployer in payload."""

    def test_genesis_event_is_agent_started(self, tmp_path: Path) -> None:
        chain = AuditChain(
            log_file=tmp_path / "audit.jsonl",
            deployer_id="acme-bank-prod",
        )
        genesis = chain._events[0]
        assert genesis.event_type is AuditEventType.AGENT_STARTED

    def test_genesis_event_uses_canonical_agent_id(self, tmp_path: Path) -> None:
        chain = AuditChain(
            log_file=tmp_path / "audit.jsonl",
            deployer_id="acme-bank-prod",
        )
        assert chain._events[0].agent_id == "finserv-audit-chain"

    def test_genesis_payload_carries_deployer_id(self, tmp_path: Path) -> None:
        chain = AuditChain(
            log_file=tmp_path / "audit.jsonl",
            deployer_id="acme-bank-prod",
        )
        payload = chain._events[0].payload
        assert payload["deployer_id"] == "acme-bank-prod"
        assert payload["genesis_version"] == "v1"
        assert "chain_creation_iso" in payload

    def test_subsequent_events_chain_off_genesis(self, tmp_path: Path) -> None:
        chain = AuditChain(
            log_file=tmp_path / "audit.jsonl",
            deployer_id="acme-bank-prod",
        )
        genesis = chain._events[0]
        e1 = chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="zeus",
            payload={"action": "buy"},
        )
        # The first non-genesis event's prev_hash MUST equal the
        # genesis event's event_hash — the chain rolls off the
        # deployer-keyed seed, not the legacy "0"*64 sentinel.
        assert e1.prev_hash == genesis.event_hash


class TestGenesisAutonomyLevel:
    """The genesis event MUST sit at the lowest autonomy level (A0)."""

    def test_genesis_event_is_a0(self, tmp_path: Path) -> None:
        chain = AuditChain(
            log_file=tmp_path / "audit.jsonl",
            deployer_id="acme-bank-prod",
        )
        assert chain._events[0].autonomy_level is AutonomyLevel.A0


class TestBackwardCompat:
    """Loading a legacy chain with the old sentinel genesis MUST warn but succeed."""

    def test_legacy_chain_without_genesis_emits_deprecation_warning(
        self,
        tmp_path: Path,
    ) -> None:
        log_file = tmp_path / "legacy.jsonl"
        # Hand-build a legacy line that uses the old sentinel
        # ``prev_hash="0"*64`` (the pre-CR-7 default) and a correctly
        # computed event_hash so the per-line ``from_jsonl`` check
        # passes. The deprecation we are looking for is about the
        # SEED, not about per-line tampering.
        from finserv_agent_audit.schemas.audit_event import AuditEvent

        legacy_event = AuditEvent.create(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="zeus",
            payload={"action": "buy"},
            prev_hash="0" * 64,
            event_id="11111111-1111-1111-1111-111111111111",
            timestamp="2026-05-22T00:00:00+00:00",
        )
        log_file.write_text(legacy_event.to_jsonl() + "\n", encoding="utf-8")

        # We construct a chain with NO deployer_id — the loader is
        # supposed to detect the legacy sentinel and accept it with a
        # deprecation warning. (The event_hash above is correct for
        # the line as written; the deprecation is about the SEED, not
        # about per-line tampering.)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            chain = AuditChain(log_file=log_file)
            assert len(chain._events) == 1

        deprecation_hits = [
            w
            for w in caught
            if issubclass(w.category, DeprecationWarning) and "deployer_id" in str(w.message)
        ]
        assert deprecation_hits, (
            "loading a legacy chain MUST emit a DeprecationWarning "
            "recommending re-creation with an explicit deployer_id"
        )

    def test_new_chain_without_deployer_id_runs_in_legacy_mode(
        self,
        tmp_path: Path,
    ) -> None:
        """The v1.x call signature (no ``deployer_id``) is preserved as
        legacy mode: no genesis event #0 is prepended and the chain
        seeds from the legacy ``"0"*64`` sentinel. v2.0 callers MUST
        pass an explicit ``deployer_id`` to engage the domain-
        separated genesis seed (CR-7 hardening); this path remains for
        backward compat only."""
        chain = AuditChain(log_file=tmp_path / "audit.jsonl")
        # Legacy mode: no genesis event #0 is prepended.
        assert len(chain._events) == 0
        # The first user-appended event chains from the legacy
        # sentinel rather than from a deployer-keyed seed.
        first = chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="zeus",
            payload={"action": "buy"},
        )
        assert first.prev_hash == "0" * 64

    def test_loaded_chain_does_not_emit_warning_when_genesis_present(
        self,
        tmp_path: Path,
    ) -> None:
        """A chain created with deployer_id, then reloaded, must NOT warn."""
        log_file = tmp_path / "audit.jsonl"
        AuditChain(log_file=log_file, deployer_id="acme")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            chain2 = AuditChain(log_file=log_file, deployer_id="acme")
            assert len(chain2._events) == 1

        deprecation_hits = [
            w
            for w in caught
            if issubclass(w.category, DeprecationWarning) and "deployer_id" in str(w.message)
        ]
        assert deprecation_hits == []


class TestGenesisDeterministicWithinDeployer:
    """For the same deployer_id + chain_creation_iso the genesis IS deterministic."""

    def test_explicit_creation_iso_produces_deterministic_genesis(
        self,
        tmp_path: Path,
    ) -> None:
        # When the caller pins both deployer_id and chain_creation_iso,
        # the genesis hash is fully determined — useful for cross-host
        # reproducibility tests.
        chain_a = AuditChain(
            log_file=tmp_path / "a.jsonl",
            deployer_id="acme",
            chain_creation_iso="2026-05-28T00:00:00+00:00",
        )
        chain_b = AuditChain(
            log_file=tmp_path / "b.jsonl",
            deployer_id="acme",
            chain_creation_iso="2026-05-28T00:00:00+00:00",
        )
        # Same deployer + same creation_iso => same genesis hash.
        assert chain_a._events[0].event_hash == chain_b._events[0].event_hash

    def test_different_creation_iso_produces_different_genesis(
        self,
        tmp_path: Path,
    ) -> None:
        chain_a = AuditChain(
            log_file=tmp_path / "a.jsonl",
            deployer_id="acme",
            chain_creation_iso="2026-05-28T00:00:00+00:00",
        )
        chain_b = AuditChain(
            log_file=tmp_path / "b.jsonl",
            deployer_id="acme",
            chain_creation_iso="2026-05-29T00:00:00+00:00",
        )
        # Same deployer, different creation_iso => different genesis.
        assert chain_a._events[0].event_hash != chain_b._events[0].event_hash


class TestGenesisHashFormula:
    """Pin the formula so an accidental refactor cannot silently change it."""

    def test_genesis_uses_documented_domain_separator(self, tmp_path: Path) -> None:
        import hashlib

        chain = AuditChain(
            log_file=tmp_path / "audit.jsonl",
            deployer_id="acme",
            chain_creation_iso="2026-05-28T00:00:00+00:00",
        )
        # The seed is the deployer_id + chain_creation_iso under a
        # documented domain separator. The seed is the prev_hash of
        # the genesis event #0; the event's event_hash is the SHA-256
        # of the genesis event's fields including that prev_hash.
        expected_seed = hashlib.sha256(
            b"finserv-agent-audit/genesis/v1/acme/2026-05-28T00:00:00+00:00",
        ).hexdigest()
        assert chain._events[0].prev_hash == expected_seed


# --------------------------------------------------------------------------- #
# P3 (AL-PROBE-03b) regression — the deployer-keyed verifier defect.
#
# Pre-fix, verify()/verify_strict() seeded prev=GENESIS_HASH ('0'*64)
# unconditionally, so a CLEAN deployer-keyed chain (whose event #0 carries
# a deployer-keyed prev_hash) raised a FALSE tamper finding. These tests pin
# the corrected contract: BOTH a hardened deployer-keyed chain AND a legacy
# chain verify True; legacy detection is unchanged.
# --------------------------------------------------------------------------- #


def _append_three(chain: AuditChain) -> None:
    for i in range(3):
        chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="zeus",
            payload={"i": i},
        )


def test_deployer_keyed_clean_chain_verifies_true(tmp_path: Path) -> None:
    """A freshly-built, untampered deployer-keyed chain must verify True."""
    chain = AuditChain(
        log_file=tmp_path / "hardened.jsonl",
        deployer_id="acme-bank-prod",
        chain_creation_iso="2026-01-01T00:00:00+00:00",
    )
    _append_three(chain)
    assert chain.verify() is True
    # verify_strict must NOT raise on a clean hardened chain.
    chain.verify_strict()


def test_legacy_chain_still_verifies_true(tmp_path: Path) -> None:
    """A legacy (no deployer_id) chain still verifies True — no regression."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        chain = AuditChain(log_file=tmp_path / "legacy.jsonl")
        _append_three(chain)
        assert chain.verify() is True
        chain.verify_strict()


def test_deployer_keyed_chain_reopened_in_legacy_mode_verifies(tmp_path: Path) -> None:
    """Re-opening a hardened chain WITHOUT passing deployer_id still verifies.

    The verifier must re-derive the seed from the on-disk genesis payload,
    not from a constructor-supplied deployer_id (which a reload omits).
    """
    log = tmp_path / "reopen.jsonl"
    first = AuditChain(
        log_file=log,
        deployer_id="acme-bank-prod",
        chain_creation_iso="2026-01-01T00:00:00+00:00",
    )
    _append_three(first)
    # Re-open with the v1.x signature (no deployer_id) — loads event #0.
    reopened = AuditChain(log_file=log)
    assert reopened.verify() is True
    reopened.verify_strict()


def test_deployer_keyed_chain_inplace_tamper_still_detected(tmp_path: Path) -> None:
    """The fix must not weaken tamper detection on a hardened chain."""
    chain = AuditChain(
        log_file=tmp_path / "tamper.jsonl",
        deployer_id="acme-bank-prod",
        chain_creation_iso="2026-01-01T00:00:00+00:00",
    )
    _append_three(chain)
    # Mutate a middle event's payload in place.
    object.__setattr__(chain._events[2], "payload", {"i": 999})
    assert chain.verify() is False
