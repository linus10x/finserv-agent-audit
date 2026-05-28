"""OpenTelemetry GenAI semantic-conventions emitter.

What this module does
---------------------
Maps a ``finserv_agent_audit`` ``AuditEvent`` to an OpenTelemetry client
span whose attributes follow the **stable** ``gen_ai.*`` semantic
conventions. The GenAI client-span attribute set exited experimental in
early 2026 (OpenTelemetry Semantic Conventions v1.30+), making it the
first universal observability contract for AI agent behavior.

Stable attributes emitted (when the source payload carries the field)::

    gen_ai.system                       - producer of the GenAI request
    gen_ai.request.model                - model id requested
    gen_ai.usage.input_tokens           - prompt token count
    gen_ai.usage.output_tokens          - completion token count
    gen_ai.response.finish_reasons      - tuple of finish-reason strings
    gen_ai.provider.name                - upstream provider (anthropic,
                                          openai, bedrock, vendor_id, ...)

Audit-side custom attribute::

    finserv_audit.event_type            - the AuditEventType enum value

Reference
---------
- OpenTelemetry GenAI Semantic Conventions:
  https://opentelemetry.io/docs/specs/semconv/gen-ai/
- Spec stability levels:
  https://opentelemetry.io/docs/specs/otel/document-status/

Dependency posture
------------------
``opentelemetry-api`` + ``opentelemetry-sdk`` are OPTIONAL. They are
import-guarded behind ``HAS_OTEL`` so the parent package keeps the
zero-runtime-dependency contract (ADR D2.2). To enable::

    pip install finserv-agent-audit[otel]

When ``HAS_OTEL`` is False (or the caller passes ``tracer=None``) every
``emit()`` is a graceful no-op.

FSI use case
------------
Any FSI agent that emits ``gen_ai.*`` spans gets vendor-mediated AI
observability into the same OTel pipeline that already carries the
firm's request/error/latency telemetry. The audit chain remains the
system of record; OTel is the analyst-facing read path.
"""

from __future__ import annotations

from typing import Any, Protocol

from finserv_agent_audit.schemas.audit_event import AuditEvent, AuditEventType

try:
    from opentelemetry import trace as _otel_trace

    HAS_OTEL = True
    _OTEL_TRACE: Any = _otel_trace
except ImportError:
    HAS_OTEL = False
    _OTEL_TRACE = None


# --------------------------------------------------------------------------- #
# Stable GenAI semantic-convention attribute names                            #
# --------------------------------------------------------------------------- #

GEN_AI_SYSTEM = "gen_ai.system"
GEN_AI_REQUEST_MODEL = "gen_ai.request.model"
GEN_AI_USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
GEN_AI_USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
GEN_AI_RESPONSE_FINISH_REASONS = "gen_ai.response.finish_reasons"
GEN_AI_PROVIDER_NAME = "gen_ai.provider.name"

EVENT_TYPE_ATTRIBUTE = "finserv_audit.event_type"
"""Audit-side custom attribute carrying the AuditEventType enum value."""

DEFAULT_SERVICE_NAME = "finserv-agent-audit"
"""Default ``gen_ai.system`` value when the caller does not supply one."""


# --------------------------------------------------------------------------- #
# Tracer Protocol — narrow surface we depend on                               #
# --------------------------------------------------------------------------- #


class _SpanLike(Protocol):
    """Minimal span surface used by the emitter."""

    def set_attribute(self, key: str, value: Any) -> None: ...
    def end(self) -> None: ...
    def __enter__(self) -> _SpanLike: ...
    def __exit__(self, *args: object) -> None: ...


class _TracerLike(Protocol):
    """Minimal tracer surface used by the emitter."""

    def start_as_current_span(self, name: str, **kwargs: Any) -> _SpanLike: ...


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def map_event_type_to_provider(
    *,
    event_type: AuditEventType,
    payload: dict[str, Any],
    agent_id: str,
) -> str | None:
    """Best-effort mapping from event payload to ``gen_ai.provider.name``.

    Resolution order:

    1. Explicit ``provider`` / ``vendor`` key in the payload.
    2. For vendor-mediated events (VENDOR_SCORE_*), the ``vendor_id``
       payload field, falling back to ``agent_id``.
    3. ``None`` otherwise — the emitter then omits the attribute rather
       than guessing.
    """
    explicit = payload.get("provider") or payload.get("vendor")
    if isinstance(explicit, str) and explicit:
        return explicit

    if event_type in {
        AuditEventType.VENDOR_SCORE_RECORDED,
        AuditEventType.VENDOR_SCORE_DRIFT_DETECTED,
    }:
        vendor_id = payload.get("vendor_id")
        if isinstance(vendor_id, str) and vendor_id:
            return vendor_id
        if agent_id:
            return agent_id

    return None


def _coerce_finish_reasons(value: Any) -> tuple[str, ...] | None:
    """Normalize a finish_reason(s) payload value to a tuple of strings.

    Accepts:
        - a single string ("stop")             -> ("stop",)
        - a list/tuple of strings              -> tuple(value)
        - anything else                        -> None (attribute omitted)
    """
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        out: list[str] = []
        for item in value:
            if isinstance(item, str):
                out.append(item)
        if out:
            return tuple(out)
    return None


