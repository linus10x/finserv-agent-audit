"""AL-PROBE re-authored as committed tests (S1 hardening, 2026-06-05).

The G-SIB-scale assurance catalog (2026-06-04) ran five adversarial probes against
the runtime primitives in this library via ephemeral ``/tmp`` scripts that no
longer exist. This module re-authors each probe as a committed, reproducible
test that recreates the catalog's exact failing construction and asserts the
HARDENED contract now holds.

Mapping to the catalog rows (finserv side):

  * AL-PROBE-01  level-gate refuses promotion when lower gates are unmet, and
                 is honestly labelled advisory unless run with independent
                 attestation.
  * AL-PROBE-02  sovereign veto blocks, logs, is un-self-clearable, and fails
                 closed in production mode (mandatory Authorizer).
  * AL-PROBE-03  hash-chain detects in-place tamper AND a CLEAN deployer-keyed
                 chain verifies True (the 03b verifier defect, now fixed); an
                 end-to-end-regenerated chain is detected against an external
                 witness anchor.
  * AL-PROBE-04  DEFCON forces every transition and fails safe on an illegal
                 HALT de-escalation (Authorizer rejects -> stays HALT).
  * AL-PROBE-05  effective challenge rejects a self-challenge (challenger IS
                 primary) — the rubber-stamp the catalog flagged.

cre-side probes live in cre-agent-audit/tests/adversarial/test_al_probes.py;
cre AL-PROBE-05 is N/A (no effective-challenge primitive) and is recorded as
such there, never fabricated.
"""

from __future__ import annotations

import warnings
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from finserv_agent_audit.governance.audit_chain import AuditChain
from finserv_agent_audit.governance.autonomy_ladder import (
    PromotionGateNotMet,
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
    EffectiveChallengeHarness,
)
from finserv_agent_audit.governance.sovereign_veto import (
    SovereignVeto,
    VetoBlockedError,
    VetoReason,
)
from finserv_agent_audit.governance.witness_anchor import WitnessReceipt
from finserv_agent_audit.schemas.audit_event import AuditEventType, AutonomyLevel


class _RejectAll:
    def authorize(self, operator_id: str, action: str, context: dict[str, Any]) -> bool:
        return False


class _AllowAll:
    def authorize(self, operator_id: str, action: str, context: dict[str, Any]) -> bool:
        return True


# --------------------------------------------------------------------------- #
# AL-PROBE-01 — promotion-without-lower-gates is refused.
# --------------------------------------------------------------------------- #


def test_al_probe_01_promotion_refused_when_all_lower_gates_unmet() -> None:
    # The catalog's exact failing construction.
    reqs = PromotionRequirements(
        sovereign_veto_load_tested=False,
        audit_ledger_running_for=timedelta(days=3),
        shadow_mode_running_for=timedelta(days=1),
        circuit_breaker_test_recent=False,
    )
    report = check_a2_to_a3_promotion(reqs)
    assert report.passed is False
    assert len(report.failures) == 4
    with pytest.raises(PromotionGateNotMet):
        report.raise_if_blocked()


def test_al_probe_01_passes_when_all_met_but_is_advisory() -> None:
    reqs = PromotionRequirements(
        sovereign_veto_load_tested=True,
        audit_ledger_running_for=timedelta(days=120),
        shadow_mode_running_for=timedelta(days=45),
        circuit_breaker_test_recent=True,
    )
    report = check_a2_to_a3_promotion(reqs)
    assert report.passed is True
    # HARDENED honesty: the default check is advisory, not an enforcing control.
    assert report.advisory is True


# --------------------------------------------------------------------------- #
# AL-PROBE-02 — veto blocks, logs, is un-self-clearable; production fails closed.
# --------------------------------------------------------------------------- #


def test_al_probe_02_veto_blocks_and_cannot_self_clear() -> None:
    veto = SovereignVeto(agent_id="zeus", authorizer=_RejectAll())
    veto.trigger(VetoReason.RISK_LIMIT_BREACH, "risk_monitor", "ALERT threshold reached")
    assert veto.allow_execution() is False
    assert any(v.is_active for v in veto.history())

    # Self-clearing is hard-blocked even with a permissive Authorizer path.
    with pytest.raises(VetoBlockedError):
        veto.clear(operator_id="zeus", reason="i cleared myself")

    # A wired (RejectAll) Authorizer blocks an external clear; veto stays active.
    with pytest.raises(VetoBlockedError):
        veto.clear(operator_id="operator_001", reason="reviewed")
    assert veto.is_vetoed is True


def test_al_probe_02_production_mode_fails_closed_without_authorizer() -> None:
    # HARDENED: production mode refuses to start without a wired Authorizer, so
    # operator_id on the chain is bound to an authenticated principal.
    with pytest.raises(ValueError, match="requires a wired Authorizer"):
        SovereignVeto(agent_id="zeus", production=True)


# --------------------------------------------------------------------------- #
# AL-PROBE-03 — in-place tamper detected; CLEAN deployer-keyed chain verifies;
# end-to-end regeneration detected against an external witness anchor.
# --------------------------------------------------------------------------- #


def _append(chain: AuditChain, n: int = 3) -> None:
    for i in range(n):
        chain.append(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="zeus",
            payload={"i": i},
        )


