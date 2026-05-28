"""Tests for the OpenTelemetry GenAI semantic-conventions emitter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from finserv_agent_audit.integrations import otel_genai
from finserv_agent_audit.integrations.otel_genai import (
    EVENT_TYPE_ATTRIBUTE,
    OTELGenAIEmitter,
    map_event_type_to_provider,
)
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)

GENESIS = "0" * 64


def _make_event(
    *,
    event_type: AuditEventType = AuditEventType.DECISION_MADE,
    payload: dict[str, Any] | None = None,
    agent_id: str = "test-agent",
) -> AuditEvent:
    return AuditEvent(
        event_type=event_type,
        autonomy_level=AutonomyLevel.A2,
        agent_id=agent_id,
        payload=payload or {"model": "claude-3-opus", "tokens_in": 42, "tokens_out": 17},
        prev_hash=GENESIS,
    )


# --------------------------------------------------------------------------- #
# Spy tracer (used to stand in for an OTel tracer when otel-sdk is missing)   #
# --------------------------------------------------------------------------- #


@dataclass
class _SpySpan:
    name: str
    attributes: dict[str, Any] = field(default_factory=dict)
    ended: bool = False

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def end(self) -> None:
        self.ended = True

    def __enter__(self) -> _SpySpan:
        return self

    def __exit__(self, *_args: object) -> None:
        self.end()


@dataclass
class _SpyTracer:
    started: list[_SpySpan] = field(default_factory=list)

    def start_as_current_span(self, name: str, **_kwargs: object) -> _SpySpan:
        span = _SpySpan(name=name)
        self.started.append(span)
        return span


# --------------------------------------------------------------------------- #
# Graceful degradation when otel-sdk is not installed                         #
# --------------------------------------------------------------------------- #


class TestGracefulDegradation:
    def test_emitter_constructs_without_otel_sdk(self) -> None:
        # Even with HAS_OTEL=False the emitter must instantiate.
        emitter = OTELGenAIEmitter(tracer=None, service_name="test")
        assert emitter.service_name == "test"

    def test_emit_is_a_no_op_when_tracer_is_none(self) -> None:
        emitter = OTELGenAIEmitter(tracer=None)
        event = _make_event()
        # No-op: must not raise, must return None.
        assert emitter.emit(event) is None

    def test_has_otel_flag_is_boolean(self) -> None:
        # Whether or not opentelemetry is installed on the test host, the
        # flag must be a deterministic boolean — never raise on import.
        assert isinstance(otel_genai.HAS_OTEL, bool)


# --------------------------------------------------------------------------- #
# Attribute mapping (using a spy tracer — independent of opentelemetry-sdk)   #
# --------------------------------------------------------------------------- #


class TestAttributeMapping:
    def test_stable_attributes_emitted_for_decision_made(self) -> None:
        tracer = _SpyTracer()
        emitter = OTELGenAIEmitter(tracer=tracer, service_name="zeus")
        event = _make_event(
            payload={
                "model": "claude-3-opus",
                "vendor": "anthropic",
                "tokens_in": 100,
                "tokens_out": 50,
                "finish_reason": "stop",
            }
        )
        emitter.emit(event)

        assert len(tracer.started) == 1
        span = tracer.started[0]
        # Stable GenAI semantic conventions (exited experimental early 2026):
        assert span.attributes["gen_ai.request.model"] == "claude-3-opus"
        assert span.attributes["gen_ai.usage.input_tokens"] == 100
        assert span.attributes["gen_ai.usage.output_tokens"] == 50
        assert span.attributes["gen_ai.response.finish_reasons"] == ("stop",)
        assert span.attributes["gen_ai.provider.name"] == "anthropic"
        # Audit-side custom attribute carries the event-type enum value.
        assert span.attributes[EVENT_TYPE_ATTRIBUTE] == "decision.made"

    def test_finish_reasons_accepts_list(self) -> None:
        tracer = _SpyTracer()
        emitter = OTELGenAIEmitter(tracer=tracer)
        event = _make_event(
            payload={
                "model": "claude-3-opus",
                "finish_reasons": ["stop", "length"],
            }
        )
        emitter.emit(event)
        span = tracer.started[0]
        assert span.attributes["gen_ai.response.finish_reasons"] == ("stop", "length")

    def test_missing_payload_fields_are_skipped(self) -> None:
        tracer = _SpyTracer()
        emitter = OTELGenAIEmitter(tracer=tracer)
        # Payload with NO GenAI fields — only event-type custom attribute
        # should land. We deliberately avoid hallucinating values.
        event = _make_event(payload={"action": "enter_position"})
        emitter.emit(event)

        span = tracer.started[0]
        assert "gen_ai.request.model" not in span.attributes
        assert "gen_ai.usage.input_tokens" not in span.attributes
        assert "gen_ai.usage.output_tokens" not in span.attributes
        assert "gen_ai.response.finish_reasons" not in span.attributes
        assert "gen_ai.provider.name" not in span.attributes
        assert span.attributes[EVENT_TYPE_ATTRIBUTE] == "decision.made"

    def test_gen_ai_system_default_is_service_name(self) -> None:
        tracer = _SpyTracer()
        emitter = OTELGenAIEmitter(tracer=tracer, service_name="apex")
        event = _make_event(payload={"model": "claude-3-opus"})
        emitter.emit(event)
        span = tracer.started[0]
        # gen_ai.system identifies the GenAI product / service producing
        # the request — service_name is the audit-side equivalent.
        assert span.attributes["gen_ai.system"] == "apex"

    def test_vendor_score_recorded_maps_provider_from_payload(self) -> None:
        tracer = _SpyTracer()
        emitter = OTELGenAIEmitter(tracer=tracer)
        event = _make_event(
            event_type=AuditEventType.VENDOR_SCORE_RECORDED,
            agent_id="experian:fraud-score-v3",
            payload={
                "vendor_id": "experian:fraud-score-v3",
                "vendor_class": "fraud_score",
                "score": 0.82,
                "model_version": "2026.04.01",
            },
        )
        emitter.emit(event)
        span = tracer.started[0]
        # vendor_id -> gen_ai.provider.name when no explicit provider is set
        assert span.attributes["gen_ai.provider.name"] == "experian:fraud-score-v3"
        assert span.attributes[EVENT_TYPE_ATTRIBUTE] == "vendor.score_recorded"

    def test_event_type_custom_attribute_for_each_relevant_enum(self) -> None:
        """Spot-check the custom attribute for the GenAI-relevant event types."""
        cases = [
            AuditEventType.DECISION_MADE,
            AuditEventType.DECISION_VETOED,
            AuditEventType.VENDOR_SCORE_RECORDED,
            AuditEventType.VENDOR_SCORE_DRIFT_DETECTED,
            AuditEventType.HALT_TRIGGERED,
            AuditEventType.MODEL_VALIDATED,
        ]
        for event_type in cases:
            tracer = _SpyTracer()
            emitter = OTELGenAIEmitter(tracer=tracer)
            event = _make_event(event_type=event_type, payload={"model": "claude-3-opus"})
            emitter.emit(event)
            span = tracer.started[0]
            assert span.attributes[EVENT_TYPE_ATTRIBUTE] == event_type.value

    def test_span_name_includes_event_type(self) -> None:
        tracer = _SpyTracer()
        emitter = OTELGenAIEmitter(tracer=tracer)
        event = _make_event(event_type=AuditEventType.HALT_TRIGGERED)
        emitter.emit(event)
        assert tracer.started[0].name.endswith("halt")

    def test_map_event_type_to_provider_default(self) -> None:
        # The helper used internally for provider-name fallbacks.
        provider = map_event_type_to_provider(
            event_type=AuditEventType.DECISION_MADE,
            payload={"vendor": "anthropic"},
            agent_id="zeus",
        )
        assert provider == "anthropic"

    def test_map_event_type_to_provider_vendor_path(self) -> None:
        provider = map_event_type_to_provider(
            event_type=AuditEventType.VENDOR_SCORE_RECORDED,
            payload={"vendor_id": "experian:fraud-score-v3"},
            agent_id="experian:fraud-score-v3",
        )
        assert provider == "experian:fraud-score-v3"

    def test_map_event_type_to_provider_none_when_unknown(self) -> None:
        provider = map_event_type_to_provider(
            event_type=AuditEventType.AGENT_STARTED,
            payload={},
            agent_id="zeus",
        )
        assert provider is None


# --------------------------------------------------------------------------- #
# Demo entrypoint (smoke-test the __main__ no-op path)                        #
# --------------------------------------------------------------------------- #


class TestDemoEntrypoint:
    def test_demo_does_not_raise(self, capsys: pytest.CaptureFixture[str]) -> None:
        otel_genai._run_demo()
        out = capsys.readouterr().out
        assert "HAS_OTEL" in out
