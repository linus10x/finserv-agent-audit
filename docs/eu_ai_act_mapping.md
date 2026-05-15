# EU AI Act — Control Mapping for Autonomous AI Agents

This document maps the governance patterns in this repository to specific
EU AI Act requirements for high-risk AI systems. Autonomous agents operating
in financial services with access to execution or credit decisions are
generally classified as high-risk under Annex III.

> **Disclaimer:** This mapping is provided for reference only and does not
> constitute legal advice. Engage qualified legal counsel for your specific
> compliance determination.

---

## Control Mapping Table

| EU AI Act Requirement | Article | Pattern in This Repo | File |
|---|---|---|---|
| Risk management system | Art. 9 | DEFCON state machine — continuous risk evaluation | `examples/defcon_state_machine.py` |
| Data and data governance | Art. 10 | Audit chain — all inputs to decisions are logged | `schemas/audit_event.py` |
| Technical documentation | Art. 11 | Decision rationale in every AuditEvent payload | `schemas/audit_event.py` |
| Record-keeping / logging | Art. 12 | Tamper-evident hash-chain audit log | `schemas/audit_event.py` |
| Transparency to deployers | Art. 13 | Autonomy Ladder — published classification per decision type | `docs/autonomy_ladder.md` |
| Human oversight | Art. 14 | Sovereign Veto — hard stop with documented human clearance | `patterns/sovereign_veto.py` |
| Accuracy, robustness, cybersecurity | Art. 15 | DEFCON hysteresis — prevents oscillation under adversarial conditions | `examples/defcon_state_machine.py` |

---

## High-Risk Classification Checklist

Under Annex III, your AI agent system is likely high-risk if it:

- [ ] Makes or influences credit decisions
- [ ] Executes trades or orders with financial consequences
- [ ] Controls access to financial products or services
- [ ] Provides recommendations that are systematically followed
- [ ] Operates in a supervisory or compliance review capacity

If any box is checked, the full Article 9–15 control set applies.

---

## Gap Analysis — What This Repo Does NOT Cover

This repository covers governance patterns at the agent-decision layer.
The following EU AI Act requirements need additional compliance work beyond
what these patterns provide:

| Requirement | Gap | Guidance |
|---|---|---|
| Conformity assessment (Art. 43) | Requires third-party audit for certain high-risk systems | Engage accredited conformity assessment body |
| Registration in EU database (Art. 49) | Requires organizational and legal steps | EU AI Office registration portal |
| Post-market monitoring (Art. 72) | Requires ongoing telemetry and reporting program | Build on top of the audit chain pattern |
| Fundamental rights impact assessment | Requires structured assessment process | EU AI Act FRIA template (forthcoming) |
