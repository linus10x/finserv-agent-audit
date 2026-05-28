"""Portfolio Governance Dashboard — multi-tenant audit-chain aggregator.

A read-only aggregator for an AI Operating Partner managing a 10-30
portco book at a private-equity fund. Each portco runs its own
``finserv_agent_audit`` AuditChain locally; this dashboard pulls
chain files (or summary feeds) and computes portfolio-level metrics
without ever writing back to a portco's chain.

The companion playbook is at
``docs/pe_portfolio_governance_playbook.md`` — read that for the
governance model, the quarterly-review process, and the
portco-onboarding checklist.

Design invariants:

  * The aggregator never writes to a portco's audit chain.
  * Each portco's chain remains the system of record for the portco.
  * Cross-portco event merge is intentionally NOT supported (that
    creates both legal-privilege and data-segregation problems).
  * Portfolio-level metrics are computed from local-only reads.
  * Stdlib-only; ruff- and mypy-strict-clean.

Demo: run ``python3 examples/portfolio_governance_dashboard.py`` to
generate a synthetic 3-portco aggregation. The demo writes synthetic
JSONL chain files to a temporary directory, registers three portcos,
and emits the quarterly report.
"""

from __future__ import annotations

import json
import tempfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------- #
# DEFCON-level ordering (mirrors examples/defcon_state_machine.py without     #
# importing it — the dashboard is intentionally decoupled from the runtime    #
# DEFCON state machine so it can aggregate across portco implementations      #
# that wire their own state-machine variants).                                #
# --------------------------------------------------------------------------- #

_DEFCON_ORDER: dict[str, int] = {
    "NORMAL": 1,
    "CAUTION": 2,
    "ALERT": 3,
    "DANGER": 4,
    "HALT": 5,
}


def _max_defcon(states: list[str]) -> str:
    """Return the highest-severity DEFCON in ``states``; ``NORMAL`` if empty."""
    if not states:
        return "NORMAL"
    return max(states, key=lambda s: _DEFCON_ORDER.get(s, 0))


# --------------------------------------------------------------------------- #
# Per-portco registration + metric structures                                 #
# --------------------------------------------------------------------------- #


@dataclass
class PortcoRegistration:
    """One registered portco's chain-file locations."""

    portco_id: str
    audit_chain_paths: list[Path]


@dataclass
class ModelInventoryHealth:
    """Per-portco model-inventory rollup."""

    total_models: int = 0
    overdue_validation: int = 0


@dataclass
class DriftAlert:
    """One vendor-score-gate drift alert from a portco's chain."""

    vendor_id: str
    detected_at: str
    payload: dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# The dashboard                                                               #
# --------------------------------------------------------------------------- #


