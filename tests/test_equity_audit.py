"""Tests for the EquityAudit ECOA / Reg B pre-flight gate.

Test surface: happy path (validated model + protected surface produces a
recorded chain entry), fail-closed posture (missing model-validation evidence
raises EquityAuditViolation), non-lending-surface bypass, the protected-class
attribute set is enforced, audit-chain emission on every check.

Regulatory anchor:
    - ECOA / Reg B § 1002 — protected-class enumeration
    - SR 11-7 — model-validation evidence requirement
    - ADR-0010 — fail-closed pre-flight gate at the agent boundary
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from finserv_agent_audit.governance.equity_audit import (
    EquityAudit,
    EquityAuditViolation,
    ProtectedClass,
)
from finserv_agent_audit.schemas.audit_event import (
    AuditChain,
    AuditEventType,
    AutonomyLevel,
)


# A minimal ModelInventory-shaped stub so this test file does not depend on
# the 2C.a implementation landing first. The runtime gate accepts anything
# that exposes the ``has_current_validation`` method per duck-typing.
@dataclass
class _StubInventory:
    valid_ids: frozenset[tuple[str, str]]

    def has_current_validation(self, model_id: str, model_version: str) -> bool:
        return (model_id, model_version) in self.valid_ids


@pytest.fixture
def chain(tmp_path: Path) -> AuditChain:
    return AuditChain(log_file=tmp_path / "audit.jsonl")


# --------------------------------------------------------------------------- #
# Happy path                                                                  #
# --------------------------------------------------------------------------- #


class TestHappyPath:
    def test_validated_lending_decision_passes(self, chain: AuditChain) -> None:
        inventory = _StubInventory(valid_ids=frozenset({("credit_v2", "2.1.0")}))
        gate = EquityAudit(audit_chain=chain, model_inventory=inventory)

        result = gate.check(
            surface="credit_underwriting_decision",
            protected_classes={ProtectedClass.RACE, ProtectedClass.SEX},
            model_id="credit_v2",
            model_version="2.1.0",
            agent_id="loan_underwriter",
        )

        assert result.passed is True
        assert result.event_id is not None
        assert len(chain._events) == 1

    def test_non_lending_surface_bypasses_validation(self, chain: AuditChain) -> None:
        # Non-protected surface — no model validation required, still audited.
        inventory = _StubInventory(valid_ids=frozenset())
        gate = EquityAudit(audit_chain=chain, model_inventory=inventory)

        result = gate.check(
            surface="marketing_open_audience",  # not in PROTECTED_LENDING_SURFACES
            protected_classes=set(),
            model_id=None,
            model_version=None,
            agent_id="marketer",
        )

        assert result.passed is True
        assert len(chain._events) == 1

    def test_emits_compliance_check_event_type(self, chain: AuditChain) -> None:
        inventory = _StubInventory(valid_ids=frozenset({("m", "1")}))
        gate = EquityAudit(audit_chain=chain, model_inventory=inventory)
        gate.check(
            surface="credit_underwriting_decision",
            protected_classes={ProtectedClass.AGE},
            model_id="m",
            model_version="1",
            agent_id="agent",
        )
        assert chain._events[0].event_type == AuditEventType.COMPLIANCE_CHECK

    def test_default_autonomy_level_is_a2(self, chain: AuditChain) -> None:
        inventory = _StubInventory(valid_ids=frozenset({("m", "1")}))
        gate = EquityAudit(audit_chain=chain, model_inventory=inventory)
        gate.check(
            surface="credit_underwriting_decision",
            protected_classes={ProtectedClass.RACE},
            model_id="m",
            model_version="1",
            agent_id="agent",
        )
        assert chain._events[0].autonomy_level == AutonomyLevel.A2


# --------------------------------------------------------------------------- #
# Fail-closed posture                                                         #
# --------------------------------------------------------------------------- #


class TestFailClosed:
    def test_missing_model_id_on_protected_surface_raises(self, chain: AuditChain) -> None:
        inventory = _StubInventory(valid_ids=frozenset())
        gate = EquityAudit(audit_chain=chain, model_inventory=inventory)

        with pytest.raises(EquityAuditViolation) as exc:
            gate.check(
                surface="credit_underwriting_decision",
                protected_classes={ProtectedClass.RACE},
                model_id=None,
                model_version=None,
                agent_id="agent",
            )
        assert "ECOA-VALIDATION-MISSING" in str(exc.value)

    def test_unvalidated_model_on_protected_surface_raises(self, chain: AuditChain) -> None:
        inventory = _StubInventory(valid_ids=frozenset())  # nothing validated
        gate = EquityAudit(audit_chain=chain, model_inventory=inventory)

        with pytest.raises(EquityAuditViolation) as exc:
            gate.check(
                surface="risk_based_pricing",
                protected_classes={ProtectedClass.SEX},
                model_id="pricing_v1",
                model_version="1.0.0",
                agent_id="pricer",
            )
        assert "ECOA-VALIDATION-MISSING" in str(exc.value)

    def test_violation_records_chain_entry_before_raising(self, chain: AuditChain) -> None:
        inventory = _StubInventory(valid_ids=frozenset())
        gate = EquityAudit(audit_chain=chain, model_inventory=inventory)

        with pytest.raises(EquityAuditViolation):
            gate.check(
                surface="credit_underwriting_decision",
                protected_classes={ProtectedClass.RACE},
                model_id=None,
                model_version=None,
                agent_id="agent",
            )
        # The violation is on the chain — auditable even if the caller
        # swallows the exception.
        assert len(chain._events) == 1
        assert chain._events[0].payload["gate_verdict"] == "violation"
        assert chain._events[0].payload["reason_code"] == "ECOA-VALIDATION-MISSING"

    def test_empty_protected_classes_with_lending_surface_still_requires_model(
        self, chain: AuditChain
    ) -> None:
        # A lending surface still requires a validated model even if the
        # caller does not yet know which protected-class dimensions apply.
        inventory = _StubInventory(valid_ids=frozenset())
        gate = EquityAudit(audit_chain=chain, model_inventory=inventory)

        with pytest.raises(EquityAuditViolation):
            gate.check(
                surface="credit_underwriting_decision",
                protected_classes=set(),
                model_id=None,
                model_version=None,
                agent_id="agent",
            )


# --------------------------------------------------------------------------- #
# Protected class enumeration                                                 #
# --------------------------------------------------------------------------- #


class TestProtectedClassEnum:
    def test_ecoa_protected_classes_present(self) -> None:
        # ECOA / Reg B enumeration must include race, color, religion, national
        # origin, sex, marital status, age.
        expected = {
            "race",
            "color",
            "religion",
            "national_origin",
            "sex",
            "marital_status",
            "age",
        }
        actual = {member.value for member in ProtectedClass}
        assert expected.issubset(actual)


# --------------------------------------------------------------------------- #
# Surface configuration                                                       #
# --------------------------------------------------------------------------- #


class TestSurfaceConfig:
    def test_known_protected_surface(self, chain: AuditChain) -> None:
        inventory = _StubInventory(valid_ids=frozenset({("m", "1")}))
        gate = EquityAudit(audit_chain=chain, model_inventory=inventory)
        # Each protected surface is gated.
        for surface in [
            "credit_underwriting_decision",
            "credit_limit_assignment",
            "risk_based_pricing",
        ]:
            chain._events.clear()  # noqa: SLF001
            result = gate.check(
                surface=surface,
                protected_classes={ProtectedClass.RACE},
                model_id="m",
                model_version="1",
                agent_id="agent",
            )
            assert result.passed is True
