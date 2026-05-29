"""Reference Kubernetes controller stub for finserv-agent-audit CRDs.

This is a REFERENCE STUB. It demonstrates the reconciliation pattern using
only the Python standard library and an in-cluster ServiceAccount token,
calling the Kubernetes API via ``urllib.request``. It is intentionally
minimal: no event-driven watch stream, no informer cache, no full leader
election. A ``/healthz``, ``/readyz``, and ``/metrics`` HTTP surface is
included so the Deployment's probes + Prometheus ServiceMonitor have
something to scrape.

Production deployers SHOULD rebuild this controller on top of a proper
operator framework:

  * ``kopf`` (Python-native, event-driven, supports finalizers)
  * ``operator-sdk`` (Go / Ansible / Helm; the CNCF reference)
  * The Kubernetes Agent Sandbox runtime
    (``github.com/kubernetes-sigs/agent-sandbox``) for stateful agent
    workloads where each agent is a long-lived Pod with its own PV.

What the stub does demonstrate, end-to-end:

  1. Reads the in-cluster ServiceAccount token + CA bundle from the
     standard mount path (``/var/run/secrets/kubernetes.io/serviceaccount/``).
     The token is RE-READ from disk on every API call so projected
     ServiceAccount token rotation (kubelet refresh, default ~1h) takes
     effect without a Pod restart.
  2. Polls the three CRD endpoints
     (``/apis/finserv.io/v1/{auditchains,sovereignvetoes,chainsinks}``)
     on a fixed interval.
  3. For each ``AuditChain`` spec, instantiates the matching
     ``finserv_agent_audit.governance.audit_chain.AuditChain`` using the
     spec's ledger_store_class + timestamp_source_class.
  4. Runs ``chain.verify()`` and PATCHes the result back onto the CRD's
     ``.status`` subresource.
  5. Serves ``/healthz``, ``/readyz``, and ``/metrics`` on
     ``FINSERV_OPERATOR_HEALTH_PORT`` (default ``8080``) so the Deployment's
     probes + Prometheus ServiceMonitor can scrape liveness + readiness
     + a minimal operator-up gauge.

The chain-verify cron pattern is intentionally surfaced here so a deployer
reading this stub understands the moving parts before swapping in kopf or
operator-sdk. See ``deploy/k8s/README.md`` for the production hardening
narrative.
"""

from __future__ import annotations

import json
import logging
import os
import ssl
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, cast
from urllib.request import Request

# --------------------------------------------------------------------------- #
# In-cluster configuration                                                    #
# --------------------------------------------------------------------------- #

SA_DIR = "/var/run/secrets/kubernetes.io/serviceaccount"
SA_TOKEN_PATH = f"{SA_DIR}/token"
SA_CA_PATH = f"{SA_DIR}/ca.crt"
SA_NAMESPACE_PATH = f"{SA_DIR}/namespace"

API_GROUP = "finserv.io"
API_VERSION = "v1"

RESOURCE_AUDIT_CHAIN = "auditchains"
RESOURCE_SOVEREIGN_VETO = "sovereignvetoes"
RESOURCE_CHAIN_SINK = "chainsinks"

DEFAULT_RECONCILE_INTERVAL_SECONDS = 30
DEFAULT_HEALTH_PORT = 8080


# --------------------------------------------------------------------------- #
# Dataclasses                                                                 #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ClusterConfig:
    """In-cluster Kubernetes API connection settings.

    The ServiceAccount token is intentionally NOT stored on this dataclass.
    Projected SA tokens rotate (kubelet default ~1h); reading the token at
    every API call keeps the controller from drifting onto a stale token
    and a sudden burst of 401s post-rotation.
    """

    api_server: str
    ca_bundle_path: str
    namespace: str


@dataclass
class ReconcileReport:
    """Per-resource reconciliation outcome surfaced into logs + status."""

    name: str
    namespace: str
    kind: str
    ok: bool
    message: str
    status_patch: dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Operator state — readiness gate + reconcile counters surfaced by /metrics  #
# --------------------------------------------------------------------------- #


@dataclass
class OperatorState:
    """Mutable runtime state shared with the health-probe HTTP server.

    The health server runs on a daemon thread and reads these fields
    on every probe — no lock needed because all mutations are simple
    scalar writes the GIL serializes per-bytecode-instruction, and
    eventual consistency is fine for liveness + readiness checks.
    """

    ready: bool = False
    last_reconcile_unix: float = 0.0
    reconcile_total: int = 0
    reconcile_failed_total: int = 0


