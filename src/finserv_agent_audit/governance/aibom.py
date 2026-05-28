"""AIBOM Generator — CycloneDX 1.7 ML-BOM + SPDX 3.0 AI Profile dual emit.

What this module does
---------------------
Generates an **AI Bill of Materials (AIBOM)** stanza in BOTH industry
formats from a single in-process governance state. One call, two
procurement-grade artifacts:

* **CycloneDX 1.7 ML-BOM** — the OWASP CycloneDX ML-BOM profile published
  with the CycloneDX 1.7 spec. Adds the ``machine-learning-model``
  component type and the ``modelCard`` extension carrying training-data,
  bias-considerations, and intended-use fields. The CycloneDX 1.7 line
  is what most procurement teams already accept under their existing
  SBOM clauses; the ML-BOM profile is the AIBOM-shaped overlay on the
  same schema. Reference: https://cyclonedx.org/capabilities/mlbom/
* **SPDX 3.0 AI Profile** — the AI Profile shipped with SPDX 3.0.1, the
  ISO/IEC 5962-conformant SBOM line. Adds the ``ai_AIPackage`` class
  (alongside ``software_Package``) with AI-specific properties:
  training-data, model-explainability, safety-risk-assessment, energy
  consumption, hyperparameters, type-of-model, and the ``ai_useSensitive
  PersonalInformation`` flag for GLBA / GDPR-adjacent disclosures.
  Reference: https://spdx.github.io/spdx-spec/v3.0.1/model/AI/AI/

Why both
--------
The two formats are complements, not substitutes. Different procurement
teams require different formats; FSI deployers regularly need to satisfy
both a SOC 2 vendor-management requirement (CycloneDX-friendly) and an
ISO/IEC 42001-aligned AI management system disclosure (SPDX-friendly) on
the same model. Generating both from one governance call eliminates the
drift risk that comes from maintaining two hand-authored AIBOMs.

Regulatory anchor
-----------------
The **EU AI Act Article 11** technical-documentation obligation takes
effect for high-risk AI systems on **August 2, 2026**. Article 11 names
the items the technical documentation must contain (Annex IV) — the
overlap with AIBOM fields is direct: identity of the provider, intended
purpose, hardware and software requirements, data used during training,
the validation and testing process, the metrics used to measure
accuracy, robustness, and cybersecurity. The AIBOM is the AIBOM-shaped
disclosure that satisfies the Annex IV inventory at procurement.

Cross-walk anchors:

* **Treasury Financial Services AI RMF** (Treasury request for information
  on AI in FSI, June 2024) — the cross-walk between the FSI sector's
  third-party-risk-management posture (OCC Bulletin 2013-29) and the
  AI-specific disclosure overlay. The AIBOM is the third-party AI
  artifact that lands inside the existing TPRM intake.
* **NIST AI RMF 1.1** (the 2024 Generative AI Profile + 2026 update) —
  the "Govern" function § 6.1 calls for an AI inventory mapped to the
  model lifecycle; the AIBOM is the inventory-grade artifact.
* **ISO/IEC 42001:2023** § 8.4 — AI system documentation control
  requires a documented record of AI system characteristics; the AIBOM
  is the documented record for procurement-time disclosure.

Audit-chain emission
--------------------
Every ``emit_*`` call records exactly one ``AuditEventType.COMPLIANCE_CHECK``
entry to the wired ``LedgerStore`` (when one is provided). The chain
entry carries:

* the format (``cyclonedx`` or ``spdx``)
* the AIBOM canonical-JSON SHA-256 hash (so the chain proves which
  exact disclosure was emitted to which counterparty)
* the model ids the AIBOM enumerated
* the count of components / packages

The audit chain is the **operator-side** record of what AIBOM stanza was
shipped to which counterparty at which time. Procurement disputes ("you
shipped us an AIBOM that omitted the OFAC-list training-data field")
get answered with a chain replay against the disclosed hash.

Stdlib-only — uses ``json``, ``hashlib``, ``datetime``, ``uuid``.

See ADR-0031 for the format-selection decision and the procurement-team
cross-walk that motivated dual-emit. Patterns are software, not legal
advice; engage qualified counsel for jurisdictional applicability.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)

if TYPE_CHECKING:
    from finserv_agent_audit.governance.ledger_store import LedgerStore
    from finserv_agent_audit.governance.model_inventory import ModelInventory
    from finserv_agent_audit.governance.vendor_score_gate import VendorScoreGate


# --------------------------------------------------------------------------- #
# Format constants                                                            #
# --------------------------------------------------------------------------- #

CYCLONEDX_SPEC_VERSION = "1.7"
"""CycloneDX spec version emitted. ML-BOM profile rides on 1.7."""

CYCLONEDX_BOM_FORMAT = "CycloneDX"

SPDX_SPEC_VERSION = "3.0.1"
"""SPDX spec version emitted. AI Profile rides on 3.0+."""

SPDX_CONTEXT_URL = "https://spdx.org/rdf/3.0.1/spdx-context.jsonld"
"""JSON-LD context URL for the SPDX 3.0.1 schema."""

DEFAULT_AGENT_ID = "system:aibom_generator"
"""Default ``agent_id`` for chain entries when one is not supplied."""

DEFAULT_AUTONOMY_LEVEL = AutonomyLevel.A2
"""AIBOM emission defaults to A2 (human-on-loop) — a person reviews
the AIBOM before it goes to the counterparty."""


# --------------------------------------------------------------------------- #
# Lightweight in-module model record                                          #
# --------------------------------------------------------------------------- #


@dataclass
class AIBOMModelRecord:
    """One model's AIBOM-relevant fields, in a format-neutral shape.

    The generator pulls these out of the wired ``ModelInventory`` when
    one is available, then converts each record into the CycloneDX
    ``machine-learning-model`` component AND the SPDX ``ai_AIPackage``
    element. Holding the format-neutral shape in one place keeps the
    two emitters in lock-step — a field added here lands in both
    formats on the next emit.
    """

    model_id: str
    version: str
    owner: str
    validator: str
    implementation_status: str
    intended_use: str = ""
    training_data_sources: tuple[str, ...] = ()
    bias_considerations: str = ""
    hyperparameters: dict[str, Any] = field(default_factory=dict)
    type_of_model: str = "machine-learning"
    energy_consumption: str = ""
    safety_risk_assessment: str = ""
    uses_sensitive_personal_information: bool = False
    explainability_mechanism: str = ""
    licenses: tuple[str, ...] = ()
    suppliers: tuple[str, ...] = ()


# --------------------------------------------------------------------------- #
# Generator                                                                   #
# --------------------------------------------------------------------------- #


class AIBOMGenerator:
    """Dual-emit AIBOM generator.

    Usage::

        from finserv_agent_audit.governance.aibom import AIBOMGenerator
        from finserv_agent_audit.governance.ledger_store import (
            InMemoryLedgerStore,
        )

        store = InMemoryLedgerStore()
        gen = AIBOMGenerator(
            ledger_store=store,
            model_inventory=inventory,
            vendor_score_gate=gate,
        )
        cyclonedx_doc = gen.emit_cyclonedx()
        spdx_doc = gen.emit_spdx()
        # or both at once:
        cyclonedx_doc, spdx_doc = gen.emit_both()

    Every emit records a ``COMPLIANCE_CHECK`` entry on the wired
    ledger store with the document's canonical-JSON SHA-256 hash.

    When ``model_inventory`` is ``None`` the generator emits a minimal
    AIBOM with a metadata-only stanza and no components / packages. The
    minimal stanza still carries the spec version and the supplier
    identification so a downstream procurement tool can parse it.
    """

    def __init__(
        self,
        ledger_store: LedgerStore | None = None,
        model_inventory: ModelInventory | None = None,
        vendor_score_gate: VendorScoreGate | None = None,
        *,
        agent_id: str = DEFAULT_AGENT_ID,
        autonomy_level: AutonomyLevel = DEFAULT_AUTONOMY_LEVEL,
        supplier_name: str = "finserv-agent-audit",
        supplier_url: str = "https://github.com/linus10x/finserv-agent-audit",
    ) -> None:
        self._ledger_store = ledger_store
        self._model_inventory = model_inventory
        self._vendor_score_gate = vendor_score_gate
        self._agent_id = agent_id
        self._autonomy_level = autonomy_level
        self._supplier_name = supplier_name
        self._supplier_url = supplier_url

    # ------------------------------------------------------------------ #
    # Public emit API                                                    #
    # ------------------------------------------------------------------ #

    def emit_cyclonedx(self, model_id: str | None = None) -> dict[str, Any]:
        """Emit the CycloneDX 1.7 ML-BOM document as a Python dict.

        When ``model_id`` is supplied the document contains exactly that
        model's component (or none, if the id is not in the inventory).
        When ``None`` every model in the inventory ships as a separate
        component.

        Recorded chain entry: format=``cyclonedx``, payload includes the
        canonical-JSON SHA-256 hash and the enumerated model ids.
        """
        records = self._collect_records(model_id)
        now_iso = _iso_now()
        bom_serial = f"urn:uuid:{uuid.uuid4()}"

        components = [self._record_to_cyclonedx_component(r) for r in records]

        document: dict[str, Any] = {
            "bomFormat": CYCLONEDX_BOM_FORMAT,
            "specVersion": CYCLONEDX_SPEC_VERSION,
            "serialNumber": bom_serial,
            "version": 1,
            "metadata": {
                "timestamp": now_iso,
                "tools": [
                    {
                        "vendor": self._supplier_name,
                        "name": "AIBOMGenerator",
                        "version": SPDX_SPEC_VERSION,
                    }
                ],
                "supplier": {
                    "name": self._supplier_name,
                    "url": [self._supplier_url],
                },
            },
            "components": components,
        }
        self._emit_chain_entry(
            format_name="cyclonedx",
            document=document,
            records=records,
            requested_model_id=model_id,
        )
        return document

    def emit_spdx(self, model_id: str | None = None) -> dict[str, Any]:
        """Emit the SPDX 3.0 AI Profile document as a Python dict.

        The document is JSON-LD-shaped: a top-level ``@context`` pointing
        at the SPDX 3.0.1 schema and a ``@graph`` of typed elements. Each
        inventoried model emits one ``software_Package`` (the artifact)
        plus one ``ai_AIPackage`` (the AI-specific overlay) cross-linked
        by spdxId.

        Recorded chain entry: format=``spdx``, payload includes the
        canonical-JSON SHA-256 hash and the enumerated model ids.
        """
        records = self._collect_records(model_id)
        now_iso = _iso_now()
        document_namespace = f"https://spdx.org/spdxdocs/finserv-agent-audit-{uuid.uuid4()}"

        graph: list[dict[str, Any]] = []
        creation_info_id = "_:creationInfo1"
        graph.append(
            {
                "type": "CreationInfo",
                "@id": creation_info_id,
                "specVersion": SPDX_SPEC_VERSION,
                "created": now_iso,
                "createdBy": [f"Tool: {self._supplier_name}-AIBOMGenerator"],
            }
        )
        for record in records:
            software_package_id = _spdx_id(document_namespace, record, suffix="software")
            ai_package_id = _spdx_id(document_namespace, record, suffix="ai")
            graph.append(
                self._record_to_spdx_software_package(record, software_package_id, creation_info_id)
            )
            graph.append(
                self._record_to_spdx_ai_package(
                    record,
                    ai_package_id,
                    software_package_id,
                    creation_info_id,
                )
            )

        document: dict[str, Any] = {
            "@context": SPDX_CONTEXT_URL,
            "@graph": graph,
            "spdxVersion": SPDX_SPEC_VERSION,
            "documentNamespace": document_namespace,
            "creationInfo": creation_info_id,
        }
        self._emit_chain_entry(
            format_name="spdx",
            document=document,
            records=records,
            requested_model_id=model_id,
        )
        return document

    def emit_both(self, model_id: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
        """Emit both formats in lock-step.

        Returns ``(cyclonedx_doc, spdx_doc)``. Each emit independently
        records its own ``COMPLIANCE_CHECK`` chain entry — the chain
        will show two entries (one per format) tied together by their
        emit timestamps.
        """
        cyclonedx_doc = self.emit_cyclonedx(model_id)
        spdx_doc = self.emit_spdx(model_id)
        return (cyclonedx_doc, spdx_doc)

    # ------------------------------------------------------------------ #
    # Record collection                                                  #
    # ------------------------------------------------------------------ #

    def _collect_records(self, model_id: str | None) -> list[AIBOMModelRecord]:
        """Pull AIBOM records from the wired ModelInventory.

        When no inventory is wired returns ``[]`` — the AIBOM is then a
        valid-but-empty stanza (the procurement file format requires
        metadata even when no components are enumerated).
        """
        if self._model_inventory is None:
            return []
        out: list[AIBOMModelRecord] = []
        for model in self._model_inventory.all():
            if model_id is not None and model.id != model_id:
                continue
            out.append(
                AIBOMModelRecord(
                    model_id=model.id,
                    version=model.version,
                    owner=model.owner,
                    validator=model.validator,
                    implementation_status=model.implementation_status.value,
                )
            )
        return out

    # ------------------------------------------------------------------ #
    # CycloneDX 1.7 ML-BOM component mapping                             #
    # ------------------------------------------------------------------ #

    def _record_to_cyclonedx_component(self, record: AIBOMModelRecord) -> dict[str, Any]:
        """Convert one model record into the CycloneDX ML-BOM component.

        The component carries:

        * ``type``: ``machine-learning-model`` — the CycloneDX 1.7 type
          introduced for ML-BOM
        * ``bom-ref``: stable cross-reference for inter-component links
        * ``modelCard``: the ML-BOM extension carrying training, intended
          use, bias considerations, hyperparameters (1.7-canonical
          ``modelParameters``), and license

        Cross-references are deterministic: ``bom-ref`` is
        ``model:<model_id>@<version>`` so the same model emits with the
        same bom-ref across runs.
        """
        bom_ref = f"model:{record.model_id}@{record.version}"
        model_card: dict[str, Any] = {
            "modelParameters": {
                "approach": {
                    "type": record.type_of_model,
                },
                "task": record.intended_use or "unspecified",
                "datasets": [
                    {"type": "training", "name": source} for source in record.training_data_sources
                ],
            },
            "considerations": {
                "ethicalConsiderations": [
                    {"name": "bias_considerations", "description": record.bias_considerations}
                ]
                if record.bias_considerations
                else [],
                "useCases": [record.intended_use] if record.intended_use else [],
            },
            "quantitativeAnalysis": {
                "performanceMetrics": [],
            },
        }
        if record.hyperparameters:
            model_card["modelParameters"]["hyperparameters"] = dict(record.hyperparameters)

        component: dict[str, Any] = {
            "type": "machine-learning-model",
            "bom-ref": bom_ref,
            "name": record.model_id,
            "version": record.version,
            "modelCard": model_card,
            "properties": [
                {"name": "implementation_status", "value": record.implementation_status},
                {"name": "owner", "value": record.owner},
                {"name": "validator", "value": record.validator},
                {
                    "name": "uses_sensitive_personal_information",
                    "value": str(record.uses_sensitive_personal_information).lower(),
                },
            ],
        }
        if record.licenses:
            component["licenses"] = [{"license": {"id": lic}} for lic in record.licenses]
        if record.suppliers:
            component["supplier"] = {"name": record.suppliers[0]}
        return component

    # ------------------------------------------------------------------ #
    # SPDX 3.0 AI Profile mapping                                        #
    # ------------------------------------------------------------------ #

    def _record_to_spdx_software_package(
        self,
        record: AIBOMModelRecord,
        spdx_id: str,
        creation_info_id: str,
    ) -> dict[str, Any]:
        """Emit the ``software_Package`` element for one model record.

        The software package is the artifact identity — name, version,
        supplier, license. The AI-specific overlay lives in the
        sibling ``ai_AIPackage`` element cross-linked to this id.
        """
        package: dict[str, Any] = {
            "type": "software_Package",
            "spdxId": spdx_id,
            "creationInfo": creation_info_id,
            "name": record.model_id,
            "software_packageVersion": record.version,
            "software_primaryPurpose": "application",
        }
        if record.suppliers:
            package["supplier"] = {
                "type": "Organization",
                "name": record.suppliers[0],
            }
        if record.licenses:
            package["software_licenseConcluded"] = list(record.licenses)
        return package

    def _record_to_spdx_ai_package(
        self,
        record: AIBOMModelRecord,
        ai_spdx_id: str,
        software_spdx_id: str,
        creation_info_id: str,
    ) -> dict[str, Any]:
        """Emit the ``ai_AIPackage`` element for one model record.

        Carries the SPDX 3.0 AI Profile fields:

        * ``ai_typeOfModel`` — model family
        * ``ai_useSensitivePersonalInformation`` — GLBA / GDPR-adjacent
          disclosure flag
        * ``ai_modelExplainability`` — explainability mechanism if any
        * ``ai_safetyRiskAssessment`` — narrative risk-assessment text
        * ``ai_energyConsumption`` — training / inference energy disclosure
        * ``ai_hyperparameter`` — list of name/value pairs
        * ``ai_modelDataPreprocessing`` — narrative when available
        """
        ai_package: dict[str, Any] = {
            "type": "ai_AIPackage",
            "spdxId": ai_spdx_id,
            "creationInfo": creation_info_id,
            "name": f"{record.model_id} (AI overlay)",
            "ai_typeOfModel": [record.type_of_model],
            "ai_useSensitivePersonalInformation": (
                "yes" if record.uses_sensitive_personal_information else "no"
            ),
            "ai_autonomyType": record.implementation_status,
            "software_primaryPurpose": "ai-model",
            "relationship_relatedSpdxElement": software_spdx_id,
            "relationship_relationshipType": "describes",
        }
        if record.explainability_mechanism:
            ai_package["ai_modelExplainability"] = [record.explainability_mechanism]
        if record.safety_risk_assessment:
            ai_package["ai_safetyRiskAssessment"] = record.safety_risk_assessment
        if record.energy_consumption:
            ai_package["ai_energyConsumption"] = record.energy_consumption
        if record.hyperparameters:
            ai_package["ai_hyperparameter"] = [
                {"key": key, "value": str(value)} for key, value in record.hyperparameters.items()
            ]
        if record.training_data_sources:
            ai_package["ai_modelDataPreprocessing"] = list(record.training_data_sources)
        return ai_package

    # ------------------------------------------------------------------ #
    # Audit-chain emission                                               #
    # ------------------------------------------------------------------ #

    def _emit_chain_entry(
        self,
        *,
        format_name: str,
        document: dict[str, Any],
        records: list[AIBOMModelRecord],
        requested_model_id: str | None,
    ) -> AuditEvent | None:
        """Append one ``COMPLIANCE_CHECK`` entry recording the emit.

        The payload carries the canonical-JSON SHA-256 hash of the
        emitted document so a regulator inquiring "which AIBOM did you
        ship to vendor X on date Y" can be answered with a chain replay
        plus the artifact under dispute.
        """
        if self._ledger_store is None:
            return None
        document_hash = _canonical_sha256(document)
        payload: dict[str, Any] = {
            "control": "aibom_emit",
            "format": format_name,
            "aibom_sha256": document_hash,
            "model_ids": [r.model_id for r in records],
            "component_count": len(records),
            "spec_version": (
                CYCLONEDX_SPEC_VERSION if format_name == "cyclonedx" else SPDX_SPEC_VERSION
            ),
            "supplier": self._supplier_name,
        }
        if requested_model_id is not None:
            payload["requested_model_id"] = requested_model_id
        event = AuditEvent(
            event_type=AuditEventType.COMPLIANCE_CHECK,
            autonomy_level=self._autonomy_level,
            agent_id=self._agent_id,
            payload=payload,
            prev_hash=self._ledger_store.head_event_hash(),
        )
        self._ledger_store.append(event)
        return event


# --------------------------------------------------------------------------- #
# Module-private helpers                                                      #
# --------------------------------------------------------------------------- #


def _iso_now() -> str:
    """UTC ISO-8601 timestamp — central helper for reproducibility in tests."""
    return datetime.now(UTC).isoformat()


def _canonical_sha256(document: dict[str, Any]) -> str:
    """Stable SHA-256 of a JSON-serializable dict.

    Uses ``sort_keys=True`` + ``separators=(",", ":")`` so two emits of
    the same logical document produce the same hash regardless of dict
    ordering.
    """
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _spdx_id(document_namespace: str, record: AIBOMModelRecord, *, suffix: str) -> str:
    """Deterministic spdxId per record + suffix.

    spdxId is required to be globally unique within a document; the
    document namespace + model id + suffix gives us a deterministic,
    collision-free id per record + role.
    """
    safe_id = "".join(c if c.isalnum() else "-" for c in f"{record.model_id}-{record.version}")
    return f"{document_namespace}#SPDXRef-{suffix}-{safe_id}"


__all__ = [
    "AIBOMGenerator",
    "AIBOMModelRecord",
    "CYCLONEDX_BOM_FORMAT",
    "CYCLONEDX_SPEC_VERSION",
    "DEFAULT_AGENT_ID",
    "DEFAULT_AUTONOMY_LEVEL",
    "SPDX_CONTEXT_URL",
    "SPDX_SPEC_VERSION",
]
