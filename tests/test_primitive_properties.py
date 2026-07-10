"""Property-based invariants for the five hardened primitives (§7 volume tier).

Uses ``hypothesis`` to generate hundreds of cases per property — thousands of
generated cases across the module — pinning the invariants the S1 hardening
established. Marked ``slow`` so they run in the property tier
(``pytest -m "slow or not slow"``), not the fast default loop.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from finserv_agent_audit.governance.audit_chain import AuditChain
from finserv_agent_audit.governance.autonomy_ladder import (
    CriterionAttestation,
    PromotionRequirements,
    check_a2_to_a3_promotion,
)
from finserv_agent_audit.governance.defcon import (
    DEFCON,
    DEFCONMachine,
    DEFCONOverrideRejectedError,
    RiskMetrics,
)
from finserv_agent_audit.governance.effective_challenge_harness import (
    ChallengerIndependence,
    EffectiveChallengeHarness,
)
from finserv_agent_audit.governance.sovereign_veto import (
    SovereignVeto,
    VetoBlockedError,
    VetoReason,
)
from finserv_agent_audit.schemas.audit_event import AuditEventType, AutonomyLevel

pytestmark = pytest.mark.slow

_CRITERIA = (
    "sovereign_veto_load_tested",
    "audit_ledger_running_for",
    "shadow_mode_running_for",
    "circuit_breaker_test_recent",
)


class _Reject:
    def authorize(self, operator_id: str, action: str, context: dict[str, Any]) -> bool:
        return False


class _Allow:
    def authorize(self, operator_id: str, action: str, context: dict[str, Any]) -> bool:
        return True


# --------------------------------------------------------------------------- #
# P1 — level-gate monotonicity + advisory/strict invariants.
# --------------------------------------------------------------------------- #


@settings(max_examples=400)
@given(
    veto=st.booleans(),
    ledger_days=st.integers(min_value=0, max_value=400),
    shadow_days=st.integers(min_value=0, max_value=400),
    cb=st.booleans(),
)
def test_p1_passes_iff_all_criteria_met(
    veto: bool, ledger_days: int, shadow_days: int, cb: bool
) -> None:
    reqs = PromotionRequirements(
        sovereign_veto_load_tested=veto,
        audit_ledger_running_for=timedelta(days=ledger_days),
        shadow_mode_running_for=timedelta(days=shadow_days),
        circuit_breaker_test_recent=cb,
    )
    report = check_a2_to_a3_promotion(reqs)
    all_met = veto and cb and ledger_days >= 90 and shadow_days >= 30
    assert report.passed is all_met
    assert report.advisory is True  # default is always advisory


@settings(max_examples=300)
@given(line=st.integers(min_value=1, max_value=3))
def test_p1_strict_requires_independent_attestation(line: int) -> None:
    reqs = PromotionRequirements(
        sovereign_veto_load_tested=True,
        audit_ledger_running_for=timedelta(days=120),
        shadow_mode_running_for=timedelta(days=45),
        circuit_breaker_test_recent=True,
    )
    atts = {
        k: CriterionAttestation(
            criterion=k,
            attestor_id="x",
            line_of_defense=line,
            attested_at="2026-06-05T00:00:00+00:00",
        )
        for k in _CRITERIA
    }
    report = check_a2_to_a3_promotion(reqs, attestations=atts, require_attestation=True)
    # Strict mode passes ONLY when the attestor is independent (line 2 or 3).
    assert report.passed is (line in (2, 3))
    assert report.advisory is False


# --------------------------------------------------------------------------- #
# P2 — veto: self-clear never succeeds; production never starts w/o authorizer.
# --------------------------------------------------------------------------- #


@settings(max_examples=300, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(agent=st.text(min_size=1, max_size=20))
def test_p2_self_clear_always_blocked(agent: str) -> None:
    veto = SovereignVeto(agent_id=agent, authorizer=_Allow())
    veto.trigger(VetoReason.RISK_LIMIT_BREACH, "monitor", "x")
    with pytest.raises(VetoBlockedError):
        veto.clear(operator_id=agent, reason="self")  # operator == agent
    assert veto.is_vetoed is True


@settings(max_examples=100)
@given(agent=st.text(min_size=1, max_size=20))
def test_p2_production_without_authorizer_always_fails(agent: str) -> None:
    with pytest.raises(ValueError):
        SovereignVeto(agent_id=agent, production=True)


# --------------------------------------------------------------------------- #
# P3 — hash-chain: clean (legacy + hardened) verifies; any in-place tamper fails.
# --------------------------------------------------------------------------- #


@settings(
    max_examples=200, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(n=st.integers(min_value=1, max_value=12), hardened=st.booleans())
def test_p3_clean_chain_verifies(tmp_path_factory: Any, n: int, hardened: bool) -> None:
    d = tmp_path_factory.mktemp("p3clean")
    kwargs: dict[str, Any] = {"log_file": d / "c.jsonl"}
    if hardened:
        kwargs.update(deployer_id="acme", chain_creation_iso="2026-01-01T00:00:00+00:00")
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        chain = AuditChain(**kwargs)
        for i in range(n):
            chain.append(
                event_type=AuditEventType.DECISION_MADE,
                autonomy_level=AutonomyLevel.A2,
                agent_id="zeus",
                payload={"i": i},
            )
        assert chain.verify() is True


@settings(
    max_examples=200, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(data=st.data(), hardened=st.booleans())
def test_p3_inplace_tamper_always_detected(
    tmp_path_factory: Any, data: Any, hardened: bool
) -> None:
    import warnings

    n = data.draw(st.integers(min_value=1, max_value=10))
    d = tmp_path_factory.mktemp("p3tamper")
    kwargs: dict[str, Any] = {"log_file": d / "c.jsonl"}
    if hardened:
        kwargs.update(deployer_id="acme", chain_creation_iso="2026-01-01T00:00:00+00:00")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        chain = AuditChain(**kwargs)
        for i in range(n):
            chain.append(
                event_type=AuditEventType.DECISION_MADE,
                autonomy_level=AutonomyLevel.A2,
                agent_id="zeus",
                payload={"i": i},
            )
        events = chain._events
        idx = data.draw(st.integers(min_value=0, max_value=len(events) - 1))
        object.__setattr__(events[idx], "payload", {"i": "TAMPERED", "n": idx})
        assert chain.verify() is False


# --------------------------------------------------------------------------- #
# P4 — DEFCON: HALT never auto-de-escalates; rejected override stays HALT.
# --------------------------------------------------------------------------- #


@settings(
    max_examples=150, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(dd=st.floats(min_value=0.0, max_value=0.06), dl=st.floats(min_value=0.0, max_value=0.03))
def test_p4_halt_never_auto_deescalates(tmp_path_factory: Any, dd: float, dl: float) -> None:
    d = tmp_path_factory.mktemp("p4")
    machine = DEFCONMachine(state_file=d / "s.json", audit_file=d / "a.jsonl", authorizer=_Reject())
    machine.evaluate(RiskMetrics(portfolio_drawdown=0.30, daily_loss=0.07, consecutive_losses=9))
    assert machine.level == DEFCON.HALT
    # Any benign metrics keep it HALT (no auto de-escalation).
    assert machine.evaluate(RiskMetrics(dd, dl, 0)) == DEFCON.HALT
    with pytest.raises(DEFCONOverrideRejectedError):
        machine.manual_override(DEFCON.NORMAL, operator_id="op", reason="resume")
    assert machine.level == DEFCON.HALT


# --------------------------------------------------------------------------- #
# P5 — effective challenge: identity always rejected; strict requires full att.
# --------------------------------------------------------------------------- #


@settings(max_examples=200)
@given(n=st.integers(min_value=1, max_value=30))
def test_p5_self_challenge_always_rejected(n: int) -> None:
    def f(x: str) -> str:
        return x

    with pytest.raises(ValueError):
        EffectiveChallengeHarness(
            primary_model=f, challenger_model=f, eval_set=[(str(i), str(i)) for i in range(n)]
        )


@settings(max_examples=200)
@given(o=st.booleans(), v=st.booleans(), t=st.booleans())
def test_p5_strict_requires_full_independence(o: bool, v: bool, t: bool) -> None:
    att = ChallengerIndependence(
        challenger_id="c",
        chosen_by="mrm",
        chosen_at="2026-06-05T00:00:00+00:00",
        not_same_owner=o,
        not_same_vendor_family=v,
        not_same_prompt_template=t,
    )
    fully = o and v and t
    if fully:
        h = EffectiveChallengeHarness(
            primary_model=(lambda x: x),
            challenger_model=(lambda x: "z"),
            eval_set=[("a", "a")],
            independence=att,
            require_independence=True,
        )
        assert h.independence is att
    else:
        with pytest.raises(ValueError):
            EffectiveChallengeHarness(
                primary_model=(lambda x: x),
                challenger_model=(lambda x: "z"),
                eval_set=[("a", "a")],
                independence=att,
                require_independence=True,
            )
