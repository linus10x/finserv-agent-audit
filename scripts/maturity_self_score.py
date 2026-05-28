#!/usr/bin/env python3
"""Agentic-AI governance maturity self-score CLI.

Interactive walk-through of 25 yes/no questions calibrated against the
5-level maturity model in ``docs/agentic_ai_governance_maturity_model.md``.
Prints a markdown report scoring the institution at Level 1-5 and listing
the named next-level gaps.

Stdlib-only; no runtime dependencies. Designed to pass ``ruff check``,
``ruff format --check``, and ``mypy --strict``.

Usage:
    python3 scripts/maturity_self_score.py                # prompts to stdout
    python3 scripts/maturity_self_score.py --output report.md
    python3 scripts/maturity_self_score.py --non-interactive --answers all-yes
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TextIO


@dataclass(frozen=True)
class Question:
    """One yes/no question + the maturity level it gates."""

    key: str
    text: str
    level: int
    evidence_module: str


@dataclass
class ScoreReport:
    """Tally of the self-score walk-through."""

    answers: dict[str, bool] = field(default_factory=dict)
    asof: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def add(self, key: str, value: bool) -> None:
        self.answers[key] = value

    def current_level(self, questions: list[Question]) -> int:
        """Return the highest level where every question at that level is YES."""
        level = 1
        for candidate in (2, 3, 4, 5):
            level_qs = [q for q in questions if q.level == candidate]
            if not level_qs:
                continue
            if all(self.answers.get(q.key, False) for q in level_qs):
                level = candidate
            else:
                break
        return level

    def gaps_at_level(self, questions: list[Question], level: int) -> list[Question]:
        """Return every question at ``level`` answered NO (in question order)."""
        return [q for q in questions if q.level == level and not self.answers.get(q.key, False)]


# --------------------------------------------------------------------------- #
# Question bank (25 items, calibrated to Levels 2-5; Level 1 is the baseline) #
# --------------------------------------------------------------------------- #

QUESTIONS: list[Question] = [
    # ---- Level 2 (Repeatable) — 5 questions ----
    Question(
        key="L2_sovereign_veto",
        text="Is the SovereignVeto pattern deployed in production?",
        level=2,
        evidence_module="finserv_agent_audit.governance.sovereign_veto.SovereignVeto",
    ),
    Question(
        key="L2_audit_chain",
        text="Is the AuditChain pattern deployed with at least an in-memory or JSONL backend?",
        level=2,
        evidence_module="finserv_agent_audit.governance.audit_chain.AuditChain",
    ),
    Question(
        key="L2_named_executive",
        text="Is there a named accountable executive (Chief AI Officer or equivalent)?",
        level=2,
        evidence_module="(org chart; board minutes)",
    ),
    Question(
        key="L2_inventory_adhoc",
        text="Does an AI inventory exist (ad-hoc form acceptable)?",
        level=2,
        evidence_module="(spreadsheet / wiki / ModelInventory)",
    ),
    Question(
        key="L2_veto_tabletop",
        text="Has the SovereignVeto kill-switch path been tabletop-tested in the last 90 days?",
        level=2,
        evidence_module="finserv_agent_audit.governance.sovereign_veto.VetoBlockedError",
    ),
    # ---- Level 3 (Defined) — 5 questions ----
    Question(
        key="L3_autonomy_ladder",
        text="Is AutonomyLadder (A0-A4) classification documented for every AI use case?",
        level=3,
        evidence_module="finserv_agent_audit.governance.autonomy_ladder.AutonomyTier",
    ),
    Question(
        key="L3_promotion_gate_programmatic",
        text="Is the A2-to-A3 promotion gate evaluated programmatically (not via slide deck)?",
        level=3,
        evidence_module="finserv_agent_audit.governance.autonomy_ladder.check_a2_to_a3_promotion",
    ),
    Question(
        key="L3_defcon_dashboard",
        text="Is the DEFCON state machine in the operations dashboard?",
        level=3,
        evidence_module="finserv_agent_audit.governance.defcon.DEFCONMachine",
    ),
    Question(
        key="L3_mrm_policy_agentic",
        text="Does the written MRM policy include an explicit agentic-AI section?",
        level=3,
        evidence_module="(MRM policy document; docs/sr11_7_mapping.md)",
    ),
    Question(
        key="L3_eu_ai_act_review",
        text="Has the EU AI Act mapping been reviewed against the institution's AI surface?",
        level=3,
        evidence_module="docs/eu_ai_act_mapping.md",
    ),
    # ---- Level 4 (Managed) — 9 questions ----
    Question(
        key="L4_ledger_substrate",
        text=(
            "Is LedgerStore deployed with a substrate-appropriate backend "
            "(SqliteLedgerStore or WORMLedgerStore + S3 Object Lock COMPLIANCE)?"
        ),
        level=4,
        evidence_module="finserv_agent_audit.governance.ledger_store_worm.WORMLedgerStore",
    ),
    Question(
        key="L4_rfc3161",
        text=(
            "Is RFC3161Source deployed for high-integrity surfaces with an "
            "explicit fallback policy?"
        ),
        level=4,
        evidence_module="finserv_agent_audit.governance.timestamp_source.RFC3161Source",
    ),
    Question(
        key="L4_witness_anchor",
        text="Is the witness-anchor cron deployed (RekorWitness or OpenTimestampsWitness)?",
        level=4,
        evidence_module="finserv_agent_audit.governance.witness_anchor.anchor_to_witness",
    ),
    Question(
        key="L4_miproxy",
        text="Is MIProxy wired so every verify_strict() run produces a verifier attestation?",
        level=4,
        evidence_module="finserv_agent_audit.governance.mi_proxy.LocalMIProxy",
    ),
    Question(
        key="L4_vendor_score_gate",
        text=(
            "Is VendorScoreGate deployed against at least one production vendor "
            "with drift detection demonstrated?"
        ),
        level=4,
        evidence_module="finserv_agent_audit.governance.vendor_score_gate.InMemoryVendorScoreGate",
    ),
    Question(
        key="L4_adverse_action",
        text="Is AdverseActionGate deployed where credit / lending applies?",
        level=4,
        evidence_module="finserv_agent_audit.governance.adverse_action_gate.AdverseActionGate",
    ),
    Question(
        key="L4_sar_workflow",
        text="Is SARWorkflowAudit deployed where BSA / AML applies?",
        level=4,
        evidence_module="finserv_agent_audit.governance.sar_workflow_audit.SARWorkflowAudit",
    ),
    Question(
        key="L4_best_interest",
        text="Is BestInterestCheck deployed where SEC Reg-BI applies?",
        level=4,
        evidence_module="finserv_agent_audit.governance.best_interest_check.BestInterestCheck",
    ),
    Question(
        key="L4_drift_quarterly",
        text="Are quantitative drift metrics reported to the Risk Committee quarterly?",
        level=4,
        evidence_module="(Risk Committee package; quarterly cadence)",
    ),
    # ---- Level 5 (Optimizing) — 6 questions ----
    Question(
        key="L5_mcp_server",
        text=(
            "Is MCP server integration deployed for controlled chain-artifact "
            "discovery by peer AI systems?"
        ),
        level=5,
        evidence_module="(deployer-supplied; v2.0 roadmap)",
    ),
    Question(
        key="L5_otel_emitter",
        text="Is an OpenTelemetry emitter producing chain events to the observability backplane?",
        level=5,
        evidence_module="(deployer-supplied; v2.0 roadmap)",
    ),
    Question(
        key="L5_adversarial_quarterly",
        text=(
            "Is the adversarial test pack against the chain "
            "(induced corruption / replay / verifier swap / witness disagreement "
            "/ vendor drift) run quarterly?"
        ),
        level=5,
        evidence_module="FAILURE-MODES.md (all 6 named-callable rows exercised)",
    ),
    Question(
        key="L5_portfolio_dashboard",
        text=(
            "Is a portfolio-level governance dashboard aggregating across "
            "business units in production?"
        ),
        level=5,
        evidence_module="(deployer-supplied)",
    ),
    Question(
        key="L5_full_day_tabletop",
        text=(
            "Has a tabletop reconstructed a full operational day from the "
            "audit chain alone in the last quarter?"
        ),
        level=5,
        evidence_module="(tabletop memo; gap-closure log)",
    ),
    Question(
        key="L5_substrate_miproxy",
        text=(
            "Is a substrate-pluggable MIProxy backend (SLSA / in-toto / "
            "equivalent) deployed for at least one high-integrity surface?"
        ),
        level=5,
        evidence_module="finserv_agent_audit.governance.mi_proxy.MIProxy (substrate backend)",
    ),
]


LEVEL_NAMES: dict[int, str] = {
    1: "Initial",
    2: "Repeatable",
    3: "Defined",
    4: "Managed",
    5: "Optimizing",
}


# --------------------------------------------------------------------------- #
# IO + scoring                                                                #
# --------------------------------------------------------------------------- #


def prompt_yes_no(question_text: str, stream_in: TextIO, stream_out: TextIO) -> bool:
    """Prompt until the user answers y / n. EOF returns False."""
    while True:
        stream_out.write(f"{question_text} [y/n]: ")
        stream_out.flush()
        raw = stream_in.readline()
        if not raw:
            return False
        token = raw.strip().lower()
        if token in {"y", "yes"}:
            return True
        if token in {"n", "no"}:
            return False
        stream_out.write("  please answer y or n\n")


def run_interactive(
    questions: list[Question], stream_in: TextIO, stream_out: TextIO
) -> ScoreReport:
    """Walk the user through every question and collect answers."""
    report = ScoreReport()
    stream_out.write("Agentic-AI governance maturity self-score\n")
    stream_out.write(f"({len(questions)} questions; answer y or n)\n\n")
    for idx, question in enumerate(questions, start=1):
        stream_out.write(f"[{idx:02d}/{len(questions)}] (Level {question.level}) ")
        answer = prompt_yes_no(question.text, stream_in, stream_out)
        report.add(question.key, answer)
    return report


def run_non_interactive(questions: list[Question], answers_mode: str) -> ScoreReport:
    """Programmatic answer modes for CI / testing."""
    report = ScoreReport()
    if answers_mode == "all-yes":
        for question in questions:
            report.add(question.key, True)
    elif answers_mode == "all-no":
        for question in questions:
            report.add(question.key, False)
    elif answers_mode == "level2-only":
        for question in questions:
            report.add(question.key, question.level == 2)
    else:
        raise ValueError(f"unknown --answers mode: {answers_mode!r}")
    return report


def render_report(report: ScoreReport, questions: list[Question]) -> str:
    """Render the score report as markdown."""
    level = report.current_level(questions)
    next_level = min(level + 1, 5)
    gaps_at_current = report.gaps_at_level(questions, level + 1) if level < 5 else []

    lines: list[str] = []
    lines.append("# Agentic-AI Governance Maturity Self-Score Report")
    lines.append("")
    lines.append(f"**Generated:** {report.asof}")
    lines.append("")
    lines.append(f"**Current level:** Level {level} ({LEVEL_NAMES[level]})")
    lines.append("")
    lines.append(f"**Next level:** Level {next_level} ({LEVEL_NAMES[next_level]})")
    lines.append("")
    lines.append(
        "**Methodology:** Self-score per "
        "`docs/agentic_ai_governance_maturity_model.md`. Highest level "
        "where every required question is YES."
    )
    lines.append("")

    if level == 5:
        lines.append("## Posture")
        lines.append("")
        lines.append(
            "Level 5 (Optimizing) achieved. Sustain the posture; consider "
            "contributing back to open-source governance frameworks and "
            "shaping industry standards."
        )
        lines.append("")
    elif gaps_at_current:
        lines.append(f"## Gaps to advance from Level {level} to Level {next_level}")
        lines.append("")
        lines.append("Address every item below to reach the next maturity level.")
        lines.append("")
        for question in gaps_at_current:
            lines.append(f"- **{question.key}** — {question.text}")
            lines.append(f"  - Evidence module / artifact: `{question.evidence_module}`")
        lines.append("")
    else:
        lines.append(f"## Level {next_level} pre-requisites")
        lines.append("")
        lines.append(
            "All current-level questions are YES; review the Level "
            f"{next_level} required-evidence list in "
            "`docs/agentic_ai_governance_maturity_model.md` for the "
            "expected next-step modules."
        )
        lines.append("")

    lines.append("## All answers (by level)")
    lines.append("")
    lines.append("| Level | Key | Answer | Question |")
    lines.append("|---|---|---|---|")
    for question in questions:
        ans_raw = report.answers.get(question.key)
        ans = "YES" if ans_raw else ("NO" if ans_raw is False else "(unanswered)")
        lines.append(f"| {question.level} | `{question.key}` | {ans} | {question.text} |")
    lines.append("")

    lines.append("## Next-step playbook")
    lines.append("")
    lines.append(
        "- Review the level-by-level required-evidence list: "
        "[`docs/agentic_ai_governance_maturity_model.md`]"
        "(../docs/agentic_ai_governance_maturity_model.md)"
    )
    lines.append(
        "- Anchor the gap-closure plan in: "
        "[`docs/caio_first_90_days_playbook.md`]"
        "(../docs/caio_first_90_days_playbook.md)"
    )
    lines.append(
        "- Stage evidence per: "
        "[`docs/pre_examination_ai_self_assessment.md`]"
        "(../docs/pre_examination_ai_self_assessment.md)"
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "*Patterns are software, not legal advice. The maturity levels "
        "are self-assessment scaffolding, not a regulatory rating.*"
    )
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CLI entry point                                                             #
# --------------------------------------------------------------------------- #


def build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="maturity_self_score",
        description=(
            "Score the institution's agentic-AI governance maturity (1-5) "
            "against the 5-level model in docs/agentic_ai_governance_maturity_model.md."
        ),
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Write the markdown report to this path (default: stdout).",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip prompts; use the --answers mode for programmatic scoring.",
    )
    parser.add_argument(
        "--answers",
        type=str,
        default="all-no",
        choices=["all-yes", "all-no", "level2-only"],
        help="Answer mode for --non-interactive (default: all-no).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argparser()
    args = parser.parse_args(argv)

    if args.non_interactive:
        report = run_non_interactive(QUESTIONS, args.answers)
    else:
        report = run_interactive(QUESTIONS, sys.stdin, sys.stdout)

    rendered = render_report(report, QUESTIONS)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(rendered)
        sys.stdout.write(f"\nMaturity report written to {args.output}\n")
    else:
        sys.stdout.write("\n")
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
