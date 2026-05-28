"""FastAPI governance endpoint — OpenAPI 3.1 + SSE streaming chain verification.

What this module does
---------------------
Exposes the framework's governance surface (audit chain, sovereign veto,
model inventory, vendor-score gate) as a first-party HTTP API built on
FastAPI 0.136+. FastAPI is the default choice for the v2.0 governance
API surface because:

* It auto-generates an **OpenAPI 3.1** specification at ``/openapi.json``
  + a Swagger UI at ``/docs``. FSI procurement teams ask for an OpenAPI
  spec before they will adopt a vendor-mediated AI control plane; the
  spec is the contract the procurement scan keys off.
* It ships **Server-Sent Events** (SSE) cleanly via Starlette's
  ``StreamingResponse``, which lets the chain-verification endpoint
  stream per-event progress to a long-poll dashboard rather than
  blocking for minutes on a multi-million-entry chain.
* The async surface composes with the audit chain's I/O-bound work
  (RFC 3161 timestamp fetches, witness register POSTs) without
  monkey-patching the synchronous chain layer.

Endpoint surface
----------------

GET  /healthz                              — liveness probe
GET  /info                                 — package + module versions
GET  /audit-chain/info                     — length, head, event-type histogram
GET  /audit-chain/verify                   — JSON {intact: bool, last_tampered}
GET  /audit-chain/verify-stream            — SSE stream of verification progress
POST /audit-chain/append                   — append (auth required)
GET  /model-inventory                      — list models + implementation_status
GET  /sovereign-veto/status                — active vetos
POST /sovereign-veto/trigger               — trigger a veto (auth required)
POST /sovereign-veto/clear                 — clear a veto with reason (auth required)
GET  /vendor-score-gate/recent-drift       — recent drift entries
GET  /openapi.json                         — auto-generated OpenAPI 3.1 spec
GET  /docs                                 — Swagger UI

Dependency posture
------------------
``fastapi`` + ``uvicorn[standard]`` + ``httpx`` are OPTIONAL. They are
import-guarded behind ``HAS_FASTAPI`` so the parent package keeps the
zero-runtime-dependency contract (ADR D2.2). To enable::

    pip install finserv-agent-audit[api]

If ``HAS_FASTAPI`` is False, calling ``create_app`` raises a
``RuntimeError`` carrying the install hint — the integration surface
is opt-in, not silently no-op, because the absence of the API is a
governance-architecture signal the operator should not paper over.

Auth posture
------------
The mutating endpoints (``POST /audit-chain/append``, ``POST
/sovereign-veto/trigger``, ``POST /sovereign-veto/clear``) are gated
by a pluggable ``AuthChecker`` callable. The shipped default rejects
every mutating call — the operator MUST supply an ``AuthChecker`` that
binds to the deployer's identity infrastructure (OIDC, mTLS,
in-cluster service account) before any mutating call lands. The
docstring is explicit: this module does not ship a default auth
layer because there is no single right answer for FSI deployers and
shipping a permissive default would be a foot-gun.

See ADR-0032 for the FastAPI / OpenAPI 3.1 / SSE decision and the
procurement-team OpenAPI preference.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable
from typing import TYPE_CHECKING, Any

from finserv_agent_audit import __version__ as _package_version
from finserv_agent_audit.schemas.audit_event import (
    AuditEventType,
    AutonomyLevel,
)

PACKAGE_VERSION = _package_version
"""Snapshot of the installed package version (exposed via /info)."""

if TYPE_CHECKING:
    from finserv_agent_audit.governance.audit_chain import AuditChain
    from finserv_agent_audit.governance.model_inventory import ModelInventory
    from finserv_agent_audit.governance.sovereign_veto import SovereignVeto
    from finserv_agent_audit.governance.vendor_score_gate import VendorScoreGate

try:
    from fastapi import Body, Depends, FastAPI, HTTPException, Request, status
    from fastapi.responses import JSONResponse, StreamingResponse

    HAS_FASTAPI = True
except ImportError:  # pragma: no cover — covered by the no-fastapi test path
    HAS_FASTAPI = False
    # When FastAPI is not installed every shim is set to ``Any`` so the
    # type system stays consistent across the optional-dependency
    # boundary; create_app raises before any shim is invoked.
    Body = Any  # type: ignore[assignment]
    FastAPI = Any  # type: ignore[assignment,misc]
    Depends = Any  # type: ignore[assignment]
    HTTPException = Any  # type: ignore[assignment,misc]
    Request = Any  # type: ignore[assignment,misc]
    JSONResponse = Any  # type: ignore[assignment,misc]
    StreamingResponse = Any  # type: ignore[assignment,misc]
    status = Any  # type: ignore[assignment]


INSTALL_HINT = (
    "FastAPI is not installed; install the optional API extra to enable "
    "the governance API: pip install finserv-agent-audit[api]"
)

# Module-level singleton holding the FastAPI ``Body(...)`` sentinel. Lifted
# out of route function defaults so ruff's B008 (function-call-in-defaults)
# stays clean; FastAPI resolves the singleton by identity so the behavior
# is unchanged.
if HAS_FASTAPI:
    _BODY_DEFAULT: Any = Body(...)
else:  # pragma: no cover — exercised only when fastapi is not installed
    _BODY_DEFAULT = None


# --------------------------------------------------------------------------- #
# Auth checker contract                                                       #
# --------------------------------------------------------------------------- #


AuthChecker = Callable[..., None]
"""Callable that raises HTTPException on auth failure, returns None on success.

