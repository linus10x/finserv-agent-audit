"""Tests for the external-witness anchoring pattern (ADR-0014).

Covers RekorWitness, OpenTimestampsWitness, and the `anchor_to_witness()`
helper that writes the receipt back to the `AuditChain` as a
`WITNESS_ANCHOR` event.

Network tests against the real Rekor / OTS public-good instances are
marked with `@pytest.mark.network` and default-skipped via a stub HTTP
transport built on `http.server` — no external calls in CI.
"""

from __future__ import annotations

import dataclasses
import json
import os
import threading
from collections.abc import Iterator
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from finserv_agent_audit.governance.witness_anchor import (
    OpenTimestampsWitness,
    RekorWitness,
    WitnessReceipt,
    anchor_to_witness,
)
from finserv_agent_audit.schemas.audit_event import (
    AuditChain,
    AuditEventType,
    AutonomyLevel,
)

# ---------------------------------------------------------------------------
# Stub Rekor server (loopback) — keeps tests offline
# ---------------------------------------------------------------------------


class _MockRekorHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        body = json.dumps(
            {
                "uuid": "deadbeef" * 8,
                "logIndex": 12345,
                "integratedTime": int(datetime.now(UTC).timestamp()),
            }
        ).encode("utf-8")
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:  # noqa: ARG002
        pass