class PortfolioGovernanceDashboard:
    """Multi-tenant audit-chain aggregator.

    Each portco is registered with one or more audit-chain file paths
    (JSONL format, as produced by ``JsonlLedgerStore``). The aggregator
    reads those files and computes portfolio-level metrics. Never
    writes.
    """

    def __init__(self) -> None:
        self._portcos: dict[str, PortcoRegistration] = {}

    # ----------------------------------------------------------------- #
    # Registration                                                      #
    # ----------------------------------------------------------------- #

    def register_portco(self, portco_id: str, audit_chain_paths: list[Path]) -> None:
        """Register a portco's audit-chain file paths (read-only)."""
        if not portco_id:
            raise ValueError("portco_id must be non-empty")
        if not audit_chain_paths:
            raise ValueError(f"portco {portco_id} requires at least one audit-chain path")
        for path in audit_chain_paths:
            if not isinstance(path, Path):
                raise TypeError(
                    f"audit_chain_paths must be Path objects; got {type(path).__name__}"
                )
        self._portcos[portco_id] = PortcoRegistration(
            portco_id=portco_id, audit_chain_paths=list(audit_chain_paths)
        )

    def registered_portcos(self) -> list[str]:
        """Return the list of registered portco IDs in registration order."""
        return list(self._portcos.keys())

    # ----------------------------------------------------------------- #
    # Internal reader                                                   #
    # ----------------------------------------------------------------- #

    def _read_chain_events(self, portco_id: str) -> list[dict[str, Any]]:
        """Read the portco's chain events (JSONL) into a list of dicts.

        Failures on any single file (missing, malformed) are
        swallowed-per-file so one portco's broken chain file does not
        prevent the aggregation of other portcos.
        """
        registration = self._portcos.get(portco_id)
        if registration is None:
            return []
        events: list[dict[str, Any]] = []
        for path in registration.audit_chain_paths:
            try:
                text = path.read_text(encoding="utf-8")
            except (FileNotFoundError, PermissionError, UnicodeDecodeError, OSError):
                continue
            for line in text.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    event = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if isinstance(event, dict):
                    events.append(event)
        return events

    # ----------------------------------------------------------------- #
    # Aggregations                                                      #
    # ----------------------------------------------------------------- #

    def aggregate_defcon_status(self) -> dict[str, str]:
        """Return the current DEFCON state per portco.

        The current state is derived from the most recent
        ``RISK_ESCALATION``, ``RISK_DEESCALATION``, or
        ``HALT_TRIGGERED`` event payload's ``defcon`` field. If no such
        event exists, the portco is reported as ``NORMAL``.
        """
        out: dict[str, str] = {}
        relevant_types = {
            "risk.escalation",
            "risk.deescalation",
            "risk.halt",
        }
        for portco_id in self._portcos:
            events = self._read_chain_events(portco_id)
            current = "NORMAL"
            latest_ts = ""
            for event in events:
                event_type = event.get("event_type", "")
                if event_type not in relevant_types:
                    continue
                payload = event.get("payload") or {}
                defcon = payload.get("defcon")
                ts = event.get("timestamp", "")
                if not isinstance(defcon, str):
                    continue
                if defcon not in _DEFCON_ORDER:
                    continue
                if ts >= latest_ts:
                    current = defcon
                    latest_ts = ts
            out[portco_id] = current
        return out

    def aggregate_drift_alerts(self, window_hours: int = 24) -> dict[str, list[DriftAlert]]:
        """Return vendor-score-gate drift alerts per portco in the window."""
        if window_hours <= 0:
            raise ValueError("window_hours must be positive")
        cutoff = datetime.now(UTC) - timedelta(hours=window_hours)
        out: dict[str, list[DriftAlert]] = {}
        for portco_id in self._portcos:
            events = self._read_chain_events(portco_id)
            alerts: list[DriftAlert] = []
            for event in events:
                if event.get("event_type") != "vendor.score_drift_detected":
                    continue
                ts_str = event.get("timestamp", "")
                try:
                    ts = datetime.fromisoformat(ts_str)
                except (ValueError, TypeError):
                    continue
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=UTC)
                if ts < cutoff:
                    continue
                payload = event.get("payload") or {}
                vendor_id = payload.get("vendor_id", "unknown")
                alerts.append(
                    DriftAlert(
                        vendor_id=str(vendor_id),
                        detected_at=ts_str,
                        payload=payload if isinstance(payload, dict) else {},
                    )
                )
            out[portco_id] = alerts
        return out

    def aggregate_model_inventory_health(self) -> dict[str, ModelInventoryHealth]:
        """Return total-models and overdue-for-validation count per portco.

        Counts unique model_ids referenced in ``fsi.model_validated`` and
        ``vendor.score_recorded`` events. Models marked as overdue come
        from explicit ``governance.compliance_check`` payloads carrying
        ``overdue=True``.
        """
        out: dict[str, ModelInventoryHealth] = {}
        for portco_id in self._portcos:
            events = self._read_chain_events(portco_id)
            model_ids: set[str] = set()
            overdue_ids: set[str] = set()
            for event in events:
                event_type = event.get("event_type", "")
                payload = event.get("payload") or {}
                if not isinstance(payload, dict):
                    continue
                model_id = payload.get("model_id") or payload.get("vendor_id")
                if isinstance(model_id, str) and event_type in (
                    "fsi.model_validated",
                    "vendor.score_recorded",
                ):
                    model_ids.add(model_id)
                if (
                    event_type == "governance.compliance_check"
                    and payload.get("overdue") is True
                    and isinstance(model_id, str)
                ):
                    overdue_ids.add(model_id)
            out[portco_id] = ModelInventoryHealth(
                total_models=len(model_ids),
                overdue_validation=len(overdue_ids),
            )
        return out

    def aggregate_maturity_scores(self) -> dict[str, int]:
        """Return the most recent maturity self-score per portco.

        Reads ``governance.compliance_check`` events whose payload
        carries ``check_type='maturity_self_score'`` and a numeric
        ``level`` field in [1..5]. Portcos with no such event are
        reported as Level 1 (the baseline).
        """
        out: dict[str, int] = {}
        for portco_id in self._portcos:
            events = self._read_chain_events(portco_id)
            level = 1
            latest_ts = ""
            for event in events:
                if event.get("event_type") != "governance.compliance_check":
                    continue
                payload = event.get("payload") or {}
                if not isinstance(payload, dict):
                    continue
                if payload.get("check_type") != "maturity_self_score":
                    continue
                candidate = payload.get("level")
                if not isinstance(candidate, int) or candidate < 1 or candidate > 5:
                    continue
                ts = event.get("timestamp", "")
                if ts >= latest_ts:
                    level = candidate
                    latest_ts = ts
            out[portco_id] = level
        return out

    # ----------------------------------------------------------------- #
    # Reporting                                                         #
    # ----------------------------------------------------------------- #

    def emit_quarterly_report(self) -> str:
        """Emit a markdown report ready for the quarterly review."""
        defcon = self.aggregate_defcon_status()
        drift = self.aggregate_drift_alerts(window_hours=24 * 90)
        inventory = self.aggregate_model_inventory_health()
        maturity = self.aggregate_maturity_scores()

        portfolio_defcon = _max_defcon(list(defcon.values()))
        maturity_dist: dict[int, int] = defaultdict(int)
        for level in maturity.values():
            maturity_dist[level] += 1

        lines: list[str] = []
        as_of = datetime.now(UTC).strftime("%Y-%m-%d")
        lines.append(f"# Portfolio Governance Quarterly Report — {as_of}")
        lines.append("")
        lines.append(
            f"**Portcos in scope:** {len(self._portcos)} · **Portfolio DEFCON:** {portfolio_defcon}"
        )
        lines.append("")
        lines.append("## Portfolio DEFCON narrative")
        lines.append("")
        lines.append("| Portco | DEFCON | Maturity | Models | Overdue | 90-Day Drift Alerts |")
        lines.append("|---|---|---|---|---|---|")
        for portco_id in self._portcos:
            inv = inventory.get(portco_id, ModelInventoryHealth())
            alerts = drift.get(portco_id, [])
            lines.append(
                f"| {portco_id} | {defcon.get(portco_id, 'NORMAL')} "
                f"| L{maturity.get(portco_id, 1)} "
                f"| {inv.total_models} | {inv.overdue_validation} "
                f"| {len(alerts)} |"
            )
        lines.append("")
        lines.append("## Maturity distribution")
        lines.append("")
        for level in (1, 2, 3, 4, 5):
            count = maturity_dist.get(level, 0)
            lines.append(f"- Level {level}: {count} portco(s)")
        lines.append("")
        lines.append("## Red-flag triggers")
        lines.append("")
        triggers: list[str] = []
        for portco_id, state in defcon.items():
            if state == "HALT":
                triggers.append(f"- **{portco_id}** is in DEFCON HALT")
            elif state == "DANGER":
                triggers.append(f"- **{portco_id}** is in DEFCON DANGER")
        for portco_id, inv in inventory.items():
            if inv.overdue_validation > 0:
                triggers.append(
                    f"- **{portco_id}** has {inv.overdue_validation} model(s) "
                    f"overdue for validation"
                )
        for portco_id, alerts in drift.items():
            if len(alerts) >= 3:
                triggers.append(
                    f"- **{portco_id}** has {len(alerts)} vendor-drift alerts in the 90-day window"
                )
        if not triggers:
            triggers.append("- No portfolio-level red-flag triggers in this report.")
        lines.extend(triggers)
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(
            "_Report generated from read-only aggregation of per-portco audit chains. "
            "See ``docs/pe_portfolio_governance_playbook.md`` for the governance model._"
        )
        lines.append("")
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Demo                                                                        #
# --------------------------------------------------------------------------- #


