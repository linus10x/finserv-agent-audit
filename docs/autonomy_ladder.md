# Autonomy Ladder — A0 through A4

A proprietary governance framework for classifying autonomous AI agent behavior
by the level of human oversight required at each decision point.

> **Status:** Proprietary framework — documented in this repository.
> This is not a published standard. It is a practitioner's classification system
> extracted from building and governing a production-bound multi-agent system
> in a regulated financial environment.

---

## The Five Levels

| Level | Name | Human Role | When to Use |
|---|---|---|---|
| **A0** | Human Decides | Agent proposes; human decides and executes | Irreversible decisions with significant capital or compliance impact |
| **A1** | Human In Loop | Agent proposes; human must confirm before execution | High-impact decisions where speed is not critical |
| **A2** | Human On Loop | Agent executes; human can override within a time window | Normal operational decisions with defined reversal procedures |
| **A3** | Human Notified | Agent executes; human receives alert and can investigate | Routine decisions with low individual impact |
| **A4** | Autonomous | Agent executes; audit trail only | High-frequency, low-impact, well-understood decisions |

---

## Governing Principle

The autonomy level is not a permanent property of an agent. It is a function of:

1. **Current risk state** — at DEFCON ALERT or above, all agents drop to A1 regardless of normal classification
2. **Decision category** — irreversible decisions always require A0 or A1 regardless of agent or risk state
3. **Regulatory context** — decisions with direct regulatory reporting implications require A0
4. **System health** — degraded infrastructure, missing data feeds, or anomalous market conditions reduce autonomy level

---

## EU AI Act Mapping

| A-Level | EU AI Act Requirement | Article |
|---|---|---|
| A0, A1 | Meaningful human oversight; human can intervene before effect | Article 14(1) |
| A2 | Human can override or interrupt; system must respond to intervention | Article 14(3)(e) |
| A3, A4 | Appropriate human oversight measures; logging and monitoring | Article 14(4) |
| All levels | Logging of decisions for post-hoc review | Article 12 |

---

## Practical Implementation Notes

**Escalation is automatic. De-escalation is deliberate.**

When risk state rises (DEFCON CAUTION → ALERT), the autonomy level of all
affected agents drops immediately — no human action required for the downgrade.
When risk state recovers, the autonomy level does NOT automatically restore.
A human operator must explicitly re-authorize elevated autonomy levels after
reviewing the incident.

This asymmetry is intentional. The cost of being too conservative during
recovery is a missed opportunity. The cost of being too aggressive during
recovery is a compounded loss.

---

## Implementation Reference

- `schemas/audit_event.py` → `AutonomyLevel` enum maps directly to A0–A4
- `patterns/sovereign_veto.py` → veto trigger integrates with A2 gate check
- `examples/defcon_state_machine.py` → DEFCON levels drive autonomy level assignment