def _coerce_int(value: Any) -> int | None:
    """Narrow a payload value to a non-negative int, or None to skip."""
    if isinstance(value, bool):
        return None  # bool is an int subclass — reject as a safety net.
    if isinstance(value, int):
        return value if value >= 0 else None
    return None


def _span_name(event_type: AuditEventType) -> str:
    """Span name convention: ``finserv_audit.<dotted_tail>``."""
    tail = event_type.value.split(".")[-1]
    return f"finserv_audit.{tail}"


# --------------------------------------------------------------------------- #
# Emitter                                                                     #
# --------------------------------------------------------------------------- #


class OTELGenAIEmitter:
    """Emit a single OTel client span per ``AuditEvent``.

    Usage::

        from opentelemetry import trace
        tracer = trace.get_tracer("finserv-agent-audit")
        emitter = OTELGenAIEmitter(tracer=tracer, service_name="zeus")

        for event in audit_chain:
            emitter.emit(event)

    When ``tracer`` is ``None`` (or the optional SDK is not installed),
    ``emit`` returns silently — the audit chain is the system of record
    regardless of whether OTel is wired.
    """

    def __init__(
        self,
        tracer: _TracerLike | None = None,
        *,
        service_name: str = DEFAULT_SERVICE_NAME,
    ) -> None:
        self._tracer = tracer
        self.service_name = service_name

    def emit(self, event: AuditEvent) -> None:
        """Emit one client span for ``event``. No-op if no tracer wired."""
        tracer = self._tracer
        if tracer is None:
            return

        span_cm = tracer.start_as_current_span(_span_name(event.event_type))
        with span_cm as span:
            self._populate_span(span, event)

    def _populate_span(self, span: _SpanLike, event: AuditEvent) -> None:
        payload = event.payload

        # Custom audit-side attribute — always emitted.
        span.set_attribute(EVENT_TYPE_ATTRIBUTE, event.event_type.value)

        # gen_ai.system identifies the GenAI product/service producing
        # the request. We default to the configured service_name.
        span.set_attribute(GEN_AI_SYSTEM, self.service_name)

        model = payload.get("model") or payload.get("request_model")
        if isinstance(model, str) and model:
            span.set_attribute(GEN_AI_REQUEST_MODEL, model)

        input_tokens = _coerce_int(
            payload.get("input_tokens") or payload.get("tokens_in") or payload.get("prompt_tokens")
        )
        if input_tokens is not None:
            span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, input_tokens)

        output_tokens = _coerce_int(
            payload.get("output_tokens")
            or payload.get("tokens_out")
            or payload.get("completion_tokens")
        )
        if output_tokens is not None:
            span.set_attribute(GEN_AI_USAGE_OUTPUT_TOKENS, output_tokens)

        finish_reasons = _coerce_finish_reasons(
            payload.get("finish_reasons") or payload.get("finish_reason")
        )
        if finish_reasons is not None:
            span.set_attribute(GEN_AI_RESPONSE_FINISH_REASONS, finish_reasons)

        provider = map_event_type_to_provider(
            event_type=event.event_type,
            payload=payload,
            agent_id=event.agent_id,
        )
        if provider is not None:
            span.set_attribute(GEN_AI_PROVIDER_NAME, provider)


# --------------------------------------------------------------------------- #
# Demo                                                                        #
# --------------------------------------------------------------------------- #


def _run_demo() -> None:
    """Print a one-line status report. Safe whether or not OTel is present."""
    print(f"OTELGenAIEmitter demo: HAS_OTEL={HAS_OTEL}")
    if not HAS_OTEL:
        print("  opentelemetry-api/-sdk not installed.")
        print("  Install with: pip install finserv-agent-audit[otel]")
        print("  No-op mode active; emit(event) returns silently.")
        return

    # When OTel is present, drive a no-op tracer so the demo never
    # requires an exporter / collector. The user wires their own tracer
    # provider in production.
    from finserv_agent_audit.schemas.audit_event import AutonomyLevel

    assert _OTEL_TRACE is not None
    tracer = _OTEL_TRACE.get_tracer("finserv_agent_audit.demo")
    emitter = OTELGenAIEmitter(tracer=tracer, service_name="demo")
    event = AuditEvent(
        event_type=AuditEventType.DECISION_MADE,
        autonomy_level=AutonomyLevel.A2,
        agent_id="demo:otel",
        payload={
            "model": "claude-3-opus",
            "tokens_in": 42,
            "tokens_out": 17,
            "finish_reason": "stop",
            "vendor": "anthropic",
        },
        prev_hash="0" * 64,
    )
    emitter.emit(event)
    print("  Emitted 1 demo span via default (no-op) tracer provider.")


if __name__ == "__main__":
    _run_demo()


__all__ = [
    "DEFAULT_SERVICE_NAME",
    "EVENT_TYPE_ATTRIBUTE",
    "GEN_AI_PROVIDER_NAME",
    "GEN_AI_REQUEST_MODEL",
    "GEN_AI_RESPONSE_FINISH_REASONS",
    "GEN_AI_SYSTEM",
    "GEN_AI_USAGE_INPUT_TOKENS",
    "GEN_AI_USAGE_OUTPUT_TOKENS",
    "HAS_OTEL",
    "OTELGenAIEmitter",
    "map_event_type_to_provider",
]