@pytest.fixture
def mock_rekor() -> Iterator[str]:
    server = HTTPServer(("127.0.0.1", 0), _MockRekorHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def tmp_chain(tmp_path: Path) -> AuditChain:
    """Fresh AuditChain backed by a per-test tmp log file."""
    return AuditChain(log_file=tmp_path / "audit_chain.jsonl")


# ---------------------------------------------------------------------------
# RekorWitness
# ---------------------------------------------------------------------------


def test_rekor_witness_returns_receipt(mock_rekor: str) -> None:
    w = RekorWitness(rekor_url=mock_rekor)
    receipt = w.anchor("a" * 64)
    assert isinstance(receipt, WitnessReceipt)
    assert receipt.register_name == "rekor"
    assert receipt.register_url == mock_rekor
    assert receipt.log_index == 12345
    assert receipt.inclusion_uuid == "deadbeef" * 8
    assert b"logIndex" in receipt.receipt_blob


def test_rekor_witness_rejects_wrong_head_length() -> None:
    w = RekorWitness(rekor_url="http://localhost:1")
    with pytest.raises(ValueError, match="64 chars"):
        w.anchor("too-short")


def test_rekor_witness_rejects_unsupported_scheme() -> None:
    w = RekorWitness(rekor_url="ftp://example.invalid")
    with pytest.raises(ValueError, match="unsupported scheme"):
        w.anchor("c" * 64)


# ---------------------------------------------------------------------------
# anchor_to_witness() helper
# ---------------------------------------------------------------------------


def test_anchor_to_witness_appends_audit_event(mock_rekor: str, tmp_chain: AuditChain) -> None:
    # Seed the chain with a non-witness event so the head is non-genesis.
    tmp_chain.append(
        event_type=AuditEventType.DECISION_MADE,
        autonomy_level=AutonomyLevel.A2,
        agent_id="zeus",
        payload={"action": "enter_position", "ticker": "SPY"},
    )
    head_before = tmp_chain._prev_hash  # noqa: SLF001

    anchor_event = anchor_to_witness(
        audit_chain=tmp_chain,
        witness=RekorWitness(rekor_url=mock_rekor),
    )

    assert anchor_event.event_type == AuditEventType.WITNESS_ANCHOR
    assert anchor_event.autonomy_level == AutonomyLevel.A4
    assert anchor_event.agent_id == "system:witness_anchor"
    assert anchor_event.payload["witness_register"] == "rekor"
    assert anchor_event.payload["witness_url"] == mock_rekor
    assert anchor_event.payload["chain_head_anchored"] == head_before
    assert anchor_event.payload["log_index"] == 12345
    assert anchor_event.payload["inclusion_uuid"] == "deadbeef" * 8
    assert "receipt_blob_hex" in anchor_event.payload
    # receipt_blob_hex is the hex of the JSON server response
    decoded = bytes.fromhex(anchor_event.payload["receipt_blob_hex"])
    assert b"logIndex" in decoded

    # Anchor entry is wired into the chain head
    assert anchor_event.prev_hash == head_before
    assert tmp_chain._prev_hash == anchor_event.event_hash  # noqa: SLF001
    assert tmp_chain.verify() is True


def test_anchor_to_witness_anchors_genesis_on_empty_chain(
    mock_rekor: str, tmp_chain: AuditChain
) -> None:
    anchor_event = anchor_to_witness(
        audit_chain=tmp_chain,
        witness=RekorWitness(rekor_url=mock_rekor),
    )
    assert anchor_event.payload["chain_head_anchored"] == AuditChain.GENESIS_HASH
    assert anchor_event.prev_hash == AuditChain.GENESIS_HASH
    assert tmp_chain.verify() is True


def test_anchor_to_witness_overrides_actor_and_autonomy(
    mock_rekor: str, tmp_chain: AuditChain
) -> None:
    anchor_event = anchor_to_witness(
        audit_chain=tmp_chain,
        witness=RekorWitness(rekor_url=mock_rekor),
        agent_id="ops:nightly-anchor",
        autonomy_level=AutonomyLevel.A2,
        actor_id="alice@finserv.example",
    )
    assert anchor_event.agent_id == "ops:nightly-anchor"
    assert anchor_event.autonomy_level == AutonomyLevel.A2
    assert anchor_event.actor_id == "alice@finserv.example"


def test_anchor_to_witness_persists_to_jsonl(
    mock_rekor: str, tmp_chain: AuditChain, tmp_path: Path
) -> None:
    anchor_to_witness(
        audit_chain=tmp_chain,
        witness=RekorWitness(rekor_url=mock_rekor),
    )
    lines = (tmp_path / "audit_chain.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event_type"] == AuditEventType.WITNESS_ANCHOR.value
    assert record["payload"]["witness_register"] == "rekor"


# ---------------------------------------------------------------------------
# Receipt invariants
# ---------------------------------------------------------------------------


def test_witness_receipt_is_frozen() -> None:
    r = WitnessReceipt(
        register_name="rekor",
        register_url="http://x",
        submitted_at=datetime.now(UTC),
        receipt_blob=b"",
        inclusion_uuid=None,
        log_index=None,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.register_name = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# OpenTimestampsWitness — offline failure path
# ---------------------------------------------------------------------------


def test_ots_witness_raises_when_all_calendars_unreachable() -> None:
    w = OpenTimestampsWitness(
        calendar_urls=("https://invalid.example.test.invalid./",),
        timeout_s=0.5,
    )
    with pytest.raises(RuntimeError, match="all OTS calendars failed"):
        w.anchor("b" * 64)


# ---------------------------------------------------------------------------
# Network-gated smoke test against the real public-good Rekor instance.
# Default-skipped. Opt in by setting FINSERV_AUDIT_NETWORK_TESTS=1 (a
# self-contained gate that avoids adding pytest markers to pyproject.toml).
# Also tagged with `@pytest.mark.network` for callers using `pytest -m`.
# ---------------------------------------------------------------------------


_NETWORK_TESTS_ENABLED = os.environ.get("FINSERV_AUDIT_NETWORK_TESTS") == "1"


@pytest.mark.network
@pytest.mark.skipif(
    not _NETWORK_TESTS_ENABLED,
    reason="Network test; set FINSERV_AUDIT_NETWORK_TESTS=1 to run.",
)
def test_rekor_witness_against_public_rekor() -> None:  # pragma: no cover
    w = RekorWitness()
    receipt = w.anchor("c" * 64)
    assert receipt.register_name == "rekor"
    assert receipt.log_index is not None
