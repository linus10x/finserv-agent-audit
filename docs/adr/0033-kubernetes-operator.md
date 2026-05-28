# ADR-0033 · Kubernetes Operator + CRDs + Admission Policies for Cluster-Native Deployment

**Status:** Accepted — Reference CRDs + Stub Controller + Sample Admission Policies (v2.0)
**Date:** 2026-05-28
**Author:** Kunjar Bhaduri
**Repo:** finserv-agent-audit v2.0

> **Reference pattern, not legal advice.** Regulatory characterizations are summaries; readers must consult qualified counsel and the firm's TPRM, security, and platform-engineering functions. See repo-root [`DISCLAIMER.md`](../../DISCLAIMER.md).

---

## Context

By 2026 the deployment substrate for stateful AI-agent workloads has consolidated on Kubernetes. The endorsement of record is the **Kubernetes Agent Sandbox** project (`github.com/kubernetes-sigs/agent-sandbox`, March 2026 endorsement from kubernetes-sigs) — a workload-API specification for long-lived agent Pods that each own a PersistentVolume for memory + tool state, with restart, scale-to-zero, and side-car-attached MCP-server semantics. The agent runtime sits inside the Pod; the cluster sits outside as the control-plane substrate.

That substrate moved an inch closer to FSI usability in the same window the v1.x framework was shipping the in-process primitives. The clients are now asking the same question in two different shapes:

1. *"How do we run AuditChain across a fleet of agent Pods without each Pod re-implementing the witness + timestamp + sink wiring?"* — the cluster question.
2. *"How do we keep an agent Pod from being admitted to the cluster at all if it does not declare a kill switch and an audit chain?"* — the admission question.

Neither question is answered by the in-process primitives alone. v1.x shipped the building blocks — `AuditChain` (ADR-0003), `SovereignVeto` (ADR-0002), `WitnessAnchor` (ADR-0014), `MIProxy` (ADR-0015), the ledger-store hierarchy, the integration sinks — but a buyer wiring them into a 50-Pod agent fleet has to invent the cluster-side reconciliation pattern themselves.

The cluster-side policy surface, in parallel, also consolidated:

- **Kyverno 1.17** (February 2026 release) promoted the **CEL policy engine** from beta to v1, joining the original YAML policy engine. Kyverno is now the Kubernetes-native admission controller of choice for teams that want admission policies expressed in Kubernetes-native YAML (or CEL) without learning Rego.
- **OPA Gatekeeper** remains the Rego standard, with the install base + audit-tooling maturity that comes from years of OPA adoption.
- The **hybrid pattern** — Kyverno for the simple validate-and-mutate cases, Gatekeeper for the complex referential cases that need data.inventory cross-namespace lookups — is winning in larger clusters where both engines coexist.

The buyer reading the v1.x README in 2026 lands in a real gap: the in-process primitives are there, the agent-runtime adapters (v2.0.A — A2A, LangGraph, MAF, CrewAI) wire them into the agent runtimes the buyer is already using, and the AIBOM + governance API (v2.0.B) gives the second line the artifact + the API. But the cluster-native deployment substrate — CRDs, an operator, admission policies — is not there.

ADR-0033 closes that gap in v2.0.

## Decision

Ship the **cluster-native deployment substrate** as three CRDs + a reference stub controller + sample admission policies for both Kyverno and OPA Gatekeeper.

The substrate is intentionally split across three concerns that match the three questions the buyer asks:

| CRD | Question it answers |
|---|---|
| `AuditChain` | "How do I declare an audit chain at the cluster level so my agent fleet can read its name and write to it?" |
| `SovereignVeto` | "How do I arm and clear the kill switch from outside the agent runtime, from a separate control plane?" |
| `ChainSink` | "How do I declare where chain events flow when they leave the cluster?" |

The reference stub controller is REFERENCE-ONLY. It uses only the Python standard library, polls the three CRD endpoints on a fixed interval, and reconciles each Spec into a `.status` block. Production deployers MUST replace the stub with a real operator framework — `kopf`, `operator-sdk`, or the Kubernetes Agent Sandbox runtime — because the stub lacks the event-driven watch stream, the informer cache, the leader-election guard, and the metrics endpoint that any production controller needs.

The sample admission policies ship in **both** Kyverno 1.17+ YAML and OPA Gatekeeper Rego. Both engines cover the same three rules:

