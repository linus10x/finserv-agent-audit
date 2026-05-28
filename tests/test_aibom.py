"""Tests for the AIBOM generator (v2.0 — ADR-0031).

The generator emits BOTH CycloneDX 1.7 ML-BOM and SPDX 3.0 AI Profile
stanzas from a single in-process governance state. The tests pin:

  * the CycloneDX 1.7 schema-level fields the procurement-team scan
    looks for (``bomFormat``, ``specVersion``, ``machine-learning-model``
    component type, ``modelCard``)
  * the SPDX 3.0 AI Profile schema-level fields (``@context``,
    ``software_Package``, ``ai_AIPackage`` with ``ai_typeOfModel``)
  * the dual-emit lock-step contract
  * audit-chain emission per call
  * empty-inventory and missing-model edge cases
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from finserv_agent_audit.governance.aibom import (
    CYCLONEDX_BOM_FORMAT,
    CYCLONEDX_SPEC_VERSION,
    SPDX_SPEC_VERSION,
    AIBOMGenerator,
    AIBOMModelRecord,
)
from finserv_agent_audit.governance.ledger_store import InMemoryLedgerStore
from finserv_agent_audit.governance.model_inventory import (
    ImplementationStatus,
    Model,
    ModelInventory,
)
from finserv_agent_audit.schemas.audit_event import AuditEventType

# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #


@pytest.fixture
def now() -> datetime:
    return datetime.now(UTC)


@pytest.fixture
def inventory_two_models(now: datetime) -> ModelInventory:
    inv = ModelInventory()
    inv.register(
        Model(
            id="credit_scorer_v3",
            version="3.0.1",
            owner="first-line@bank.example",
            validator="mrm@bank.example",
            implementation_status=ImplementationStatus.APPROVED_FOR_PRODUCTION,
            validation_date=now - timedelta(days=10),
            next_validation_due=now + timedelta(days=355),
        )
    )
    inv.register(
        Model(
            id="fraud_scorer_v2",
            version="2.1.0",
            owner="first-line@bank.example",
            validator="mrm@bank.example",
            implementation_status=ImplementationStatus.APPROVED_FOR_LIMITED_USE,
            validation_date=now - timedelta(days=5),
            next_validation_due=now + timedelta(days=180),
        )
    )
    return inv


@pytest.fixture
def store() -> InMemoryLedgerStore:
    return InMemoryLedgerStore()


# --------------------------------------------------------------------------- #
# CycloneDX 1.7 schema                                                        #
# --------------------------------------------------------------------------- #


class TestCycloneDXEmission:
    def test_top_level_fields_present(self, inventory_two_models: ModelInventory) -> None:
        gen = AIBOMGenerator(model_inventory=inventory_two_models)
        doc = gen.emit_cyclonedx()
        assert doc["bomFormat"] == CYCLONEDX_BOM_FORMAT
        assert doc["specVersion"] == CYCLONEDX_SPEC_VERSION
        assert "serialNumber" in doc
        assert doc["serialNumber"].startswith("urn:uuid:")
        assert doc["version"] == 1
        assert "metadata" in doc and "timestamp" in doc["metadata"]
        assert "components" in doc

    def test_component_per_model(self, inventory_two_models: ModelInventory) -> None:
        gen = AIBOMGenerator(model_inventory=inventory_two_models)
        doc = gen.emit_cyclonedx()
        assert len(doc["components"]) == 2
        types = {c["type"] for c in doc["components"]}
        assert types == {"machine-learning-model"}

    def test_modelcard_block_present(self, inventory_two_models: ModelInventory) -> None:
        gen = AIBOMGenerator(model_inventory=inventory_two_models)
        doc = gen.emit_cyclonedx()
        for component in doc["components"]:
            card = component["modelCard"]
            assert "modelParameters" in card
            assert "considerations" in card
            assert "approach" in card["modelParameters"]

    def test_filter_by_model_id(self, inventory_two_models: ModelInventory) -> None:
        gen = AIBOMGenerator(model_inventory=inventory_two_models)
        doc = gen.emit_cyclonedx(model_id="credit_scorer_v3")
        assert len(doc["components"]) == 1
        assert doc["components"][0]["name"] == "credit_scorer_v3"


# --------------------------------------------------------------------------- #
# SPDX 3.0 AI Profile schema                                                  #
# --------------------------------------------------------------------------- #


class TestSPDXEmission:
    def test_top_level_jsonld_shape(self, inventory_two_models: ModelInventory) -> None:
        gen = AIBOMGenerator(model_inventory=inventory_two_models)
        doc = gen.emit_spdx()
        assert "@context" in doc
        assert "@graph" in doc
        assert doc["spdxVersion"] == SPDX_SPEC_VERSION
        assert doc["documentNamespace"].startswith("https://spdx.org/spdxdocs/")
        assert isinstance(doc["@graph"], list)

    def test_ai_aipackage_present_per_model(self, inventory_two_models: ModelInventory) -> None:
        gen = AIBOMGenerator(model_inventory=inventory_two_models)
        doc = gen.emit_spdx()
        ai_packages = [e for e in doc["@graph"] if e.get("type") == "ai_AIPackage"]
        software_packages = [e for e in doc["@graph"] if e.get("type") == "software_Package"]
        assert len(ai_packages) == 2
        assert len(software_packages) == 2

    def test_ai_typeofmodel_field_emitted(self, inventory_two_models: ModelInventory) -> None:
        gen = AIBOMGenerator(model_inventory=inventory_two_models)
        doc = gen.emit_spdx()
        ai_packages = [e for e in doc["@graph"] if e.get("type") == "ai_AIPackage"]
        for pkg in ai_packages:
            assert "ai_typeOfModel" in pkg
            assert "ai_useSensitivePersonalInformation" in pkg
            assert pkg["relationship_relationshipType"] == "describes"


# --------------------------------------------------------------------------- #
# Dual emit                                                                   #
# --------------------------------------------------------------------------- #


class TestDualEmit:
    def test_emit_both_returns_two_documents(self, inventory_two_models: ModelInventory) -> None:
        gen = AIBOMGenerator(model_inventory=inventory_two_models)
        cyclonedx_doc, spdx_doc = gen.emit_both()
        assert cyclonedx_doc["bomFormat"] == CYCLONEDX_BOM_FORMAT
        assert spdx_doc["spdxVersion"] == SPDX_SPEC_VERSION
        # Both must independently enumerate every inventoried model.
        assert len(cyclonedx_doc["components"]) == 2
        ai_packages = [e for e in spdx_doc["@graph"] if e.get("type") == "ai_AIPackage"]
        assert len(ai_packages) == 2


# --------------------------------------------------------------------------- #
# Audit-chain emission                                                        #
# --------------------------------------------------------------------------- #


class TestChainEmission:
    def test_cyclonedx_emit_records_compliance_check(
        self,
        inventory_two_models: ModelInventory,
        store: InMemoryLedgerStore,
    ) -> None:
        gen = AIBOMGenerator(ledger_store=store, model_inventory=inventory_two_models)
        doc = gen.emit_cyclonedx()
        events = list(store)
        assert len(events) == 1
        entry = events[0]
        assert entry.event_type == AuditEventType.COMPLIANCE_CHECK
        assert entry.payload["control"] == "aibom_emit"
        assert entry.payload["format"] == "cyclonedx"
        assert entry.payload["component_count"] == 2
        # The hash recorded in the chain must equal the freshly-computed
        # canonical hash of the emitted document — the operator-side
        # proof of which exact disclosure went to the counterparty.
        canonical = json.dumps(doc, sort_keys=True, separators=(",", ":"), default=str).encode(
            "utf-8"
        )
        assert entry.payload["aibom_sha256"] == hashlib.sha256(canonical).hexdigest()

    def test_spdx_emit_records_compliance_check(
        self,
        inventory_two_models: ModelInventory,
        store: InMemoryLedgerStore,
    ) -> None:
        gen = AIBOMGenerator(ledger_store=store, model_inventory=inventory_two_models)
        gen.emit_spdx()
        events = list(store)
        assert len(events) == 1
        assert events[0].payload["format"] == "spdx"

    def test_emit_both_writes_two_entries(
        self,
        inventory_two_models: ModelInventory,
        store: InMemoryLedgerStore,
    ) -> None:
        gen = AIBOMGenerator(ledger_store=store, model_inventory=inventory_two_models)
        gen.emit_both()
        events = list(store)
        assert len(events) == 2
        assert {events[0].payload["format"], events[1].payload["format"]} == {
            "cyclonedx",
            "spdx",
        }


# --------------------------------------------------------------------------- #
# Edge cases                                                                  #
# --------------------------------------------------------------------------- #


class TestEdgeCases:
    def test_empty_inventory_emits_metadata_only(self) -> None:
        gen = AIBOMGenerator()
        cyclonedx_doc = gen.emit_cyclonedx()
        spdx_doc = gen.emit_spdx()
        assert cyclonedx_doc["components"] == []
        # SPDX still emits the CreationInfo element so the document
        # parses even when no packages are enumerated.
        types = {e.get("type") for e in spdx_doc["@graph"]}
        assert "CreationInfo" in types

    def test_missing_model_id_returns_empty_components(
        self, inventory_two_models: ModelInventory
    ) -> None:
        gen = AIBOMGenerator(model_inventory=inventory_two_models)
        doc = gen.emit_cyclonedx(model_id="does-not-exist")
        assert doc["components"] == []

    def test_no_ledger_store_is_graceful_no_op(self, inventory_two_models: ModelInventory) -> None:
        # Without a wired ledger store, emit must succeed and return the
        # document; the operator simply forfeits the chain entry.
        gen = AIBOMGenerator(model_inventory=inventory_two_models)
        doc = gen.emit_cyclonedx()
        assert doc["bomFormat"] == CYCLONEDX_BOM_FORMAT

    def test_aibommodelrecord_dataclass_field_defaults(self) -> None:
        record = AIBOMModelRecord(
            model_id="x",
            version="0.1",
            owner="o",
            validator="v",
            implementation_status="proposed",
        )
        assert record.training_data_sources == ()
        assert record.hyperparameters == {}
        assert record.uses_sensitive_personal_information is False


# --------------------------------------------------------------------------- #
# Sanity — module lives where the ADR says                                    #
# --------------------------------------------------------------------------- #


def test_module_lives_at_documented_path() -> None:
    root = Path(__file__).resolve().parent.parent
    expected = root / "src" / "finserv_agent_audit" / "governance" / "aibom.py"
    assert expected.is_file()
