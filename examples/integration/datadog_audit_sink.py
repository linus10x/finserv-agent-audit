"""Datadog Logs API sink for the audit chain.

What this integration does
--------------------------
Implements the ``LedgerStore`` Protocol against Datadog's Logs API v2.
Every ``AuditEvent`` appended to the chain is POSTed to
``https://http-intake.logs.datadoghq.com/api/v2/logs`` (or a regional
intake host) as a single JSON log with ``service="finserv-agent-audit"``
and ``ddtags="env:prod,framework:autonomy-ladder"``. An in-process mirror
satisfies the Protocol's iteration / head / get-by-sequence contract.

What service it talks to
------------------------
Datadog Logs intake (us1 / us3 / us5 / eu / ap1 / gov regional hosts).
Stdlib-only transport (``urllib.request``). No ``datadog`` SDK.

Regulatory framework benefits
-----------------------------
- **SOC 2 CC7.2** — system monitoring and anomaly detection; Datadog's
  log-pipeline + monitors page on ``HALT_TRIGGERED`` or ``VETO_APPLIED``
  events. Pair with Datadog SIEM for the security-monitoring control.
- **PCI-DSS Requirement 10** — log all access to cardholder data; the
  audit chain is the agent-side input to that requirement and Datadog
  is the aggregation tier most fintechs already operate.
- **EU AI Act Article 12** — logging capabilities; the regional EU
  intake host (``http-intake.logs.datadoghq.eu``) keeps the audit log
  inside the EEA boundary for GDPR + AI-Act dual-pass.
- **NYDFS Part 500** — covered-entity cybersecurity event monitoring;
  the chain is the agent-decision audit trail and Datadog is the
  notification + 72-hour reporting pipe.

This is a REFERENCE integration. It is NOT imported by the package
surface and adds no runtime dependency to the wheel.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer

from finserv_agent_audit.governance.ledger_store import GENESIS_PREV_HASH
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)

DEFAULT_DATADOG_INTAKE = "https://http-intake.logs.datadoghq.com/api/v2/logs"


class DatadogLogsLedgerStore:
    """``LedgerStore`` Protocol implementation backed by the Datadog Logs API."""

    def __init__(
        self,
        api_key: str,
        *,
        intake_url: str = DEFAULT_DATADOG_INTAKE,
        service: str = "finserv-agent-audit",
        ddtags: str = "env:prod,framework:autonomy-ladder",
        hostname: str | None = None,
        timeout_s: float = 5.0,
    ) -> None:
        self._intake_url = intake_url
        self._api_key = api_key
        self._service = service
        self._ddtags = ddtags
        self._hostname = hostname
        self._timeout_s = timeout_s
        self._events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:
        log_entry: dict[str, object] = {
            "ddsource": "finserv-agent-audit",
            "ddtags": self._ddtags,
            "service": self._service,
            "message": event.to_jsonl(),
            "event": event.to_dict(),
            "status": _severity_for(event),
        }
        if self._hostname is not None:
            log_entry["hostname"] = self._hostname
        body = json.dumps([log_entry], sort_keys=True).encode("utf-8")
        req = urllib.request.Request(
            self._intake_url,
            data=body,
            method="POST",
            headers={
                "DD-API-KEY": self._api_key,
                "Content-Type": "application/json",
                "Content-Length": str(len(body)),
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout_s) as resp:  # noqa: S310
                status = resp.status
                resp.read()
        except urllib.error.HTTPError as http_err:
            status = http_err.code
        # Datadog returns 202 Accepted on success.
        if status not in (200, 202):
            raise RuntimeError(f"Datadog Logs intake returned HTTP {status}")
        self._events.append(event)

    def __iter__(self) -> Iterator[AuditEvent]:
        return iter(self._events)

    def __len__(self) -> int:
        return len(self._events)

    def get(self, sequence: int) -> AuditEvent:
        if sequence < 0 or sequence >= len(self._events):
            raise IndexError(f"sequence {sequence} out of range [0, {len(self._events)})")
        return self._events[sequence]

    def head_sequence(self) -> int:
        return len(self._events) - 1

    def head_event_hash(self) -> str:
        if not self._events:
            return str(GENESIS_PREV_HASH)
        return str(self._events[-1].event_hash)


def _severity_for(event: AuditEvent) -> str:
    """Map AuditEventType -> Datadog log status field."""
    high = {
        AuditEventType.HALT_TRIGGERED,
        AuditEventType.VETO_APPLIED,
        AuditEventType.POLICY_VIOLATION,
        AuditEventType.AGENT_ERROR,
        AuditEventType.VENDOR_SCORE_DRIFT_DETECTED,
    }
    if event.event_type in high:
        return "error"
    if event.event_type is AuditEventType.RISK_ESCALATION:
        return "warn"
    return "info"


# --------------------------------------------------------------------- #
# Demo — in-process mock intake server, no external network.           #
# --------------------------------------------------------------------- #

_RECEIVED: list[list[dict[str, object]]] = []


class _MockIntakeHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        _RECEIVED.append(json.loads(raw))
        self.send_response(202)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return


def _run_demo() -> None:
    server = HTTPServer(("127.0.0.1", 0), _MockIntakeHandler)
    host = str(server.server_address[0])
    port = int(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        store = DatadogLogsLedgerStore(
            api_key="DEMO-API-KEY-NOT-A-REAL-SECRET",
            intake_url=f"http://{host}:{port}/api/v2/logs",
            hostname="demo-host-01",
        )
        prev = GENESIS_PREV_HASH
        event_types = [
            AuditEventType.DECISION_MADE,
            AuditEventType.RISK_ESCALATION,
            AuditEventType.HUMAN_APPROVED,
            AuditEventType.VETO_APPLIED,
            AuditEventType.HALT_TRIGGERED,
        ]
        for i, et in enumerate(event_types):
            event = AuditEvent(
                event_type=et,
                autonomy_level=AutonomyLevel.A2,
                agent_id="demo:datadog_sink",
                payload={"step": i, "action": "noop"},
                prev_hash=prev,
            )
            store.append(event)
            prev = event.event_hash
        print(f"DatadogLogsLedgerStore demo: posted {len(store)} events to mock intake")
        print(f"mock intake received   : {len(_RECEIVED)} batches")
        print(f"head_event_hash        : {store.head_event_hash()}")
        print(f"head_sequence          : {store.head_sequence()}")
        first_batch = _RECEIVED[0]
        first_entry = first_batch[0]
        print(f"first entry ddsource   : {first_entry.get('ddsource')!r}")
        print(f"first entry service    : {first_entry.get('service')!r}")
        print(f"first entry ddtags     : {first_entry.get('ddtags')!r}")
        last_batch = _RECEIVED[-1]
        last_entry = last_batch[0]
        print(f"last entry status      : {last_entry.get('status')!r}  (halt -> error)")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    _run_demo()
