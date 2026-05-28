# ADR-0032 · FastAPI Governance API — OpenAPI 3.1 + SSE Streaming Chain Verification

**Status:** Accepted (shipped in v2.0)
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit v2.0

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel for jurisdictional applicability. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

---

## Context

Through v1.3 the framework's governance surface — audit chain verification, sovereign-veto triggers, model-inventory queries, vendor-score-gate drift events — was reachable only from inside the same Python process the agent was running in. The v2.0 ship moves the framework into a posture where adopters increasingly need to expose the governance surface over HTTP:

- **Procurement-team scanners.** FSI procurement teams running automated vendor-management scans key off **OpenAPI 3.1** specifications. The procurement scan does not read Python type annotations; it asks "does this vendor publish an OpenAPI spec naming the endpoints we care about" before moving the engagement forward.
- **Dashboard / SOC operators.** A 24x7 security-operations-center team monitoring the agent posture needs to render veto status, chain-verification progress, and recent vendor drift in a browser. The browser cannot import the Python module; it asks an HTTP endpoint.
- **Long-running chain verification.** A multi-million-entry audit chain takes minutes to verify end-to-end. A blocking HTTP call that returns only the final verdict is operationally hostile; the dashboard needs an incremental progress signal so the operator can render a progress bar without polling.
- **Cross-process veto triggers.** An external risk monitor (a separate microservice, a SIEM hook, a peer agent on a different host) needs to trigger a sovereign veto on the in-process agent without a deploy-side IPC mechanism.

The procurement-team OpenAPI preference is decisive. A FastAPI-based control plane auto-generates an OpenAPI 3.1 specification at `/openapi.json` + a Swagger UI at `/docs` from the route definitions; the procurement scan keys off the auto-generated spec on day one. Hand-rolling an OpenAPI spec from a Flask / aiohttp / Tornado server is a maintenance burden the framework does not need to take on.

## Decision

Ship `create_app(audit_chain, model_inventory, sovereign_veto, vendor_score_gate)` in `finserv_agent_audit.integrations.governance_api` as a FastAPI factory that returns a fully-wired `FastAPI` app. The factory accepts every governance Protocol seam the framework ships; passing `None` for an optional seam causes the matching endpoints to return 503 with a clear "not configured" payload.

