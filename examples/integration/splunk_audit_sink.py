"""Splunk HTTP Event Collector (HEC) sink for the audit chain.

What this integration does
--------------------------
Implements the ``LedgerStore`` Protocol against Splunk's HTTP Event
Collector. Every ``AuditEvent`` appended to the chain is POSTed to Splunk
as a single JSON event with ``sourcetype="finserv_audit_chain"``. The
sink keeps an in-process mirror so the Protocol's iteration / head /
get-by-sequence contract is satisfied without round-tripping Splunk on
every read.

What service it talks to
------------------------
Splunk Enterprise / Splunk Cloud HEC endpoint. Stdlib-only transport
(``urllib.request``). No ``splunk-sdk``, no ``requests``.

Regulatory framework benefits
-----------------------------
- **SOX 404 ITGC** — Splunk is the canonical log-aggregation tier for
  most enterprise SOX programs. Routing the audit chain into the same
  index inherits the firm's existing access-control + retention policies
  ("log aggregation pass-through").
- **SEC Rule 17a-4** — broker-dealer electronic records retention; pair
  the Splunk index with an S3-frozen-bucket retention policy or with the
  in-repo WORM ``LedgerStore`` as a primary, with Splunk as the searchable
  secondary.
- **SOC 2 CC7.2** — system monitoring; Splunk's alerting subsystem can
  page on ``AuditEventType.HALT_TRIGGERED`` or
  ``AuditEventType.VETO_APPLIED`` events out of the box.
- **EU AI Act Article 12** — logging capabilities for high-risk AI; this
  sink is the operational pipe that feeds the regulator-facing log.

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


class SplunkHECLedgerStore:
    """``LedgerStore`` Protocol implementation backed by Splunk HEC.

    Every ``append`` POSTs the event to Splunk; the in-process list keeps
    the Protocol's iteration / get / head contract cheap.
    """

    def __init__(
        self,
        hec_url: str,
        hec_token: str,
        *,
        sourcetype: str = "finserv_audit_chain",
        source: str = "finserv-agent-audit",
        index: str | None = None,
        timeout_s: float = 5.0,
    ) -> None:
        if not hec_url.endswith("/services/collector") and "/services/collector" not in hec_url:
            # Allow either the full path or just the host:port; we'll
            # append the canonical HEC path when only the host is given.
            hec_url = hec_url.rstrip("/") + "/services/collector"
        self._hec_url = hec_url
        self._hec_token = hec_token
        self._sourcetype = sourcetype
        self._source = source
        self._index = index
        self._timeout_s = timeout_s
        self._events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:
        body = {
            "sourcetype": self._sourcetype,
            "source": self._source,
            "event": event.to_dict(),
        }
        if self._index is not None:
            body["index"] = self._index
        raw = json.dumps(body, sort_keys=True).encode("utf-8")
        req = urllib.request.Request(
            self._hec_url,
            data=raw,
            method="POST",
            headers={
                "Authorization": f"Splunk {self._hec_token}",
                "Content-Type": "application/json",
                "Content-Length": str(len(raw)),
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout_s) as resp:  # noqa: S310
                status = resp.status
                resp.read()
        except urllib.error.HTTPError as http_err:
            status = http_err.code
        if status not in (200, 201):
            raise RuntimeError(f"Splunk HEC returned HTTP {status}")
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


# --------------------------------------------------------------------- #
# Demo — uses an in-process mock HEC server so no external network.    #
# --------------------------------------------------------------------- #

_RECEIVED: list[dict[str, object]] = []


class _MockHECHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802  (stdlib handler signature)
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        _RECEIVED.append(json.loads(raw))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"text":"Success","code":0}')

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        # Silence the default per-request stderr noise.
        return


def _run_demo() -> None:
    server = HTTPServer(("127.0.0.1", 0), _MockHECHandler)
    host = str(server.server_address[0])
    port = int(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        store = SplunkHECLedgerStore(
            hec_url=f"http://{host}:{port}/services/collector",
            hec_token="DEMO-TOKEN-NOT-A-REAL-SECRET",
            index="audit_chain",
        )
        prev = GENESIS_PREV_HASH
        for i in range(5):
            event = AuditEvent(
                event_type=AuditEventType.DECISION_MADE,
                autonomy_level=AutonomyLevel.A2,
                agent_id="demo:splunk_sink",
                payload={"step": i, "action": "noop"},
                prev_hash=prev,
            )
            store.append(event)
            prev = event.event_hash
        print(f"SplunkHECLedgerStore demo: posted {len(store)} events to mock HEC")
        print(f"mock HEC received   : {len(_RECEIVED)} events")
        print(f"head_event_hash     : {store.head_event_hash()}")
        print(f"head_sequence       : {store.head_sequence()}")
        first = _RECEIVED[0]
        print(f"first event sourcetype : {first.get('sourcetype')!r}")
        print(f"first event index      : {first.get('index')!r}")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    _run_demo()
