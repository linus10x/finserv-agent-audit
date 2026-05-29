"""CR-2 — Replay paths MUST recompute the hash and reject tampered lines.

Previously, ``AuditChain._load_existing`` (and the JSONL / WORM
``LedgerStore`` decoders) reconstructed the event then overwrote the
freshly-computed ``event_hash`` with the value stored on disk. An
attacker who edited a JSONL line could leave the chain replay
consistent with itself — the hash matched the tampered fields because
both came from the same tampered line.

The fix: ``AuditEvent.from_jsonl`` recomputes the hash from the
reconstructed fields and raises ``AuditChainTamperError`` when the
recomputed hash disagrees with the stored one. The chain is now
self-verifying on load, not just on explicit ``verify()`` /
``verify_strict()``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from finserv_agent_audit.governance.audit_chain import (
    AuditChain,
    AuditChainTamperError,
)
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)


def _write_one_event(log_file: Path) -> dict[str, object]:
    """Append a real chain entry so the on-disk format is canonical."""
    chain = AuditChain(log_file=log_file)
    chain.append(
        event_type=AuditEventType.DECISION_MADE,
        autonomy_level=AutonomyLevel.A2,
        agent_id="zeus",
        payload={"action": "buy", "ticker": "SPY"},
    )
    raw = log_file.read_text(encoding="utf-8").strip()
    return dict(json.loads(raw))


class TestFromJsonlSelfVerification:
    """``AuditEvent.from_jsonl`` recomputes and raises on mismatch."""

    def test_from_jsonl_roundtrips_clean_event(self) -> None:
        original = AuditEvent.create(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="zeus",
            payload={"action": "buy"},
            prev_hash="0" * 64,
        )
        rebuilt = AuditEvent.from_jsonl(original.to_dict())
        assert rebuilt.event_hash == original.event_hash
        assert rebuilt.event_id == original.event_id

    def test_from_jsonl_raises_on_event_hash_mismatch(self) -> None:
        original = AuditEvent.create(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="zeus",
            payload={"action": "buy"},
            prev_hash="0" * 64,
        )
        tampered = original.to_dict()
        tampered["event_hash"] = "f" * 64
        with pytest.raises(AuditChainTamperError):
            AuditEvent.from_jsonl(tampered)

    def test_from_jsonl_raises_when_payload_was_rewritten(self) -> None:
        """An attacker rewrote a field but forgot to recompute the hash."""
        original = AuditEvent.create(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="zeus",
            payload={"action": "buy", "amount": 100},
            prev_hash="0" * 64,
        )
        tampered = original.to_dict()
        # Adversary rewrites the amount but leaves the stored hash alone.
        tampered["payload"] = {"action": "buy", "amount": 1_000_000}
        with pytest.raises(AuditChainTamperError):
            AuditEvent.from_jsonl(tampered)


class TestChainLoadRejectsTampering:
    """``AuditChain._load_existing`` MUST raise on a tampered JSONL line."""

    def test_load_existing_clean_chain(self, tmp_path: Path) -> None:
        log_file = tmp_path / "audit.jsonl"
        _write_one_event(log_file)
        # Reload — no tampering, must construct without raising.
        c2 = AuditChain(log_file=log_file)
        assert len(c2._events) == 1

    def test_load_existing_raises_on_tampered_event_hash(
        self,
        tmp_path: Path,
    ) -> None:
        log_file = tmp_path / "audit.jsonl"
        record = _write_one_event(log_file)
        # Adversary edits the on-disk event_hash to a value that does
        # not match the line's other fields.
        record["event_hash"] = "f" * 64
        log_file.write_text(json.dumps(record, sort_keys=True) + "\n")

        with pytest.raises(AuditChainTamperError):
            AuditChain(log_file=log_file)

    def test_load_existing_raises_on_tampered_payload(
        self,
        tmp_path: Path,
    ) -> None:
        log_file = tmp_path / "audit.jsonl"
        record = _write_one_event(log_file)
        # Adversary rewrites the payload but leaves the stored hash.
        record["payload"] = {"action": "buy", "ticker": "QQQ"}
        log_file.write_text(json.dumps(record, sort_keys=True) + "\n")

        with pytest.raises(AuditChainTamperError):
            AuditChain(log_file=log_file)

    def test_load_existing_raises_on_tampered_agent_id(
        self,
        tmp_path: Path,
    ) -> None:
        log_file = tmp_path / "audit.jsonl"
        record = _write_one_event(log_file)
        record["agent_id"] = "spoofed-agent"
        log_file.write_text(json.dumps(record, sort_keys=True) + "\n")

        with pytest.raises(AuditChainTamperError):
            AuditChain(log_file=log_file)
