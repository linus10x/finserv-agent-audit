#!/usr/bin/env python3
"""Demotion-gated control surface — runnable demo (clone-and-run, no network).

This is the falsifiable-under-audit claim, executable. It builds an authority
lifecycle, anchors it to an external witness, and then runs four attacks that
a hash-chain ALONE would miss — proving each is caught:

    1. a forged GRANT inserted with no evidence (chain hashes regenerated so the
       cryptographic verify() is happy) -> caught by the SEMANTIC verifier;
    2. a deleted REVOCATION / head-truncation (so the agent appears to still
       hold A3) -> caught by the EXTERNAL-ANCHOR verifier;
    3. an in-place MUTATION of a recorded event -> caught by the HASH-CHAIN
       verifier;
    4. a backdated REGENERATION of the whole history that omits the revocation
       -> caught by the EXTERNAL-ANCHOR verifier (the witnessed head is absent).

It is SELF-VERIFYING: it asserts each expected catch actually fires and exits
non-zero if any does not. A green run is the proof, not the printout.

What this does NOT prove: there is no named production deployment behind this,
and no regulator/examiner has reviewed a chain produced by this code in situ.
The claim demonstrated here is about the control surface's mechanism — that a
claimed authority level is falsifiable under audit — not about an operational
track record.

Run it (from a cold clone, no install, no network):

    ./demo.sh

or directly:

    PYTHONPATH=src python3 examples/demotion_gate_demo.py
"""

from __future__ import annotations

import sys
from datetime import timedelta

from finserv_agent_audit.governance.audit_chain import (
    AuditChain,
    AuditChainTamperError,
)
from finserv_agent_audit.governance.authority_lifecycle import (
    AuthorityInvariantError,
    AuthorityLifecycle,
    verify_authority_invariants,
)
from finserv_agent_audit.governance.autonomy_ladder import (
    PromotionRequirements,
    check_a2_to_a3_promotion,
)
from finserv_agent_audit.governance.ledger_store import InMemoryLedgerStore
from finserv_agent_audit.governance.witness_anchor import (
    RecordingWitness,
    WitnessContradictionError,
    anchor_to_witness,
    verify_against_external_anchors,
)
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)

DEPLOYER_ID = "example-deployer"  # transparently synthetic — NOT a real deployment
CREATION_ISO = "2026-06-24T00:00:00+00:00"
GRANTOR = "first-line:model-owner"
EXAMINER = "second-line:model-risk"  # independent of the grantor (SR 11-7)


def _print(verbose: bool, *args: object) -> None:
    if verbose:
        print(*args)


def _build_honest_chain() -> tuple[AuditChain, RecordingWitness, str]:
    """grant A2->A3 against evidence, examine (fails), revoke A3->A1, anchor."""
    chain = AuditChain(
        ledger_store=InMemoryLedgerStore(),
        deployer_id=DEPLOYER_ID,
        chain_creation_iso=CREATION_ISO,
    )
    lc = AuthorityLifecycle(chain, agent_id="rebalancer-agent")
    # The A3 grant's evidence is the OUTPUT of the real A2->A3 promotion gate,
    # not a free-text assertion — so the recorded grant is provably gate-cleared.
    requirements = PromotionRequirements(
        sovereign_veto_load_tested=True,
        audit_ledger_running_for=timedelta(days=120),
        shadow_mode_running_for=timedelta(days=45),
        circuit_breaker_test_recent=True,
    )
    gate = check_a2_to_a3_promotion(requirements)
    gate.raise_if_blocked()  # demo asserts the gate actually passed
    grant = lc.grant(
        level=AutonomyLevel.A3,
        evidence={
            "promotion_gate": "A2->A3",
            "gate_passed": gate.passed,
            "sovereign_veto_load_tested": requirements.sovereign_veto_load_tested,
            "audit_ledger_running_days": requirements.audit_ledger_running_for.days,
            "shadow_mode_running_days": requirements.shadow_mode_running_for.days,
            "circuit_breaker_test_recent": requirements.circuit_breaker_test_recent,
        },
        actor_id=GRANTOR,
    )
    exam = lc.examine(
        grant_event_id=grant.event_id,
        at_level=AutonomyLevel.A3,
        finding="2 out-of-envelope writes exceeded the drift band threshold",
        passed=False,
        actor_id=EXAMINER,  # independent of GRANTOR — enforced by the verifier
    )
    revoke = lc.revoke(
        grant_event_id=grant.event_id,
        examination_event_id=exam.event_id,
        to_level=AutonomyLevel.A1,
        reason="examination failed: out-of-envelope drift",
        actor_id=EXAMINER,
    )
    witness = RecordingWitness()
    anchor_to_witness(audit_chain=chain, witness=witness)
    return chain, witness, revoke.event_hash


