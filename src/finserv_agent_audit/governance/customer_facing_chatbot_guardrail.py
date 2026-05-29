"""CustomerFacingChatbotGuardrail — three-layer customer-facing-chatbot interception (ADR-0026).

Banking chatbots sit at the point of action — a wrong answer can trigger
a money movement, a security change, or a customer commitment the
institution is then liable for. The settled-liability anchor of record
is **Moffatt v. Air Canada**, BC Civil Resolution Tribunal, February 14,
2024, awarding CA$812.02 against Air Canada after its customer-facing
chatbot fabricated a retroactive bereavement-refund policy that did not
exist in any approved source. The tribunal rejected the carrier's
argument that the chatbot was a separate legal entity: the operator was
liable for the chatbot's representations to the customer. Subsequent
incidents reinforce the pattern — the Microsoft Bing demo misreporting
Gap's quarterly margins; the Google Bard launch demo misstating which
telescope took the first picture of an exoplanet, with a reported
intraday market-cap impact in the tens of billions. Reported financial
impact from chatbot fabrications in financial services is in the tens of
billions globally in 2024, with hallucination rates up to ~41% in
finance-domain queries [UNVERIFIED — composite industry-press figures,
not a primary-source statistic].

The guardrail wraps the agent with three layered checks. The decision
order is *handoff -> RAG -> fabrication-pattern*: an
action-class that requires a human handoff stops the pipeline before any
RAG or fabrication-pattern check runs, because the chatbot is not
authorized to make the commitment in the first place. A response that
passes the action-class arm then has to ground each factual claim in a
cited source from the deployer's policy corpus, and the cited source
must itself be in the corpus and semantically consistent with the
response. A response with neither a money-movement nor an in-corpus
citation is checked for Air-Canada-style fabrication patterns ("our
policy states", "we offer", "you can receive a refund").

The three arms map to three concrete failure shapes:

  1. **Policy-grounded RAG check.** Every response carrying a factual
     claim cites at least one ``PolicySource`` from the deployer's
     corpus. The guardrail validates the cited source exists, and that
     the response is semantically consistent with the cited source.
     Semantic-consistency for the v1.3 reference ships as a simple
     keyword-overlap heuristic; the ``RAGSourceCheck`` Protocol is the
     seam for deployers to plug in embedding-based checks.

  2. **Money-movement / commitment-class interception.** Five
     action-classes require a human handoff before the chatbot can
     issue a commitment: ``MONEY_MOVEMENT``, ``COMMITMENT``,
     ``SECURITY_CHANGE``, ``LEGAL_REPRESENTATION``,
     ``REGULATORY_DISCLOSURE``. Deployers narrow or widen the set on
     the constructor.

  3. **No-fabricated-policy assertion.** The guardrail checks for
     Air-Canada-style fabrication-signal patterns ("our policy states",
     "we offer", "you can receive" without a cited source), and for a
     known-bad-pattern set (refund-policy fabrications, late-payment
     forgiveness fabrications, fee-waiver fabrications). The
     known-good-responses allow-list (a frozenset of approved
     responses, or a bloom filter once the corpus grows large enough to
     justify it) short-circuits the pattern check.

Every ``evaluate`` call emits one ``AuditEventType.COMPLIANCE_CHECK``
audit-chain entry naming the decision, the reason code, the cited
source IDs, the session id, and the action class (when supplied). The
audit entry is written **before** any exception is raised so a
regulator inquiring about a blocked response can still reconstruct what
the chatbot tried to say.

Regulatory + precedent anchors:
    - Moffatt v. Air Canada, BC Civil Resolution Tribunal, Feb 14, 2024
      (operator liable for chatbot fabricated policy; CA$812.02 award)
    - NIST AI 600-1 — Confabulation risk category
    - EU AI Act Art. 13 — transparency obligations toward customer-
      facing users; Art. 14 — human oversight of high-risk systems
    - CFPB Circular 2022-03 — adverse-action notices for AI-driven
      consumer decisions (forced into the REGULATORY_DISCLOSURE
      handoff arm)
    - finserv-agent-audit ADR-0009 (FCRA adverse-action gate)
    - finserv-agent-audit ADR-0017 (audit-chain retention, privilege,
      discovery posture for FSI)
    - finserv-agent-audit ADR-0026 (this pattern's design ADR)

> Patterns are software, not legal advice. Consult counsel for
> applicability of the Air Canada precedent to your jurisdiction; the
> guardrail is a reference implementation of the operator-side defense
> the precedent indicates, not a substitute for the policy and process
> the institution layers on top.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable

from finserv_agent_audit.governance.subject_id import SubjectIdHasher
from finserv_agent_audit.schemas.audit_event import (
    AuditChain,
    AuditEventType,
    AutonomyLevel,
)

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Exceptions                                                                  #
# --------------------------------------------------------------------------- #


class RequiresHumanHandoff(RuntimeError):  # noqa: N818
    """Raised when the agent attempts an action that requires human handoff.

    The exception is raised only when the caller passes
    ``raise_on_handoff=True``; the default path returns a
    ``GuardrailResponse`` with ``decision=REQUIRES_HUMAN_HANDOFF`` so
    the caller can route the customer to a human agent without an
    exception traversing the chatbot's normal-flow code paths.
    """


class FabricatedPolicyDetected(RuntimeError):  # noqa: N818
    """Raised when a fabricated-policy pattern or off-corpus citation is detected.

    The exception is raised only when the caller passes
    ``raise_on_block=True``; the default path returns a
    ``GuardrailResponse`` with ``decision=BLOCK`` so the caller can
    surface a deterministic fallback ("Let me connect you to a
    human agent.") instead of propagating the exception to the
    customer.
    """


# --------------------------------------------------------------------------- #
# Enums + value types                                                         #
# --------------------------------------------------------------------------- #


class ActionClass(Enum):
    """Action classes that require a human handoff before chatbot commitment.

    The classes correspond to the failure shapes the Air Canada
    precedent + subsequent incidents put on the operator: money moves,
    contractual commitments, security-relevant changes, legal-opinion
    statements, and regulatory-notice issuance.
    """

    MONEY_MOVEMENT = "MONEY_MOVEMENT"
    COMMITMENT = "COMMITMENT"
    SECURITY_CHANGE = "SECURITY_CHANGE"
    LEGAL_REPRESENTATION = "LEGAL_REPRESENTATION"
    REGULATORY_DISCLOSURE = "REGULATORY_DISCLOSURE"


DEFAULT_HANDOFF_CLASSES: tuple[ActionClass, ...] = (
    ActionClass.MONEY_MOVEMENT,
    ActionClass.COMMITMENT,
    ActionClass.SECURITY_CHANGE,
    ActionClass.LEGAL_REPRESENTATION,
    ActionClass.REGULATORY_DISCLOSURE,
)


class GuardrailDecision(Enum):
    """The four decisions the guardrail can return."""

    ALLOW = "allow"
    BLOCK = "block"
    REQUIRES_HUMAN_HANDOFF = "requires_human_handoff"
    REVISE = "revise"


# --------------------------------------------------------------------------- #
# Policy corpus + RAG check Protocol                                          #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class PolicySource:
    """One entry in the deployer's policy corpus.

    Fields:
        source_id: Stable identifier the chatbot cites (e.g. POL-WIRE-001).
        source_url: URL or document locator; surfaced to the customer
            when the response is revised back into a corpus-grounded form.
        title: Human-readable title.
        body: The full policy text the guardrail uses for the
            semantic-consistency check.
        trust_level: Free-text trust band (e.g. ``primary``,
            ``secondary``, ``draft``); deployers can plug their own
            tiering into the RAG check.
    """

    source_id: str
    source_url: str
    title: str
    body: str
    trust_level: str = "primary"


@dataclass
class PolicyCorpus:
    """The deployer-provided policy source-of-truth.

    A small wrapper around a list of ``PolicySource`` objects with an
    O(1) lookup by ``source_id``. The wrapper exists so a deployer can
    later subclass with a database-backed or vector-store-backed
    implementation without changing the guardrail.
    """

    sources: list[PolicySource]
    _index: dict[str, PolicySource] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._index = {s.source_id: s for s in self.sources}

    def get(self, source_id: str) -> PolicySource | None:
        return self._index.get(source_id)

    def __contains__(self, source_id: object) -> bool:
        if not isinstance(source_id, str):
            return False
        return source_id in self._index

    def __len__(self) -> int:
        return len(self.sources)


@runtime_checkable
class RAGSourceCheck(Protocol):
    """Protocol seam — deployers plug in stronger semantic-consistency checks.

    The v1.3 default implementation is a keyword-overlap heuristic
    (see ``_KeywordOverlapRAGCheck``). A deployer with an embedding
    backend supplies an object whose ``is_consistent`` method returns
    True when the chatbot response is consistent with the cited
    ``PolicySource``.
    """

    def is_consistent(self, response: str, source: PolicySource) -> bool: ...


# --------------------------------------------------------------------------- #
# Reference RAG check — keyword overlap (v1.3 default)                        #
# --------------------------------------------------------------------------- #


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")

# Tokens too common to carry signal. Kept short on purpose — the
# reference check is meant to be replaced for production, not tuned.
_STOPWORDS: frozenset[str] = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "of",
        "to",
        "for",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "in",
        "on",
        "at",
        "by",
        "with",
        "as",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "we",
        "you",
        "your",
        "our",
        "i",
        "they",
        "them",
        "their",
        "from",
        "but",
        "if",
        "so",
        "do",
        "does",
        "did",
        "not",
        "no",
        "yes",
        "have",
        "has",
        "had",
        "will",
        "would",
        "should",
        "can",
        "may",
        "might",
        "shall",
        "what",
        "which",
        "who",
        "whom",
        "how",
        "when",
        "where",
        "why",
        "any",
        "all",
        "some",
        "more",
        "most",
    }
)


def _tokenize(text: str) -> set[str]:
    return {
        token.lower()
        for token in _TOKEN_RE.findall(text)
        if token.lower() not in _STOPWORDS and len(token) >= 2
    }


@dataclass
class _KeywordOverlapRAGCheck:
    """Stdlib-only reference RAG check used when the deployer plugs in nothing.

    Computes Jaccard overlap between content tokens in the response and
    in the source body, with stopwords removed. A response is consistent
    when at least ``min_overlap_ratio`` of its content tokens appear in
    the source body. This is intentionally weak — the docstring on
    ``RAGSourceCheck`` directs deployers to plug in an embedding-based
    check for production use.

    The ``min_overlap_ratio`` of 0.30 was chosen so that a one-sentence
    response paraphrasing a policy sentence still passes (typically
    50%+ overlap once stopwords are stripped), while a response on a
    completely unrelated topic fails (typically <10% overlap).
    """

    min_overlap_ratio: float = 0.30

    def is_consistent(self, response: str, source: PolicySource) -> bool:
        response_tokens = _tokenize(response)
        if not response_tokens:
            # No content tokens at all — chitchat. The fabrication
            # arm is the place to catch problems here; the RAG arm
            # has nothing to say.
            return True
        source_tokens = _tokenize(source.body + " " + source.title)
        if not source_tokens:
            return False
        intersection = response_tokens & source_tokens
        ratio = len(intersection) / len(response_tokens)
        return ratio >= self.min_overlap_ratio


# --------------------------------------------------------------------------- #
# Fabrication-pattern detection                                               #
# --------------------------------------------------------------------------- #


# Patterns the framework treats as fabrication-shaped when they appear
# in a response that does not also carry an in-corpus citation. The
# regex set is deliberately narrow — the goal is high precision on
# Air-Canada-shaped fabrications, not high recall on every plausible
# misstatement. False positives here are paid by a customer hand-off,
# which is the right side of the trade-off.
_FABRICATION_SIGNAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bour\s+policy\s+(states|is|allows|requires|says)\b", re.IGNORECASE),
    re.compile(r"\bwe\s+offer\b", re.IGNORECASE),
    re.compile(r"\byou\s+(can|may)\s+receive\b", re.IGNORECASE),
    re.compile(r"\bwe\s+(will|can)\s+(waive|refund|credit|reverse)\b", re.IGNORECASE),
    re.compile(r"\bretroactive\s+(refund|credit|adjustment)\b", re.IGNORECASE),
    re.compile(r"\b(eligible|entitled)\s+to\s+a\s+(refund|credit|waiver)\b", re.IGNORECASE),
    re.compile(r"\bwe\s+guarantee\b", re.IGNORECASE),
)

# Air-Canada-specific known-bad patterns. These are blocked even when
# the response carries a citation, because the deployer-side discipline
# is that the chatbot does not promise refunds / waivers / forgiveness
# autonomously — those flow through the handoff arm by policy.
_KNOWN_BAD_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bbereavement\s+refund\b", re.IGNORECASE),
    re.compile(r"\blate[-\s]payment\s+forgiveness\b", re.IGNORECASE),
    re.compile(
        r"\bfee\s+waive(d|r)\b(?!.*\b(human\s+agent|specialist|representative)\b)",
        re.IGNORECASE,
    ),
)

# Regex that, when matched, signals "this response carries a factual
# policy claim". When this matches and no citation is provided, the
# RAG arm escalates to BLOCK rather than waving the chitchat through.
_FACTUAL_CLAIM_PATTERN: re.Pattern[str] = re.compile(
    r"(\$\d|"
    r"\bfee\b|\brate\b|\bhours?\b|\bpolicy\b|\bAPY\b|\bAPR\b|\brefund\b|"
    r"\bdeposit\b|\bwithdrawal\b|\btransfer\b|\bwaive\b|\boffer\b|"
    r"\bentitled\b|\beligible\b|\binterest\b|\boverdraft\b|\bminimum\b)",
    re.IGNORECASE,
)


# --------------------------------------------------------------------------- #
# GuardrailResponse                                                           #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class GuardrailResponse:
    """The decision returned by ``CustomerFacingChatbotGuardrail.evaluate``.

    ``agent_response`` is echoed back so a caller using the guardrail
    inline gets the cleared-or-revised text in one structure.
    ``suggested_revision`` is populated when the decision is REVISE —
    typically a corpus-grounded restatement that the chatbot can return
    in place of the original draft.
    """

    decision: GuardrailDecision
    agent_response: str
    cited_source_ids: tuple[str, ...]
    reason_code: str | None = None
    suggested_revision: str | None = None
    handoff_path: str | None = None
    event_id: str | None = None


# --------------------------------------------------------------------------- #
# The guardrail                                                               #
# --------------------------------------------------------------------------- #


class CustomerFacingChatbotGuardrail:
    """Three-layered guardrail for customer-facing banking chatbots.

    Wire the guardrail at the chatbot-response-emission boundary: every
    prospective response calls ``evaluate`` before reaching the
    customer. The guardrail emits one
    ``AuditEventType.COMPLIANCE_CHECK`` event per call (allow, block,
    handoff, or revise) so the audit chain becomes the operator-side
    evidence record the Air Canada precedent indicates.

    The autonomy-level default is A2 (human on the loop) — the chatbot
    runs autonomously per turn but a human supervisor can override or
    take over. Deployers running A3 (human notified) layer their own
    notification surface above this guardrail; A4 (autonomous) is not
    recommended for customer-facing chatbots and the guardrail does
    not change its decisions when ``autonomy_level=AutonomyLevel.A4``
    is passed — the audit record will name the level the deployer
    asserted, not relax the check.
    """

    def __init__(
        self,
        policy_corpus: PolicyCorpus,
        audit_chain: AuditChain | None = None,
        rag_source_check: RAGSourceCheck | None = None,
        handoff_action_classes: Iterable[ActionClass] = DEFAULT_HANDOFF_CLASSES,
        known_good_responses: frozenset[str] = frozenset(),
        autonomy_level: AutonomyLevel = AutonomyLevel.A2,
        default_handoff_path: str = "human-agent-queue",
        subject_id_hasher: SubjectIdHasher | None = None,
    ) -> None:
        self._corpus = policy_corpus
        self._chain = audit_chain
        self._rag_check: RAGSourceCheck = rag_source_check or _KeywordOverlapRAGCheck()
        self._handoff_classes: frozenset[ActionClass] = frozenset(handoff_action_classes)
        self._known_good = known_good_responses
        self._autonomy_level = autonomy_level
        self._default_handoff_path = default_handoff_path
        self._subject_id_hasher = subject_id_hasher

    # ------------------------------------------------------------------ #
    # Public entry point                                                 #
    # ------------------------------------------------------------------ #

    def evaluate(
        self,
        *,
        agent_response: str,
        cited_source_ids: list[str],
        customer_id: str,
        agent_id: str,
        session_id: str,
        intended_action_class: ActionClass | None = None,
        intended_action_payload: dict[str, object] | None = None,
        raise_on_handoff: bool = False,
        raise_on_block: bool = False,
    ) -> GuardrailResponse:
        """Run all three arms and return a ``GuardrailResponse``.

        Decision order:

        1. **Action-class handoff arm.** If the deployer flagged the
           intended action class as handoff-required, the guardrail
           returns REQUIRES_HUMAN_HANDOFF immediately. The chatbot
           never gets a chance to fabricate a policy when it is not
           authorized to make the commitment in the first place.

        2. **Known-good short-circuit.** Approved responses (the
           ``known_good_responses`` set) skip the rest of the
           pipeline; this is the place to wire the bloom-filter
           short-circuit when the approved-response corpus grows large
           enough to justify it.

        3. **RAG citation arm.** Every cited source must exist in the
           corpus; the cited source must be semantically consistent
           with the response. Off-corpus citation -> BLOCK. Inconsistent
           citation -> REVISE.

        4. **Fabrication-pattern arm.** Responses without a citation
           are checked for Air-Canada-style factual claims and
           known-bad patterns. Match -> BLOCK.

        5. **Allow.** Anything that survives the four arms above.
        """
        self._validate_inputs(
            agent_response=agent_response,
            customer_id=customer_id,
            agent_id=agent_id,
            session_id=session_id,
        )

        # --- 1. Action-class handoff ----------------------------------- #
        if intended_action_class is not None and intended_action_class in self._handoff_classes:
            response = self._build_response(
                decision=GuardrailDecision.REQUIRES_HUMAN_HANDOFF,
                agent_response=agent_response,
                cited_source_ids=cited_source_ids,
                reason_code="ACTION-CLASS-REQUIRES-HANDOFF",
                handoff_path=self._default_handoff_path,
            )
            event_id = self._emit_audit(
                response=response,
                customer_id=customer_id,
                agent_id=agent_id,
                session_id=session_id,
                action_class=intended_action_class,
                action_payload=intended_action_payload,
            )
            response = self._with_event_id(response, event_id)
            if raise_on_handoff:
                raise RequiresHumanHandoff(
                    f"ACTION-CLASS-REQUIRES-HANDOFF: action_class="
                    f"{intended_action_class.value} requires human handoff "
                    f"(session_id={session_id!r}); handoff recorded at "
                    f"event_id={event_id!r}."
                )
            return response

        # --- 2. Known-good short-circuit ------------------------------- #
        if agent_response in self._known_good:
            response = self._build_response(
                decision=GuardrailDecision.ALLOW,
                agent_response=agent_response,
                cited_source_ids=cited_source_ids,
                reason_code=None,
            )
            event_id = self._emit_audit(
                response=response,
                customer_id=customer_id,
                agent_id=agent_id,
                session_id=session_id,
                action_class=intended_action_class,
                action_payload=intended_action_payload,
            )
            return self._with_event_id(response, event_id)

        # --- 3a. RAG arm: every cited source must exist in corpus ------ #
        for src_id in cited_source_ids:
            if src_id not in self._corpus:
                response = self._build_response(
                    decision=GuardrailDecision.BLOCK,
                    agent_response=agent_response,
                    cited_source_ids=cited_source_ids,
                    reason_code="RAG-OFF-CORPUS-CITATION",
                )
                event_id = self._emit_audit(
                    response=response,
                    customer_id=customer_id,
                    agent_id=agent_id,
                    session_id=session_id,
                    action_class=intended_action_class,
                    action_payload=intended_action_payload,
                )
                response = self._with_event_id(response, event_id)
                if raise_on_block:
                    raise FabricatedPolicyDetected(
                        f"RAG-OFF-CORPUS-CITATION: cited source_id={src_id!r} is "
                        f"not in the deployer policy corpus "
                        f"(session_id={session_id!r}); block recorded at "
                        f"event_id={event_id!r}."
                    )
                return response

        # --- 3b. RAG arm: each cited source must be consistent --------- #
        if cited_source_ids:
            inconsistent = self._first_inconsistent_source(
                response_text=agent_response,
                cited_source_ids=cited_source_ids,
            )
            if inconsistent is not None:
                suggested = self._build_suggested_revision(inconsistent)
                response = self._build_response(
                    decision=GuardrailDecision.REVISE,
                    agent_response=agent_response,
                    cited_source_ids=cited_source_ids,
                    reason_code="RAG-CITATION-INCONSISTENT",
                    suggested_revision=suggested,
                )
                event_id = self._emit_audit(
                    response=response,
                    customer_id=customer_id,
                    agent_id=agent_id,
                    session_id=session_id,
                    action_class=intended_action_class,
                    action_payload=intended_action_payload,
                )
                return self._with_event_id(response, event_id)

        # --- 3c. RAG arm: no citation but response carries a claim ----- #
        if not cited_source_ids and _FACTUAL_CLAIM_PATTERN.search(agent_response):
            # Distinguish between an explicit fabrication-signal and a
            # bare factual claim; both block but the reason code
            # differs so deployers can tune monitoring.
            reason = self._fabrication_reason(agent_response)
            response = self._build_response(
                decision=GuardrailDecision.BLOCK,
                agent_response=agent_response,
                cited_source_ids=cited_source_ids,
                reason_code=reason,
            )
            event_id = self._emit_audit(
                response=response,
                customer_id=customer_id,
                agent_id=agent_id,
                session_id=session_id,
                action_class=intended_action_class,
                action_payload=intended_action_payload,
            )
            response = self._with_event_id(response, event_id)
            if raise_on_block:
                raise FabricatedPolicyDetected(
                    f"{reason}: factual claim emitted without an in-corpus citation "
                    f"(session_id={session_id!r}); block recorded at "
                    f"event_id={event_id!r}."
                )
            return response

        # --- 4. Fabrication-pattern arm (known-bad patterns regardless) --- #
        for pattern in _KNOWN_BAD_PATTERNS:
            if pattern.search(agent_response):
                response = self._build_response(
                    decision=GuardrailDecision.BLOCK,
                    agent_response=agent_response,
                    cited_source_ids=cited_source_ids,
                    reason_code="FABRICATED-POLICY-PATTERN",
                )
                event_id = self._emit_audit(
                    response=response,
                    customer_id=customer_id,
                    agent_id=agent_id,
                    session_id=session_id,
                    action_class=intended_action_class,
                    action_payload=intended_action_payload,
                )
                response = self._with_event_id(response, event_id)
                if raise_on_block:
                    raise FabricatedPolicyDetected(
                        f"FABRICATED-POLICY-PATTERN: response matches a known-bad "
                        f"fabrication pattern "
                        f"(session_id={session_id!r}); block recorded at "
                        f"event_id={event_id!r}."
                    )
                return response

        # --- 5. Allow -------------------------------------------------- #
        response = self._build_response(
            decision=GuardrailDecision.ALLOW,
            agent_response=agent_response,
            cited_source_ids=cited_source_ids,
            reason_code=None,
        )
        event_id = self._emit_audit(
            response=response,
            customer_id=customer_id,
            agent_id=agent_id,
            session_id=session_id,
            action_class=intended_action_class,
            action_payload=intended_action_payload,
        )
        return self._with_event_id(response, event_id)

    # ------------------------------------------------------------------ #
    # Helpers                                                            #
    # ------------------------------------------------------------------ #

    def _validate_inputs(
        self,
        *,
        agent_response: str,
        customer_id: str,
        agent_id: str,
        session_id: str,
    ) -> None:
        if not agent_response or not agent_response.strip():
            raise ValueError("agent_response must be a non-empty, non-whitespace string")
        if not customer_id:
            raise ValueError("customer_id must be a non-empty string")
        if not agent_id:
            raise ValueError("agent_id must be a non-empty string")
        if not session_id:
            raise ValueError("session_id must be a non-empty string")

    def _first_inconsistent_source(
        self,
        *,
        response_text: str,
        cited_source_ids: list[str],
    ) -> PolicySource | None:
        for src_id in cited_source_ids:
            source = self._corpus.get(src_id)
            if source is None:
                # Already handled in the prior arm; defensive.
                continue
            if not self._rag_check.is_consistent(response_text, source):
                return source
        return None

    def _build_suggested_revision(self, source: PolicySource) -> str:
        # The reference revision points the customer at the source.
        # A production deployer can plug a stronger generator in by
        # subclassing the guardrail and overriding this method.
        return (
            f"Refer to {source.title} ({source.source_url}) for the "
            f"current terms; the original chatbot response did not "
            f"match the cited source."
        )

    def _fabrication_reason(self, response_text: str) -> str:
        for pattern in _FABRICATION_SIGNAL_PATTERNS:
            if pattern.search(response_text):
                return "FABRICATED-POLICY-PATTERN"
        return "RAG-NO-CITATION-WITH-CLAIM"

    def _build_response(
        self,
        *,
        decision: GuardrailDecision,
        agent_response: str,
        cited_source_ids: list[str],
        reason_code: str | None,
        suggested_revision: str | None = None,
        handoff_path: str | None = None,
    ) -> GuardrailResponse:
        return GuardrailResponse(
            decision=decision,
            agent_response=agent_response,
            cited_source_ids=tuple(cited_source_ids),
            reason_code=reason_code,
            suggested_revision=suggested_revision,
            handoff_path=handoff_path,
        )

    def _with_event_id(
        self, response: GuardrailResponse, event_id: str | None
    ) -> GuardrailResponse:
        # GuardrailResponse is frozen; rebuild with event_id populated.
        return GuardrailResponse(
            decision=response.decision,
            agent_response=response.agent_response,
            cited_source_ids=response.cited_source_ids,
            reason_code=response.reason_code,
            suggested_revision=response.suggested_revision,
            handoff_path=response.handoff_path,
            event_id=event_id,
        )

    def _emit_audit(
        self,
        *,
        response: GuardrailResponse,
        customer_id: str,
        agent_id: str,
        session_id: str,
        action_class: ActionClass | None,
        action_payload: dict[str, object] | None,
    ) -> str | None:
        if self._chain is None:
            return None
        payload: dict[str, object] = {
            "regulation": "Air Canada (Moffatt v. Air Canada, BC CRT 2024-02-14)",
            "obligation": "operator-side chatbot guardrail",
            "citation": "ADR-0026",
            "decision": response.decision.value,
            "reason_code": response.reason_code,
            "cited_source_ids": list(response.cited_source_ids),
            "session_id": session_id,
        }
        if self._subject_id_hasher is not None:
            hashed = self._subject_id_hasher.hash_subject(customer_id)
            payload["customer_id_hash_b64"] = hashed.hash_b64
            payload["customer_id_pepper_version"] = hashed.pepper_version
            payload["customer_id_algorithm"] = hashed.algorithm
        else:
            logger.warning(
                "CustomerFacingChatbotGuardrail emitting COMPLIANCE_CHECK with "
                "cleartext customer_id=%r — GLBA Safeguards Rule (NPI at rest) "
                "and GDPR Art. 17 (right to erasure) risk. Inject a "
                "SubjectIdHasher to hash customer_id before payload write.",
                customer_id,
            )
            payload["customer_id"] = customer_id
        if action_class is not None:
            payload["action_class"] = action_class.value
        if action_payload is not None:
            payload["action_payload"] = action_payload
        if response.handoff_path is not None:
            payload["handoff_path"] = response.handoff_path
        if response.suggested_revision is not None:
            payload["suggested_revision"] = response.suggested_revision
        event = self._chain.append(
            event_type=AuditEventType.COMPLIANCE_CHECK,
            autonomy_level=self._autonomy_level,
            agent_id=agent_id,
            payload=payload,
        )
        event_id: str = event.event_id
        return event_id


__all__ = [
    "ActionClass",
    "CustomerFacingChatbotGuardrail",
    "DEFAULT_HANDOFF_CLASSES",
    "FabricatedPolicyDetected",
    "GuardrailDecision",
    "GuardrailResponse",
    "PolicyCorpus",
    "PolicySource",
    "RAGSourceCheck",
    "RequiresHumanHandoff",
]