def _write_synthetic_chain(path: Path, events: list[dict[str, Any]]) -> None:
    """Write a synthetic JSONL chain file at ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for event in events:
            fh.write(json.dumps(event) + "\n")


def _now_iso(offset_hours: int = 0) -> str:
    """Return a UTC ISO-8601 timestamp shifted by ``offset_hours``."""
    return (datetime.now(UTC) + timedelta(hours=offset_hours)).isoformat()


def _build_synthetic_portfolio(root: Path) -> dict[str, list[Path]]:
    """Write three synthetic portco chains under ``root`` and return paths."""
    # Portco A: healthy specialty-finance lender at maturity Level 3
    portco_a_events: list[dict[str, Any]] = [
        {
            "event_type": "fsi.model_validated",
            "timestamp": _now_iso(-720),
            "payload": {"model_id": "underwriting-v3", "validator": "second-line"},
        },
        {
            "event_type": "fsi.model_validated",
            "timestamp": _now_iso(-360),
            "payload": {"model_id": "fraud-screen-v2", "validator": "second-line"},
        },
        {
            "event_type": "governance.compliance_check",
            "timestamp": _now_iso(-72),
            "payload": {"check_type": "maturity_self_score", "level": 3},
        },
        {
            "event_type": "risk.deescalation",
            "timestamp": _now_iso(-1),
            "payload": {"defcon": "NORMAL"},
        },
    ]
    # Portco B: insurance carrier with a vendor-drift problem
    portco_b_events: list[dict[str, Any]] = [
        {
            "event_type": "vendor.score_recorded",
            "timestamp": _now_iso(-200),
            "payload": {"vendor_id": "claims-llm-vendor-x", "score": 0.81},
        },
        {
            "event_type": "vendor.score_drift_detected",
            "timestamp": _now_iso(-12),
            "payload": {"vendor_id": "claims-llm-vendor-x", "drift_magnitude": 0.18},
        },
        {
            "event_type": "vendor.score_drift_detected",
            "timestamp": _now_iso(-6),
            "payload": {"vendor_id": "claims-llm-vendor-x", "drift_magnitude": 0.22},
        },
        {
            "event_type": "governance.compliance_check",
            "timestamp": _now_iso(-48),
            "payload": {"check_type": "maturity_self_score", "level": 2},
        },
        {
            "event_type": "governance.compliance_check",
            "timestamp": _now_iso(-24),
            "payload": {
                "check_type": "model_validation",
                "model_id": "claims-llm-vendor-x",
                "overdue": True,
            },
        },
        {
            "event_type": "risk.escalation",
            "timestamp": _now_iso(-2),
            "payload": {"defcon": "ALERT"},
        },
    ]
    # Portco C: consumer-lending portco in DEFCON HALT (red flag)
    portco_c_events: list[dict[str, Any]] = [
        {
            "event_type": "fsi.model_validated",
            "timestamp": _now_iso(-400),
            "payload": {"model_id": "credit-decision-v1", "validator": "second-line"},
        },
        {
            "event_type": "governance.compliance_check",
            "timestamp": _now_iso(-300),
            "payload": {"check_type": "maturity_self_score", "level": 1},
        },
        {
            "event_type": "risk.halt",
            "timestamp": _now_iso(-5),
            "payload": {"defcon": "HALT"},
        },
    ]

    path_a = root / "portco_a" / "chain.jsonl"
    path_b = root / "portco_b" / "chain.jsonl"
    path_c = root / "portco_c" / "chain.jsonl"
    _write_synthetic_chain(path_a, portco_a_events)
    _write_synthetic_chain(path_b, portco_b_events)
    _write_synthetic_chain(path_c, portco_c_events)

    return {
        "portco_a_specialty_finance": [path_a],
        "portco_b_insurance_carrier": [path_b],
        "portco_c_consumer_lending": [path_c],
    }


def _run_demo() -> None:
    """Run the synthetic 3-portco demo and print the quarterly report."""
    with tempfile.TemporaryDirectory(prefix="portfolio_gov_demo_") as tmp:
        root = Path(tmp)
        portcos = _build_synthetic_portfolio(root)
        dashboard = PortfolioGovernanceDashboard()
        for portco_id, paths in portcos.items():
            dashboard.register_portco(portco_id, paths)
        report = dashboard.emit_quarterly_report()
        print(report)


if __name__ == "__main__":
    _run_demo()
