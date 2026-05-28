"""Deprecation Watch — ADR-0025.

The 2025-2026 record of foundation-model deprecation cycles makes the
problem explicit:

  * OpenAI deprecated o1-preview on July 28, 2025 with a short
    transition window.
  * Google Cloud Vertex AI deprecated Claude 3.7 Sonnet on November 11,
    2025; shutdown May 11, 2026.
  * Novita's January 2026 deprecation notice gave 14 days.

A bank running Reg-BI-relevant flows on these endpoints cannot survive
a 14-day cycle. The institution needs an early-warning monitor that
polls each vendor's changelog, computes days-until-sunset, and emits
an audit-chain `DEPRECATION_ALERT` while there is still time to swap
the upstream.

This module is the polling harness. Each vendor is registered with a
changelog URL and a `ChangelogParser` callable (the parser is
vendor-specific; we ship no defaults because every vendor's changelog
format differs). On `check()`, the watch fetches every registered URL,
runs the parser, computes days-until-sunset for each
`DeprecationAnnouncement`, and emits a chain entry for any sunset
inside `alert_window_days` (default 60). HTTP and parser failures are
swallowed-per-vendor: one vendor's broken changelog must not block the
poll of other vendors.

The default `http_get` is `urllib.request.urlopen` (stdlib only). Tests
inject a synthesizable callable so the harness is fully exercisable
without network access.

Regulatory anchors:
    - OpenAI o1-preview deprecation (July 28, 2025) — short-window
      precedent
    - Google Cloud Vertex AI / Claude 3.7 deprecation (Nov 11, 2025;
      shutdown May 11, 2026) — six-month cycle as the longer end
    - Novita January 2026 deprecation (14-day notice) — the floor the
      bank must guard against
    - SR 11-7 § V.4 — model implementation, use, and change
    - DORA Article 28 — exit-strategy + contractual-transition
      requirements

> Reference pattern, not legal advice. Regulatory characterizations are
> summaries; consult counsel for applicability. See repo-root
> `DISCLAIMER.md`.
"""

from __future__ import annotations

import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from finserv_agent_audit.governance.ledger_store import LedgerStore
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)

# HTTP-get callable signature. The default is a thin wrapper over
# `urllib.request.urlopen`; tests inject a synthesizable callable.
HttpGet = Callable[..., str]

DEFAULT_TIMEOUT_SECONDS: float = 10.0
DEFAULT_ALERT_WINDOW_DAYS: int = 60


