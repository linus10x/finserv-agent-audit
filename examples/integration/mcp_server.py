"""Model Context Protocol (MCP) server adapter for the audit chain.

What this integration does
--------------------------
Exposes ``finserv_agent_audit`` governance primitives as MCP tools and
resources so any MCP client (Claude Desktop, Cursor, Continue, an
agentic IDE plugin) can audit-trail through this server. The MCP spec
became the de-facto agentic-AI interop standard in 2025; the protocol
governance was donated to the Linux Foundation in December 2025, and
the public MCP registry crossed 22,000+ servers by Q1 2026. Datadog and
Splunk shipped first-party MCP integrations in early 2026 — those
shape the production template this adapter follows.

Tools exposed
-------------
- ``audit_chain.append``      — append an event to the audit chain
- ``audit_chain.verify``      — verify chain integrity; reports the
                                 last clean sequence on tamper
- ``vendor_score_gate.record`` — record a vendor score; raises
                                  VendorScoreDriftDetected on drift
                                  against (vendor_id, input_hash,
                                  model_version)
- ``model_inventory.query``    — query the SR 11-7 model registry

Resources exposed
-----------------
- ``audit-chain://current/head``    — current chain head hash
- ``audit-chain://current/length``  — current chain length
- ``failure-modes://matrix``        — the FAILURE-MODES.md matrix
                                       (rendered from repo root)

What service it talks to
------------------------
An MCP client over stdio. Transport is the official MCP Python SDK
(``pip install mcp``). The SDK import is GUARDED; the parent package
keeps the zero-runtime-dependency contract.

Regulatory framework benefits
-----------------------------
- **SR 11-7** — every agent action taken via an MCP tool can be
  inventoried; ``model_inventory.query`` exposes the registry as a
  read resource for second-line / third-line review.
- **EU AI Act Article 12** — MCP-mediated agent calls are append-only
  audit-trailed at the protocol boundary, not at the model-call
  boundary, so the trail survives provider swaps.
- **FFIEC IT Handbook App J** — third-party model risk; every
  vendor-scoring tool call is captured through ``VendorScoreGate``
  with full provenance.
- **Anthropic supported-workloads carve-out** — Anthropic explicitly
  excludes FSI from supported Claude workloads. This adapter is the
  wedge that converts an unsupported-by-default MCP tool surface into
  an auditable one suitable for regulated deployment.

Reference
---------
- MCP specification 2025-11-25:
  https://spec.modelcontextprotocol.io/
- Linux Foundation Agentic AI Foundation governance (Dec 2025):
  https://www.linuxfoundation.org/press/
- MCP Python SDK:
  https://github.com/modelcontextprotocol/python-sdk

This is a REFERENCE integration. It is NOT imported by the package
surface and adds no runtime dependency to the wheel.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from finserv_agent_audit.governance.audit_chain import (
    AuditChain,
    AuditChainTamperError,
)
from finserv_agent_audit.governance.ledger_store import InMemoryLedgerStore
from finserv_agent_audit.governance.model_inventory import (
    ImplementationStatus,
    Model,
    ModelInventory,
    ModelNotFoundError,
)
from finserv_agent_audit.governance.vendor_score_gate import (
    InMemoryVendorScoreGate,
    VendorClass,
    VendorScoreDriftDetected,
)
from finserv_agent_audit.schemas.audit_event import AuditEventType, AutonomyLevel

try:
    from mcp.server import Server  # type: ignore[import-not-found]
    from mcp.types import Resource, TextContent, Tool  # type: ignore[import-not-found]

    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    Server = None  # type: ignore[assignment,misc]
    Tool = None  # type: ignore[assignment,misc]
    Resource = None  # type: ignore[assignment,misc]
    TextContent = None  # type: ignore[assignment,misc]


REPO_ROOT = Path(__file__).resolve().parents[2]
FAILURE_MODES_PATH = REPO_ROOT / "FAILURE-MODES.md"


# --------------------------------------------------------------------------- #
# State bundle — wired once at server construction, shared across handlers    #
# --------------------------------------------------------------------------- #


class FinservAuditState:
    """Per-server state: chain + vendor gate + model inventory."""

    def __init__(self) -> None:
        self.chain = AuditChain(ledger_store=InMemoryLedgerStore())
        self.vendor_gate = InMemoryVendorScoreGate(
            audit_chain=self.chain,
            raise_on_drift=True,
        )
        self.inventory = ModelInventory()


# --------------------------------------------------------------------------- #
# Tool implementations — pure-Python, MCP-independent                         #
# --------------------------------------------------------------------------- #


def _tool_audit_chain_append(state: FinservAuditState, arguments: dict[str, Any]) -> dict[str, Any]:
    event = state.chain.append(
        event_type=AuditEventType(arguments["event_type"]),
        autonomy_level=AutonomyLevel(arguments.get("autonomy_level", "A2")),
        agent_id=str(arguments["agent_id"]),
        payload=dict(arguments.get("payload", {})),
        actor_id=arguments.get("actor_id"),
    )
    return {
        "event_id": event.event_id,
        "event_hash": event.event_hash,
        "prev_hash": event.prev_hash,
        "sequence": len(state.chain._events) - 1,  # noqa: SLF001
    }


def _tool_audit_chain_verify(
    state: FinservAuditState, _arguments: dict[str, Any]
) -> dict[str, Any]:
    try:
        state.chain.verify_strict()
    except AuditChainTamperError as exc:
        # Walk the chain to find the last clean sequence so the operator
        # has a quarantine boundary.
        prev = state.chain.GENESIS_HASH
        last_clean = -1
        for index, event in enumerate(state.chain._events):  # noqa: SLF001
            expected = event._compute_hash()  # noqa: SLF001
            if event.event_hash != expected or event.prev_hash != prev:
                break
            prev = event.event_hash
            last_clean = index
        return {
            "verified": False,
            "error": str(exc),
            "last_clean_sequence": last_clean,
            "length": len(state.chain._events),  # noqa: SLF001
        }
    return {
        "verified": True,
        "length": len(state.chain._events),  # noqa: SLF001
        "head": state.chain.chain_head(),
    }


def _tool_vendor_score_gate_record(
    state: FinservAuditState, arguments: dict[str, Any]
) -> dict[str, Any]:
    try:
        entry = state.vendor_gate.emit(
            vendor_id=str(arguments["vendor_id"]),
            vendor_class=VendorClass(arguments["vendor_class"]),
            input_hash=str(arguments["input_hash"]),
            score=float(arguments["score"]),
            model_version=str(arguments["model_version"]),
        )
    except VendorScoreDriftDetected as exc:
        return {
            "recorded": True,
            "drift_detected": True,
            "error": str(exc),
        }
    return {
        "recorded": True,
        "drift_detected": entry.drift_detected,
        "sequence": entry.sequence,
        "event_id": entry.event_id,
    }


def _tool_model_inventory_query(
    state: FinservAuditState, arguments: dict[str, Any]
) -> dict[str, Any]:
    model_id = arguments.get("model_id")
    if model_id is not None:
        try:
            model: Model = state.inventory.get(str(model_id))
        except ModelNotFoundError:
            return {"found": False, "model_id": str(model_id)}
        return {
            "found": True,
            "model": _model_to_dict(model),
        }
    status_raw = arguments.get("status")
    if status_raw is not None:
        models = state.inventory.query_by_status(ImplementationStatus(status_raw))
        return {"count": len(models), "models": [_model_to_dict(m) for m in models]}
    # Default: full registry dump.
    return {
        "count": len(state.inventory),
        "models": [_model_to_dict(m) for m in state.inventory.all()],
    }


def _model_to_dict(model: Model) -> dict[str, Any]:
    return {
        "id": model.id,
        "version": model.version,
        "owner": model.owner,
        "validator": model.validator,
        "status": model.implementation_status.value,
        "validation_date": (
            model.validation_date.isoformat() if model.validation_date is not None else None
        ),
        "next_validation_due": model.next_validation_due.isoformat(),
    }


# --------------------------------------------------------------------------- #
# Resource readers — pure-Python, MCP-independent                             #
# --------------------------------------------------------------------------- #


def _resource_chain_head(state: FinservAuditState) -> str:
    return state.chain.chain_head()


def _resource_chain_length(state: FinservAuditState) -> str:
    return str(len(state.chain._events))  # noqa: SLF001


def _resource_failure_modes_matrix() -> str:
    if not FAILURE_MODES_PATH.exists():
        return "FAILURE-MODES.md not found at repo root."
    return FAILURE_MODES_PATH.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# MCP server wiring (only active when HAS_MCP)                                #
# --------------------------------------------------------------------------- #


def build_server(state: FinservAuditState | None = None) -> Any:
    """Construct an MCP ``Server`` with tools + resources registered.

    Raises ``RuntimeError`` when the MCP SDK is not installed; callers
    should gate on ``HAS_MCP`` first.
    """
    if not HAS_MCP:
        raise RuntimeError(
            "MCP SDK not installed; `pip install mcp` to enable. "
            "Reference patterns are documented in this module's docstring."
        )
    assert Server is not None and Tool is not None and Resource is not None  # noqa: S101

    server = Server("finserv-agent-audit")
    bound_state = state or FinservAuditState()

    @server.list_tools()  # type: ignore[misc, no-untyped-call]
    async def _list_tools() -> list[Any]:
        return [
            Tool(
                name="audit_chain.append",
                description="Append an event to the audit chain (hash-chained, append-only).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "event_type": {"type": "string"},
                        "autonomy_level": {"type": "string", "default": "A2"},
                        "agent_id": {"type": "string"},
                        "payload": {"type": "object"},
                        "actor_id": {"type": ["string", "null"]},
                    },
                    "required": ["event_type", "agent_id"],
                },
            ),
            Tool(
                name="audit_chain.verify",
                description=(
                    "Verify chain integrity. Returns the last clean sequence "
                    "on tamper so the operator has a quarantine boundary."
                ),
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="vendor_score_gate.record",
                description=(
                    "Record a vendor AI score with full provenance. Raises on "
                    "drift against (vendor_id, input_hash, model_version)."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "vendor_id": {"type": "string"},
                        "vendor_class": {"type": "string"},
                        "input_hash": {"type": "string"},
                        "score": {"type": "number"},
                        "model_version": {"type": "string"},
                    },
                    "required": [
                        "vendor_id",
                        "vendor_class",
                        "input_hash",
                        "score",
                        "model_version",
                    ],
                },
            ),
            Tool(
                name="model_inventory.query",
                description=(
                    "Query the SR 11-7 model registry. Provide model_id for a "
                    "single record, status for a filtered list, or neither for "
                    "a full dump."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "model_id": {"type": "string"},
                        "status": {"type": "string"},
                    },
                },
            ),
        ]

    @server.call_tool()  # type: ignore[misc, no-untyped-call]
    async def _call_tool(name: str, arguments: dict[str, Any]) -> list[Any]:
        import json

        if name == "audit_chain.append":
            result = _tool_audit_chain_append(bound_state, arguments)
        elif name == "audit_chain.verify":
            result = _tool_audit_chain_verify(bound_state, arguments)
        elif name == "vendor_score_gate.record":
            result = _tool_vendor_score_gate_record(bound_state, arguments)
        elif name == "model_inventory.query":
            result = _tool_model_inventory_query(bound_state, arguments)
        else:
            raise ValueError(f"unknown tool: {name!r}")
        return [TextContent(type="text", text=json.dumps(result, sort_keys=True))]

    @server.list_resources()  # type: ignore[misc, no-untyped-call]
    async def _list_resources() -> list[Any]:
        return [
            Resource(
                uri="audit-chain://current/head",
                name="Audit chain head",
                description="SHA-256 hash of the current chain head.",
                mimeType="text/plain",
            ),
            Resource(
                uri="audit-chain://current/length",
                name="Audit chain length",
                description="Number of events currently in the chain.",
                mimeType="text/plain",
            ),
            Resource(
                uri="failure-modes://matrix",
                name="FAILURE-MODES.md matrix",
                description=(
                    "The adversarial/partition/corruption matrix the package "
                    "ships against. Read at the repo root."
                ),
                mimeType="text/markdown",
            ),
        ]

    @server.read_resource()  # type: ignore[misc, no-untyped-call]
    async def _read_resource(uri: str) -> str:
        if uri == "audit-chain://current/head":
            return _resource_chain_head(bound_state)
        if uri == "audit-chain://current/length":
            return _resource_chain_length(bound_state)
        if uri == "failure-modes://matrix":
            return _resource_failure_modes_matrix()
        raise ValueError(f"unknown resource: {uri!r}")

    return server


# --------------------------------------------------------------------------- #
# Demo                                                                        #
# --------------------------------------------------------------------------- #


def _run_demo() -> None:
    """Print HAS_MCP status; start a stdio server when the SDK is present."""
    print(f"finserv-agent-audit MCP server: HAS_MCP={HAS_MCP}")
    if not HAS_MCP:
        print("  MCP SDK not installed; `pip install mcp` to enable.")
        print("  Reference implementation only — patterns documented in module docstring.")
        print("  Tool surface:")
        print("    - audit_chain.append")
        print("    - audit_chain.verify")
        print("    - vendor_score_gate.record")
        print("    - model_inventory.query")
        print("  Resource surface:")
        print("    - audit-chain://current/head")
        print("    - audit-chain://current/length")
        print("    - failure-modes://matrix")
        return

    print("  Constructing server bound to in-memory state.")
    server = build_server()
    print(f"  Server constructed: {server!r}")
    print("  To run over stdio, embed in an asyncio event loop with mcp.server.stdio.")


if __name__ == "__main__":
    _run_demo()