def run_demo(*, verbose: bool = True) -> int:
    """Return 0 iff the honest chain verifies AND all four attacks are caught."""
    ok = True

    # ---- 1. Honest lifecycle: all three verifiers agree it is clean. ------- #
    chain, witness, revoked_head = _build_honest_chain()
    _print(verbose, "=" * 70)
    _print(verbose, "HONEST CHAIN — grant A3 (vs evidence) -> examined (failed) -> revoked to A1")
    _print(verbose, "=" * 70)
    honest_clean = True
    try:
        assert chain.verify() is True
        chain.verify_strict()
        verify_authority_invariants(chain)
        verify_against_external_anchors(chain, witness.records)
    except (
        AuditChainTamperError,
        AuthorityInvariantError,
        WitnessContradictionError,
        AssertionError,
    ) as exc:
        honest_clean = False
        ok = False
        _print(verbose, f"  UNEXPECTED: honest chain failed verification: {exc}")
    if honest_clean:
        _print(verbose, "  hash-chain verify()           : PASS")
        _print(verbose, "  authority invariants          : PASS")
        _print(verbose, "  external-anchor check         : PASS")
        _print(verbose, f"  revoked head anchored externally: {revoked_head[:16]}...")

    # ---- 2. Attack: forged grant with no evidence. ------------------------ #
    _print(verbose, "\n" + "-" * 70)
    _print(verbose, "ATTACK 1 — forge an AUTHORITY_GRANTED with NO evidence (regenerate hashes)")
    _print(verbose, "-" * 70)
    chain1, _, _ = _build_honest_chain()
    forged = AuditEvent.create(
        event_type=AuditEventType.AUTHORITY_GRANTED,
        autonomy_level=AutonomyLevel.A4,
        agent_id="attacker-agent",
        payload={"granted_level": "A4"},  # no evidence
        prev_hash=chain1.chain_head(),
    )
    chain1._store.append(forged)  # noqa: SLF001 — storage-layer attacker
    caught = False
    if chain1.verify() is not True:
        _print(verbose, "  (note) verify() did not pass — forgery was not even hash-consistent")
    else:
        _print(verbose, "  hash-chain verify()           : PASS (forgery hash-consistent; fooled)")
    try:
        verify_authority_invariants(chain1)
    except AuthorityInvariantError as exc:
        caught = True
        _print(verbose, f"  authority invariants          : CAUGHT -> {exc}")
    if not caught:
        ok = False
        _print(verbose, "  authority invariants          : MISSED (expected a catch!)")

    # ---- 3. Attack: delete the revocation (head-truncation). -------------- #
    _print(verbose, "\n" + "-" * 70)
    _print(verbose, "ATTACK 2 — delete the revocation so the agent looks like it still holds A3")
    _print(verbose, "-" * 70)
    chain2, witness2, revoked_head2 = _build_honest_chain()
    del chain2._store._events[-2:]  # noqa: SLF001 — drop WITNESS_ANCHOR + revocation (tail truncation)
    if chain2.verify() is True:
        _print(verbose, "  hash-chain verify()           : PASS (truncated tail re-links; fooled)")
    else:
        _print(verbose, "  (note) hash-chain verify() did not pass")
    caught = False
    try:
        verify_against_external_anchors(chain2, witness2.records)
    except WitnessContradictionError as exc:
        caught = True
        _print(verbose, f"  external-anchor check         : CAUGHT -> {revoked_head2[:12]}... gone")
        _print(verbose, f"      {exc}")
    if not caught:
        ok = False
        _print(verbose, "  external-anchor check         : MISSED (expected a catch!)")

    # ---- 4. Attack: in-place mutation of a recorded event. ---------------- #
    _print(verbose, "\n" + "-" * 70)
    _print(verbose, "ATTACK 3 — mutate a recorded event's payload in place (keep its stored hash)")
    _print(verbose, "-" * 70)
    chain3, _, _ = _build_honest_chain()
    target = chain3._store._events[1]  # noqa: SLF001 — the grant event
    mutated = AuditEvent(
        event_type=target.event_type,
        autonomy_level=target.autonomy_level,
        agent_id=target.agent_id,
        payload={**target.payload, "granted_level": "A4"},  # silently widen authority
        prev_hash=target.prev_hash,
        event_id=target.event_id,
        timestamp=target.timestamp,
        actor_id=target.actor_id,
        schema_version=target.schema_version,
        event_hash=target.event_hash,  # keep the ORIGINAL hash -> recompute will mismatch
    )
    chain3._store._events[1] = mutated  # noqa: SLF001
    caught = False
    try:
        chain3.verify_strict()
    except AuditChainTamperError as exc:
        caught = True
        _print(verbose, f"  hash-chain verify_strict()    : CAUGHT -> {exc}")
    if not caught:
        ok = False
        _print(verbose, "  hash-chain verify_strict()    : MISSED (expected a catch!)")

    # ---- 5. Attack: backdated regeneration of the whole chain. ------------ #
    _print(verbose, "\n" + "-" * 70)
    _print(verbose, "ATTACK 4 — regenerate a backdated history that omits the revocation")
    _print(verbose, "-" * 70)
    _, witness4, revoked_head4 = _build_honest_chain()
    honest_anchors = witness4.records  # what the external witness saw on the real chain
    # Attacker rebuilds a different, internally-consistent history: a grant with
    # NO revocation, so the agent appears to still hold A3.
    regenerated = AuditChain(
        ledger_store=InMemoryLedgerStore(),
        deployer_id=DEPLOYER_ID,
        chain_creation_iso=CREATION_ISO,
    )
    lc4 = AuthorityLifecycle(regenerated, agent_id="rebalancer-agent")
    lc4.grant(level=AutonomyLevel.A3, evidence={"shadow_mode_running_days": 45})
    if regenerated.verify() is True:
        _print(verbose, "  hash-chain verify()           : PASS (regenerated chain consistent)")
    caught = False
    try:
        verify_against_external_anchors(regenerated, honest_anchors)
    except WitnessContradictionError:
        caught = True
        _print(verbose, f"  external-anchor check         : CAUGHT -> {revoked_head4[:10]}... gone")
    if not caught:
        ok = False
        _print(verbose, "  external-anchor check         : MISSED (expected a catch!)")

    _print(verbose, "\n" + "=" * 70)
    if ok:
        _print(verbose, "RESULT: PASS — honest chain verifies and all four attacks were caught.")
    else:
        _print(verbose, "RESULT: FAIL — an expected catch did not fire.")
    _print(verbose, "=" * 70)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run_demo())
