"""GOLDEN real-world corpus — fair-lending enforcement matters (§7 credibility tier).

Each fixture is a real, primary-source-cited U.S. fair-lending enforcement
matter-of-record (DOJ Combating Redlining Initiative consent orders + a CFPB
ECOA/Reg-B adverse-action order). The corpus asserts how this library's
controls WOULD have flagged or governed the documented failure shape — what
makes the assurance story undismissable.

**Matters of record only.** Every fact traces to the cited primary source
(verified 2026-06-05). No invented allegations or outcomes. Figures marked
``UNVERIFIED`` in a matter are not asserted as primary-source-confirmed.

Sources:
  - DOJ Civil Rights Division case pages (justice.gov/crt)
  - CFPB consent-order PDF (files.consumerfinance.gov), docket 2023-CFPB-0013
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from finserv_agent_audit.governance.adverse_action_gate import (
    AdverseActionGate,
    AdverseActionKind,
    AdverseActionPacket,
    AdverseActionViolation,
    ReasonCode,
)
from finserv_agent_audit.governance.audit_chain import AuditChain
from finserv_agent_audit.governance.equity_audit import (
    EquityAudit,
    EquityAuditViolation,
    ProtectedClass,
)


@dataclass(frozen=True)
class Matter:
    matter_id: str
    title: str
    date: str  # absolute, verified
    regulators: tuple[str, ...]
    statutes: tuple[str, ...]
    remedy: str
    failure_shape: str
    governance_primitive: str
    primary_source_url: str
    verification: str  # VERIFIED | PARTIAL


# Verified matters-of-record (primary-source URLs confirmed to resolve, 2026-06-05).
MATTERS: tuple[Matter, ...] = (
    Matter(
        matter_id="city-national-redlining-2023",
        title="United States v. City National Bank (C.D. Cal.)",
        date="2023-01-31",  # consent order entered (complaint/proposed order filed 2023-01-12)
        regulators=("DOJ Civil Rights Division", "USAO C.D. Cal."),
        statutes=("ECOA, 15 U.S.C. § 1691 et seq.", "Fair Housing Act, 42 U.S.C. § 3601 et seq."),
        remedy="$31M+ relief ($29.5M loan-subsidy fund + outreach/education/partnerships)",
        failure_shape=(
            "2017–2020: bank avoided marketing/underwriting/originating mortgages in "
            "majority-Black/Hispanic LA County tracts; peers saw >6x application volume."
        ),
        governance_primitive="equity_audit",
        primary_source_url="https://www.justice.gov/crt/case/united-states-v-city-national-bank-cd-cali",
        verification="VERIFIED",
    ),
    Matter(
        matter_id="trustmark-redlining-2021",
        title="United States v. Trustmark National Bank (W.D. Tenn.)",
        date="2021-10-27",  # consent order entered (complaint filed 2021-10-22)
        regulators=("DOJ Civil Rights Division", "CFPB", "OCC"),
        statutes=(
            "Fair Housing Act, 42 U.S.C. § 3601 et seq.",
            "ECOA, 15 U.S.C. § 1691 et seq.",
            "Consumer Financial Protection Act",
        ),
        remedy=(
            "~$9M combined: $3.85M loan-subsidy fund + outreach + $5M CMP "
            "($4M to OCC, $1M to CFPB; OCC NR 2021-109)"
        ),
        failure_shape=(
            "Only 4 of 25 Memphis-area branches in majority-nonwhite neighborhoods, none with an "
            "assigned mortgage loan officer; failed to market/offer/originate in those tracts."
        ),
        governance_primitive="equity_audit",
        primary_source_url="https://www.justice.gov/crt/case/consent-order-united-states-v-trustmark-national-bank-wd-tenn",
        # CMP confirmed via OCC News Release 2021-109 (2026-06-05 Chrome primary-source pass)
        verification="VERIFIED",
    ),
    Matter(
        matter_id="fnb-pennsylvania-redlining-2024",
        title="United States v. First National Bank of Pennsylvania (M.D.N.C.)",
        date="2024-02-13",  # consent order entered (complaint filed 2024-02-05, US + NC)
        regulators=("DOJ Civil Rights Division", "North Carolina DOJ"),
        statutes=("ECOA, 15 U.S.C. § 1691 et seq.", "Fair Housing Act, 42 U.S.C. § 3601 et seq."),
        remedy="$13.5M total ($11.75M loan-subsidy fund + partnerships/outreach/counseling)",
        failure_shape=(
            "2017–2021: branches/loan officers located outside majority-Black/Hispanic "
            "Charlotte & Winston-Salem neighborhoods; peers lent there at 2–4x its rate."
        ),
        governance_primitive="equity_audit",
        primary_source_url="https://www.justice.gov/crt/case/united-states-v-first-national-bank-pennsylvania-md-nc",
        verification="VERIFIED",
    ),
    Matter(
        matter_id="citibank-armenian-adverse-action-2023",
        title="In the Matter of Citibank, N.A. (CFPB Consent Order, File No. 2023-CFPB-0013)",
        date="2023-11-08",  # filed (verified verbatim on every PDF page)
        regulators=("CFPB",),
        statutes=(
            "ECOA, 15 U.S.C. § 1691(a); Reg B, 12 C.F.R. §§ 1002.4(a), 1002.6(b)",
            "ECOA, 15 U.S.C. § 1691(d); Reg B, 12 C.F.R. § 1002.9(a)-(b) (adverse-action notice)",
            "CFPA, 12 U.S.C. §§ 5481, 5536",
        ),
        remedy="$25.9M total ($24.5M CMP + $1.4M consumer redress)",
        failure_shape=(
            "2015–2021: extra scrutiny / more frequent DENIAL of applicants associated with "
            "Armenian national origin (surnames ending -ian/-yan); denied applicants received "
            "PRETEXTUAL adverse-action reason codes masking the national-origin basis."
        ),
        governance_primitive="adverse_action_gate",
        primary_source_url="https://www.consumerfinance.gov/enforcement/actions/citibank-n-a/",
        verification="VERIFIED",
    ),
)

_ALLOWED_PRIMITIVES = {"equity_audit", "adverse_action_gate", "protected_class_proxy_detector"}


# --------------------------------------------------------------------------- #
# Corpus integrity — matters of record, primary-source-cited.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("m", MATTERS, ids=[m.matter_id for m in MATTERS])
def test_matter_is_primary_source_cited(m: Matter) -> None:
    assert m.primary_source_url.startswith("https://")
    assert m.statutes and all(s.strip() for s in m.statutes)
    # Date is an absolute ISO date.
    datetime.strptime(m.date, "%Y-%m-%d")
    assert m.governance_primitive in _ALLOWED_PRIMITIVES
    assert m.verification in {"VERIFIED", "PARTIAL"}


# --------------------------------------------------------------------------- #
# Citibank (adverse-action) — the gate would flag the pretextual-reason failure.
# --------------------------------------------------------------------------- #


def _packet(
    reasons: tuple[ReasonCode, ...], *, validation: str, cra: str | None
) -> AdverseActionPacket:
    return AdverseActionPacket(
        decision_id="d1",
        consumer_id="c1",
        action_kind=AdverseActionKind.CREDIT_DENIED,
        primary_reasons=reasons,
        model_id="m1",
        model_version="1.0",
        model_validation_id=validation,
        cra_used=cra,
        decision_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
    )


def test_citibank_pretextual_reasons_are_blocked() -> None:
    """A denial with a generic/pretextual reason and no validation is blocked.

    Maps the Citibank failure: pretextual denial codes masking the real basis.
    """
    gate = AdverseActionGate()
    pretextual = (
        ReasonCode(
            code="GEN",
            plain_language="model decision",  # a generic fragment -> FCRA-REASONS-MISSING
            factor_contribution=1.0,
            upstream_feature_ids=("f1",),
        ),
    )
    packet = _packet(pretextual, validation="", cra=None)
    with pytest.raises(AdverseActionViolation) as exc:
        gate.evaluate(packet)
    assert "FCRA-REASONS-MISSING" in exc.value.codes


def test_citibank_specific_reasons_with_validation_pass() -> None:
    """A denial with specific, traceable reasons + validation + CRA passes."""
    gate = AdverseActionGate()
    specific = (
        ReasonCode(
            code="DTI",
            plain_language="debt-to-income ratio above program maximum",
            factor_contribution=0.6,
            upstream_feature_ids=("dti_ratio",),
        ),
    )
    packet = _packet(specific, validation="val-2026-001", cra="Equifax")
    gate.evaluate(packet)  # must NOT raise


# --------------------------------------------------------------------------- #
# Redlining matters (equity_audit) — the gate would flag an ungoverned
# protected-class lending surface (no current model validation).
# --------------------------------------------------------------------------- #


class _Inventory:
    def __init__(self, current: bool) -> None:
        self._current = current

    def has_current_validation(self, model_id: str, model_version: str) -> bool:
        return self._current


def _equity_gate(current_validation: bool, tmp_path) -> EquityAudit:  # type: ignore[no-untyped-def]
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        chain = AuditChain(log_file=tmp_path / "eq.jsonl")
    return EquityAudit(audit_chain=chain, model_inventory=_Inventory(current_validation))


def test_redlining_ungoverned_protected_surface_is_blocked(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """A protected lending surface without a current validation fails closed.

    Maps the redlining failure shape: a protected-class lending decision surface
    operating without a governed, validated equitable-coverage control.
    """
    gate = _equity_gate(current_validation=False, tmp_path=tmp_path)
    with pytest.raises(EquityAuditViolation):
        gate.check(
            surface="credit_underwriting_decision",
            protected_classes={ProtectedClass.RACE, ProtectedClass.NATIONAL_ORIGIN},
            model_id="m1",
            model_version="1.0",
            agent_id="agent-1",
        )


def test_redlining_governed_protected_surface_passes(tmp_path) -> None:  # type: ignore[no-untyped-def]
    gate = _equity_gate(current_validation=True, tmp_path=tmp_path)
    result = gate.check(
        surface="credit_underwriting_decision",
        protected_classes={ProtectedClass.RACE},
        model_id="m1",
        model_version="1.0",
        agent_id="agent-1",
    )
    assert result.passed is True