### Endpoint surface

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/healthz` | none | Liveness probe |
| GET | `/info` | none | Package + module versions |
| GET | `/audit-chain/info` | none | Length, head hash, event-type histogram |
| GET | `/audit-chain/verify` | none | `{intact, last_tampered}` JSON |
| GET | `/audit-chain/verify-stream` | none | SSE stream of per-chunk verification progress |
| POST | `/audit-chain/append` | required | Append an event |
| GET | `/model-inventory` | none | List inventoried models |
| GET | `/sovereign-veto/status` | none | Active vetos + history count |
| POST | `/sovereign-veto/trigger` | required | Trigger a veto (emits chain entry) |
| POST | `/sovereign-veto/clear` | required | Clear a veto with documented reason |
| GET | `/vendor-score-gate/recent-drift` | none | Recent drift events |
| GET | `/openapi.json` | none | Auto-generated OpenAPI 3.1 spec |
| GET | `/docs` | none | Swagger UI |

### Design contracts

1. **OpenAPI 3.1 by construction.** FastAPI auto-generates the spec from the route definitions. The factory pins `openapi_version="3.1.0"` so the procurement scan keys off the version-stable surface.
2. **SSE streaming for chain verification.** The `/audit-chain/verify-stream` endpoint emits one `progress` event per `sse_chunk_size` audited entries (default 1000) plus a terminal `result` event carrying the final verdict. The SSE wire format (`event:` + `data:` + blank line) traverses corporate proxies cleanly over standard HTTP/1.1; WebSockets are rejected for this surface because the proxy traversal story is worse.
3. **Auth is operator-supplied.** The factory accepts an `auth_checker: Callable[[Request], None]` that raises `HTTPException` on auth failure. The shipped default rejects every mutating call — there is no permissive default because the absence of an auth layer is a deploy-time error, not a runtime convenience. The operator MUST bind the checker to their identity infrastructure (OIDC bearer-token, mTLS subject lookup, internal service-account check).
4. **Mutating calls emit audit-chain entries.** Every `POST /sovereign-veto/trigger` appends a `VETO_APPLIED` entry to the chain; every `POST /sovereign-veto/clear` appends a `HUMAN_OVERRIDE` entry. The API-layer veto is hash-chained alongside in-process vetos so a regulator-side replay shows the full veto history regardless of trigger surface.
5. **Import-guarded optional dependency.** The module import-guards FastAPI behind a `HAS_FASTAPI` boolean and the `[api]` extra. Without FastAPI installed, `create_app` raises `RuntimeError` with the install hint — the integration surface is opt-in, not silently no-op.
6. **Stable API contract across deploys.** Endpoints for unwired seams (`/model-inventory` when no inventory is wired; `/sovereign-veto/status` when no veto is wired) return 503 with a clear `{detail: "<seam> not wired"}` payload rather than 404. The procurement scan sees the endpoint enumerated in the OpenAPI spec regardless of which seams the deployer chose to wire.

### Dependency posture

`fastapi>=0.136`, `uvicorn[standard]>=0.30`, `httpx>=0.27` ship under the `[api]` extra. SSE streaming uses Starlette's built-in `StreamingResponse` — no extra dependency needed. The base wheel keeps the zero-runtime-dependency contract (ADR D2.2).

## Alternatives Considered

- **Hand-roll an OpenAPI 3.1 spec on top of Flask.** Rejected: maintenance burden the framework does not need. FastAPI's auto-generation is the entire reason it dominates the FSI control-plane surface in 2026.
- **Use aiohttp / Starlette directly.** Rejected: Starlette IS what FastAPI is built on; choosing Starlette directly is choosing FastAPI without the OpenAPI auto-generation. The procurement scan wants the spec; choosing the layer below FastAPI gives up the procurement-team win for no gain.
- **WebSockets for chain-verification progress.** Rejected: SSE traverses corporate proxies cleanly over standard HTTP/1.1; WebSockets require the proxy to support HTTP UPGRADE which many FSI environments block by policy. SSE is the right wire format for a one-way progress channel.
- **Ship a permissive default auth checker.** Rejected: the absence of auth is a deploy-time error. A permissive default would let an operator wire the governance API to a production audit chain with no auth boundary; the cost of that mistake is too high. The reject-all default is loud.
- **Inline the API into a separate `finserv-agent-audit-api` package.** Rejected: the factory composes onto the existing in-process governance seams; splitting the package would force every adopter to coordinate two release lines for one ship. The import-guard pattern keeps the base wheel dependency-free.
- **Defer the API to v2.1.** Rejected: the procurement-team OpenAPI ask is the current 2026 buying signal. Without an OpenAPI spec, the framework does not clear the FSI vendor-management intake; deferring the API costs adoption today.

## Consequences

**Positive.** A v2.0 deployment exposes the framework's governance surface as a first-party HTTP API with an OpenAPI 3.1 contract that FSI procurement teams already know how to scan. The SSE endpoint lets the SOC dashboard render incremental progress on million-entry chains without polling. The auth-checker seam composes onto the deployer's identity infrastructure without locking the framework to a single auth library. The API-layer veto triggers are hash-chained alongside in-process triggers, preserving the chain-of-custody contract across the trust boundary.

**Negative.** The factory ships with a reject-all default auth checker. An operator who fails to read the docstring will see 401 on every mutating call and conclude the API is broken; the fix is documented (supply an `auth_checker`) but the friction is real. The trade-off is intentional — silent permissive defaults on a governance API are a worse failure mode than a loud rejection.

The SSE endpoint walks the chain in-memory. For multi-million-entry chains backed by a remote `LedgerStore` (Postgres+WAL, S3 + Object Lock), the in-memory walk is wrong — the chain should be paged from the backend. The v2.0 ship documents this; a v2.1 ADR may add a paged-walk seam to the chain-verification path.

**Architectural.** The integration introduces one new module (`integrations/governance_api.py`) and one new optional-dependency extra (`[api]`). It composes onto every governance Protocol seam the framework ships without modifying the chain, the inventory, the veto, or the gate. The audit-chain emission contract for mutating endpoints (`VETO_APPLIED` on trigger, `HUMAN_OVERRIDE` on clear) is the load-bearing piece.

## Regulatory Mapping

- **EU AI Act, Regulation (EU) 2024/1689 — Article 14** (human oversight of high-risk AI systems). The API surface is the operator-side path for the human-on-the-loop trigger / clear actions that Article 14 demands; the chain emission on every mutating call is the evidentiary record.
- **EU AI Act — Article 12** (logging capabilities for high-risk AI systems). Every API-layer veto / clear / append emits a chained audit event; the chain is the Article-12-grade log.
- **SR 11-7** (model risk management) — the API gives the second-line model-risk team a non-engineering surface for inventory queries and veto triggers; the chain emission preserves the third-line evidence.
- **FFIEC IT Examination Handbook** — third-party API surfaces require documented authentication, authorization, and audit-logging controls. The factory pins all three: pluggable auth checker, mutating-endpoint chain emission, and OpenAPI-documented endpoint enumeration.
- **OWASP API Security Top 10 (2023)** — the reject-all default auth checker, the OpenAPI 3.1 spec generation, and the input-validation-by-Pydantic posture address the API1 (Broken Object-Level Authorization) and API2 (Broken Authentication) categories at design time rather than at incident time.
- **FastAPI 0.136+ + OpenAPI 3.1 + SSE production patterns** — Starlette's `StreamingResponse` with `media_type="text/event-stream"` is the canonical SSE wire-format implementation; FastAPI's `openapi_version="3.1.0"` pin is the canonical procurement-grade contract emitter.
- **finserv-agent-audit ADR-0002** (Sovereign Veto) — the in-process veto contract this API exposes over HTTP.
- **finserv-agent-audit ADR-0003** (Hash-Chained Audit Ledger) — the substrate the API-layer chain entries land on.
- **finserv-agent-audit ADR-0007** (SR 11-7 Model Inventory) — the in-process inventory contract this API exposes over HTTP.
- **finserv-agent-audit ADR-0016** (Vendor Score Gate) — the in-process drift contract this API exposes as a read-only convenience view.
- **finserv-agent-audit ADR-0031** (AIBOM Generator) — the v2.0 procurement-grade artifact emitter; a future ADR may add an AIBOM-emit endpoint on this API surface.

## Pre-mortem

The failure mode this ADR prevents: an FSI buyer scans the framework, sees a Python package with no HTTP surface, concludes there is no procurement-grade contract, and exits the engagement. With the API and the auto-generated OpenAPI 3.1 spec, the buyer's procurement scan passes on day one; the engagement proceeds.

The failure mode this ADR creates if mishandled: an operator wires the factory into production without supplying an `auth_checker`, hits 401 on every mutating call, swaps the default for a permissive lambda to "make it work", and now the audit chain accepts unauthenticated appends. Mitigation: the module docstring is explicit that the reject-all default is intentional; the `RuntimeError` on missing FastAPI carries the install hint; the `auth_checker` parameter is named, typed, and documented; the test suite exercises the 401 path so the operator sees the rejection in CI before deploy.

## Reversibility

Reversible. The endpoint surface is the contract; the FastAPI implementation is the substrate. Replacing FastAPI with a successor framework that auto-generates OpenAPI 3.1 (Starlette + a hand-rolled spec, Litestar, Robyn) is a non-breaking change as long as `create_app` continues to return an ASGI-compatible app with the documented endpoints. The OpenAPI 3.1 contract + the audit-chain emission contract for mutating endpoints are the load-bearing pieces.

## Cross-references

- ADR-0002 (Sovereign Veto) — the in-process veto contract this API exposes.
- ADR-0003 (Hash-Chained Audit Ledger) — the chain the API-layer mutating endpoints emit to.
- ADR-0007 (SR 11-7 Model Inventory) — the in-process inventory contract this API exposes.
- ADR-0014 (Persistence-Witness-Timestamp Pattern) — when the chain head is anchored, the API-layer chain entries inherit the witness-side evidence.
- ADR-0016 (Vendor Score Gate) — the in-process drift contract this API exposes.
- ADR-0017 (Audit-Chain Retention, Privilege & Discovery) — the retention schedule the API-layer chain entries land inside.
- ADR-0031 (AIBOM Generator) — the v2.0 procurement-grade artifact emitter exposed alongside this API.

---

*Patterns are software, not legal advice. Regulatory citations are reference mappings; consult counsel for applicability to your control environment.*