1. **`require-audit-chain`** — any namespace labeled `finserv.io/agent-namespace=true` must declare at least one AuditChain CRD before any Pod is admitted into it.
2. **`require-sovereign-veto-armed`** — any Pod labeled `app.kubernetes.io/component=agent` must carry an annotation `finserv.io/sovereign-veto-ref=<name>` pointing at an existing SovereignVeto CRD in the same namespace.
3. **`verify-chain-sink`** — any namespace carrying an AuditChain CRD must also carry at least one ChainSink CRD, so chain events never get bottled inside the cluster.

All three policies fail closed — admission is denied when the policy cannot find what it is required to find. This is the cluster-side enforcement of ADR-0002 (kill switch), ADR-0003 (audit chain), and ADR-0017 (retention).

The stub controller has no tests by design. The CRDs are declarative YAML the cluster API server validates against the OpenAPI schema. The policies are declarative YAML the admission controllers validate at apply-time. The Python stub is reference scaffolding meant to be replaced before production — adding a test harness around a controller a deployer is told not to ship would create a false sense of safety. The ADR is explicit about this and the README repeats it.

## Alternatives Considered

- **Skip the cluster-native substrate; ship the v1.x primitives only.** Rejected: the buyer who runs a 50-Pod agent fleet has already invented the cluster-side reconciliation pattern by the time they read the v1.x README. The framework is the second-line artifact; if the second line cannot point at a CRD and a policy that enforces the framework's contract at the cluster boundary, the framework's value drops by a step function in any cluster-shipping FSI environment.
- **Ship a production controller built on `kopf` or `operator-sdk` in this tranche.** Rejected for v2.0: a production controller adds runtime dependencies (kopf is a third-party Python package; operator-sdk requires a Go toolchain), a Helm chart story, a leader-election design, a metrics-endpoint design, a webhook-conversion design, and a release cadence the v2.0 ship cannot absorb without slipping the other v2.0 tranches. The stub plus the documented upgrade path is the right step for v2.0. Production tools land in v2.1 if the buyer demand profile warrants it.
- **Ship Kyverno policies only (skip the OPA Gatekeeper Rego variants).** Rejected: the FSI install base is split. The teams that adopted OPA Gatekeeper early have built audit tooling around Rego, and asking them to add Kyverno alongside is a non-starter in any conservative platform-engineering function. Shipping both variants lets the deployer pick the engine their cluster already runs and removes the cluster-engine-choice question from the v2.0 onboarding path.
- **Use the Kubernetes Agent Sandbox CRDs directly without a finserv-agent-audit-specific layer.** Rejected: the Agent Sandbox describes the *agent workload* (the Pod that runs the agent). The CRDs in this ADR describe the *governance substrate* (the audit chain, the kill switch, the sink) the agent workload writes to and reads from. The two are complementary — production deployers run both, with the Agent Sandbox Pod spec referencing the SovereignVeto CRD by annotation. The README documents this pairing.
- **Express the policies in CEL only (Kyverno 1.17's GA path) and skip the YAML policy syntax.** Rejected: the YAML policy syntax is the older, more widely-deployed path, and a buyer on Kyverno 1.16 still using YAML policies cannot upgrade to CEL without a cluster-coordinated rollout. Shipping the YAML form covers both 1.16 and 1.17; the CEL upgrade can land in a later patch when the install base catches up.

## Consequences

**Positive.** The buyer can now deploy the framework across a Kubernetes-native agent fleet without re-implementing the cluster-side wiring. The admission policies give the second line a hard cluster-boundary enforcement of the framework's contract: a Pod cannot be admitted into an agent namespace without an audit chain, and an agent Pod cannot be admitted without a wired kill switch. The CRD schemas are declarative + versioned at the API-server boundary; the framework's contract surfaces to the cluster operator the same way a Service or a ConfigMap does. The hybrid Kyverno + OPA samples remove the engine-choice question from the v2.0 onboarding path.

**Negative.** The stub controller is, by design, not production-ready. A deployer who copies the Dockerfile + the stub + the rbac.yaml and ships them into production without reading the ADR or the README will get a controller that does not retry on transient API errors, does not leader-elect (so a two-replica deploy will race), and does not emit metrics. The framework signals this loudly in three places (the controller docstring, this ADR, the README's production-hardening section), but the surface area for a missed-warning failure is real. Mitigation: the README's production-hardening section is the first heading after the install walkthrough; the stub controller's docstring leads with the "REFERENCE STUB" notice; the Dockerfile's LABEL block carries the same notice.

**Architectural.** The CRDs introduce no new in-process Python types — they are declarative YAML the cluster API server stores. The stub controller introduces no new Python imports beyond the standard library + the existing `finserv_agent_audit.governance.*` modules. The framework's wheel + the framework's test suite are unchanged; the operator scaffolding lives entirely under `deploy/k8s/` and the framework wheel does not depend on it. The cluster-native substrate is a strict add-on; nothing in v1.x changes shape.

## Regulatory + Standards Mapping

- **Kubernetes Agent Sandbox** (`github.com/kubernetes-sigs/agent-sandbox`, kubernetes-sigs endorsement March 2026) — the workload-API specification for long-lived agent Pods. The SovereignVeto CRD in this ADR is the cluster-side control plane the Agent Sandbox Pod spec references via annotation.
- **Kyverno 1.17** (February 2026 release) — promoted the CEL policy engine from beta to v1. The sample policies in `deploy/k8s/policies/kyverno/` use the original YAML policy syntax (1.16+ compatible) for broad install-base coverage.
- **OPA Gatekeeper** (CNCF graduated) — the Rego admission-policy reference. The sample ConstraintTemplate + Constraint pairs in `deploy/k8s/policies/opa/` require Gatekeeper's `referential` sync to be configured for the finserv.io/v1 CRDs (covered in the README).
- **NIST AI 600-1** (Generative AI Profile, July 2024) — the Governance + Operations control families map cleanly onto the CRD-as-declarative-spec pattern.
- finserv-agent-audit **ADR-0002** (Sovereign Veto) — the SovereignVeto CRD is the cluster-side control plane for the in-process veto.
- finserv-agent-audit **ADR-0003** (Hash-chained Audit Ledger) — the AuditChain CRD is the cluster-side declaration of an in-process chain.
- finserv-agent-audit **ADR-0014** (Persistence + Witness + Timestamp pattern) — the AuditChain CRD spec carries the witness + timestamp seam class references.
- finserv-agent-audit **ADR-0015** (MI Proxy module-integrity attestation) — optional MIProxy class is named in the AuditChain CRD spec.
- finserv-agent-audit **ADR-0017** (Audit-chain retention + privilege + discovery posture) — the ChainSink CRD is the cluster-side declaration of where chain events flow for the retention substrate ADR-0017 specifies.

## Pre-mortem

The failure mode this ADR prevents: a buyer reads the v2.0 README, deploys the v1.x primitives across a 50-Pod fleet, and three months later cannot answer the OCC question *"show me, at the cluster boundary, the control that prevents a new agent Pod from being deployed without a kill switch"*. With the admission policy in place, the answer is `kubectl describe clusterpolicy require-sovereign-veto-armed` (or the matching Gatekeeper Constraint) plus the admission-log replay showing the policy blocking the offending Pod.

The failure mode this ADR creates if mishandled: a deployer copies the stub controller into production without reading the docstring or this ADR, runs two replicas behind a Deployment, and the second replica races the first on every PATCH cycle (no leader election). The chain status flips between two values; a downstream alert fires on the flip; the second line concludes the framework is unstable. Mitigation: the controller stub explicitly does not include a Deployment with replicas > 1 by default (the reference rbac.yaml ships `replicas: 1`); the README's production-hardening section names leader election as the first item; the stub controller docstring leads with the "REFERENCE STUB" notice.

## Reversibility

Reversible at the CRD layer. The OpenAPI schema is versioned (`finserv.io/v1`); a future version (`finserv.io/v2`) can land alongside v1 with a CRD conversion webhook, the existing v1 instances continue to function, and the operator reconciles both versions until the buyer migrates. The admission policies are reversible by deleting the ClusterPolicy / ConstraintTemplate — the next Pod admission falls back to the default-allow stance with no residual state.

Less reversible at the buyer's cluster-policy layer. Once a cluster operator has wired their agent-namespace label scheme to the `require-audit-chain` policy, removing the policy is a deliberate action — a buyer who has trained their second-line auditors to read `kubectl describe clusterpolicy` outputs is not going to silently delete one of those policies without notice. The framework treats this as positive friction: the admission policy is supposed to be load-bearing once it is in place.

## Cross-references

- ADR-0002 (Sovereign Veto) — the in-process kill switch the SovereignVeto CRD exposes at the cluster control plane.
- ADR-0003 (Hash-chained Audit Ledger) — the in-process chain the AuditChain CRD declares + reconciles.
- ADR-0014 (Persistence + Witness + Timestamp pattern) — the seam classes the AuditChain CRD references.
- ADR-0015 (MI Proxy) — the optional module-integrity seam the AuditChain CRD names.
- ADR-0017 (Audit-Chain Retention) — the retention substrate the ChainSink CRD points at.

---

*Patterns are software, not legal advice. Regulatory citations are reference mappings; consult counsel for applicability to your control environment.*
