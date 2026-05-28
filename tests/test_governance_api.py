"""Tests for the FastAPI governance API (v2.0 — ADR-0032).

The API ships behind an import guard (``HAS_FASTAPI``); the test module
gracefully no-ops every endpoint test when FastAPI is not installed and
still asserts the one contract that must hold without the optional
dependency: calling ``create_app`` without FastAPI installed raises a
``RuntimeError`` carrying the install hint.

When FastAPI IS installed (the v2.0 dev posture), every endpoint is
exercised through ``fastapi.testclient.TestClient``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from finserv_agent_audit.governance.audit_chain import AuditChain
from finserv_agent_audit.governance.ledger_store import InMemoryLedgerStore
from finserv_agent_audit.governance.model_inventory import ModelInventory
from finserv_agent_audit.governance.sovereign_veto import SovereignVeto, VetoReason
from finserv_agent_audit.governance.vendor_score_gate import (
    InMemoryVendorScoreGate,
)
from finserv_agent_audit.integrations import governance_api
from finserv_agent_audit.integrations.governance_api import (
    HAS_FASTAPI,
    INSTALL_HINT,
    create_app,
)
from finserv_agent_audit.schemas.audit_event import (
    AuditEventType,
    AutonomyLevel,
)

# --------------------------------------------------------------------------- #
# Import guard contract — must hold whether or not fastapi is installed       #
# --------------------------------------------------------------------------- #


def test_has_fastapi_is_boolean() -> None:
    """``HAS_FASTAPI`` must always be a deterministic boolean."""
    assert isinstance(HAS_FASTAPI, bool)


def test_install_hint_mentions_extra() -> None:
    """The install hint must mention the ``[api]`` extra."""
    assert "[api]" in INSTALL_HINT


@pytest.mark.skipif(HAS_FASTAPI, reason="FastAPI IS installed; covered elsewhere")
def test_create_app_without_fastapi_raises_runtime_error() -> None:
    """Without FastAPI installed, ``create_app`` must raise RuntimeError.

    The integration surface is opt-in, not silently no-op — the absence
    of the API is a governance-architecture signal the operator should
    not paper over.
    """
    chain = AuditChain(ledger_store=InMemoryLedgerStore())
    with pytest.raises(RuntimeError, match="finserv-agent-audit\\[api\\]"):
        create_app(audit_chain=chain)


# --------------------------------------------------------------------------- #
# All remaining tests require FastAPI                                         #
# --------------------------------------------------------------------------- #

pytestmark_fastapi = pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI not installed")


# --------------------------------------------------------------------------- #
# Test-app builder                                                            #
# --------------------------------------------------------------------------- #


def _build_app_and_chain(
    *,
    include_model_inventory: bool = True,
    include_veto: bool = True,
    include_vendor_gate: bool = True,
    auth_checker: Any = None,
) -> tuple[Any, AuditChain, SovereignVeto | None]:
    """Construct an app with a fresh in-memory chain + wired seams.

    Returns the FastAPI app, the underlying AuditChain, and the
    SovereignVeto (or None) so individual tests can assert against
    chain entries / veto state directly.
    """
    chain = AuditChain(ledger_store=InMemoryLedgerStore())
    inventory = ModelInventory() if include_model_inventory else None
    veto = SovereignVeto(agent_id="zeus") if include_veto else None
    gate = (
        InMemoryVendorScoreGate(audit_chain=chain, raise_on_drift=False)
        if include_vendor_gate
        else None
    )
    app = create_app(
        audit_chain=chain,
        model_inventory=inventory,
        sovereign_veto=veto,
        vendor_score_gate=gate,
        auth_checker=auth_checker,
    )
    return app, chain, veto


def _client(app: Any) -> Any:
    from fastapi.testclient import TestClient

    return TestClient(app)


if HAS_FASTAPI:
    from fastapi import Request as _FastAPIRequest

    def _allow_all_auth(request: _FastAPIRequest) -> None:
        """Test-only auth checker that allows every mutating call."""
        _ = request
        return None

else:  # pragma: no cover

    def _allow_all_auth(request: Any) -> None:
        return None


# --------------------------------------------------------------------------- #
# Endpoint tests                                                              #
# --------------------------------------------------------------------------- #


class TestHealthAndInfo:
    @pytestmark_fastapi
    def test_healthz_returns_ok(self) -> None:
        app, _, _ = _build_app_and_chain()
        client = _client(app)
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    @pytestmark_fastapi
    def test_info_reports_wired_modules(self) -> None:
        app, _, _ = _build_app_and_chain()
        client = _client(app)
        response = client.get("/info")
        assert response.status_code == 200
        body = response.json()
        assert body["package"] == "finserv-agent-audit"
        assert "package_version" in body
        wired = body["modules_wired"]
        assert wired["audit_chain"] is True
        assert wired["model_inventory"] is True
        assert wired["sovereign_veto"] is True


class TestAuditChainInfo:
    @pytestmark_fastapi
    def test_empty_chain_reports_zero_length(self) -> None:
        app, _, _ = _build_app_and_chain()
        client = _client(app)
        response = client.get("/audit-chain/info")
        assert response.status_code == 200
        body = response.json()
        assert body["length"] == 0
        assert body["head_event_hash"] == "0" * 64
        assert body["event_type_histogram"] == {}

    @pytestmark_fastapi
    def test_populated_chain_reports_histogram(self) -> None:
        app, chain, _ = _build_app_and_chain()
        chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="agent-a",
            payload={"action": "noop"},
        )
        chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="agent-b",
            payload={"action": "noop"},
        )
        client = _client(app)
        body = client.get("/audit-chain/info").json()
        assert body["length"] == 2
        assert body["event_type_histogram"]["decision.made"] == 2


class TestAuditChainVerify:
    @pytestmark_fastapi
    def test_clean_chain_verifies(self) -> None:
        app, chain, _ = _build_app_and_chain()
        chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="agent",
            payload={},
        )
        client = _client(app)
        body = client.get("/audit-chain/verify").json()
        assert body["intact"] is True
        assert body["last_tampered"] is None

    @pytestmark_fastapi
    def test_tampered_chain_reports_index(self) -> None:
        app, chain, _ = _build_app_and_chain()
        chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="agent",
            payload={"action": "first"},
        )
        chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="agent",
            payload={"action": "second"},
        )
        # Tamper with the first event's payload after the fact — the
        # stored event_hash now differs from the freshly-computed hash.
        chain._events[0].payload["action"] = "MUTATED"  # noqa: SLF001
        client = _client(app)
        body = client.get("/audit-chain/verify").json()
        assert body["intact"] is False
        assert body["last_tampered"] == 0


class TestAuditChainVerifyStream:
    @pytestmark_fastapi
    def test_sse_stream_emits_result_event(self) -> None:
        app, chain, _ = _build_app_and_chain()
        for i in range(3):
            chain.append(
                event_type=AuditEventType.DECISION_MADE,
                autonomy_level=AutonomyLevel.A2,
                agent_id=f"agent-{i}",
                payload={"i": i},
            )
        client = _client(app)
        response = client.get("/audit-chain/verify-stream")
        assert response.status_code == 200
        # The SSE wire format puts a terminal ``event: result`` chunk
        # carrying the final verdict.
        body = response.text
        assert "event: result" in body
        assert '"intact": true' in body
        assert '"total_verified": 3' in body


class TestSovereignVeto:
    @pytestmark_fastapi
    def test_status_with_no_active_vetos(self) -> None:
        app, _, _ = _build_app_and_chain()
        client = _client(app)
        body = client.get("/sovereign-veto/status").json()
        assert body["is_vetoed"] is False
        assert body["active_vetos"] == []

    @pytestmark_fastapi
    def test_trigger_emits_chain_entry(self) -> None:
        app, chain, veto = _build_app_and_chain(auth_checker=_allow_all_auth)
        assert veto is not None
        client = _client(app)
        response = client.post(
            "/sovereign-veto/trigger",
            json={
                "reason": VetoReason.RISK_LIMIT_BREACH.value,
                "triggered_by": "risk-monitor",
                "description": "ALERT threshold reached",
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["is_active"] is True
        # The trigger must have emitted a VETO_APPLIED chain entry so
        # the API-layer veto is hash-chained alongside in-process vetos.
        events = list(chain._events)  # noqa: SLF001
        assert any(e.event_type == AuditEventType.VETO_APPLIED for e in events)

    @pytestmark_fastapi
    def test_trigger_requires_auth(self) -> None:
        # No auth_checker supplied; the default reject-all should fire.
        app, _, _ = _build_app_and_chain()
        client = _client(app)
        response = client.post(
            "/sovereign-veto/trigger",
            json={
                "reason": VetoReason.RISK_LIMIT_BREACH.value,
                "triggered_by": "risk-monitor",
                "description": "ALERT",
            },
        )
        assert response.status_code == 401

    @pytestmark_fastapi
    def test_clear_requires_nonempty_reason(self) -> None:
        app, _, veto = _build_app_and_chain(auth_checker=_allow_all_auth)
        assert veto is not None
        veto.trigger(
            reason=VetoReason.MANUAL_OPERATOR,
            triggered_by="ops",
            description="manual veto",
        )
        client = _client(app)
        response = client.post(
            "/sovereign-veto/clear",
            json={"operator_id": "human", "reason": "   "},
        )
        assert response.status_code == 400


class TestModelInventoryEndpoint:
    @pytestmark_fastapi
    def test_empty_inventory_returns_empty_list(self) -> None:
        app, _, _ = _build_app_and_chain()
        client = _client(app)
        body = client.get("/model-inventory").json()
        assert body["models"] == []
        assert body["count"] == 0

    @pytestmark_fastapi
    def test_unwired_inventory_returns_503(self) -> None:
        app, _, _ = _build_app_and_chain(include_model_inventory=False)
        client = _client(app)
        response = client.get("/model-inventory")
        assert response.status_code == 503


class TestOpenAPISpec:
    @pytestmark_fastapi
    def test_openapi_json_emits_3_1_spec(self) -> None:
        app, _, _ = _build_app_and_chain()
        client = _client(app)
        response = client.get("/openapi.json")
        assert response.status_code == 200
        spec = response.json()
        assert spec["openapi"].startswith("3.1")
        # The governance endpoints must be enumerated.
        paths = set(spec["paths"].keys())
        assert "/healthz" in paths
        assert "/audit-chain/verify" in paths
        assert "/sovereign-veto/status" in paths


# --------------------------------------------------------------------------- #
# Sanity                                                                      #
# --------------------------------------------------------------------------- #


def test_module_lives_at_documented_path() -> None:
    root = Path(__file__).resolve().parent.parent
    expected = root / "src" / "finserv_agent_audit" / "integrations" / "governance_api.py"
    assert expected.is_file()


def test_governance_api_module_imports_without_error() -> None:
    """Importing the module must succeed regardless of FastAPI install state."""
    assert hasattr(governance_api, "create_app")
    assert hasattr(governance_api, "HAS_FASTAPI")