def test_al_probe_03a_inplace_tamper_detected_legacy(tmp_path: Path) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        chain = AuditChain(log_file=tmp_path / "legacy.jsonl")
        _append(chain)
        assert chain.verify() is True
        # In-place payload edit on a middle event.
        object.__setattr__(chain._events[1], "payload", {"i": 999})
        assert chain.verify() is False


def test_al_probe_03b_clean_deployer_keyed_chain_verifies(tmp_path: Path) -> None:
    # The defect the catalog found: a CLEAN hardened chain raised a false TAMPER.
    chain = AuditChain(
        log_file=tmp_path / "hardened.jsonl",
        deployer_id="acme-bank-prod",
        chain_creation_iso="2026-01-01T00:00:00+00:00",
    )
    _append(chain)
    assert chain.verify() is True
    chain.verify_strict()  # must NOT raise


def test_al_probe_03_end_to_end_regeneration_detected_by_witness(tmp_path: Path) -> None:
    """A regenerated chain has a different head than the witnessed head.

    verify() alone cannot catch end-to-end regeneration (documented in the
    module). The external witness anchor is the control: the witnessed head is
    published out-of-band; a regenerated chain's head will not match it.
    """
    witnessed: dict[str, str] = {}

    class _FakeWitness:
        def anchor(self, chain_head_hex: str) -> WitnessReceipt:
            from datetime import UTC, datetime

            witnessed["head"] = chain_head_hex
            return WitnessReceipt(
                register_name="custom",
                register_url="memory://",
                submitted_at=datetime.now(UTC),
                receipt_blob=chain_head_hex.encode(),
                inclusion_uuid=None,
                log_index=None,
            )

    legit = AuditChain(
        log_file=tmp_path / "legit.jsonl",
        deployer_id="acme-bank-prod",
        chain_creation_iso="2026-01-01T00:00:00+00:00",
        witness_register=_FakeWitness(),
    )
    _append(legit)
    legit.anchor_to_witness()
    legit_head = witnessed["head"]
    assert legit.verify() is True

    # Attacker regenerates a DIFFERENT chain end-to-end (different events).
    regenerated = AuditChain(
        log_file=tmp_path / "regen.jsonl",
        deployer_id="acme-bank-prod",
        chain_creation_iso="2026-01-01T00:00:00+00:00",
    )
    regenerated.append(
        event_type=AuditEventType.DECISION_MADE,
        autonomy_level=AutonomyLevel.A2,
        agent_id="zeus",
        payload={"i": "TAMPERED"},
    )
    # The regenerated chain is internally consistent (verify True) — which is
    # exactly why the witness anchor is required: its head != the witnessed head.
    assert regenerated.verify() is True
    assert regenerated.chain_head() != legit_head, "regeneration must be detectable via witness"


def test_al_probe_03_production_requires_witness(tmp_path: Path) -> None:
    # HARDENED: production mode makes the witness anchor non-optional.
    with pytest.raises(ValueError, match="requires a witness_register"):
        AuditChain(
            log_file=tmp_path / "p.jsonl",
            deployer_id="acme-bank-prod",
            production=True,
        )


# --------------------------------------------------------------------------- #
# AL-PROBE-04 — illegal DEFCON de-escalation fails safe.
# --------------------------------------------------------------------------- #


def test_al_probe_04_halt_deescalation_rejected_stays_halt(tmp_path: Path) -> None:
    machine = DEFCONMachine(
        state_file=tmp_path / "state.json",
        audit_file=tmp_path / "audit.jsonl",
        authorizer=_RejectAll(),
    )
    # Drive to HALT via a >=20% drawdown.
    machine.evaluate(RiskMetrics(portfolio_drawdown=0.25, daily_loss=0.07, consecutive_losses=8))
    assert machine.level == DEFCON.HALT
    # Benign metrics while HALTED do NOT auto-de-escalate.
    assert machine.evaluate(RiskMetrics(0.0, 0.0, 0)) == DEFCON.HALT
    # A RejectAll Authorizer rejects the manual override; stays HALT (fail-safe).
    with pytest.raises(DEFCONOverrideRejectedError):
        machine.manual_override(DEFCON.NORMAL, operator_id="op", reason="resume")
    assert machine.level == DEFCON.HALT


def test_al_probe_04_legal_override_works(tmp_path: Path) -> None:
    machine = DEFCONMachine(
        state_file=tmp_path / "state2.json",
        audit_file=tmp_path / "audit2.jsonl",
        authorizer=_AllowAll(),
    )
    machine.evaluate(RiskMetrics(portfolio_drawdown=0.25, daily_loss=0.07, consecutive_losses=8))
    assert machine.level == DEFCON.HALT
    machine.manual_override(DEFCON.NORMAL, operator_id="op", reason="reviewed; safe")
    assert machine.level == DEFCON.NORMAL


# --------------------------------------------------------------------------- #
# AL-PROBE-05 — effective challenge rejects a self-challenge.
# --------------------------------------------------------------------------- #


def test_al_probe_05_self_challenge_rejected() -> None:
    def primary(x: str) -> str:
        return x

    # The catalog's rubber-stamp construction: challenger IS the primary.
    with pytest.raises(ValueError, match="not be the same object"):
        EffectiveChallengeHarness(
            primary_model=primary,
            challenger_model=primary,
            eval_set=[(str(i), str(i)) for i in range(20)],
        )