# --------------------------------------------------------------------------- #
# In-cluster discovery                                                        #
# --------------------------------------------------------------------------- #


def _read_text(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read().strip()


def _read_sa_token() -> str:
    """Re-read the ServiceAccount token from disk on every API call.

    Projected SA tokens (the default since Kubernetes 1.21) rotate roughly
    hourly. Caching the token at startup means a long-running operator
    holds a stale token forever after the first rotation and starts
    issuing 401s. Read-per-call costs ~1 syscall; rotation is invisible.
    """
    return _read_text(SA_TOKEN_PATH)


def load_cluster_config() -> ClusterConfig:
    """Read the in-cluster CA bundle + namespace.

    Falls back to ``$KUBERNETES_SERVICE_HOST``/``$KUBERNETES_SERVICE_PORT``
    for the API-server URL — the standard in-cluster envvars Kubernetes
    sets on every Pod. The SA token is NOT loaded here; see
    ``_read_sa_token``.
    """
    host = os.environ.get("KUBERNETES_SERVICE_HOST")
    port = os.environ.get("KUBERNETES_SERVICE_PORT", "443")
    if not host:
        raise RuntimeError(
            "KUBERNETES_SERVICE_HOST not set; this controller stub must run "
            "inside a Kubernetes Pod with a mounted ServiceAccount."
        )
    return ClusterConfig(
        api_server=f"https://{host}:{port}",
        ca_bundle_path=SA_CA_PATH,
        namespace=_read_text(SA_NAMESPACE_PATH),
    )


# --------------------------------------------------------------------------- #
# Kubernetes API client (stdlib urllib)                                       #
# --------------------------------------------------------------------------- #


def _ssl_context(ca_bundle_path: str) -> ssl.SSLContext:
    context = ssl.create_default_context(cafile=ca_bundle_path)
    context.verify_mode = ssl.CERT_REQUIRED
    return context


def _request(
    config: ClusterConfig,
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    content_type: str = "application/json",
) -> dict[str, Any]:
    url = f"{config.api_server}{path}"
    data: bytes | None = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = Request(url=url, method=method, data=data)
    # Re-read the token per call — projected SA tokens rotate.
    req.add_header("Authorization", f"Bearer {_read_sa_token()}")
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", content_type)
    ctx = _ssl_context(config.ca_bundle_path)
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:  # noqa: S310
        raw = resp.read()
    if not raw:
        return {}
    parsed = json.loads(raw.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise RuntimeError(f"non-object response from {method} {path}")
    return cast(dict[str, Any], parsed)


def list_namespaced(config: ClusterConfig, resource: str, namespace: str) -> list[dict[str, Any]]:
    """List all CRD instances of ``resource`` in ``namespace``."""
    path = f"/apis/{API_GROUP}/{API_VERSION}/namespaces/{namespace}/{resource}"
    try:
        body = _request(config, "GET", path)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return []
        raise
    items_raw = body.get("items", [])
    if not isinstance(items_raw, list):
        return []
    return [cast(dict[str, Any], item) for item in items_raw if isinstance(item, dict)]


def patch_status(
    config: ClusterConfig,
    resource: str,
    namespace: str,
    name: str,
    status: dict[str, Any],
) -> None:
    """PATCH the ``.status`` subresource using merge-patch semantics."""
    path = f"/apis/{API_GROUP}/{API_VERSION}/namespaces/{namespace}/{resource}/{name}/status"
    _request(
        config,
        "PATCH",
        path,
        body={"status": status},
        content_type="application/merge-patch+json",
    )


# --------------------------------------------------------------------------- #
# AuditChain reconciliation                                                   #
# --------------------------------------------------------------------------- #


def _build_audit_chain(spec: dict[str, Any]) -> Any:
    """Construct a framework AuditChain from the CRD spec.

    Imports are deferred to call-time so the stub remains importable
    outside a cluster (mypy --strict + ruff lint).
    """
    from finserv_agent_audit.governance.audit_chain import AuditChain
    from finserv_agent_audit.governance.ledger_store import InMemoryLedgerStore

    store_class = str(spec.get("ledger_store_class", "inmemory"))
    store_config = spec.get("ledger_store_config", {}) or {}

    store: Any
    if store_class == "inmemory":
        store = InMemoryLedgerStore()
    elif store_class == "jsonl":
        from pathlib import Path

        from finserv_agent_audit.governance.ledger_store_jsonl import (
            JSONLLedgerStore,
        )

        store = JSONLLedgerStore(path=Path(str(store_config.get("path", "audit.jsonl"))))
    elif store_class == "sqlite":
        from pathlib import Path

        from finserv_agent_audit.governance.ledger_store_sqlite import (
            SQLiteLedgerStore,
        )

        store = SQLiteLedgerStore(path=Path(str(store_config.get("path", "audit.sqlite"))))
    elif store_class == "worm":
        from pathlib import Path

        from finserv_agent_audit.governance.ledger_store_worm import (
            WORMLedgerStore,
        )

        store = WORMLedgerStore(
            path=Path(str(store_config.get("path", "audit.worm"))),
            manifest_dir=Path(str(store_config.get("manifest_dir", "audit-manifest"))),
        )
    else:
        # 'custom' branch — production deployers wire their own factory.
        raise NotImplementedError(
            f"ledger_store_class={store_class!r} not handled by reference stub"
        )

    return AuditChain(ledger_store=store)


def reconcile_audit_chain(
    config: ClusterConfig,
    item: dict[str, Any],
    logger: logging.Logger,
) -> ReconcileReport:
    metadata = cast(dict[str, Any], item.get("metadata", {}))
    name = str(metadata.get("name", ""))
    namespace = str(metadata.get("namespace", config.namespace))
    spec = cast(dict[str, Any], item.get("spec", {}))
    now_iso = datetime.now(UTC).isoformat()

    try:
        chain = _build_audit_chain(spec)
        intact = bool(chain.verify())
        head_hash = str(chain._prev_hash)  # public property by convention
        length = len(chain._events)
        status_patch: dict[str, Any] = {
            "chain_length": length,
            "head_hash": head_hash,
            "intact": intact,
            "last_verified_at": now_iso,
            "last_reconciled_at": now_iso,
            "retention_days_configured": int(spec.get("retention_days", 0)),
        }
        patch_status(config, RESOURCE_AUDIT_CHAIN, namespace, name, status_patch)
        message = f"verify={intact} length={length}"
        logger.info("AuditChain %s/%s reconciled: %s", namespace, name, message)
        return ReconcileReport(
            name=name,
            namespace=namespace,
            kind="AuditChain",
            ok=True,
            message=message,
            status_patch=status_patch,
        )
    except (RuntimeError, ValueError, NotImplementedError, OSError) as exc:
        message = f"reconcile failed: {exc}"
        logger.error("AuditChain %s/%s %s", namespace, name, message)
        return ReconcileReport(
            name=name,
            namespace=namespace,
            kind="AuditChain",
            ok=False,
            message=message,
        )


# --------------------------------------------------------------------------- #
# SovereignVeto reconciliation (status surface only in the stub)              #
# --------------------------------------------------------------------------- #


def reconcile_sovereign_veto(
    config: ClusterConfig,
    item: dict[str, Any],
    logger: logging.Logger,
) -> ReconcileReport:
    metadata = cast(dict[str, Any], item.get("metadata", {}))
    name = str(metadata.get("name", ""))
    namespace = str(metadata.get("namespace", config.namespace))
    spec = cast(dict[str, Any], item.get("spec", {}))
    agent_id = str(spec.get("agent_id", ""))
    now_iso = datetime.now(UTC).isoformat()

    # The stub does not maintain veto state across reconciles — production
    # controllers should back the SovereignVeto by a persistent store
    # (e.g. the namespaced AuditChain). We surface the agent_id and an
    # idle status so the CRD always has a well-formed status block.
    status_patch: dict[str, Any] = {
        "is_vetoed": False,
        "active_vetos": [],
        "last_reconciled_at": now_iso,
        "webhook_delivery_status": "none",
    }
    try:
        patch_status(config, RESOURCE_SOVEREIGN_VETO, namespace, name, status_patch)
        message = f"agent_id={agent_id} stub-reconcile-ok"
        logger.info("SovereignVeto %s/%s reconciled: %s", namespace, name, message)
        return ReconcileReport(
            name=name,
            namespace=namespace,
            kind="SovereignVeto",
            ok=True,
            message=message,
            status_patch=status_patch,
        )
    except (urllib.error.HTTPError, urllib.error.URLError, OSError) as exc:
        message = f"reconcile failed: {exc}"
        logger.error("SovereignVeto %s/%s %s", namespace, name, message)
        return ReconcileReport(
            name=name,
            namespace=namespace,
            kind="SovereignVeto",
            ok=False,
            message=message,
        )


# --------------------------------------------------------------------------- #
# ChainSink reconciliation (status surface only in the stub)                  #
# --------------------------------------------------------------------------- #


def reconcile_chain_sink(
    config: ClusterConfig,
    item: dict[str, Any],
    logger: logging.Logger,
) -> ReconcileReport:
    metadata = cast(dict[str, Any], item.get("metadata", {}))
    name = str(metadata.get("name", ""))
    namespace = str(metadata.get("namespace", config.namespace))
    spec = cast(dict[str, Any], item.get("spec", {}))
    sink_type = str(spec.get("sink_type", ""))
    now_iso = datetime.now(UTC).isoformat()

    # The stub does not emit to sinks — production controllers should
    # batch + flush per .spec.flush_interval_seconds. We surface a
    # well-formed status block so the CRD reports cleanly.
    status_patch: dict[str, Any] = {
        "events_emitted_total": 0,
        "events_dropped_total": 0,
        "last_emit_at": None,
        "last_reconciled_at": now_iso,
    }
    try:
        patch_status(config, RESOURCE_CHAIN_SINK, namespace, name, status_patch)
        message = f"sink_type={sink_type} stub-reconcile-ok"
        logger.info("ChainSink %s/%s reconciled: %s", namespace, name, message)
        return ReconcileReport(
            name=name,
            namespace=namespace,
            kind="ChainSink",
            ok=True,
            message=message,
            status_patch=status_patch,
        )
    except (urllib.error.HTTPError, urllib.error.URLError, OSError) as exc:
        message = f"reconcile failed: {exc}"
        logger.error("ChainSink %s/%s %s", namespace, name, message)
        return ReconcileReport(
            name=name,
            namespace=namespace,
            kind="ChainSink",
            ok=False,
            message=message,
        )


# --------------------------------------------------------------------------- #
# Health probe + metrics HTTP server (stdlib http.server)                     #
# --------------------------------------------------------------------------- #


class _HealthHandler(BaseHTTPRequestHandler):
    """Stdlib HTTP handler for /healthz, /readyz, and /metrics.

    The handler reads from a module-level OperatorState injected by
    :func:`start_health_server`. /healthz is always 200 once the server
    is up (the process is by definition alive); /readyz is 200 only
    after the first reconcile cycle completes (gates Service traffic
    until the operator is genuinely usable); /metrics emits a minimal
    Prometheus-format surface.
    """

    # Class-level state pointer wired by start_health_server.
    state: OperatorState = OperatorState()

    def do_GET(self) -> None:  # noqa: N802 — BaseHTTPRequestHandler API
        if self.path == "/healthz":
            self._respond(200, b"OK\n", "text/plain")
            return
        if self.path == "/readyz":
            if self.state.ready:
                self._respond(200, b"OK\n", "text/plain")
            else:
                self._respond(503, b"NOT READY\n", "text/plain")
            return
        if self.path == "/metrics":
            self._respond(
                200,
                self._render_metrics(),
                "text/plain; version=0.0.4",
            )
            return
        self._respond(404, b"not found\n", "text/plain")

    def _respond(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _render_metrics(self) -> bytes:
        # Minimal Prometheus exposition. Production controllers should
        # use prometheus_client and emit controller_runtime_*
        # histograms; this stub keeps the dependency surface stdlib-only.
        ready = 1 if self.state.ready else 0
        failed_help = (
            "# HELP finserv_operator_reconcile_failed_total "
            "Total reconcile cycles with at least one failure."
        )
        last_help = (
            "# HELP finserv_operator_last_reconcile_timestamp_seconds "
            "Unix timestamp of the last reconcile cycle."
        )
        lines = [
            "# HELP finserv_operator_up Operator is up.",
            "# TYPE finserv_operator_up gauge",
            "finserv_operator_up 1",
            "# HELP finserv_operator_ready Operator has completed first reconcile.",
            "# TYPE finserv_operator_ready gauge",
            f"finserv_operator_ready {ready}",
            "# HELP finserv_operator_reconcile_total Total reconcile cycles attempted.",
            "# TYPE finserv_operator_reconcile_total counter",
            f"finserv_operator_reconcile_total {self.state.reconcile_total}",
            failed_help,
            "# TYPE finserv_operator_reconcile_failed_total counter",
            f"finserv_operator_reconcile_failed_total {self.state.reconcile_failed_total}",
            last_help,
            "# TYPE finserv_operator_last_reconcile_timestamp_seconds gauge",
            f"finserv_operator_last_reconcile_timestamp_seconds {self.state.last_reconcile_unix}",
            "",
        ]
        return "\n".join(lines).encode("utf-8")

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 — stdlib name
        # Silence the default access log — kubectl logs is already noisy
        # with reconcile output. Production controllers should emit
        # structured access logs to a dedicated stream.
        return


def start_health_server(state: OperatorState, port: int = DEFAULT_HEALTH_PORT) -> HTTPServer:
    """Start the /healthz + /readyz + /metrics server on a daemon thread.

    Returns the underlying HTTPServer so callers can call ``shutdown()``
    on SIGTERM. The daemon thread dies with the process; we keep the
    handle so a graceful path is available.
    """
    _HealthHandler.state = state
    server = HTTPServer(("0.0.0.0", port), _HealthHandler)  # noqa: S104 — Pod-scoped binding
    thread = threading.Thread(
        target=server.serve_forever,
        name="finserv-operator-health",
        daemon=True,
    )
    thread.start()
    return server


# --------------------------------------------------------------------------- #
# Reconcile loop                                                              #
# --------------------------------------------------------------------------- #


def reconcile_once(config: ClusterConfig, logger: logging.Logger) -> list[ReconcileReport]:
    """Reconcile every CRD instance in the operator's namespace once."""
    reports: list[ReconcileReport] = []

    for item in list_namespaced(config, RESOURCE_AUDIT_CHAIN, config.namespace):
        reports.append(reconcile_audit_chain(config, item, logger))

    for item in list_namespaced(config, RESOURCE_SOVEREIGN_VETO, config.namespace):
        reports.append(reconcile_sovereign_veto(config, item, logger))

    for item in list_namespaced(config, RESOURCE_CHAIN_SINK, config.namespace):
        reports.append(reconcile_chain_sink(config, item, logger))

    return reports


def run_forever(
    config: ClusterConfig,
    logger: logging.Logger,
    state: OperatorState,
    interval_seconds: int = DEFAULT_RECONCILE_INTERVAL_SECONDS,
) -> None:
    """Reconcile every ``interval_seconds`` until SIGTERM.

    Flips ``state.ready`` to True after the first cycle completes so the
    readiness probe gates Service traffic until the operator is genuinely
    usable.
    """
    logger.info(
        "finserv-agent-audit operator stub starting; namespace=%s interval=%ds",
        config.namespace,
        interval_seconds,
    )
    while True:
        try:
            reports = reconcile_once(config, logger)
            ok_count = sum(1 for r in reports if r.ok)
            failed_count = sum(1 for r in reports if not r.ok)
            state.reconcile_total += 1
            if failed_count > 0:
                state.reconcile_failed_total += 1
            state.last_reconcile_unix = time.time()
            state.ready = True
            logger.info("reconcile cycle complete: ok=%d failed=%d", ok_count, failed_count)
        except (urllib.error.HTTPError, urllib.error.URLError, OSError) as exc:
            state.reconcile_total += 1
            state.reconcile_failed_total += 1
            state.last_reconcile_unix = time.time()
            logger.error("reconcile cycle errored: %s", exc)
        time.sleep(interval_seconds)


# --------------------------------------------------------------------------- #
# Entry point                                                                 #
# --------------------------------------------------------------------------- #


def _build_logger() -> logging.Logger:
    level_name = os.environ.get("FINSERV_OPERATOR_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )
    return logging.getLogger("finserv.operator")


def main() -> int:
    logger = _build_logger()
    try:
        config = load_cluster_config()
    except (RuntimeError, OSError) as exc:
        logger.error("failed to load in-cluster config: %s", exc)
        return 2

    # Start the health/metrics surface BEFORE the first reconcile so the
    # liveness probe has something to hit during the cold-start window.
    health_port = int(os.environ.get("FINSERV_OPERATOR_HEALTH_PORT", str(DEFAULT_HEALTH_PORT)))
    state = OperatorState()
    health_server = start_health_server(state, port=health_port)
    logger.info("health/metrics server listening on :%d", health_port)

    interval = int(
        os.environ.get(
            "FINSERV_OPERATOR_RECONCILE_INTERVAL",
            str(DEFAULT_RECONCILE_INTERVAL_SECONDS),
        )
    )
    try:
        run_forever(config, logger, state, interval_seconds=interval)
    except KeyboardInterrupt:
        logger.info("SIGINT received; shutting down")
        return 0
    finally:
        health_server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
