"""Command-line interface — verify / inspect a JSONL audit chain.

What this module does
---------------------
Provides ``finserv-audit`` (entry point) and ``python -m
finserv_agent_audit.cli`` (module form), used by the GitHub Actions
composite action ``linus10x/finserv-agent-audit-action@v1`` and by
operators investigating an audit chain on disk.

Three subcommands::

    verify          - load a JSONL chain; verify integrity; exit 1 on tamper
    info            - print chain length, head hash, event-type histogram
    witness-status  - count WITNESS_ANCHOR events in the last N entries

Dependency posture
------------------
Stdlib only — argparse, json, collections. Wires into the same
governance package the rest of the codebase uses; no new runtime deps.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

from finserv_agent_audit.governance.audit_chain import (
    AuditChain,
    AuditChainTamperError,
)
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)

EXIT_OK = 0
EXIT_TAMPERED = 1
EXIT_BAD_INPUT = 2


# --------------------------------------------------------------------------- #
# JSONL loader (does NOT mutate the file; load-only path for verify/info)     #
# --------------------------------------------------------------------------- #


def _iter_jsonl(path: Path) -> Iterator[AuditEvent]:
    """Yield ``AuditEvent`` rows from a JSONL audit-chain file."""
    text = path.read_text(encoding="utf-8")
    for line_no, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc

        event = AuditEvent(
            event_type=AuditEventType(data["event_type"]),
            autonomy_level=AutonomyLevel(data["autonomy_level"]),
            agent_id=data["agent_id"],
            payload=data["payload"],
            prev_hash=data["prev_hash"],
            event_id=data["event_id"],
            timestamp=data["timestamp"],
            actor_id=data.get("actor_id"),
            schema_version=data.get("schema_version", "1.0.0"),
        )
        event.event_hash = data["event_hash"]
        yield event


def _load_chain(jsonl_path: Path) -> AuditChain:
    """Materialize a full ``AuditChain`` from a JSONL file."""
    if not jsonl_path.exists():
        raise FileNotFoundError(f"audit JSONL file not found: {jsonl_path}")

    from finserv_agent_audit.governance.ledger_store import InMemoryLedgerStore

    store = InMemoryLedgerStore()
    for event in _iter_jsonl(jsonl_path):
        store.append(event)

    return AuditChain(ledger_store=store)


# --------------------------------------------------------------------------- #
# Subcommand handlers                                                         #
# --------------------------------------------------------------------------- #


def _cmd_verify(args: argparse.Namespace) -> int:
    jsonl_path = Path(args.jsonl)
    try:
        chain = _load_chain(jsonl_path)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_BAD_INPUT

    mi_proxy = None
    if args.mi_proxy_key:
        from finserv_agent_audit.governance.mi_proxy import (
            MIN_KEY_BYTES,
            LocalMIProxy,
            _decode_key,
        )

        raw = args.mi_proxy_key.strip()
        # Accept either a base64/hex-encoded key (matching ``LocalMIProxy.from_env``)
        # or a raw ASCII secret >= MIN_KEY_BYTES.
        try:
            key = _decode_key(raw)
        except ValueError:
            key_bytes = raw.encode("utf-8")
            if len(key_bytes) < MIN_KEY_BYTES:
                print(
                    f"error: --mi-proxy-key must decode to >= {MIN_KEY_BYTES} bytes",
                    file=sys.stderr,
                )
                return EXIT_BAD_INPUT
            key = key_bytes
        mi_proxy = LocalMIProxy(signing_key=key)

    try:
        chain.verify_strict(mi_proxy=mi_proxy)
    except AuditChainTamperError as exc:
        print(f"TAMPERED: {exc}", file=sys.stderr)
        return EXIT_TAMPERED
    except Exception as exc:  # noqa: BLE001 — surface any verifier-side failure
        print(f"VERIFY FAILED: {exc}", file=sys.stderr)
        return EXIT_TAMPERED

    print(f"OK: chain verified ({len(chain._events)} events)")  # noqa: SLF001
    print(f"head: {chain.chain_head()}")
    return EXIT_OK


def _cmd_info(args: argparse.Namespace) -> int:
    jsonl_path = Path(args.jsonl)
    try:
        chain = _load_chain(jsonl_path)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_BAD_INPUT

    events = list(chain._events)  # noqa: SLF001
    histogram: Counter[str] = Counter(e.event_type.value for e in events)

    print(f"file:   {jsonl_path}")
    print(f"length: {len(events)}")
    print(f"head:   {chain.chain_head()}")
    print("event_type histogram:")
    for event_type, count in sorted(histogram.items()):
        print(f"  {count:6d}  {event_type}")
    return EXIT_OK


def _cmd_witness_status(args: argparse.Namespace) -> int:
    jsonl_path = Path(args.jsonl)
    last_n = int(args.last_n)
    if last_n <= 0:
        print(f"error: --last-n must be positive (got {last_n})", file=sys.stderr)
        return EXIT_BAD_INPUT

    try:
        chain = _load_chain(jsonl_path)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_BAD_INPUT

    events = list(chain._events)  # noqa: SLF001
    tail = events[-last_n:] if len(events) >= last_n else events
    witness_count = sum(1 for e in tail if e.event_type is AuditEventType.WITNESS_ANCHOR)

    print(f"window:        last {len(tail)} of {len(events)} events")
    print(f"WITNESS_ANCHOR entries: {witness_count}")
    if args.expect_witness_anchor and witness_count == 0:
        print(
            "FAIL: expected at least one WITNESS_ANCHOR in the window; found 0",
            file=sys.stderr,
        )
        return EXIT_TAMPERED
    return EXIT_OK


# --------------------------------------------------------------------------- #
# argparse plumbing                                                           #
# --------------------------------------------------------------------------- #


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="finserv-audit",
        description=(
            "Verify and inspect a JSONL audit chain produced by "
            "finserv_agent_audit. Used standalone or as the verification "
            "step of the linus10x/finserv-agent-audit-action GitHub Action."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_verify = sub.add_parser("verify", help="verify chain integrity")
    p_verify.add_argument("--jsonl", required=True, help="path to the JSONL audit-chain file")
    p_verify.add_argument(
        "--mi-proxy-key",
        default=None,
        help="optional HMAC signing key for MI Proxy verifier attestation (ADR-0015)",
    )
    p_verify.set_defaults(func=_cmd_verify)

    p_info = sub.add_parser("info", help="show chain length, head hash, event histogram")
    p_info.add_argument("--jsonl", required=True, help="path to the JSONL audit-chain file")
    p_info.set_defaults(func=_cmd_info)

    p_witness = sub.add_parser(
        "witness-status",
        help="count WITNESS_ANCHOR events in the last N entries",
    )
    p_witness.add_argument("--jsonl", required=True, help="path to the JSONL audit-chain file")
    p_witness.add_argument(
        "--last-n",
        type=int,
        default=100,
        help="window size (default: 100)",
    )
    p_witness.add_argument(
        "--expect-witness-anchor",
        action="store_true",
        help="exit nonzero if no WITNESS_ANCHOR entries are present in the window",
    )
    p_witness.set_defaults(func=_cmd_witness_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    rc: int = args.func(args)
    return rc


if __name__ == "__main__":
    sys.exit(main())


__all__ = ["main"]