def _default_http_get(url: str, *, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> str:
    """Stdlib HTTP GET; returns the response body as a UTF-8 string."""
    with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310
        data: bytes = response.read()
    return data.decode("utf-8", errors="replace")


@dataclass(frozen=True)
class DeprecationAnnouncement:
    """One vendor-published deprecation record.

    Fields:
        vendor_id: stable identifier for the vendor.
        model_id: vendor-side identifier for the deprecated model.
        sunset_date: when the model becomes unavailable.
        deprecation_date: when the deprecation was announced.
        replacement_model_id: vendor-recommended replacement, or None.
        source_url: where the parser extracted the announcement from.
    """

    vendor_id: str
    model_id: str
    sunset_date: datetime
    deprecation_date: datetime
    replacement_model_id: str | None
    source_url: str


class ChangelogParser(Protocol):
    """Vendor-specific parser that converts a changelog blob into announcements.

    Implementations are operator-supplied because every vendor's
    changelog format differs (HTML, JSON, RSS, plain markdown). The
    parser MUST return an empty list when no deprecations are present;
    raising signals a malformed-changelog condition the watch handles
    by skipping the vendor for the current poll cycle.
    """

    def __call__(self, payload: str) -> list[DeprecationAnnouncement]: ...


@dataclass
class _RegisteredVendor:
    """Internal registry entry."""

    vendor_id: str
    changelog_url: str
    parser: ChangelogParser


class DeprecationWatch:
    """Poll vendor changelogs and emit chain alerts for upcoming sunsets.

    Wire a `LedgerStore` to receive a `DEPRECATION_ALERT` chain event
    for each sunset inside the alert window. Without a store the watch
    still returns the alert list from `check()`; chain emission is
    silent.
    """

    def __init__(
        self,
        ledger_store: LedgerStore | None = None,
        http_get: HttpGet | None = None,
    ) -> None:
        self._store: LedgerStore | None = ledger_store
        self._http_get: HttpGet = http_get if http_get is not None else _default_http_get
        self._vendors: dict[str, _RegisteredVendor] = {}
        self._agent_id = "system:deprecation_watch"

    # ------------------------------------------------------------------ #
    # Register                                                           #
    # ------------------------------------------------------------------ #

    def register_vendor(
        self,
        vendor_id: str,
        changelog_url: str,
        parser: ChangelogParser,
    ) -> None:
        """Register a vendor's changelog source."""
        if not vendor_id:
            raise ValueError("vendor_id must be a non-empty string")
        if not changelog_url:
            raise ValueError("changelog_url must be a non-empty string")
        if vendor_id in self._vendors:
            raise ValueError(f"vendor {vendor_id!r} already registered")
        self._vendors[vendor_id] = _RegisteredVendor(
            vendor_id=vendor_id,
            changelog_url=changelog_url,
            parser=parser,
        )

    # ------------------------------------------------------------------ #
    # Check                                                              #
    # ------------------------------------------------------------------ #

    def check(
        self,
        now: datetime | None = None,
        alert_window_days: int = DEFAULT_ALERT_WINDOW_DAYS,
    ) -> list[DeprecationAnnouncement]:
        """Fetch every registered changelog and emit alerts within the window.

        Returns the list of announcements that fell inside (or already
        past) the alert window. HTTP failures and parser failures are
        swallowed per-vendor: one broken vendor cannot block the rest.
        """
        if alert_window_days < 0:
            raise ValueError(f"alert_window_days must be non-negative; got {alert_window_days}")
        evaluation_time = now if now is not None else datetime.now(UTC)
        alerts: list[DeprecationAnnouncement] = []
        for vendor in self._vendors.values():
            try:
                payload = self._http_get(vendor.changelog_url, timeout=DEFAULT_TIMEOUT_SECONDS)
            except (OSError, ValueError):
                # Network failure / unreachable changelog — skip this
                # vendor for this poll cycle. The next cron run retries.
                continue
            try:
                announcements = vendor.parser(payload)
            except Exception:  # noqa: BLE001
                # Parser failure on one vendor must not block others.
                continue
            for announcement in announcements:
                days_until_sunset = (announcement.sunset_date - evaluation_time).days
                if days_until_sunset > alert_window_days:
                    continue
                alerts.append(announcement)
                self._emit_alert(announcement, days_until_sunset)
        return alerts

    # ------------------------------------------------------------------ #
    # Internals                                                          #
    # ------------------------------------------------------------------ #

    def _emit_alert(
        self,
        announcement: DeprecationAnnouncement,
        days_until_sunset: int,
    ) -> None:
        if self._store is None:
            return
        prev_hash = self._store.head_event_hash()
        event = AuditEvent(
            event_type=AuditEventType.DEPRECATION_ALERT,
            autonomy_level=AutonomyLevel.A2,
            agent_id=self._agent_id,
            payload={
                "vendor_id": announcement.vendor_id,
                "model_id": announcement.model_id,
                "sunset_date": announcement.sunset_date.isoformat(),
                "deprecation_date": announcement.deprecation_date.isoformat(),
                "replacement_model_id": announcement.replacement_model_id,
                "source_url": announcement.source_url,
                "days_until_sunset": days_until_sunset,
            },
            prev_hash=prev_hash,
        )
        self._store.append(event)


__all__ = [
    "ChangelogParser",
    "DEFAULT_ALERT_WINDOW_DAYS",
    "DeprecationAnnouncement",
    "DeprecationWatch",
]
