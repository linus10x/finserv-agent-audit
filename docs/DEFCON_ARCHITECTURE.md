# DEFCON Architecture — Design Decisions

This document explains the architectural decisions behind the DEFCON state machine
implementation and provides guidance for calibrating it to your system.

---

## Why DEFCON Naming?

The US military DEFCON scale is widely understood and intuitive: lower numbers mean
higher alert. We invert this — NORMAL is lowest risk, HALT is highest — because
from a software perspective, ascending integer values mapping to ascending severity
is more natural for `if level >= DEFCON.ALERT` comparisons.

The naming communicates urgency to operators who may have never read the code.

---

## Hysteresis: Why De-escalation Is Harder Than Escalation

A naïve state machine that transitions immediately in both directions will
oscillate under normal market volatility. If a 7% drawdown threshold triggers
CAUTION, and portfolio value fluctuates between 6.9% and 7.1%, the system
transitions CAUTION → NORMAL → CAUTION → NORMAL on every evaluation cycle.

Hysteresis solves this by requiring N consecutive evaluations at the lower level
before confirming a de-escalation. The cost is slightly delayed recovery. The
benefit is stability under volatility.

**Calibration guidance for `HYSTERESIS_CONFIRMATIONS`:**
- Short evaluation cycles (< 1 min): use 5–10 confirmations
- Medium cycles (1–15 min): use 3–5 confirmations
- Long cycles (> 15 min): use 2–3 confirmations

---

## Threshold Calibration Guidance

The illustrative values in `defcon_state_machine.py` are round numbers chosen
to be clearly non-production. To calibrate for your system:

1. **Drawdown thresholds:** Start from your risk policy's maximum tolerable
   drawdown and work backwards. HALT should be below your policy limit.
   CAUTION should give you enough runway to react before reaching HALT.

2. **Daily loss thresholds:** Typically 30–50% of your drawdown thresholds,
   since daily losses compound. A 5% daily loss for 4 consecutive days = ~18%
   drawdown.

3. **Consecutive loss thresholds:** Calibrate to your strategy's expected
   win rate. A 60% win-rate strategy should see runs of 4+ losses rarely;
   flagging at 4 is aggressive but safe. A 45% win-rate strategy should
   set this higher.

---

## State Persistence: Why Load the Last Confirmed Level?

On restart after a crash or deployment, the machine loads the last persisted
state — not the live evaluation. This means:

- If the machine crashed during DANGER, it restarts in DANGER
- The operator must manually review and decide to override
- The system does NOT assume "everything is fine" after a restart

This is the correct behavior for regulated systems. An unexpected restart
is itself a governance event and should require human acknowledgment.

---

## HALT: Why No Automatic De-escalation?

HALT represents complete execution suspension. In a financial system, this
means no trades, no position adjustments, no automated responses. It is
reached only when drawdown or daily loss exceeds the highest threshold.

Automatic de-escalation from HALT would mean the system restarts execution
after drawdown recovers — potentially during a chaotic market recovery where
the initial loss was the first sign of a larger structural problem.

Requiring a human operator to call `manual_override()` forces a deliberate
review before resuming. This is the safest default for any system where the
cost of a wrong restart exceeds the cost of delayed resumption.
