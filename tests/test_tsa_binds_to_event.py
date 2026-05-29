"""CR-3 — ``TimestampSource.stamp()`` MUST receive the event's digest, not b"".

The v1.x ``AuditChain.append`` called ``self._timestamp_source.stamp(b"")``
— the TSA token, when one was issued (``RFC3161Source``), was signing
empty bytes. The signature attested only that the TSA's clock said
"now" at the moment of the request; it did not bind the resulting time
to any specific event. A regulator examining a chain could not
distinguish a TSR that was issued *for* the event from a TSR that was
copied from any other event in the chain.

The fix: compute a canonical pre-timestamp digest from the event's
identifying fields (event_id, event_type, autonomy_level, agent_id,
payload, actor_id, prev_hash, schema_version) and pass that digest
to ``stamp()``. The TSR's ``messageImprint`` field now binds the
TSA-asserted time to the specific event being timestamped — a TSR
copied from a different event will not re-verify against the new
event's pre-digest.

The TSR token (when present) is stashed in
``payload["_tsr_token_b64"]`` so a verifier can later re-check
``messageImprint == pre_digest`` of the event whose payload the
token lives in.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from finserv_agent_audit.governance.audit_chain import AuditChain
from finserv_agent_audit.governance.timestamp_source import TrustedTimestamp
from finserv_agent_audit.schemas.audit_event import (
    AuditEventType,
    AutonomyLevel,
)


class _SpyTimestampSource:
    """Records each ``stamp(digest)`` call so the test can assert on it."""

    def __init__(self) -> None:
        self.calls: list[bytes] = []
        # A deterministic TSR token so the test can re-derive the
        # token-in-payload binding without depending on time.
        self._token = b"spy-tsr-token-bytes"

    def stamp(self, payload_digest: bytes) -> TrustedTimestamp:
        # Record the digest the chain handed us so the test can
        # assert it is NOT empty and IS the canonical pre-digest of
        # the event.
        self.calls.append(payload_digest)
        return TrustedTimestamp(
            asserted_at=datetime(2026, 5, 28, 12, 0, 0, tzinfo=UTC),
            tsa_url="https://spy.example.com/tsr",
            tsr_token_b64="c3B5LXRzci10b2tlbi1ieXRlcw==",  # base64 of self._token
        )


def _canonical_pre_digest(
    *,
    event_id: str,
    event_type: AuditEventType,
    autonomy_level: AutonomyLevel,
    agent_id: str,
    payload: dict[str, object],
    actor_id: str | None,
    prev_hash: str,
    schema_version: str,
) -> bytes:
    """Mirror the canonicalization the chain uses, so the test is exact."""
    canonical = json.dumps(
        {
            "event_id": event_id,
            "event_type": event_type.value,
            "autonomy_level": autonomy_level.value,
            "agent_id": agent_id,
            "payload": payload,
            "actor_id": actor_id,
            "prev_hash": prev_hash,
            "schema_version": schema_version,
        },
        sort_keys=True,
    ).encode()
    return hashlib.sha256(canonical).digest()


class TestTsaBindsDigest:
    """The chain MUST pass a non-empty, event-bound digest to ``stamp``."""

    def test_stamp_receives_non_empty_digest(self, tmp_path: Path) -> None:
        spy = _SpyTimestampSource()
        chain = AuditChain(log_file=tmp_path / "audit.jsonl", timestamp_source=spy)
        chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="zeus",
            payload={"action": "buy", "ticker": "SPY"},
        )
        assert len(spy.calls) == 1
        digest = spy.calls[0]
        # The pre-CR-3 bug: ``stamp(b"")`` — the test guards against
        # any regression to that path.
        assert digest != b""
        # A SHA-256 digest is 32 bytes.
        assert len(digest) == 32

    def test_stamp_receives_canonical_event_pre_digest(self, tmp_path: Path) -> None:
        spy = _SpyTimestampSource()
        chain = AuditChain(log_file=tmp_path / "audit.jsonl", timestamp_source=spy)

        event = chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="zeus",
            payload={"action": "buy", "ticker": "SPY"},
        )

        # The digest passed to ``stamp`` must equal the canonical
        # pre-timestamp digest computed from the event's identifying
        # fields. ``payload`` here is the *user-supplied* payload (the
        # chain may add a ``_tsr_token_b64`` wrapper after the stamp,
        # but the pre-digest is computed BEFORE the timestamp call).
        expected = _canonical_pre_digest(
            event_id=event.event_id,
            event_type=event.event_type,
            autonomy_level=event.autonomy_level,
            agent_id=event.agent_id,
            # The stored payload has the TSR-token side-channel; the
            # pre-digest is computed from the user-supplied payload
            # alone.
            payload={"action": "buy", "ticker": "SPY"},
            actor_id=event.actor_id,
            prev_hash=event.prev_hash,
            schema_version=event.schema_version,
        )
        assert spy.calls[0] == expected

    def test_two_events_have_distinct_pre_digests(self, tmp_path: Path) -> None:
        """A TSR issued for event A must not re-verify against event B."""
        spy = _SpyTimestampSource()
        chain = AuditChain(log_file=tmp_path / "audit.jsonl", timestamp_source=spy)
        chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="zeus",
            payload={"action": "buy"},
        )
        chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="zeus",
            payload={"action": "sell"},
        )
        assert len(spy.calls) == 2
        assert spy.calls[0] != spy.calls[1]


class TestTsaTokenStoredInPayload:
    """When a TSR is present, the token MUST land in the event payload."""

    def test_tsr_token_b64_stashed_in_payload(self, tmp_path: Path) -> None:
        spy = _SpyTimestampSource()
        chain = AuditChain(log_file=tmp_path / "audit.jsonl", timestamp_source=spy)
        event = chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="zeus",
            payload={"action": "buy"},
        )
        # The token rides in the payload under the documented side-
        # channel key. A verifier re-derives the pre-digest from the
        # other payload fields and checks the TSR's messageImprint.
        assert "_tsr_token_b64" in event.payload
        assert event.payload["_tsr_token_b64"] == "c3B5LXRzci10b2tlbi1ieXRlcw=="

    def test_local_clock_does_not_inject_tsr_token(self, tmp_path: Path) -> None:
        """LocalClock returns ``tsr_token_b64=None``; no side-channel key."""
        # No spy — default LocalClock backs the chain.
        chain = AuditChain(log_file=tmp_path / "audit.jsonl")
        event = chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="zeus",
            payload={"action": "buy"},
        )
        assert "_tsr_token_b64" not in event.payload
