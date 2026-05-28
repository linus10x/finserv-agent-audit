"""Smoke tests for the ``finserv-audit`` CLI.

The CLI is exercised by the GitHub Actions composite action and by
operators on the command line; the v1.2 closeout tranche pulls it
under the 90% coverage gate via these tests. The tests construct a
real JSONL chain with the production ``AuditChain`` pipeline, then
drive the three subcommands (``verify``, ``info``, ``witness-status``)
through ``main``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from finserv_agent_audit.cli import main
from finserv_agent_audit.schemas.audit_event import (
    AuditChain,
    AuditEventType,
    AutonomyLevel,
)

# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #


@pytest.fixture
def populated_jsonl(tmp_path: Path) -> Path:
    """Build a real, integrity-clean JSONL chain on disk."""
    log_file = tmp_path / "audit.jsonl"
    chain = AuditChain(log_file=log_file)
    for i in range(3):
        chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id=f"agent_{i}",
            payload={"step": i},
        )
    return log_file


@pytest.fixture
def chain_with_witness(tmp_path: Path) -> Path:
    log_file = tmp_path / "audit_with_witness.jsonl"
    chain = AuditChain(log_file=log_file)
    chain.append(
        event_type=AuditEventType.DECISION_MADE,
        autonomy_level=AutonomyLevel.A2,
        agent_id="agent_a",
        payload={},
    )
    chain.append(
        event_type=AuditEventType.WITNESS_ANCHOR,
        autonomy_level=AutonomyLevel.A2,
        agent_id="anchor",
        payload={"witness": "rekor"},
    )
    return log_file


# --------------------------------------------------------------------------- #
# verify subcommand                                                           #
# --------------------------------------------------------------------------- #


class TestVerify:
    def test_verify_clean_chain_returns_zero(
        self, populated_jsonl: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        rc = main(["verify", "--jsonl", str(populated_jsonl)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "OK: chain verified" in captured.out

    def test_verify_missing_file_returns_bad_input(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        bogus = tmp_path / "does_not_exist.jsonl"
        rc = main(["verify", "--jsonl", str(bogus)])
        assert rc == 2
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_verify_tampered_chain_returns_tampered(
        self, populated_jsonl: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # Tamper: rewrite one event's agent_id but keep its event_hash
        # — chain verify will fail.
        lines = populated_jsonl.read_text(encoding="utf-8").splitlines()
        first = json.loads(lines[0])
        first["agent_id"] = "tampered_agent"
        lines[0] = json.dumps(first, sort_keys=True)
        populated_jsonl.write_text("\n".join(lines) + "\n", encoding="utf-8")

        rc = main(["verify", "--jsonl", str(populated_jsonl)])
        assert rc == 1
        captured = capsys.readouterr()
        # Either TAMPERED (AuditChainTamperError) or VERIFY FAILED
        # depending on which check fires first.
        assert "TAMPERED" in captured.err or "VERIFY FAILED" in captured.err

    def test_verify_short_mi_proxy_key_returns_bad_input(
        self, populated_jsonl: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        rc = main(
            [
                "verify",
                "--jsonl",
                str(populated_jsonl),
                "--mi-proxy-key",
                "too_short",
            ]
        )
        assert rc == 2
        assert "decode to >=" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# info subcommand                                                             #
# --------------------------------------------------------------------------- #


class TestInfo:
    def test_info_prints_length_and_histogram(
        self, populated_jsonl: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        rc = main(["info", "--jsonl", str(populated_jsonl)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "length: 3" in out
        assert "decision.made" in out

    def test_info_missing_file_returns_bad_input(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        bogus = tmp_path / "missing.jsonl"
        rc = main(["info", "--jsonl", str(bogus)])
        assert rc == 2
        assert "not found" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# witness-status subcommand                                                   #
# --------------------------------------------------------------------------- #


class TestWitnessStatus:
    def test_witness_status_counts_anchor_entries(
        self, chain_with_witness: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        rc = main(["witness-status", "--jsonl", str(chain_with_witness)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "WITNESS_ANCHOR entries: 1" in out

    def test_witness_status_zero_n_returns_bad_input(
        self, chain_with_witness: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        rc = main(["witness-status", "--jsonl", str(chain_with_witness), "--last-n", "0"])
        assert rc == 2
        assert "--last-n must be positive" in capsys.readouterr().err

    def test_witness_status_missing_file_returns_bad_input(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        bogus = tmp_path / "missing.jsonl"
        rc = main(["witness-status", "--jsonl", str(bogus)])
        assert rc == 2

    def test_witness_status_expect_anchor_fails_when_absent(
        self, populated_jsonl: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # populated_jsonl has no WITNESS_ANCHOR entries.
        rc = main(
            [
                "witness-status",
                "--jsonl",
                str(populated_jsonl),
                "--expect-witness-anchor",
            ]
        )
        assert rc == 1
        assert "expected at least one WITNESS_ANCHOR" in capsys.readouterr().err

    def test_witness_status_small_chain_within_window(
        self, chain_with_witness: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # last-n larger than the chain: window collapses to chain size.
        rc = main(["witness-status", "--jsonl", str(chain_with_witness), "--last-n", "999"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "window:" in out


# --------------------------------------------------------------------------- #
# Bad JSONL handling                                                          #
# --------------------------------------------------------------------------- #


class TestBadInput:
    def test_invalid_json_line_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.jsonl"
        bad.write_text("not-json\n", encoding="utf-8")
        # The CLI loader raises ValueError before the verify subcommand's
        # exception arm runs (the ValueError is not a recognized tamper
        # signal nor a FileNotFoundError). Propagation is the
        # expected v1.1 contract; v1.2 may catch this earlier.
        with pytest.raises(ValueError, match="invalid JSON"):
            main(["verify", "--jsonl", str(bad)])

    def test_blank_lines_in_jsonl_ignored(self, tmp_path: Path) -> None:
        # The loader treats blank lines as no-ops. A genesis-only file
        # with a stray blank trailing line should still load cleanly.
        log_file = tmp_path / "chain.jsonl"
        chain = AuditChain(log_file=log_file)
        chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="a",
            payload={},
        )
        # Append a blank line.
        with open(log_file, "a", encoding="utf-8") as fh:
            fh.write("\n")
        rc = main(["info", "--jsonl", str(log_file)])
        assert rc == 0
