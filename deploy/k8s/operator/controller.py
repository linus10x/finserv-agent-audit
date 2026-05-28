"""Reference Kubernetes controller stub for finserv-agent-audit CRDs.

This is a REFERENCE STUB. It demonstrates the reconciliation pattern using
only the Python standard library and an in-cluster ServiceAccount token,
calling the Kubernetes API via ``urllib.request``. It is intentionally
minimal: no event-driven watch stream, no informer cache, no leader
election, no metrics endpoint.

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
  2. Polls the three CRD endpoints
     (``/apis/finserv.io/v1/{auditchains,sovereignvetoes,chainsinks}``)
     on a fixed interval.
  3. For each ``AuditChain`` spec, instantiates the matching
     ``finserv_agent_audit.governance.audit_chain.AuditChain`` using the
     spec's ledger_store_class + timestamp_source_class.
  4. Runs ``chain.verify()`` and PATCHes the result back onto the CRD's
     ``.status`` subresource.

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
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
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


# --------------------------------------------------------------------------- #
# Dataclasses                                                                 #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ClusterConfig:
    """In-cluster Kubernetes API connection settings."""

    api_server: str
    token: str
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
# In-cluster discovery                                                        #
# --------------------------------------------------------------------------- #


def _read_text(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read().strip()


def load_cluster_config() -> ClusterConfig:
    """Read the in-cluster ServiceAccount token + namespace.

    Falls back to ``$KUBERNETES_SERVICE_HOST``/``$KUBERNETES_SERVICE_PORT``
    for the API-server URL — the standard in-cluster envvars Kubernetes
    sets on every Pod.
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
        token=_read_text(SA_TOKEN_PATH),
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
    req.add_header("Authorization", f"Bearer {config.token}")
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
    interval_seconds: int = DEFAULT_RECONCILE_INTERVAL_SECONDS,
) -> None:
    """Reconcile every ``interval_seconds`` until SIGTERM."""
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
            logger.info("reconcile cycle complete: ok=%d failed=%d", ok_count, failed_count)
        except (urllib.error.HTTPError, urllib.error.URLError, OSError) as exc:
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
    interval = int(
        os.environ.get(
            "FINSERV_OPERATOR_RECONCILE_INTERVAL",
            str(DEFAULT_RECONCILE_INTERVAL_SECONDS),
        )
    )
    try:
        run_forever(config, logger, interval_seconds=interval)
    except KeyboardInterrupt:
        logger.info("SIGINT received; shutting down")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
