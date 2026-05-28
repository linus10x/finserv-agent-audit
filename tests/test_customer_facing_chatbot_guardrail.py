"""Tests for the CustomerFacingChatbotGuardrail (v1.3 — ADR-0026).

The guardrail wraps a customer-facing banking chatbot with three layered
checks:

1. Policy-grounded RAG citation check — every response cites a real
   source from the deployer's policy corpus; the cited source must
   exist and be semantically consistent with the response.
2. Money-movement / commitment-class interception — certain
   action-classes require a human handoff before any chatbot
   commitment reaches the customer.
3. No-fabricated-policy assertion — Air-Canada-pattern fabrications
   (refund policies, fee waivers, late-payment forgiveness, "we offer"
   / "our policy states" / "you can receive" without citation) are
   blocked.

Regulatory anchor:
    - Moffatt v. Air Canada, BC Civil Resolution Tribunal, February 14,
      2024 — operator liable for chatbot fabricated refund policy
    - NIST AI 600-1 (Confabulation risk category)
    - EU AI Act Art. 13 (transparency to customer-facing users)
    - ADR-0026
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from finserv_agent_audit.governance.customer_facing_chatbot_guardrail import (
    ActionClass,
    CustomerFacingChatbotGuardrail,
    FabricatedPolicyDetected,
    GuardrailDecision,
    GuardrailResponse,
    PolicyCorpus,
    PolicySource,
    RAGSourceCheck,
    RequiresHumanHandoff,
)
from finserv_agent_audit.schemas.audit_event import (
    AuditChain,
    AuditEventType,
    AutonomyLevel,
)

# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #


@pytest.fixture
def chain(tmp_path: Path) -> AuditChain:
    return AuditChain(log_file=tmp_path / "audit.jsonl")


@pytest.fixture
def policy_corpus() -> PolicyCorpus:
    """A small deployer policy corpus with realistic banking text."""
    return PolicyCorpus(
        sources=[
            PolicySource(
                source_id="POL-WIRE-001",
                source_url="https://bank.example.com/policy/wire-transfers",
                title="Wire Transfer Policy",
                body=(
                    "Outbound wire transfers require two-factor authentication "
                    "and a phone confirmation for amounts above $10,000. "
                    "Processing window is 9 AM to 4 PM Eastern on business days. "
                    "Wire fees are $25 domestic and $45 international."
                ),
                trust_level="primary",
            ),
            PolicySource(
                source_id="POL-FEE-014",
                source_url="https://bank.example.com/policy/fee-schedule",
                title="Consumer Fee Schedule",
                body=(
                    "Monthly maintenance fee is $12, waived with a $1,500 daily "
                    "minimum balance. Overdraft fee is $35 per item. "
                    "Stop-payment requests are $30."
                ),
                trust_level="primary",
            ),
            PolicySource(
                source_id="POL-HOURS-002",
                source_url="https://bank.example.com/policy/hours",
                title="Branch Hours",
                body=(
                    "Branch hours are 9 AM to 5 PM Monday through Friday "
                    "and 9 AM to 1 PM Saturday. Closed on federal holidays."
                ),
                trust_level="primary",
            ),
        ]
    )


# --------------------------------------------------------------------------- #
# Happy path                                                                  #
# --------------------------------------------------------------------------- #


class TestHappyPath:
    def test_cited_real_source_with_consistent_response_allows(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        response = guardrail.evaluate(
            agent_response=(
                "Our branch hours are 9 AM to 5 PM Monday through Friday and 9 AM to 1 PM Saturday."
            ),
            cited_source_ids=["POL-HOURS-002"],
            customer_id="cust-001",
            agent_id="chatbot-v3",
            session_id="sess-abc",
        )
        assert response.decision is GuardrailDecision.ALLOW
        assert response.reason_code is None or response.reason_code == ""

    def test_happy_path_emits_compliance_check_event(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        guardrail.evaluate(
            agent_response=(
                "Wire transfers above $10,000 require two-factor authentication "
                "and a phone confirmation."
            ),
            cited_source_ids=["POL-WIRE-001"],
            customer_id="cust-002",
            agent_id="chatbot-v3",
            session_id="sess-abd",
        )
        assert len(chain._events) == 1
        event = chain._events[0]
        assert event.event_type == AuditEventType.COMPLIANCE_CHECK
        assert event.payload["decision"] == "allow"
        assert event.payload["cited_source_ids"] == ["POL-WIRE-001"]

    def test_default_autonomy_level_is_a2(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        guardrail.evaluate(
            agent_response=("Branch hours are 9 AM to 5 PM Monday through Friday."),
            cited_source_ids=["POL-HOURS-002"],
            customer_id="cust-003",
            agent_id="chatbot-v3",
            session_id="sess-ace",
        )
        assert chain._events[0].autonomy_level == AutonomyLevel.A2


# --------------------------------------------------------------------------- #
# Policy-grounded RAG check                                                   #
# --------------------------------------------------------------------------- #


class TestRAGSourceCheck:
    def test_cited_source_not_in_corpus_blocks(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        with pytest.raises(FabricatedPolicyDetected) as exc:
            guardrail.evaluate(
                agent_response="The fee for that is $5.",
                cited_source_ids=["POL-DOES-NOT-EXIST"],
                customer_id="cust-004",
                agent_id="chatbot-v3",
                session_id="sess-acf",
                raise_on_block=True,
            )
        assert "POL-DOES-NOT-EXIST" in str(exc.value)
        # Audit-chain entry written before the raise.
        assert len(chain._events) == 1
        assert chain._events[0].payload["decision"] == "block"
        assert chain._events[0].payload["reason_code"] == "RAG-OFF-CORPUS-CITATION"

    def test_response_not_in_corpus_returns_block_without_raise(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        response = guardrail.evaluate(
            agent_response="The fee for that is $5.",
            cited_source_ids=["POL-DOES-NOT-EXIST"],
            customer_id="cust-005",
            agent_id="chatbot-v3",
            session_id="sess-acg",
        )
        assert response.decision is GuardrailDecision.BLOCK
        assert response.reason_code == "RAG-OFF-CORPUS-CITATION"

    def test_response_inconsistent_with_cited_source_returns_revise(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        # The cited source is the branch-hours policy; the response is
        # about exchange-rate stuff with zero keyword overlap.
        response = guardrail.evaluate(
            agent_response=(
                "Foreign currency exchange happens through correspondent "
                "rails settled overnight on Singapore time."
            ),
            cited_source_ids=["POL-HOURS-002"],
            customer_id="cust-006",
            agent_id="chatbot-v3",
            session_id="sess-ach",
        )
        assert response.decision is GuardrailDecision.REVISE
        assert response.reason_code == "RAG-CITATION-INCONSISTENT"
        # A suggested revision points back to the corpus.
        assert response.suggested_revision is not None

    def test_no_citation_with_factual_claim_blocks(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        response = guardrail.evaluate(
            agent_response="Our policy states we waive the overdraft fee on first occurrence.",
            cited_source_ids=[],
            customer_id="cust-007",
            agent_id="chatbot-v3",
            session_id="sess-aci",
        )
        # No citation + factual policy claim = fabricated-policy pattern.
        assert response.decision is GuardrailDecision.BLOCK
        assert response.reason_code in {
            "FABRICATED-POLICY-PATTERN",
            "RAG-NO-CITATION-WITH-CLAIM",
        }


# --------------------------------------------------------------------------- #
# Money-movement / commitment interception                                    #
# --------------------------------------------------------------------------- #


class TestActionClassInterception:
    def test_money_movement_requires_human_handoff(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        response = guardrail.evaluate(
            agent_response=(
                "I have initiated the $500 transfer from your checking "
                "account to your savings account."
            ),
            cited_source_ids=["POL-WIRE-001"],
            customer_id="cust-008",
            agent_id="chatbot-v3",
            session_id="sess-acj",
            intended_action_class=ActionClass.MONEY_MOVEMENT,
            intended_action_payload={"amount_usd": 500, "type": "internal_transfer"},
        )
        assert response.decision is GuardrailDecision.REQUIRES_HUMAN_HANDOFF
        assert response.reason_code == "ACTION-CLASS-REQUIRES-HANDOFF"
        assert response.handoff_path is not None
        assert "human" in response.handoff_path.lower() or "agent" in response.handoff_path.lower()

    def test_money_movement_raises_when_requested(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        with pytest.raises(RequiresHumanHandoff):
            guardrail.evaluate(
                agent_response="I will move $1,000 right now for you.",
                cited_source_ids=["POL-WIRE-001"],
                customer_id="cust-009",
                agent_id="chatbot-v3",
                session_id="sess-ack",
                intended_action_class=ActionClass.MONEY_MOVEMENT,
                intended_action_payload={"amount_usd": 1000},
                raise_on_handoff=True,
            )

    def test_commitment_class_late_fee_waiver_requires_handoff(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        response = guardrail.evaluate(
            agent_response="We will waive the late fee for this billing cycle.",
            cited_source_ids=["POL-FEE-014"],
            customer_id="cust-010",
            agent_id="chatbot-v3",
            session_id="sess-acl",
            intended_action_class=ActionClass.COMMITMENT,
            intended_action_payload={"commitment_type": "fee_waiver"},
        )
        assert response.decision is GuardrailDecision.REQUIRES_HUMAN_HANDOFF
        assert response.reason_code == "ACTION-CLASS-REQUIRES-HANDOFF"

    def test_security_change_requires_handoff(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        response = guardrail.evaluate(
            agent_response="I have reset your password. A new one is on the way.",
            cited_source_ids=["POL-WIRE-001"],
            customer_id="cust-011",
            agent_id="chatbot-v3",
            session_id="sess-acm",
            intended_action_class=ActionClass.SECURITY_CHANGE,
            intended_action_payload={"change_type": "password_reset"},
        )
        assert response.decision is GuardrailDecision.REQUIRES_HUMAN_HANDOFF

    def test_legal_representation_requires_handoff(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        response = guardrail.evaluate(
            agent_response=(
                "Based on the facts you described, you are entitled to a refund under our policy."
            ),
            cited_source_ids=["POL-FEE-014"],
            customer_id="cust-012",
            agent_id="chatbot-v3",
            session_id="sess-acn",
            intended_action_class=ActionClass.LEGAL_REPRESENTATION,
            intended_action_payload={"claim_type": "entitlement_opinion"},
        )
        assert response.decision is GuardrailDecision.REQUIRES_HUMAN_HANDOFF

    def test_regulatory_disclosure_requires_handoff(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        response = guardrail.evaluate(
            agent_response="This action is an adverse-action notice under FCRA.",
            cited_source_ids=["POL-FEE-014"],
            customer_id="cust-013",
            agent_id="chatbot-v3",
            session_id="sess-aco",
            intended_action_class=ActionClass.REGULATORY_DISCLOSURE,
            intended_action_payload={"notice_type": "adverse_action"},
        )
        assert response.decision is GuardrailDecision.REQUIRES_HUMAN_HANDOFF

    def test_handoff_class_subset_customizable(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        # Deployer only routes MONEY_MOVEMENT through handoff —
        # SECURITY_CHANGE flows through some other control plane.
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
            handoff_action_classes=(ActionClass.MONEY_MOVEMENT,),
        )
        response = guardrail.evaluate(
            agent_response="I have updated your MFA settings.",
            cited_source_ids=["POL-WIRE-001"],
            customer_id="cust-014",
            agent_id="chatbot-v3",
            session_id="sess-acp",
            intended_action_class=ActionClass.SECURITY_CHANGE,
            intended_action_payload={"change_type": "mfa_update"},
        )
        # SECURITY_CHANGE is not in the deployer's handoff set on this
        # guardrail instance, so the action-class arm does not fire.
        # The other arms (RAG + fabrication patterns) still run.
        assert response.decision is not GuardrailDecision.REQUIRES_HUMAN_HANDOFF


# --------------------------------------------------------------------------- #
# No-fabricated-policy assertion                                              #
# --------------------------------------------------------------------------- #


class TestFabricationPatterns:
    def test_air_canada_refund_pattern_blocks(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        # The Moffatt v. Air Canada chatbot fabricated a "retroactive
        # bereavement-refund" policy. The shape: an unprompted refund
        # promise unsupported by any policy source.
        response = guardrail.evaluate(
            agent_response=(
                "You can receive a retroactive refund within 90 days "
                "by submitting the request through our portal."
            ),
            cited_source_ids=[],
            customer_id="cust-015",
            agent_id="chatbot-v3",
            session_id="sess-acq",
        )
        assert response.decision is GuardrailDecision.BLOCK
        assert response.reason_code in {
            "FABRICATED-POLICY-PATTERN",
            "RAG-NO-CITATION-WITH-CLAIM",
        }

    def test_we_offer_without_citation_blocks(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        response = guardrail.evaluate(
            agent_response="We offer a special 4.5% APY on new accounts.",
            cited_source_ids=[],
            customer_id="cust-016",
            agent_id="chatbot-v3",
            session_id="sess-acr",
        )
        assert response.decision is GuardrailDecision.BLOCK

    def test_known_good_response_passes(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        approved = "Branch hours are 9 AM to 5 PM Monday through Friday and 9 AM to 1 PM Saturday."
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
            known_good_responses=frozenset({approved}),
        )
        response = guardrail.evaluate(
            agent_response=approved,
            cited_source_ids=["POL-HOURS-002"],
            customer_id="cust-017",
            agent_id="chatbot-v3",
            session_id="sess-acs",
        )
        assert response.decision is GuardrailDecision.ALLOW


# --------------------------------------------------------------------------- #
# Custom RAGSourceCheck plug-in                                               #
# --------------------------------------------------------------------------- #


@dataclass
class _AlwaysConsistentRAG:
    """Deployer-supplied stub that always confirms semantic consistency.

    Demonstrates the Protocol seam: a real deployment plugs in an
    embedding-based check; the test plugs in a constant.
    """

    def is_consistent(
        self,
        response: str,
        source: PolicySource,
    ) -> bool:
        del response, source  # unused — this stub is constant
        return True


@dataclass
class _AlwaysInconsistentRAG:
    def is_consistent(
        self,
        response: str,
        source: PolicySource,
    ) -> bool:
        del response, source
        return False


class TestCustomRAGSourceCheck:
    def test_custom_rag_check_overrides_default(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        custom: RAGSourceCheck = _AlwaysConsistentRAG()
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
            rag_source_check=custom,
        )
        # The response has zero keyword overlap with the cited source,
        # but the custom check returns True so the response passes.
        response = guardrail.evaluate(
            agent_response="The lobby has soft seating and complimentary coffee.",
            cited_source_ids=["POL-HOURS-002"],
            customer_id="cust-018",
            agent_id="chatbot-v3",
            session_id="sess-act",
        )
        assert response.decision is GuardrailDecision.ALLOW

    def test_custom_inconsistent_rag_returns_revise(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        custom: RAGSourceCheck = _AlwaysInconsistentRAG()
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
            rag_source_check=custom,
        )
        response = guardrail.evaluate(
            agent_response=("Branch hours are 9 AM to 5 PM Monday through Friday."),
            cited_source_ids=["POL-HOURS-002"],
            customer_id="cust-019",
            agent_id="chatbot-v3",
            session_id="sess-acu",
        )
        # The text is otherwise consistent; the plugged-in check is the
        # one that fires REVISE.
        assert response.decision is GuardrailDecision.REVISE


# --------------------------------------------------------------------------- #
# Edge cases                                                                  #
# --------------------------------------------------------------------------- #


class TestEdgeCases:
    def test_empty_agent_response_rejected(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        with pytest.raises(ValueError):
            guardrail.evaluate(
                agent_response="",
                cited_source_ids=["POL-HOURS-002"],
                customer_id="cust-020",
                agent_id="chatbot-v3",
                session_id="sess-acv",
            )

    def test_whitespace_only_agent_response_rejected(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        with pytest.raises(ValueError):
            guardrail.evaluate(
                agent_response="   \n\t  ",
                cited_source_ids=["POL-HOURS-002"],
                customer_id="cust-021",
                agent_id="chatbot-v3",
                session_id="sess-acw",
            )

    def test_empty_policy_corpus_with_any_citation_blocks(self, chain: AuditChain) -> None:
        empty = PolicyCorpus(sources=[])
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=empty,
            audit_chain=chain,
        )
        response = guardrail.evaluate(
            agent_response="The fee is $5.",
            cited_source_ids=["ANY-ID"],
            customer_id="cust-022",
            agent_id="chatbot-v3",
            session_id="sess-acx",
        )
        # No corpus to ground against, citation falls off-corpus.
        assert response.decision is GuardrailDecision.BLOCK

    def test_chitchat_response_with_no_factual_claim_passes(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        response = guardrail.evaluate(
            agent_response="Hello, how can I help you today?",
            cited_source_ids=[],
            customer_id="cust-023",
            agent_id="chatbot-v3",
            session_id="sess-acy",
        )
        # Pure greeting carries no factual claim — should not block.
        assert response.decision is GuardrailDecision.ALLOW

    def test_guardrail_response_dataclass_is_immutable(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        response = guardrail.evaluate(
            agent_response=("Branch hours are 9 AM to 5 PM Monday through Friday."),
            cited_source_ids=["POL-HOURS-002"],
            customer_id="cust-024",
            agent_id="chatbot-v3",
            session_id="sess-acz",
        )
        with pytest.raises((AttributeError, TypeError)):
            response.decision = GuardrailDecision.BLOCK  # type: ignore[misc]

    def test_guardrail_without_audit_chain_still_evaluates(
        self, policy_corpus: PolicyCorpus
    ) -> None:
        # Audit chain is optional — deployers without an in-process chain
        # can still use the guardrail and route audit elsewhere.
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=None,
        )
        response = guardrail.evaluate(
            agent_response=("Branch hours are 9 AM to 5 PM Monday through Friday."),
            cited_source_ids=["POL-HOURS-002"],
            customer_id="cust-025",
            agent_id="chatbot-v3",
            session_id="sess-ada",
        )
        assert isinstance(response, GuardrailResponse)


# --------------------------------------------------------------------------- #
# Audit-chain emission across decision paths                                  #
# --------------------------------------------------------------------------- #


class TestAuditEmissionEachPath:
    def test_revise_path_emits_event(self, chain: AuditChain, policy_corpus: PolicyCorpus) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        guardrail.evaluate(
            agent_response="Singapore correspondent overnight settlement.",
            cited_source_ids=["POL-HOURS-002"],
            customer_id="cust-026",
            agent_id="chatbot-v3",
            session_id="sess-adb",
        )
        assert len(chain._events) == 1
        assert chain._events[0].payload["decision"] == "revise"

    def test_handoff_path_emits_event(self, chain: AuditChain, policy_corpus: PolicyCorpus) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        guardrail.evaluate(
            agent_response="I will transfer the funds now.",
            cited_source_ids=["POL-WIRE-001"],
            customer_id="cust-027",
            agent_id="chatbot-v3",
            session_id="sess-adc",
            intended_action_class=ActionClass.MONEY_MOVEMENT,
            intended_action_payload={"amount_usd": 200},
        )
        assert len(chain._events) == 1
        assert chain._events[0].payload["decision"] == "requires_human_handoff"
        assert chain._events[0].payload["action_class"] == "MONEY_MOVEMENT"

    def test_fabrication_block_path_emits_event(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        guardrail.evaluate(
            agent_response="We offer a special discount today.",
            cited_source_ids=[],
            customer_id="cust-028",
            agent_id="chatbot-v3",
            session_id="sess-add",
        )
        assert len(chain._events) == 1
        assert chain._events[0].payload["decision"] == "block"

    def test_session_id_present_in_payload(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        guardrail.evaluate(
            agent_response=("Branch hours are 9 AM to 5 PM Monday through Friday."),
            cited_source_ids=["POL-HOURS-002"],
            customer_id="cust-029",
            agent_id="chatbot-v3",
            session_id="sess-ade",
        )
        assert chain._events[0].payload["session_id"] == "sess-ade"


# --------------------------------------------------------------------------- #
# Input validation                                                            #
# --------------------------------------------------------------------------- #


class TestInputValidation:
    def test_empty_customer_id_rejected(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        with pytest.raises(ValueError):
            guardrail.evaluate(
                agent_response="Branch hours are 9 to 5.",
                cited_source_ids=["POL-HOURS-002"],
                customer_id="",
                agent_id="chatbot-v3",
                session_id="sess-adf",
            )

    def test_empty_agent_id_rejected(self, chain: AuditChain, policy_corpus: PolicyCorpus) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        with pytest.raises(ValueError):
            guardrail.evaluate(
                agent_response="Branch hours are 9 to 5.",
                cited_source_ids=["POL-HOURS-002"],
                customer_id="cust-030",
                agent_id="",
                session_id="sess-adg",
            )

    def test_empty_session_id_rejected(
        self, chain: AuditChain, policy_corpus: PolicyCorpus
    ) -> None:
        guardrail = CustomerFacingChatbotGuardrail(
            policy_corpus=policy_corpus,
            audit_chain=chain,
        )
        with pytest.raises(ValueError):
            guardrail.evaluate(
                agent_response="Branch hours are 9 to 5.",
                cited_source_ids=["POL-HOURS-002"],
                customer_id="cust-031",
                agent_id="chatbot-v3",
                session_id="",
            )
