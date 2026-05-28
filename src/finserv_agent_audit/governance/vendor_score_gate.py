"""VendorScoreGate — third-party AI scoring captured into the audit chain (FSI).

Most FSI operators do not run in-house AI models for the high-risk decision
classes; they consume vendor outputs across five named categories: KYC /
identity verification, fraud-score / device-risk, credit-decision /
underwriting, robo-advisor / signal-generation, and AML transaction
monitoring. The Sovereign Veto (ADR-0002), the Fair-Lending Pre-Flight
analog, and the per-decision Audit Ledger (ADR-0003) all assume operator-
side control of the feature vector and the model. That assumption is wrong
for the majority of FSI agent surface.

This module is the concrete adapter that converts opaque vendor outputs into
operator-side, audit-chain-recorded events without requiring access to the
vendor's feature vector. Every vendor-score event hits the audit chain with
full provenance — vendor_id, vendor_class, input_hash, score, model_version,
timestamp — and the gate watches for drift on the (vendor_id, input_hash,
model_version) key. Drift surfaces as a flagged chain entry typed
``AuditEventType.VENDOR_SCORE_DRIFT_DETECTED`` and, by default, raises
``VendorScoreDriftDetected`` so the caller's pipeline halts rather than
silently absorbing the change. Set ``raise_on_drift=False`` for shadow-mode
rollouts where the caller wants to record drift but not halt the pipeline.

The Protocol surface is two methods (``emit`` and ``history_for``); the
in-memory default backend writes through to a caller-provided ``AuditChain``.
See ADR-0016 for the FSI vendor-class enumeration, the regulatory mapping
(ECOA / Reg B, FCRA, BSA / CIP, SAR filing, OFAC, SR 11-7, OCC Bulletin
2013-29, NYDFS Part 504, SEC Reg BI, FINRA Rule 2111, CFPB UDAAP, EU AI
Act Annex III §5), and the procurement-clause companion artifacts.

> Patterns are software, not legal advice. Regulatory citations live in
> ADR-0016; consult counsel for applicability to your control environment.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable

from finserv_agent_audit.schemas.audit_event import (
    AuditChain,
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)


class VendorClass(Enum):
    """The five FSI vendor-mediated AI surfaces named in ADR-0016.

    Each class carries a distinct reason-code vocabulary, regulator routing,
    and adverse-action posture; downstream report generation routes off it.
    """

    KYC = "kyc"
    FRAUD_SCORE = "fraud_score"
    CREDIT_DECISION = "credit_decision"
    ROBO_ADVISOR_SIGNAL = "robo_advisor_signal"
    AML_TRANSACTION_MONITORING = "aml_transaction_monitoring"


class VendorScoreDriftDetected(RuntimeError):  # noqa: N818
    """Raised when a vendor returns a different score for the same input + model.

    The flagged event is written to the audit chain BEFORE the exception
    propagates, so the drift is auditable even if the caller swallows the
    error. Recovery is operator-driven: vendor review playbook, freeze the
    vendor's signal, escalate per ADR-0016.
    """


@dataclass(frozen=True)
class VendorScoreEntry:
    """One vendor-scoring event, as returned by ``VendorScoreGate.emit``.

    Wraps the audit-chain event with the vendor-specific fields decoded for
    the caller, plus the drift signal (``drift_detected`` + ``previous_score``).
    ``sequence`` is the 0-based position of the chain event at emit time.
    """

    vendor_id: str
    vendor_class: VendorClass
    input_hash: str
    score: float
    model_version: str
    sequence: int
    event_id: str
    drift_detected: bool = False
    previous_score: float | None = None


@runtime_checkable
class VendorScoreGate(Protocol):
    """Capture third-party AI scoring decisions into the audit chain.

    ``emit`` records a (vendor_id, vendor_class, input_hash, score,
    model_version) tuple and watches for score drift on the (vendor_id,
    input_hash, model_version) key. ``history_for`` returns the recorded
    score events for a given (vendor_id, input_hash) — the audit-friendly
    read path.
    """

    def emit(
        self,
        *,
        vendor_id: str,
        vendor_class: VendorClass,
        input_hash: str,
        score: float,
        model_version: str,
    ) -> VendorScoreEntry: ...

    def history_for(
        self,
        *,
        vendor_id: str,
        input_hash: str,
    ) -> list[VendorScoreEntry]: ...


@dataclass
class InMemoryVendorScoreGate:
    """Default backend: write through to a caller-provided ``AuditChain``.

    All durability, retention, and verification semantics come from the
    underlying ``AuditChain`` and its configured ``LedgerStore`` — the gate
    is a thin shim that enforces the vendor-scoring schema and the drift
    check.

    ``raise_on_drift`` (default True) controls whether drift propagates as
    ``VendorScoreDriftDetected`` after the flagged entry is written. Set
    False for shadow-mode rollouts where the caller wants to record drift
    but not halt the pipeline. Vendor-mediated decisions inherit the A2
    default (human on the loop) for autonomy level; deployers can override
    via the constructor.
    """

    audit_chain: AuditChain
    raise_on_drift: bool = True
    autonomy_level: AutonomyLevel = AutonomyLevel.A2
    _seen: dict[tuple[str, str, str], float] = field(default_factory=dict)

    def emit(
        self,
        *,
        vendor_id: str,
        vendor_class: VendorClass,
        input_hash: str,
        score: float,
        model_version: str,
    ) -> VendorScoreEntry:
        _validate_inputs(
            vendor_id=vendor_id,
            input_hash=input_hash,
            score=score,
            model_version=model_version,
        )

        key = (vendor_id, input_hash, model_version)
        previous = self._seen.get(key)
        drift = previous is not None and not math.isclose(
            previous, score, rel_tol=0.0, abs_tol=1e-12
        )

        if drift:
            return self._emit_drift(
                vendor_id=vendor_id,
                vendor_class=vendor_class,
                input_hash=input_hash,
                score=score,
                model_version=model_version,
                previous=previous,  # type: ignore[arg-type]
            )

        event = self.audit_chain.append(
            event_type=AuditEventType.VENDOR_SCORE_RECORDED,
            autonomy_level=self.autonomy_level,
            agent_id=vendor_id,
            payload={
                "vendor_id": vendor_id,
                "vendor_class": vendor_class.value,
                "input_hash": input_hash,
                "score": score,
                "model_version": model_version,
                "gate_verdict": "recorded",
            },
        )
        self._seen[key] = score
        return VendorScoreEntry(
            vendor_id=vendor_id,
            vendor_class=vendor_class,
            input_hash=input_hash,
            score=score,
            model_version=model_version,
            sequence=_sequence_of(self.audit_chain, event),
            event_id=event.event_id,
            drift_detected=False,
            previous_score=None,
        )

    def history_for(
        self,
        *,
        vendor_id: str,
        input_hash: str,
    ) -> list[VendorScoreEntry]:
        out: list[VendorScoreEntry] = []
        for index, event in enumerate(self.audit_chain._events):  # noqa: SLF001
            if event.event_type not in {
                AuditEventType.VENDOR_SCORE_RECORDED,
                AuditEventType.VENDOR_SCORE_DRIFT_DETECTED,
            }:
                continue
            if event.agent_id != vendor_id:
                continue
            payload = event.payload
            if payload.get("input_hash") != input_hash:
                continue
            previous_raw = payload.get("previous_score")
            class_raw = payload.get("vendor_class")
            decoded_class = VendorClass(class_raw) if class_raw is not None else VendorClass.KYC
            out.append(
                VendorScoreEntry(
                    vendor_id=vendor_id,
                    vendor_class=decoded_class,
                    input_hash=input_hash,
                    score=_as_float(payload["score"]),
                    model_version=str(payload["model_version"]),
                    sequence=index,
                    event_id=event.event_id,
                    drift_detected=(event.event_type == AuditEventType.VENDOR_SCORE_DRIFT_DETECTED),
                    previous_score=(_as_float(previous_raw) if previous_raw is not None else None),
                )
            )
        return out

    def _emit_drift(
        self,
        *,
        vendor_id: str,
        vendor_class: VendorClass,
        input_hash: str,
        score: float,
        model_version: str,
        previous: float,
    ) -> VendorScoreEntry:
        event = self.audit_chain.append(
            event_type=AuditEventType.VENDOR_SCORE_DRIFT_DETECTED,
            autonomy_level=self.autonomy_level,
            agent_id=vendor_id,
            payload={
                "vendor_id": vendor_id,
                "vendor_class": vendor_class.value,
                "input_hash": input_hash,
                "score": score,
                "model_version": model_version,
                "previous_score": previous,
                "gate_verdict": "drift_flagged",
            },
        )
        # Update the seen-table to the latest score so a third call with the
        # same drift target does not re-flag against the original score.
        # Operators reviewing the chain see the full sequence regardless.
        self._seen[(vendor_id, input_hash, model_version)] = score
        entry = VendorScoreEntry(
            vendor_id=vendor_id,
            vendor_class=vendor_class,
            input_hash=input_hash,
            score=score,
            model_version=model_version,
            sequence=_sequence_of(self.audit_chain, event),
            event_id=event.event_id,
            drift_detected=True,
            previous_score=previous,
        )
        if self.raise_on_drift:
            raise VendorScoreDriftDetected(
                f"Vendor {vendor_id!r} (class={vendor_class.value}) returned "
                f"score={score} for input_hash={input_hash!r} under "
                f"model_version={model_version!r}; previous score was {previous}. "
                f"Flagged chain entry at sequence {entry.sequence}."
            )
        return entry


# --------------------------------------------------------------------------- #
# Module-private helpers                                                      #
# --------------------------------------------------------------------------- #


def _validate_inputs(
    *,
    vendor_id: str,
    input_hash: str,
    score: float,
    model_version: str,
) -> None:
    if not vendor_id:
        raise ValueError("vendor_id must be a non-empty string")
    if not input_hash:
        raise ValueError("input_hash must be a non-empty string")
    if not model_version:
        raise ValueError("model_version must be a non-empty string")
    if math.isnan(score) or math.isinf(score):
        raise ValueError(f"score must be finite; got {score!r}")
    if not (0.0 <= score <= 1.0):
        raise ValueError(
            f"score must be in [0.0, 1.0] (the canonical risk-score interval); got {score!r}"
        )


def _sequence_of(audit_chain: AuditChain, event: AuditEvent) -> int:
    """Return the 0-based position of ``event`` in the chain."""
    return len(audit_chain._events) - 1  # noqa: SLF001


def _as_float(value: object) -> float:
    """Narrow an Any-from-payload value to float.

    Surfaces a clear error if a chain entry was somehow written with a
    non-numeric score field — we'd rather raise here than silently coerce.
    """
    if isinstance(value, bool):
        # bool is a subclass of int; reject explicitly to catch corruption.
        raise TypeError(f"Expected numeric score, got bool: {value!r}")
    if isinstance(value, (int, float)):
        return float(value)
    raise TypeError(f"Expected numeric score, got {type(value).__name__}")


__all__ = [
    "InMemoryVendorScoreGate",
    "VendorClass",
    "VendorScoreDriftDetected",
    "VendorScoreEntry",
    "VendorScoreGate",
]
