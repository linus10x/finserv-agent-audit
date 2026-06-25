"""The runnable demo must actually run and self-verify.

A green ``run_demo()`` proves: the honest lifecycle verifies, AND all four
attacks (forged grant / deleted revocation / in-place mutation) are caught.
``run_demo`` returns non-zero if any expected catch fails to fire, so this
test is a polarity check on the whole demo — it would fail if a verifier
silently stopped catching its attack.
"""

from __future__ import annotations

from examples.demotion_gate_demo import run_demo


def test_demo_runs_and_all_attacks_are_caught() -> None:
    assert run_demo(verbose=False) == 0
