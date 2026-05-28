"""Vendor Attestation Ledger — ADR-0023.

The bulk of an FSI institution's third-party AI exposure is mediated by
two-page "trust portal" pages and "SOC 2 Type II under NDA" promises.
That is a self-attestation, not an independent verification, and it is
not a chain-of-custody record. When the OCC examiner asks "show me who
attested what version of OpenAI's safety controls when," the bank's
TPRM team should be able to produce a hash-chained ledger entry inside
sixty seconds.

This module records WHO attested WHAT version on WHAT date, supports
re-attestation on a cadence, and turns vendor-side receipts (SOC 2,
ISO 27001, ISO 42001, FedRAMP, PCI DSS, HITRUST, plus SR 11-7
validation pass-through tokens) into chain-of-custody evidence the
third-line auditor can replay. Every recorded attestation emits an
`AuditEventType.COMPLIANCE_CHECK` entry through the injected
`LedgerStore`; the chain is the evidentiary backbone.

Regulatory anchors:
    - SR 11-7 / OCC Bulletin 2026-13 (third-party-model-validation
      pass-through; the operator's first line carries the exposure even
      when the model is rented)
    - DORA Article 28 (Regulation (EU) 2022/2554) — ICT third-party
      risk management; written agreement + audit access requirements
    - Treasury FS AI RMF (February 2026) — third-party + fourth-party
      AI oversight control objectives
    - OCC Bulletin 2013-29 — original third-party-risk-management
      framework, superseded for AI workloads by the 2026 interagency
      RFI process
    - DORA RTS on subcontracting (Commission Delegated Regulation
      2024/1773) — fourth-party-disclosure cadence
    - NIST AI 600-1 § "Value Chain and Component Integration" — the
      generative-AI third-party-component-control objective

> Reference pattern, not legal advice. Regulatory characterizations are
> summaries; consult qualified counsel for compliance determinations.
> See repo-root `DISCLAIMER.md`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from finserv_agent_audit.governance.ledger_store import LedgerStore
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)

# The literal of supported attestation types. Adding a new type is a
# minor (additive) change; removing one is a breaking change because
# downstream chain entries reference the literal in their payload.
AttestationType = Literal[
    "SOC2_TYPE_I",
    "SOC2_TYPE_II",
    "ISO_27001",
    "ISO_42001",
    "FedRAMP_Moderate",
    "FedRAMP_High",
    "PCI_DSS",
    "HITRUST",
    "SR_11_7_validation",
    "SR_11_7_validation_independent_review",
]


@dataclass(frozen=True)
class VendorAttestation:
    """One vendor-attestation record.

    Fields:
        vendor_id: stable identifier for the vendor (e.g. ``"anthropic"``).
        attestation_type: one of the supported `AttestationType` values.
        attesting_entity: who signed the attestation. For self-attestation
            this is the vendor; for independent review this is the
            third-party auditor (e.g. ``"bsi_independent_auditor"``).
        version: vendor-side version identifier for the attestation
            (e.g. ``"2025-Q4"`` for a SOC 2 Type II audit period).
        attestation_hash: SHA-256 (or equivalent) hash of the canonical
            attestation document the operator has on file.
        valid_from: start of the attestation's coverage window.
        valid_until: end of the attestation's coverage window.
        evidence_url: optional pointer to the operator-side artifact
            (trust-portal link, vendor-furnished doc store).
    """

    vendor_id: str
    attestation_type: AttestationType
    attesting_entity: str
    version: str
    attestation_hash: str
    valid_from: datetime
    valid_until: datetime
    evidence_url: str | None = None


@dataclass(frozen=True)
class AttestationGap:
    """A required (vendor, attestation_type) pair that is not satisfied.

    Returned by `VendorAttestationLedger.query_missing` so the TPRM team
    can convert the gap list directly into a remediation backlog.
    """

    vendor_id: str
    attestation_type: AttestationType


class VendorAttestationLedger:
    """Chain-of-custody record for vendor AI-control attestations.

    Wire a `LedgerStore` in the constructor to receive a
    `COMPLIANCE_CHECK` event on every `record_attestation` call. Without
    a store the ledger still tracks attestations in memory and supports
    queries; emissions become silent.
    """

    def __init__(self, ledger_store: LedgerStore | None = None) -> None:
        self._store: LedgerStore | None = ledger_store
        self._attestations: list[VendorAttestation] = []
        self._agent_id = "system:vendor_attestation_ledger"

    # ------------------------------------------------------------------ #
    # Record                                                             #
    # ------------------------------------------------------------------ #

    def record_attestation(
        self,
        vendor_id: str,
        attestation_type: AttestationType,
        attesting_entity: str,
        version: str,
        attestation_hash: str,
        valid_from: datetime,
        valid_until: datetime,
        evidence_url: str | None = None,
    ) -> VendorAttestation:
        """Record a new attestation and emit a chain entry."""
        _validate_inputs(
            vendor_id=vendor_id,
            attesting_entity=attesting_entity,
            version=version,
            attestation_hash=attestation_hash,
            valid_from=valid_from,
            valid_until=valid_until,
        )
        attestation = VendorAttestation(
            vendor_id=vendor_id,
            attestation_type=attestation_type,
            attesting_entity=attesting_entity,
            version=version,
            attestation_hash=attestation_hash,
            valid_from=valid_from,
            valid_until=valid_until,
            evidence_url=evidence_url,
        )
        self._attestations.append(attestation)
        self._emit_compliance_event(attestation)
        return attestation

    # ------------------------------------------------------------------ #
    # Queries                                                            #
    # ------------------------------------------------------------------ #

    def query(
        self,
        vendor_id: str,
        attestation_type: AttestationType | None = None,
        valid_as_of: datetime | None = None,
    ) -> list[VendorAttestation]:
        """Return attestations matching the filter.

        When `valid_as_of` is supplied, only attestations whose
        coverage window contains the timestamp are returned.
        """
        results: list[VendorAttestation] = []
        for att in self._attestations:
            if att.vendor_id != vendor_id:
                continue
            if attestation_type is not None and att.attestation_type != attestation_type:
                continue
            if valid_as_of is not None and not (att.valid_from <= valid_as_of <= att.valid_until):
                continue
            results.append(att)
        return results

    def query_expired(self, grace_period_days: int = 30) -> list[VendorAttestation]:
        """Return attestations expiring within the grace window.

        Includes attestations already past their `valid_until`. Default
        grace period is 30 days — calibrate per the TPRM team's
        remediation cycle.
        """
        if grace_period_days < 0:
            raise ValueError(f"grace_period_days must be non-negative; got {grace_period_days}")
        now = datetime.now(UTC)
        results: list[VendorAttestation] = []
        for att in self._attestations:
            days_until_expiry = (att.valid_until - now).days
            if days_until_expiry <= grace_period_days:
                results.append(att)
        return results

    def query_missing(
        self,
        required_attestations: list[tuple[str, AttestationType]],
    ) -> list[AttestationGap]:
        """Return required (vendor_id, attestation_type) pairs not currently satisfied.

        "Satisfied" means at least one matching attestation exists whose
        coverage window contains ``datetime.now(UTC)``. Expired
        attestations do not satisfy current requirements — that is the
        whole point.
        """
        now = datetime.now(UTC)
        gaps: list[AttestationGap] = []
        for vendor_id, attestation_type in required_attestations:
            matches = self.query(
                vendor_id=vendor_id,
                attestation_type=attestation_type,
                valid_as_of=now,
            )
            if not matches:
                gaps.append(
                    AttestationGap(
                        vendor_id=vendor_id,
                        attestation_type=attestation_type,
                    )
                )
        return gaps

    # ------------------------------------------------------------------ #
    # Internals                                                          #
    # ------------------------------------------------------------------ #

    def _emit_compliance_event(self, attestation: VendorAttestation) -> None:
        if self._store is None:
            return
        prev_hash = self._store.head_event_hash()
        event = AuditEvent(
            event_type=AuditEventType.COMPLIANCE_CHECK,
            autonomy_level=AutonomyLevel.A2,
            agent_id=self._agent_id,
            payload={
                "control": "vendor_attestation_recorded",
                "vendor_id": attestation.vendor_id,
                "attestation_type": attestation.attestation_type,
                "attesting_entity": attestation.attesting_entity,
                "version": attestation.version,
                "attestation_hash": attestation.attestation_hash,
                "valid_from": attestation.valid_from.isoformat(),
                "valid_until": attestation.valid_until.isoformat(),
                "evidence_url": attestation.evidence_url,
            },
            prev_hash=prev_hash,
        )
        self._store.append(event)


# --------------------------------------------------------------------------- #
# Module-private helpers                                                      #
# --------------------------------------------------------------------------- #


def _validate_inputs(
    *,
    vendor_id: str,
    attesting_entity: str,
    version: str,
    attestation_hash: str,
    valid_from: datetime,
    valid_until: datetime,
) -> None:
    if not vendor_id:
        raise ValueError("vendor_id must be a non-empty string")
    if not attesting_entity:
        raise ValueError("attesting_entity must be a non-empty string")
    if not version:
        raise ValueError("version must be a non-empty string")
    if not attestation_hash:
        raise ValueError("attestation_hash must be a non-empty string")
    if valid_until < valid_from:
        raise ValueError(
            f"valid_until ({valid_until.isoformat()}) precedes "
            f"valid_from ({valid_from.isoformat()})"
        )


__all__ = [
    "AttestationGap",
    "AttestationType",
    "VendorAttestation",
    "VendorAttestationLedger",
]
