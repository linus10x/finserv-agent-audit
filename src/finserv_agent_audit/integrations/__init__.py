"""Ecosystem onramps — OPTIONAL on-package integrations (v1.2 + v2.0).

Where ``examples/integration/*`` ships reference adapters for downstream
LedgerStore / WitnessRegister backends, this package ships first-party
integrations that map ``finserv_agent_audit`` events into industry-wide
agentic-runtime, observability, and platform-surface contracts:

    otel_genai          - emit AuditEvents as OpenTelemetry GenAI client
                          spans using the stable ``gen_ai.*`` semantic
                          conventions (exited experimental in early 2026).
    a2a_adapter         - wrap a Google / Linux-Foundation A2A
                          (Agent2Agent) server or client surface and
                          emit one AuditEvent per task-lifecycle
                          transition and per message exchange
                          (ADR-0027).
    langgraph_adapter   - LangGraph node / edge / conditional /
                          human-in-the-loop interrupt callback that
                          emits an AuditEvent per node-entry, node-exit,
                          conditional-edge resolution, and HITL
                          interrupt (ADR-0028).
    maf_adapter         - Microsoft Agent Framework adapter emitting
                          one AuditEvent per agent-step, tool-call, and
                          orchestrator-handoff (ADR-0029).
    crewai_adapter      - CrewAI adapter wrapping Crew / Agent / Task
                          lifecycle hooks; emits per-task-start /
                          per-task-end / per-tool-invocation AuditEvents
                          and surfaces SovereignVeto at the Crew
                          kickoff boundary (ADR-0030).
    governance_api      - FastAPI governance endpoint exposing DEFCON
                          state, veto log, audit-chain verification,
                          vendor-score drift, deprecation calendar,
                          and AIBOM emit as REST resources under
                          OpenAPI 3.1; includes a Server-Sent Events
                          live stream of AuditEvent flow (ADR-0032).
                          NOT re-exported at this package level because
                          it requires FastAPI; import directly via
                          ``from finserv_agent_audit.integrations.governance_api
                          import create_app``.

Each module import-guards its optional dependency with a ``HAS_X``
boolean so the parent package keeps the zero-runtime-dependency
contract documented in ADR D2.2. To enable an integration, install
the matching extra::

    pip install finserv-agent-audit[otel]
    pip install finserv-agent-audit[a2a]
    pip install finserv-agent-audit[langgraph]
    pip install finserv-agent-audit[maf]
    pip install finserv-agent-audit[crewai]
    pip install finserv-agent-audit[api]
    pip install finserv-agent-audit[all-agentic]      # all four runtime adapters
    pip install finserv-agent-audit[all-integrations] # every v1.2 + v2.0 onramp
"""

from __future__ import annotations

__all__: list[str] = []

# v1.2 OpenTelemetry GenAI emitter — re-export only the public surface;
# fall back to no-op import when the otel SDK is missing so importing the
# parent package never triggers an ImportError on a bare wheel install.
try:  # pragma: no cover - exercised in the integration test environment
    from finserv_agent_audit.integrations.otel_genai import (  # noqa: F401
        OTELGenAIEmitter,
    )

    __all__.append("OTELGenAIEmitter")
except ImportError:  # pragma: no cover
    pass

# v2.0 agentic-runtime adapters — each adapter module already import-
# guards its upstream SDK with a HAS_X boolean. The try/except here is
# the package-level belt-and-braces guard against a future hard import
# in any of the adapter modules.
try:  # pragma: no cover
    from finserv_agent_audit.integrations.a2a_adapter import (  # noqa: F401
        A2AAuditAdapter,
    )

    __all__.append("A2AAuditAdapter")
except ImportError:  # pragma: no cover
    pass

try:  # pragma: no cover
    from finserv_agent_audit.integrations.langgraph_adapter import (  # noqa: F401
        LangGraphAuditCallback,
    )

    __all__.append("LangGraphAuditCallback")
except ImportError:  # pragma: no cover
    pass

try:  # pragma: no cover
    from finserv_agent_audit.integrations.maf_adapter import (  # noqa: F401
        MAFAuditAdapter,
    )

    __all__.append("MAFAuditAdapter")
except ImportError:  # pragma: no cover
    pass

try:  # pragma: no cover
    from finserv_agent_audit.integrations.crewai_adapter import (  # noqa: F401
        CrewAIAuditAdapter,
    )

    __all__.append("CrewAIAuditAdapter")
except ImportError:  # pragma: no cover
    pass