The callable receives the FastAPI ``Request`` as its sole positional
argument (typed as ``fastapi.Request`` so FastAPI's dependency
resolver wires it correctly). The operator binds the checker to their
identity infrastructure (OIDC bearer-token validation, mTLS subject
lookup, internal service-account check). The shipped default
``_reject_all_auth`` rejects every mutating call — the operator must
supply a real checker before any mutating endpoint lands.
"""


def _reject_all_auth(request: Request) -> None:
    """Default ``AuthChecker`` — rejects every mutating request.

    Operators MUST replace this with a real auth checker. The default
    rejects rather than allows because the absence of an auth layer is
    a deploy-time error, not a runtime convenience.

    The ``request`` parameter is typed ``fastapi.Request`` (rebound to
    ``Any`` when FastAPI is not installed) so the FastAPI dependency
    resolver wires the Request through rather than treating the
    parameter as a query string field.
    """
    _ = request
    if not HAS_FASTAPI:  # pragma: no cover — guarded by create_app
        raise RuntimeError(INSTALL_HINT)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=(
            "No AuthChecker configured. Mutating governance endpoints "
            "require an operator-supplied AuthChecker bound to the "
            "deployer's identity infrastructure. See ADR-0032 § Auth."
        ),
    )


# --------------------------------------------------------------------------- #
# Factory                                                                     #
# --------------------------------------------------------------------------- #


def create_app(
    audit_chain: AuditChain,
    model_inventory: ModelInventory | None = None,
    sovereign_veto: SovereignVeto | None = None,
    vendor_score_gate: VendorScoreGate | None = None,
    *,
    auth_checker: AuthChecker | None = None,
    title: str = "finserv-agent-audit governance API",
    sse_chunk_size: int = 1000,
) -> Any:
    """Build and return a FastAPI app exposing the governance surface.

    The factory accepts every governance Protocol seam the framework
    ships; passing ``None`` for an optional seam causes the matching
    endpoints to return 503 with a clear "not configured" payload.
    That keeps the API contract stable across deploys that wire
    different subsets of the framework.

    The ``auth_checker`` argument defaults to the shipped reject-all
    placeholder. Mutating endpoints will return 401 until the operator
    supplies a real auth checker.

    The ``sse_chunk_size`` controls how often the verify-stream endpoint
    emits a progress event. The default (1000 events per emitted SSE
    chunk) keeps the streamed response light for million-entry chains
    while letting a dashboard render an incremental progress bar.
    """
    if not HAS_FASTAPI:
        raise RuntimeError(INSTALL_HINT)

    checker = auth_checker or _reject_all_auth

    app = FastAPI(
        title=title,
        version=PACKAGE_VERSION,
        description=(
            "Governance API for finserv-agent-audit — OpenAPI 3.1 + SSE "
            "streaming chain verification. See ADR-0032."
        ),
        openapi_version="3.1.0",
    )

    # ---------------- health + info ----------------

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        """Liveness probe — always returns 200 OK with a static payload."""
        return {"status": "ok"}

    @app.get("/info")
    def info() -> dict[str, Any]:
        """Package + module versions for procurement-time disclosure."""
        return {
            "package": "finserv-agent-audit",
            "package_version": PACKAGE_VERSION,
            "api_module": "finserv_agent_audit.integrations.governance_api",
            "modules_wired": {
                "audit_chain": True,
                "model_inventory": model_inventory is not None,
                "sovereign_veto": sovereign_veto is not None,
                "vendor_score_gate": vendor_score_gate is not None,
            },
        }

    # ---------------- audit chain ----------------

    @app.get("/audit-chain/info")
    def audit_chain_info() -> dict[str, Any]:
        """Current chain length, head hash, and event-type histogram."""
        histogram: dict[str, int] = {}
        length = 0
        for event in audit_chain._events:  # noqa: SLF001
            length += 1
            key = event.event_type.value
            histogram[key] = histogram.get(key, 0) + 1
        return {
            "length": length,
            "head_event_hash": audit_chain.chain_head(),
            "event_type_histogram": histogram,
        }

    @app.get("/audit-chain/verify")
    def audit_chain_verify() -> dict[str, Any]:
        """Replay the chain and report whether it verifies.

        Returns ``{intact: bool, last_tampered: int | None}``. The
        ``last_tampered`` field is the 0-based sequence of the first
        tampered entry, or ``None`` when the chain verifies.
        """
        prev = "0" * 64
        last_tampered: int | None = None
        for index, event in enumerate(audit_chain._events):  # noqa: SLF001
            expected = event._compute_hash()  # noqa: SLF001
            if event.event_hash != expected or event.prev_hash != prev:
                last_tampered = index
                break
            prev = event.event_hash
        return {"intact": last_tampered is None, "last_tampered": last_tampered}

    @app.get("/audit-chain/verify-stream")
    def audit_chain_verify_stream() -> Any:
        """SSE stream of chain-verification progress.

        Emits one ``progress`` event per ``sse_chunk_size`` entries and a
        terminal ``result`` event carrying the verify outcome. The SSE
        contract is the SSE wire format (``event:`` + ``data:`` + blank
        line), not WebSockets — chosen because it traverses corporate
        proxies cleanly under standard HTTP/1.1.
        """

        async def event_generator() -> AsyncIterator[bytes]:
            prev = "0" * 64
            last_tampered: int | None = None
            total = 0
            for index, event in enumerate(audit_chain._events):  # noqa: SLF001
                total = index + 1
                expected = event._compute_hash()  # noqa: SLF001
                if event.event_hash != expected or event.prev_hash != prev:
                    last_tampered = index
                    break
                prev = event.event_hash
                if (index + 1) % sse_chunk_size == 0:
                    payload = json.dumps({"verified_so_far": index + 1})
                    yield f"event: progress\ndata: {payload}\n\n".encode()
            payload = json.dumps(
                {
                    "intact": last_tampered is None,
                    "last_tampered": last_tampered,
                    "total_verified": total,
                }
            )
            yield f"event: result\ndata: {payload}\n\n".encode()

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    @app.post("/audit-chain/append", status_code=201)
    def audit_chain_append(
        body: dict[str, Any] = _BODY_DEFAULT,
        _: None = Depends(checker),
    ) -> dict[str, Any]:
        """Append a new event to the chain.

        Requires the configured ``AuthChecker``. The body schema:

        .. code-block:: json

            {
              "event_type": "governance.compliance_check",
              "autonomy_level": "A2",
              "agent_id": "external-caller",
              "payload": {...},
              "actor_id": "optional-human-actor"
            }
        """
        try:
            event_type = AuditEventType(body["event_type"])
            autonomy_level = AutonomyLevel(body["autonomy_level"])
            agent_id = str(body["agent_id"])
            payload = body.get("payload") or {}
            actor_id = body.get("actor_id")
        except (KeyError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"invalid body: {exc}",
            ) from exc
        event = audit_chain.append(
            event_type=event_type,
            autonomy_level=autonomy_level,
            agent_id=agent_id,
            payload=payload,
            actor_id=actor_id,
        )
        return {
            "event_id": event.event_id,
            "event_hash": event.event_hash,
            "prev_hash": event.prev_hash,
        }

    # ---------------- model inventory ----------------

    @app.get("/model-inventory")
    def model_inventory_list() -> Any:
        """List inventoried models with implementation status."""
        if model_inventory is None:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "ModelInventory not wired"},
            )
        models = []
        for model in model_inventory.all():
            models.append(
                {
                    "id": model.id,
                    "version": model.version,
                    "owner": model.owner,
                    "validator": model.validator,
                    "implementation_status": model.implementation_status.value,
                    "validation_date": (
                        model.validation_date.isoformat()
                        if model.validation_date is not None
                        else None
                    ),
                    "next_validation_due": model.next_validation_due.isoformat(),
                }
            )
        return {"models": models, "count": len(models)}

    # ---------------- sovereign veto ----------------

    @app.get("/sovereign-veto/status")
    def sovereign_veto_status() -> Any:
        """Active veto records + total veto history count."""
        if sovereign_veto is None:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "SovereignVeto not wired"},
            )
        active = [_serialize_veto(v) for v in sovereign_veto.active_vetos()]
        return {
            "is_vetoed": sovereign_veto.is_vetoed,
            "active_vetos": active,
            "active_count": len(active),
            "history_count": len(sovereign_veto.history()),
        }

    @app.post("/sovereign-veto/trigger", status_code=201)
    def sovereign_veto_trigger(
        body: dict[str, Any] = _BODY_DEFAULT,
        _: None = Depends(checker),
    ) -> Any:
        """Trigger a veto. Emits a chain entry recording the trigger."""
        if sovereign_veto is None:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "SovereignVeto not wired"},
            )
        from finserv_agent_audit.governance.sovereign_veto import VetoReason

        try:
            reason = VetoReason(body["reason"])
            triggered_by = str(body["triggered_by"])
            description = str(body["description"])
        except (KeyError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"invalid body: {exc}",
            ) from exc
        record = sovereign_veto.trigger(
            reason=reason,
            triggered_by=triggered_by,
            description=description,
        )
        # Emit an audit-chain entry so the API-triggered veto is hash-chained
        # alongside vetos triggered from inside the process.
        audit_chain.append(
            event_type=AuditEventType.VETO_APPLIED,
            autonomy_level=AutonomyLevel.A0,
            agent_id="api:sovereign_veto",
            payload={
                "veto_id": record.veto_id,
                "reason": record.reason.value,
                "triggered_by": record.triggered_by,
                "description": record.description,
                "source": "governance_api",
            },
            actor_id=triggered_by,
        )
        return _serialize_veto(record)

    @app.post("/sovereign-veto/clear")
    def sovereign_veto_clear(
        body: dict[str, Any] = _BODY_DEFAULT,
        _: None = Depends(checker),
    ) -> Any:
        """Clear active vetos with a documented reason.

        Body schema::

            {
              "operator_id": "human@bank.example",
              "reason": "Risk reviewed; drawdown within policy",
              "veto_id": "optional-specific-id"
            }

        ``reason`` is required and must be non-empty — the audit
        framework rejects empty clear reasons because the regulator
        cares why the veto was cleared more than that it was cleared.
        """
        if sovereign_veto is None:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "SovereignVeto not wired"},
            )
        operator_id = body.get("operator_id")
        reason = body.get("reason")
        veto_id = body.get("veto_id")
        if not operator_id or not isinstance(operator_id, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="operator_id is required",
            )
        if not reason or not isinstance(reason, str) or not reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="reason is required and must be non-empty",
            )
        cleared = sovereign_veto.clear(operator_id=operator_id, reason=reason, veto_id=veto_id)
        for record in cleared:
            audit_chain.append(
                event_type=AuditEventType.HUMAN_OVERRIDE,
                autonomy_level=AutonomyLevel.A0,
                agent_id="api:sovereign_veto",
                payload={
                    "veto_id": record.veto_id,
                    "clear_reason": reason,
                    "source": "governance_api",
                },
                actor_id=operator_id,
            )
        return {
            "cleared_count": len(cleared),
            "cleared_vetos": [_serialize_veto(r) for r in cleared],
        }

    # ---------------- vendor score gate ----------------

    @app.get("/vendor-score-gate/recent-drift")
    def vendor_score_gate_recent_drift(limit: int = 20) -> Any:
        """Recent vendor-score drift events.

        Walks the audit chain looking for ``VENDOR_SCORE_DRIFT_DETECTED``
        entries; returns the most recent ``limit`` of them. The drift
        events are themselves audit-chain entries — the gate writes them
        before raising — so this endpoint is a read-only convenience
        view, not an authoritative source.
        """
        if vendor_score_gate is None:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "VendorScoreGate not wired"},
            )
        out: list[dict[str, Any]] = []
        for event in audit_chain._events:  # noqa: SLF001
            if event.event_type != AuditEventType.VENDOR_SCORE_DRIFT_DETECTED:
                continue
            out.append(
                {
                    "event_id": event.event_id,
                    "timestamp": event.timestamp,
                    "vendor_id": event.payload.get("vendor_id"),
                    "vendor_class": event.payload.get("vendor_class"),
                    "input_hash": event.payload.get("input_hash"),
                    "score": event.payload.get("score"),
                    "previous_score": event.payload.get("previous_score"),
                    "model_version": event.payload.get("model_version"),
                }
            )
        if limit > 0:
            out = out[-limit:]
        return {"drift_events": out, "count": len(out)}

    return app


# --------------------------------------------------------------------------- #
# Module-private helpers                                                      #
# --------------------------------------------------------------------------- #


def _serialize_veto(record: Any) -> dict[str, Any]:
    """Stable JSON-shape for a ``VetoRecord``.

    Kept module-private so callers do not couple to the internal
    serialization — change here without touching every endpoint.
    """
    return {
        "veto_id": record.veto_id,
        "reason": record.reason.value,
        "triggered_by": record.triggered_by,
        "description": record.description,
        "timestamp": record.timestamp,
        "cleared_by": record.cleared_by,
        "cleared_at": record.cleared_at,
        "clear_reason": record.clear_reason,
        "is_active": record.is_active,
    }


__all__ = [
    "AuthChecker",
    "HAS_FASTAPI",
    "INSTALL_HINT",
    "create_app",
]
