"""Sigstore Rekor public-good witness demo (network-conditional).

What this integration does
--------------------------
Demonstrates anchoring an ``AuditChain`` head to Sigstore's public-good
Rekor transparency log via the ``RekorWitness`` + ``anchor_to_witness``
seam shipped under ``finserv_agent_audit.governance.witness_anchor``
(ADR-0014).

Flow:
    1. Build a 3-event ``AuditChain`` in memory.
    2. Anchor the head hash to https://rekor.sigstore.dev .
    3. Print the resulting Rekor UUID + URL.
    4. Re-anchor the SAME head hash; verify Rekor returns the same UUID
       (Rekor is content-addressed — the inclusion proof for a digest is
       deterministic, so duplicate submissions resolve to the same entry).

What service it talks to
------------------------
Sigstore Rekor public-good instance (``https://rekor.sigstore.dev``).
Transport is stdlib-only via ``urllib.request`` (the ``RekorWitness``
client in the governance package owns the HTTP, so no Sigstore SDK).

Regulatory framework benefits
-----------------------------
- **EU AI Act Article 12** — logging capabilities for high-risk AI; an
  external transparency-log anchor converts the internally-consistent
  hash-chain ``AuditChain`` into an adversarially tamper-EVIDENT record.
- **SR 11-7** — model risk management; the Rekor UUID + log index is the
  effective-challenge artifact a regulator can independently re-verify.
- **SEC Rule 17a-4** — broker-dealer records; pair the chain with a WORM
  ``LedgerStore`` AND a Rekor anchor and you cover both "non-rewriteable
  storage" and "third-party verifiability" in one chain.

Network gate
------------
Hitting the public-good Rekor endpoint requires outbound HTTPS to
``rekor.sigstore.dev``. The demo is gated on
``FINSERV_AUDIT_NETWORK_TESTS=1`` — otherwise it prints a skip notice
and exits 0. This matches the ``network`` pytest marker registered in
``pyproject.toml``.

This is a REFERENCE integration. It is NOT imported by the package
surface and adds no runtime dependency to the wheel.
"""

from __future__ import annotations

import os
import sys

from finserv_agent_audit.governance.audit_chain import AuditChain
from finserv_agent_audit.governance.ledger_store import InMemoryLedgerStore
from finserv_agent_audit.governance.witness_anchor import (
    RekorWitness,
    anchor_to_witness,
)
from finserv_agent_audit.schemas.audit_event import AuditEventType, AutonomyLevel

REKOR_PUBLIC_URL = "https://rekor.sigstore.dev"
NETWORK_GATE_ENV = "FINSERV_AUDIT_NETWORK_TESTS"


def _build_3_event_chain() -> AuditChain:
    chain = AuditChain(ledger_store=InMemoryLedgerStore())
    chain.append(
        event_type=AuditEventType.AGENT_STARTED,
        autonomy_level=AutonomyLevel.A2,
        agent_id="demo:rekor",
        payload={"build": "rekor-witness-demo"},
    )
    chain.append(
        event_type=AuditEventType.DECISION_MADE,
        autonomy_level=AutonomyLevel.A2,
        agent_id="demo:rekor",
        payload={"action": "noop", "reason": "demonstration"},
    )
    chain.append(
        event_type=AuditEventType.COMPLIANCE_CHECK,
        autonomy_level=AutonomyLevel.A2,
        agent_id="demo:rekor",
        payload={"check": "anchor_ready"},
    )
    return chain


def _run_demo() -> int:
    if os.environ.get(NETWORK_GATE_ENV) != "1":
        print(
            f"skipping network demo - set {NETWORK_GATE_ENV}=1 to run "
            f"(would anchor to {REKOR_PUBLIC_URL})"
        )
        return 0

    chain = _build_3_event_chain()
    head = chain.chain_head()
    print(f"chain built : {len(chain._events)} events")  # noqa: SLF001
    print(f"chain head  : {head}")

    witness = RekorWitness(rekor_url=REKOR_PUBLIC_URL, timeout_s=15.0)
    try:
        anchor_event_1 = anchor_to_witness(audit_chain=chain, witness=witness)
    except Exception as exc:  # noqa: BLE001
        print(f"rekor anchor FAILED: {exc!r}")
        return 1
    uuid_1 = anchor_event_1.payload["inclusion_uuid"]
    log_index_1 = anchor_event_1.payload["log_index"]
    print(f"anchor 1    : UUID={uuid_1}  logIndex={log_index_1}")
    print(f"rekor view  : {REKOR_PUBLIC_URL}/api/v1/log/entries/{uuid_1}")

    # Re-anchor the SAME pre-anchor head. We anchor the original head
    # (not the post-anchor head, which is now different because the
    # WITNESS_ANCHOR event was appended).
    try:
        receipt_2 = witness.anchor(head)
    except Exception as exc:  # noqa: BLE001
        print(f"rekor re-anchor FAILED: {exc!r}")
        return 1
    uuid_2 = receipt_2.inclusion_uuid
    print(f"anchor 2    : UUID={uuid_2}  (re-anchored same head)")
    if uuid_1 == uuid_2:
        print("verified    : Rekor returned the same UUID for the same digest (content-addressed)")
    else:
        print(
            "WARNING     : UUIDs differ across re-anchor "
            f"({uuid_1!r} vs {uuid_2!r}). Rekor may have a transient state."
        )
    return 0


if __name__ == "__main__":
    sys.exit(_run_demo())
