# ADR-0031 · AIBOM Generator — CycloneDX 1.7 ML-BOM + SPDX 3.0 AI Profile Dual Emit

**Status:** Accepted (shipped in v2.0)
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit v2.0

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel for jurisdictional applicability. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

---

## Context

The **EU AI Act Article 11** technical-documentation obligation takes effect for high-risk AI systems on **August 2, 2026** (EU AI Act, Regulation (EU) 2024/1689). Annex IV enumerates the items the technical documentation must contain: identity of the provider, intended purpose, hardware and software requirements, the data used during training, validation and testing processes, accuracy / robustness / cybersecurity metrics. The overlap with the AI-Bill-of-Materials (AIBOM) concept is direct — the AIBOM is the procurement-time disclosure artifact that satisfies the Annex IV inventory for a deployer integrating a third-party model.

Two AIBOM formats lead the industry standardization race; both are at production-grade today:

- **CycloneDX 1.7 ML-BOM** (OWASP CycloneDX, https://cyclonedx.org/capabilities/mlbom/). The CycloneDX 1.7 spec added the `machine-learning-model` component type and a `modelCard` extension that carries training-data, intended-use, bias-considerations, and hyperparameter fields. CycloneDX is the SBOM line most procurement teams already accept under existing SOC 2 / vendor-management clauses; the ML-BOM profile is the AIBOM overlay on the same schema.
- **SPDX 3.0 AI Profile** (Linux Foundation SPDX, ISO/IEC 5962-conformant, https://spdx.github.io/spdx-spec/v3.0.1/model/AI/AI/). SPDX 3.0.1 added an `ai_AIPackage` class alongside the existing `software_Package`, with AI-specific properties: `ai_typeOfModel`, `ai_useSensitivePersonalInformation`, `ai_modelExplainability`, `ai_safetyRiskAssessment`, `ai_energyConsumption`, `ai_hyperparameter`, `ai_modelDataPreprocessing`. SPDX is the SBOM line ISO/IEC 42001-aligned AI management systems lean on.

A US-regulated bank doing third-party AI procurement in 2026 needs both. Different procurement teams require different formats — the SOC 2 vendor-management owner asks for CycloneDX; the ISO/IEC 42001 internal-audit owner asks for SPDX. The bank cannot afford to maintain two hand-authored AIBOMs per model; the drift risk between two hand-authored disclosures is itself an audit finding.

The cross-walks that motivate the dual-format ship:

- **Treasury Financial Services AI RMF** (Treasury request for information on AI in FSI, June 2024) — the FSI sector's third-party-risk-management posture (anchored in OCC Bulletin 2013-29) is the intake the AIBOM lands inside.
- **NIST AI RMF 1.1** — the "Govern" function § 6.1 calls for an AI inventory mapped to the model lifecycle; the AIBOM is the inventory-grade artifact.
- **ISO/IEC 42001:2023** § 8.4 — AI system documentation control requires a documented record of AI system characteristics.

## Decision

Ship `AIBOMGenerator` in v2.0 as a **dual-emit** generator that produces BOTH CycloneDX 1.7 ML-BOM and SPDX 3.0 AI Profile stanzas from a single in-process governance state.

### Module surface

```python
from finserv_agent_audit.governance.aibom import AIBOMGenerator
from finserv_agent_audit.governance.ledger_store import InMemoryLedgerStore

store = InMemoryLedgerStore()
gen = AIBOMGenerator(
    ledger_store=store,
    model_inventory=inventory,
    vendor_score_gate=gate,
)
cyclonedx_doc = gen.emit_cyclonedx()
spdx_doc = gen.emit_spdx()
cyclonedx_doc, spdx_doc = gen.emit_both()
```

### Design contracts

1. **Single source of truth.** The generator pulls every AIBOM field out of the wired `ModelInventory` and converts each record into the matching CycloneDX `machine-learning-model` component AND the SPDX `ai_AIPackage` + `software_Package` pair. Adding a field to the format-neutral `AIBOMModelRecord` lands in both emitters on the next call.
2. **Audit-chain emission per call.** Every `emit_*` records exactly one `AuditEventType.COMPLIANCE_CHECK` entry to the wired `LedgerStore`. The chain entry carries the canonical-JSON SHA-256 hash of the emitted document — the operator-side proof of which exact disclosure went to which counterparty on which date.
3. **Stdlib-only.** Uses `json`, `hashlib`, `datetime`, `uuid`. No third-party SBOM / AIBOM library is pulled in; the schemas are public and stable enough to emit from a typed dict literal.
4. **Empty inventory is valid.** When no `ModelInventory` is wired the generator emits the metadata-only stanza in each format. The procurement file format requires document-level metadata even when no components are enumerated; the empty stanza is a valid procurement-shaped artifact.
5. **Deterministic identifiers.** CycloneDX `bom-ref` is `model:<id>@<version>`; SPDX `spdxId` is `<document_namespace>#SPDXRef-<role>-<id>-<version>`. Two emits of the same logical inventory produce structurally comparable documents.

### Audit-chain payload schema

The `COMPLIANCE_CHECK` payload emitted on each call:

```json
{
  "control": "aibom_emit",
  "format": "cyclonedx" | "spdx",
  "aibom_sha256": "<64-char hex>",
  "model_ids": ["..."],
  "component_count": <int>,
  "spec_version": "1.7" | "3.0.1",
  "supplier": "finserv-agent-audit",
  "requested_model_id": "<optional>"
}
```

The `aibom_sha256` is computed over the canonical-JSON serialization (sort_keys=True, separators=(",", ":")) so two emits of the same logical document produce the same hash. A regulator-side dispute — "the AIBOM you delivered to vendor X on date Y omitted field Z" — gets answered with a chain replay against the disclosed hash.

## Alternatives Considered

- **Ship CycloneDX only.** Rejected: the ISO/IEC 42001-aligned procurement-team asks for SPDX. A v2.0 ship that names "AIBOM" but only emits CycloneDX is a deliberate deferral that the buyer's audit team will catch on the first procurement scan.
- **Ship SPDX only.** Rejected: the SOC 2 vendor-management team already runs CycloneDX scanners. An SPDX-only AIBOM lands outside the existing TPRM intake.
- **Vendor a CycloneDX library + an SPDX library.** Rejected for v2.0: the schemas are stable enough to emit from typed dicts, the libraries vary in maintenance posture, and the zero-runtime-dependency contract (ADR D2.2) is load-bearing for the base wheel. The dual-emit module is ~550 lines of stdlib; the dependency cost of two third-party emitters is not justified.
- **Defer to v2.1.** Rejected: the August 2, 2026 EU AI Act Article 11 enforcement date is the hard external deadline. v2.0 has to ship the procurement-grade artifact; deferring leaves adopters with no audit-quality disclosure during the enforcement window.
- **Ship a converter from one format to the other rather than dual-emit.** Rejected: lossy in both directions. CycloneDX `modelCard.considerations.ethicalConsiderations` does not have a clean SPDX 3.0 analog; SPDX `ai_safetyRiskAssessment` does not map cleanly to a single CycloneDX property. Dual-emit from a format-neutral record keeps both formats first-class.

## Consequences

**Positive.** A v2.0 deployment closes the Article 11 procurement-artifact gap before the August 2, 2026 enforcement date. Procurement teams asking for either CycloneDX or SPDX get a first-class artifact; teams asking for both get them in lock-step. The audit-chain `aibom_sha256` field gives the operator the disclosure-of-record they need when a counterparty disputes the contents of a past AIBOM. The generator composes onto the existing `ModelInventory` + `LedgerStore` seams without introducing new persistence or new network calls.

**Negative.** The dual-emit generator necessarily carries two parallel mapping paths (record → CycloneDX component, record → SPDX package pair). When the underlying spec versions advance (CycloneDX 1.8, SPDX 3.1), both paths must update together. The ADR's "single source of truth" contract is enforced by tests: every emit_both call must enumerate the same model set in both formats.

The keyword-overlap between AIBOM fields and the broader EU AI Act Annex IV inventory is partial. The AIBOM covers the model-level disclosure; the Annex IV technical documentation also requires system-level fields (intended-use limits, risk-management process, post-market monitoring plan) that the AIBOM does not carry. A v2.1 ADR may add a separate `TechnicalDocumentationGenerator` for the system-level fields; the AIBOM is the model-level inventory and stops there.

**Architectural.** The generator introduces no new persistence, no new network call, and no new runtime dependency. It composes onto the existing `AuditChain` (ADR-0003 + ADR-0014) and consumes the same `AuditEventType.COMPLIANCE_CHECK` event class the rest of the v1.x patterns use.

## Regulatory Mapping

- EU AI Act, Regulation (EU) 2024/1689 — Article 11 (technical documentation), Annex IV (documentation contents), enforcement date August 2, 2026 for high-risk AI systems.
- OWASP CycloneDX 1.7 ML-BOM — https://cyclonedx.org/capabilities/mlbom/ (the schema this ADR's CycloneDX emitter targets).
- SPDX 3.0.1 AI Profile — https://spdx.github.io/spdx-spec/v3.0.1/model/AI/AI/ (the schema this ADR's SPDX emitter targets).
- Treasury request for information on AI in FSI (June 2024) — third-party-risk-management cross-walk anchoring AIBOM intake.
- NIST AI RMF 1.1 — "Govern" function § 6.1 (AI inventory) and "Map" function (procurement-time disclosure inventory).
- ISO/IEC 42001:2023 § 8.4 — AI system documentation control.
- ISO/IEC 5962:2021 — SPDX 3.0 international-standard conformance.
- finserv-agent-audit ADR-0003 — hash-chain audit ledger (the substrate the AIBOM-emit chain entries land on).
- finserv-agent-audit ADR-0007 — SR 11-7 model inventory (the data source the generator pulls AIBOM records from).
- finserv-agent-audit ADR-0016 — vendor-score gate (the procurement-time companion seam).

## Pre-mortem

The failure mode this ADR prevents: a buyer wires the generator into the procurement intake, the counterparty asks for either CycloneDX or SPDX, the generator emits both, the chain captures the SHA-256 of the exact bytes shipped, and a future audit inquiry about disclosure contents is answered with a chain replay rather than a hand-rolled reconstruction.

The failure mode this ADR creates if mishandled: a deployer extends `AIBOMModelRecord` with a new field, the CycloneDX path picks it up via the `modelCard` extension surface, the SPDX path silently omits it because the operator forgot to wire the field into `_record_to_spdx_ai_package`, and the two emitted documents drift. Mitigation: the test suite pins `emit_both` to enumerate the same model set in both formats; the module docstring is explicit that field additions land in both emitters on the same commit; the ADR's "single source of truth" contract names the failure mode.

## Reversibility

Reversible. The dual-emit contract is the surface; replacing one of the two formats with a successor spec (CycloneDX 1.8, SPDX 3.1) is a non-breaking change as long as `emit_<format>` continues to return a procurement-shaped dict carrying the spec-version field. The audit-chain `aibom_emit` payload schema (above) is the load-bearing piece — replacing the format emitters while preserving the chain payload is a non-breaking change.

## Cross-references

- ADR-0003 (Hash-chained Audit Ledger) — the substrate the AIBOM-emit chain entries land on.
- ADR-0007 (SR 11-7 Model Inventory) — the data source the generator pulls AIBOM records from.
- ADR-0014 (Witness Anchor) — when the AIBOM chain head is anchored to an external witness, the AIBOM disclosure becomes evidence outside the operator's trust boundary.
- ADR-0016 (Vendor Score Gate) — the procurement-time companion seam; AIBOM enumerates the model, VendorScoreGate captures the runtime score against that model.
- ADR-0032 (FastAPI Governance API) — the v2.0 HTTP surface that exposes the AIBOM disclosure to procurement-team callers.

---

*Patterns are software, not legal advice. Regulatory citations are reference mappings; consult counsel for applicability to your control environment.*
