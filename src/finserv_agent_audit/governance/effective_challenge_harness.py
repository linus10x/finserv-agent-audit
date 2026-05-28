"""EffectiveChallengeHarness — frontier-API effective challenge (v1.3, ADR-0022).

SR 11-7 names "effective challenge" as a non-optional element of model
risk management. Section V.1 expects the second-line MRM function to
demonstrate a credible test of the primary model — a parallel
implementation, a competing methodology, or a published benchmark
the primary's performance can be measured against. When the primary
model is a frontier API the bank does not control (Anthropic's
Claude, OpenAI's GPT, Google's Gemini, etc.), the standard parallel-
implementation challenger is unavailable: the bank cannot reproduce
the model's weights, cannot inspect its training data, and cannot
audit its inference path.

OCC Bulletin 2026-13 acknowledged that the agencies have not scoped
agentic AI under the historical model-risk framework. The bulletin
narrowed the scope of OCC 2011-12 to non-agentic AI; the model-risk
governance principles continue to apply via SR 11-7 + the
interagency Statement of Principles, but the operational gap is
real. This harness fills the gap by running a deployer-supplied
challenger LLM against the primary on a fixed evaluation set and
emitting a ``ChallengeReport`` artifact second-line MRM can attach
to a validation file.

**The contract.** Constructor takes:

- ``primary_model``: callable ``(input: str) -> Any``.
- ``challenger_model``: callable ``(input: str) -> Any``. The
  challenger is the deployer's choice — a smaller open-source model,
  a different frontier-API vendor, a rule-based heuristic, or a
  domain-specific fine-tune. The framework does not prescribe.
- ``eval_set``: ``list[tuple[input, expected_output]]``. The MRM
  function curates this set; the framework does not synthesize it.
- ``audit_chain``: optional. When supplied (the production path)
  every ``run`` emits one ``AuditEventType.MODEL_VALIDATED`` entry
  (the v1.1 enum member tied to ADR-0007 SR 11-7 model risk
  management).

``run()`` evaluates both models on the eval set; computes per-row
agreement with the expected output and per-row agreement between
the two models; aggregates accuracy + disagreement rate; emits a
``ChallengeReport`` with up to 20 sample disagreements (the first
twenty in eval-set order) and a recommendation in the
``{"accept_primary", "investigate", "escalate"}`` band.

The recommendation thresholds are deployer-overridable but default
to:

- ``disagreement_rate <= 0.05`` -> ``accept_primary``
- ``0.05 < disagreement_rate <= 0.30`` -> ``investigate``
- ``disagreement_rate > 0.30`` -> ``escalate``

The eval-set hash (SHA-256 over the JSON-serialized eval set with
sorted keys) is recorded on the chain entry so a regulator-facing
investigation can attest the eval set used for the validation was
the one named in the artifact.

**Stdlib-only.** No ``sklearn`` / ``pandas``. The harness uses
``hashlib.sha256`` + ``json.dumps`` for the eval-set hash and stdlib
``zip`` / ``sum`` for the aggregates.

**Known limitations.**

- The challenger is only as good as the deployer's choice. A
  challenger that always agrees with the primary by construction
  (same vendor, same model family, same prompt template) produces a
  rubber-stamp report. ADR-0022 documents the challenger-design
  question.
- The harness does not interpret the disagreements. A high
  disagreement rate is a signal the MRM function investigates; it
  is not a verdict on the primary's correctness.
- The eval-set hash binds the artifact to the eval set, not to the
  model versions. A model-version pin is the deployer's
  responsibility and lives in the model-inventory entry per
  ADR-0007.

See ADR-0022 (``docs/adr/0022-effective-challenge-harness.md``) for
the full decision record, the SR 11-7 + OCC 2026-13 scope-exclusion
citations, and the regulatory mapping.

> Reference pattern, not legal advice. Model-risk-management
> characterizations are summaries; consult qualified counsel and
> qualified MRM practitioners.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from finserv_agent_audit.schemas.audit_event import (
    AuditChain,
    AuditEventType,
    AutonomyLevel,
)

_METHODOLOGY_ID: str = "effective_challenge_v1"

# Recommendation-band thresholds. Tuneable per ADR-0022 §
# "Calibration"; deployer overrides on the constructor.
_DEFAULT_ACCEPT_THRESHOLD: float = 0.05
_DEFAULT_INVESTIGATE_THRESHOLD: float = 0.30

_MAX_DISAGREEMENT_EXAMPLES: int = 20

Recommendation = Literal["accept_primary", "investigate", "escalate"]

ModelCallable = Callable[[str], Any]


@dataclass(frozen=True)
class ChallengeReport:
    """Artifact second-line MRM attaches to a validation file.

    Fields are MRM-canonical: primary + challenger accuracy against
    the expected outputs, the disagreement rate between the two
    models, a capped list of disagreement examples (input, primary
    output, challenger output), the methodology identifier, the
    eval-set SHA-256 hash for replay attestation, and a
    ``recommendation`` in the three-band MRM vocabulary.
    """

    primary_accuracy: float
    challenger_accuracy: float
    disagreement_rate: float
    disagreement_examples: list[tuple[Any, Any, Any]] = field(default_factory=list)
    methodology: str = _METHODOLOGY_ID
    eval_set_hash: str = ""
    recommendation: Recommendation = "accept_primary"


class EffectiveChallengeHarness:
    """SR 11-7 effective-challenge harness for frontier-API primaries (ADR-0022).

    Wire at the second-line MRM boundary: the MRM analyst supplies a
    primary (the production frontier-API call), a challenger (their
    chosen counter-evidence model), and a curated eval set. Each
    ``run`` emits one ``MODEL_VALIDATED`` chain entry carrying the
    aggregated accuracy + disagreement statistics; the returned
    ``ChallengeReport`` is the attachable artifact.
    """

    def __init__(
        self,
        *,
        primary_model: ModelCallable,
        challenger_model: ModelCallable,
        eval_set: list[tuple[Any, Any]],
        audit_chain: AuditChain | None = None,
        accept_threshold: float = _DEFAULT_ACCEPT_THRESHOLD,
        investigate_threshold: float = _DEFAULT_INVESTIGATE_THRESHOLD,
        autonomy_level: AutonomyLevel = AutonomyLevel.A2,
    ) -> None:
        self.primary_model = primary_model
        self.challenger_model = challenger_model
        self.eval_set = eval_set
        self.audit_chain = audit_chain
        self.accept_threshold = accept_threshold
        self.investigate_threshold = investigate_threshold
        self.autonomy_level = autonomy_level

    # ------------------------------------------------------------------ #
    # Public surface                                                     #
    # ------------------------------------------------------------------ #

    def run(
        self,
        *,
        agent_id: str = "effective_challenge_harness",
        actor_id: str | None = None,
    ) -> ChallengeReport:
        """Evaluate both models on the eval set. Returns a ``ChallengeReport``.

        Raises:
            ValueError: When the eval set is empty.
        """
        if not self.eval_set:
            raise ValueError("eval_set must contain at least one (input, expected) pair")

        primary_correct = 0
        challenger_correct = 0
        disagreements: list[tuple[Any, Any, Any]] = []
        disagreement_count = 0

        for input_value, expected in self.eval_set:
            primary_output = self.primary_model(input_value)
            challenger_output = self.challenger_model(input_value)
            if primary_output == expected:
                primary_correct += 1
            if challenger_output == expected:
                challenger_correct += 1
            if primary_output != challenger_output:
                disagreement_count += 1
                if len(disagreements) < _MAX_DISAGREEMENT_EXAMPLES:
                    disagreements.append((input_value, primary_output, challenger_output))

        n = len(self.eval_set)
        primary_accuracy = primary_correct / n
        challenger_accuracy = challenger_correct / n
        disagreement_rate = disagreement_count / n
        recommendation = self._recommend(disagreement_rate)
        eval_set_hash = self._hash_eval_set()

        report = ChallengeReport(
            primary_accuracy=primary_accuracy,
            challenger_accuracy=challenger_accuracy,
            disagreement_rate=disagreement_rate,
            disagreement_examples=disagreements,
            methodology=_METHODOLOGY_ID,
            eval_set_hash=eval_set_hash,
            recommendation=recommendation,
        )

        if self.audit_chain is not None:
            self._emit_model_validated(
                report=report,
                agent_id=agent_id,
                actor_id=actor_id,
            )

        return report

    # ------------------------------------------------------------------ #
    # Internals                                                          #
    # ------------------------------------------------------------------ #

    def _recommend(self, disagreement_rate: float) -> Recommendation:
        if disagreement_rate <= self.accept_threshold:
            return "accept_primary"
        if disagreement_rate <= self.investigate_threshold:
            return "investigate"
        return "escalate"

    def _hash_eval_set(self) -> str:
        # Serialize each tuple as a list to keep JSON-encodable; the
        # eval set is hashed in order so callers reordering the rows
        # produce a different hash (which is intentional — the order
        # of evaluation is part of the artifact).
        serialized = json.dumps(
            [[i, e] for i, e in self.eval_set],
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _emit_model_validated(
        self,
        *,
        report: ChallengeReport,
        agent_id: str,
        actor_id: str | None,
    ) -> None:
        # Disagreement examples are redacted to ``str(...)`` in the
        # chain payload so callers who pass non-JSON-serializable
        # input/output types do not break the chain.
        payload: dict[str, Any] = {
            "adr_reference": "ADR-0022",
            "methodology": report.methodology,
            "n_eval_rows": len(self.eval_set),
            "primary_accuracy": report.primary_accuracy,
            "challenger_accuracy": report.challenger_accuracy,
            "disagreement_rate": report.disagreement_rate,
            "eval_set_hash": report.eval_set_hash,
            "recommendation": report.recommendation,
            "disagreement_examples_count": len(report.disagreement_examples),
            "disagreement_examples_preview": [
                {
                    "input": str(i),
                    "primary": str(p),
                    "challenger": str(c),
                }
                for (i, p, c) in report.disagreement_examples
            ],
        }
        if self.audit_chain is None:
            return
        self.audit_chain.append(
            event_type=AuditEventType.MODEL_VALIDATED,
            autonomy_level=self.autonomy_level,
            agent_id=agent_id,
            payload=payload,
            actor_id=actor_id,
        )


__all__ = [
    "ChallengeReport",
    "EffectiveChallengeHarness",
    "ModelCallable",
    "Recommendation",
]
