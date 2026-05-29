"""CR-2 — ``AuditEvent`` MUST be a frozen dataclass.

The v2.0 docstring claimed the record was immutable; the v1.x impl
defined ``event_hash`` as ``field(init=False)`` and set it via
``__post_init__``, leaving the field freely re-assignable post-
construction. Audit-chain replay paths exploited that hole to "restore"
the on-disk stored hash, which masked tampering: an attacker who edited
the JSONL line could leave the chain replay consistent because the
re-loaded ``event_hash`` was simply overwritten with whatever the
tampered line claimed.

This test pins the contract — any attempt to mutate a constructed
``AuditEvent`` MUST raise ``FrozenInstanceError``. The on-disk replay
path now reconstructs the event via ``AuditEvent.from_jsonl``, which
recomputes the hash and raises ``AuditChainTamperError`` on mismatch
rather than silently overwriting the stored value.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)

GENESIS = "0" * 64


def _make_event() -> AuditEvent:
    return AuditEvent.create(
        event_type=AuditEventType.DECISION_MADE,
        autonomy_level=AutonomyLevel.A2,
        agent_id="test-agent",
        payload={"action": "buy", "ticker": "SPY"},
        prev_hash=GENESIS,
    )


class TestAuditEventFrozen:
    """Every dataclass field MUST be immutable after construction."""

    def test_event_hash_cannot_be_reassigned(self) -> None:
        event = _make_event()
        with pytest.raises(FrozenInstanceError):
            event.event_hash = "tampered" * 8  # type: ignore[misc]

    def test_event_id_cannot_be_reassigned(self) -> None:
        event = _make_event()
        with pytest.raises(FrozenInstanceError):
            event.event_id = "rewritten"  # type: ignore[misc]

    def test_timestamp_cannot_be_reassigned(self) -> None:
        event = _make_event()
        with pytest.raises(FrozenInstanceError):
            event.timestamp = "1970-01-01T00:00:00+00:00"  # type: ignore[misc]

    def test_prev_hash_cannot_be_reassigned(self) -> None:
        event = _make_event()
        with pytest.raises(FrozenInstanceError):
            event.prev_hash = "f" * 64  # type: ignore[misc]

    def test_agent_id_cannot_be_reassigned(self) -> None:
        event = _make_event()
        with pytest.raises(FrozenInstanceError):
            event.agent_id = "different-agent"  # type: ignore[misc]

    def test_actor_id_cannot_be_reassigned(self) -> None:
        event = _make_event()
        with pytest.raises(FrozenInstanceError):
            event.actor_id = "spoofed-actor"  # type: ignore[misc]

    def test_schema_version_cannot_be_reassigned(self) -> None:
        event = _make_event()
        with pytest.raises(FrozenInstanceError):
            event.schema_version = "9.9.9"  # type: ignore[misc]


class TestAuditEventCreateConvenience:
    """``AuditEvent.create`` is the construction classmethod for new events."""

    def test_create_returns_a_frozen_event(self) -> None:
        event = AuditEvent.create(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="zeus",
            payload={"k": "v"},
            prev_hash=GENESIS,
        )
        assert event.prev_hash == GENESIS
        # The hash is a 64-char hex string of SHA-256.
        assert len(event.event_hash) == 64
        with pytest.raises(FrozenInstanceError):
            event.event_hash = "x" * 64  # type: ignore[misc]

    def test_create_is_deterministic_for_same_fields(self) -> None:
        e1 = AuditEvent.create(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="zeus",
            payload={"k": "v"},
            prev_hash=GENESIS,
            event_id="11111111-1111-1111-1111-111111111111",
            timestamp="2026-05-22T00:00:00+00:00",
        )
        e2 = AuditEvent.create(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="zeus",
            payload={"k": "v"},
            prev_hash=GENESIS,
            event_id="11111111-1111-1111-1111-111111111111",
            timestamp="2026-05-22T00:00:00+00:00",
        )
        assert e1.event_hash == e2.event_hash
