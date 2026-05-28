"""Ecosystem onramps — OPTIONAL on-package integrations (v1.2).

Where ``examples/integration/*`` ships reference adapters for downstream
LedgerStore / WitnessRegister backends, this package ships first-party
integrations that map ``finserv_agent_audit`` events into industry-wide
observability / interop contracts:

    otel_genai - emit AuditEvents as OpenTelemetry GenAI client spans
                 using the stable ``gen_ai.*`` semantic conventions
                 (exited experimental in early 2026).

Each module import-guards its optional dependency with a ``HAS_X``
boolean so the parent package keeps the zero-runtime-dependency contract
documented in ADR D2.2. To enable an integration, install the matching
extra::

    pip install finserv-agent-audit[otel]
    pip install finserv-agent-audit[all-integrations]
"""

__all__: list[str] = []
