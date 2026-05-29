# finserv-agent-audit · Kubernetes Deployment Substrate

Cluster-native deployment scaffolding for the v2.0 framework: three CRDs,
a reference operator stub, and admission-policy samples for both
Kyverno 1.17+ and OPA Gatekeeper. Pair with the in-process primitives
shipped in v1.x and the agent-runtime adapters shipped in v2.0.A.

See **[ADR-0033](../../docs/adr/0033-kubernetes-operator.md)** for the
full decision record. This README is the operator-facing walkthrough.

> The operator stub in `operator/controller.py` is **reference-only**.
> It uses only the Python standard library, polls CRD endpoints on a
> fixed interval, and lacks the watch stream, informer cache, and
> leader election any production controller needs. It DOES ship a
> minimal `/healthz` + `/readyz` + `/metrics` HTTP surface (port 8080)
> so the Deployment's probes and Prometheus scrape have something
> useful to hit, but the metrics set is starter-only. Production
> deployers MUST replace it with `kopf`, `operator-sdk`, or the
> Kubernetes Agent Sandbox runtime before going live. The
> production-hardening section below is the first thing to read after
> the install walkthrough.

---

## Layout

```
deploy/k8s/
├── crds/
│   ├── auditchain.yaml          # AuditChain CRD (finserv.io/v1)
│   ├── sovereignveto.yaml       # SovereignVeto CRD (finserv.io/v1)
│   └── chainsink.yaml           # ChainSink CRD (finserv.io/v1)
├── operator/
│   ├── Dockerfile               # Multi-stage, digest-pinned, non-root UID 65532
│   ├── controller.py            # Stdlib reconciler + /healthz + /readyz + /metrics
│   ├── rbac.yaml                # SA + ClusterRole + Role (leader-election) + Service + PDB + Deployment
│   ├── servicemonitor.yaml      # Prometheus Operator ServiceMonitor (optional)
│   ├── pvc-sample.yaml          # Sample PVC for persistent ledger backends
│   └── networkpolicy.yaml       # Default-deny egress with explicit allow-list
└── policies/
    ├── kyverno/
    │   ├── require-audit-chain.yaml
    │   ├── require-sovereign-veto-armed.yaml
    │   └── verify-chain-sink.yaml
    └── opa/
        ├── require-audit-chain.rego
        ├── require-sovereign-veto-armed.rego
        └── verify-chain-sink.rego
```

---

## Step 1 — Install the CRDs

```bash
kubectl apply -f deploy/k8s/crds/
```

Verify:

```bash
kubectl api-resources --api-group=finserv.io
# NAME             SHORTNAMES   APIVERSION       NAMESPACED   KIND
# auditchains      ac           finserv.io/v1    true         AuditChain
# chainsinks       cs           finserv.io/v1    true         ChainSink
# sovereignvetoes  sv           finserv.io/v1    true         SovereignVeto
```

The CRDs are namespaced. Every AuditChain, SovereignVeto, and
ChainSink instance belongs to exactly one namespace, and the operator
reconciles them per namespace.

---

## Step 2 — Deploy the operator

The reference operator stub is published as a container image at
`ghcr.io/linus10x/finserv-agent-audit-operator:2.0.0` (the framework
release tag). To build locally:

```bash
# From repository root — the Dockerfile is multi-stage and needs
# pyproject.toml + src/ from the repo root to build the wheel.
docker build \
    -f deploy/k8s/operator/Dockerfile \
    -t finserv-agent-audit-operator:2.0.0 \
    .
# Push to your registry, then edit rbac.yaml's image: field if you
# changed the registry path.
```

Create the operator namespace, then apply the RBAC bundle (it includes
the Deployment):

```bash
kubectl create namespace finserv-system
kubectl apply -f deploy/k8s/operator/rbac.yaml
```

The Deployment ships `replicas: 1` by design — the stub has no leader
election. Production controllers MUST add leader election before
scaling to two or more replicas.

Verify the operator is running:

```bash
kubectl -n finserv-system get pods -l app.kubernetes.io/name=finserv-agent-audit-operator
kubectl -n finserv-system logs -l app.kubernetes.io/name=finserv-agent-audit-operator -f
# 2026-05-28 ... INFO finserv.operator finserv-agent-audit operator stub starting; namespace=finserv-system interval=30s
# 2026-05-28 ... INFO finserv.operator reconcile cycle complete: ok=0 failed=0
```

---

## Step 3 — Install the admission policies

Pick **one** of Kyverno or OPA Gatekeeper. The hybrid-cluster pattern
(both engines installed, with non-overlapping policy responsibilities)
also works — see the production-hardening section.

### Option A — Kyverno 1.17+

Install Kyverno first if not already present
(https://kyverno.io/docs/installation/). Then:

```bash
kubectl apply -f deploy/k8s/policies/kyverno/
kubectl get clusterpolicies
# NAME                              ADMISSION   BACKGROUND   VALIDATE ACTION   READY
# require-audit-chain               true        false        Enforce           True
# require-sovereign-veto-armed      true        false        Enforce           True
# verify-chain-sink                 true        false        Enforce           True
```

### Option B — OPA Gatekeeper

Install Gatekeeper first if not already present
(https://open-policy-agent.github.io/gatekeeper/website/docs/install).
Then configure the referential sync so the policies can read the
finserv.io CRDs across namespaces:

```yaml
# gatekeeper-sync-config.yaml — required for the OPA policies to see
# AuditChain, SovereignVeto, and ChainSink instances in
# data.inventory.namespace[ns]["finserv.io/v1"][...].
apiVersion: config.gatekeeper.sh/v1alpha1
kind: Config
metadata:
  name: config
  namespace: gatekeeper-system
spec:
  sync:
    syncOnly:
      - group: "finserv.io"
        version: "v1"
        kind: "AuditChain"
      - group: "finserv.io"
        version: "v1"
        kind: "SovereignVeto"
      - group: "finserv.io"
        version: "v1"
        kind: "ChainSink"
      - group: ""
        version: "v1"
        kind: "Namespace"
```

Apply the sync config + the policies:

```bash
kubectl apply -f gatekeeper-sync-config.yaml
kubectl apply -f deploy/k8s/policies/opa/
kubectl get constrainttemplates
kubectl get constraints
```

---

## Step 4 — Verify the policy enforcement path

Create an agent namespace, deploy the CRDs, then try (and fail) to
deploy an agent Pod without the required wiring:

```bash
# 1. Create a namespace labeled as an agent namespace.
kubectl create namespace agent-zeus
kubectl label namespace agent-zeus finserv.io/agent-namespace=true

# 2. Try to schedule a Pod into it — should FAIL admission, because
#    no AuditChain CRD exists in agent-zeus yet.
kubectl -n agent-zeus run zeus-test --image=busybox --restart=Never --command -- sleep 60
# Error from server: admission webhook "validate.kyverno.svc" denied
# the request: Namespace 'agent-zeus' is labeled
# finserv.io/agent-namespace=true but has no AuditChain CRD instances.

# 3. Create the AuditChain CRD.
cat <<'EOF' | kubectl apply -f -
apiVersion: finserv.io/v1
kind: AuditChain
metadata:
  name: zeus-audit
  namespace: agent-zeus
spec:
  ledger_store_class: jsonl
  ledger_store_config:
    path: /var/finserv/audit/zeus.jsonl
  timestamp_source_class: finserv_agent_audit.governance.timestamp_source.LocalClock
  retention_days: 2555  # 7 years, SEC 17a-4 anchor
EOF

# 4. Try the Pod again — STILL fails, because the namespace has no
#    ChainSink CRD (verify-chain-sink policy on AuditChain creation
#    will also have flagged this).
```

The pattern continues for the agent Pod itself: deploy a Pod labeled
`app.kubernetes.io/component=agent` without the
`finserv.io/sovereign-veto-ref` annotation and admission is denied.
Add the annotation pointing at a SovereignVeto CRD that exists in the
namespace and admission proceeds.

---

## Production hardening

The reference stub is the starting point, not the finish line. Before
running this in a production FSI cluster, work through the following.

### 1. Replace the stub controller

Pick one path:

- **kopf** — the Python-native operator framework. Drop the stub's
  poll loop, register handlers decorated with `@kopf.on.create` /
  `@kopf.on.update` for each CRD, and let kopf handle the watch
  stream, exponential backoff, and finalizers. The reconcile logic
  in `controller.py` (the per-resource `reconcile_*` functions)
  ports across nearly verbatim.
- **operator-sdk** — the CNCF Go reference. Higher upfront cost
  (Go toolchain, scaffolding generators, controller-runtime
  semantics) but better-trodden production path in conservative
  platform-engineering shops. The CRD schemas in `crds/` ship
  unchanged.
- **Kubernetes Agent Sandbox runtime** — for clusters that adopt
  the kubernetes-sigs/agent-sandbox workload API as their agent
  Pod spec, the operator becomes a controller over the Agent
  Sandbox CRDs plus the finserv.io CRDs in this directory. The
  SovereignVeto CRD's `on_veto_webhook` is the natural integration
  point for the Sandbox Pod's halt-signal listener.

### 2. Leader election

Any controller running with `replicas > 1` MUST leader-elect or two
replicas will race on every PATCH. kopf and operator-sdk both ship
this out of the box; the stub does not. The reference rbac.yaml
ships `replicas: 1` for this reason.

### 3. Metrics endpoint

The stub exposes a minimal Prometheus-format surface on port 8080:

```
finserv_operator_up                                 # 1 if alive
finserv_operator_ready                              # 1 after first reconcile
finserv_operator_reconcile_total                    # cycles attempted
finserv_operator_reconcile_failed_total             # cycles with failures
finserv_operator_last_reconcile_timestamp_seconds   # last cycle wall-clock
```

Scrape via the Prometheus Operator ServiceMonitor at
`deploy/k8s/operator/servicemonitor.yaml`, or via the
`prometheus.io/scrape: "true"` annotation on the Deployment template
for clusters not running the Prometheus Operator. The accompanying
Service (named port `metrics`, 8080) is shipped in `rbac.yaml`.

Production controllers SHOULD swap the stub's stdlib exposition for
the `prometheus_client` library and emit the full
`controller_runtime_reconcile_total`,
`controller_runtime_reconcile_errors_total`, and
`controller_runtime_reconcile_time_seconds` histograms the
operator-sdk reference image emits.

### 3a. Health probes

The stub serves `/healthz`, `/readyz`, and `/metrics` on
`FINSERV_OPERATOR_HEALTH_PORT` (default 8080). The Deployment in
`rbac.yaml` wires all three probe types:

- **startupProbe** — `/healthz`, 60s window before liveness takes over.
- **livenessProbe** — `/healthz`, restarts the container if the HTTP
  server thread dies.
- **readinessProbe** — `/readyz`, returns 503 until the first reconcile
  cycle completes (gates Service traffic until the operator is genuinely
  usable, not just process-alive).

### 3b. NetworkPolicy

`deploy/k8s/operator/networkpolicy.yaml` ships a default-deny egress
posture with explicit allow-lists for the kube-apiserver, DNS, and a
TCP/443 sink-and-webhook clause. Production deployers SHOULD narrow
the sink/webhook clause to explicit namespaceSelectors or ipBlocks
matching their actual ChainSink and SovereignVeto-webhook endpoints.
Requires a NetworkPolicy-capable CNI (Calico, Cilium, antrea-policy).

### 3c. Persistent ledger storage (PVC)

The `inmemory` ledger store is for dev / kind / minikube only — it
loses state on every Pod restart. Production AuditChain CRDs with
`spec.ledger_store_class` set to `jsonl`, `sqlite`, or `worm` MUST
have a PersistentVolumeClaim mounted into the operator Pod at the
path referenced by `spec.ledger_store_config.path`.

`deploy/k8s/operator/pvc-sample.yaml` is a starter template — 100Gi
on a `gp3-encrypted` StorageClass (EKS convention). Adapt the
StorageClass + capacity to your cluster's encrypted-at-rest storage
substrate, then add the matching `volumes` + `volumeMounts` block to
the operator Deployment in `rbac.yaml`. The Deployment ships the
volume mount commented out because the mount path is deployer-specific
to whatever path each AuditChain CRD declares.

### 3d. Image distroless conversion path

The reference `Dockerfile` uses a multi-stage build with
`python:3.13-slim-bookworm` pinned by digest in both stages and runs
as UID 65532 (the distroless `nonroot` convention). It is NOT yet
distroless because the final stage needs `pip install` to populate
site-packages with the framework wheel, and `gcr.io/distroless/python3-debian12`
ships no pip.

Production deployers SHOULD complete the distroless swap by:

1. In the builder stage, install the wheel into a target directory
   with `pip install --no-deps --target=/wheelout /dist/*.whl`.
2. Change the final stage to
   `FROM gcr.io/distroless/python3-debian12:nonroot@sha256:<digest>`.
3. Copy `/wheelout` from the builder into `/app/site-packages` and
   set `PYTHONPATH=/app/site-packages`.
4. Drop the `pip install` line from the runtime stage; entrypoint
   stays `["python", "-u", "/app/controller.py"]`.

The UID (65532) matches the distroless `nonroot` user, so the
Deployment `securityContext` block needs no changes when the base
image swaps.

### 4. Chain-verify cron

The stub runs `chain.verify()` every reconcile cycle. For large
chains, this is expensive — `verify()` walks the full chain. A
production setup SHOULD move the verify call into a separate
CronJob that runs the `finserv-audit verify` CLI against the chain's
backing ledger store on a daily or hourly cadence and PATCHes the
result onto `.status.intact` + `.status.last_verified_at`. The
operator's reconcile loop then just reads the most recent status
without re-walking the chain.

```yaml
# Example chain-verify CronJob.
apiVersion: batch/v1
kind: CronJob
metadata:
  name: zeus-audit-verify
  namespace: agent-zeus
spec:
  schedule: "0 * * * *"  # hourly
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: verify
              image: ghcr.io/linus10x/finserv-agent-audit:2.0.0
              command:
                - finserv-audit
                - verify
                - --ledger-store=jsonl
                - --path=/var/finserv/audit/zeus.jsonl
              volumeMounts:
                - name: audit-vol
                  mountPath: /var/finserv/audit
          volumes:
            - name: audit-vol
              persistentVolumeClaim:
                claimName: zeus-audit-pvc
```

### 5. Hybrid Kyverno + OPA Gatekeeper

Larger clusters increasingly run both engines side-by-side: Kyverno
for the high-volume admit / mutate paths (where its YAML syntax keeps
the policy library readable) and Gatekeeper for the cross-cluster
referential policies (where Rego's expressiveness pays off). The
samples in this directory are designed to be installed independently;
pick the engine per policy if your operating model warrants it.

### 6. Pair with the framework CLI

The `finserv-audit` CLI shipped in v1.x is the deployer-side
companion to the operator. Three flows are explicitly designed for
the cluster context:

- `finserv-audit verify` — the chain-verify command the CronJob above
  invokes.
- `finserv-audit aibom` — the AI Bill of Materials generator (v2.0.B)
  the operator can invoke on demand via a Job to emit the cluster's
  AIBOM into a ChainSink.
- `finserv-audit replay` — the audit-event replay command second-line
  auditors use to reconstruct a cluster timeline from a chain JSONL.

### 7. Stateful agent workloads — pair with Kubernetes Agent Sandbox

For long-lived agent Pods that own a PersistentVolume for memory +
tool state, install the Kubernetes Agent Sandbox runtime
(`github.com/kubernetes-sigs/agent-sandbox`) alongside this deployment
substrate. The Agent Sandbox CRD describes the Pod's lifecycle; the
finserv.io CRDs describe the governance substrate the Pod writes to
and reads from. The pair is the v2.0 reference architecture for FSI-
grade cluster-native agent deployments.

---

## What this does NOT do

- **No multi-cluster federation.** The CRDs are per-cluster; a fleet
  spanning multiple clusters needs a higher-level coordination layer
  (Karmada, ClusterAPI, or the deployer's own GitOps controller).
- **No identity-binding to SPIFFE / SPIRE.** The SovereignVeto CRD's
  webhook calls authenticate via a bearer token from a referenced
  Secret. Production deployers running a SPIFFE-based mesh SHOULD
  swap that for SPIFFE-issued mTLS.
- **No automatic chain-encryption at rest.** The ledger stores carry
  audit data; production clusters SHOULD encrypt the backing PV at
  rest (EBS encryption, csi-driver-side encryption, or the platform's
  envelope-encryption story).

These are deliberate scope cuts for v2.0. Track issues on the repo
if your environment needs them and they may land in a future tranche.

---

## See also

- [ADR-0033](../../docs/adr/0033-kubernetes-operator.md) — the decision record
- [ADR-0002](../../docs/adr/0002-sovereign-veto.md) — SovereignVeto
- [ADR-0003](../../docs/adr/0003-hash-chain-audit.md) — AuditChain
- [ADR-0017](../../docs/adr/0017-audit-chain-retention-privilege-discovery.md) — retention
- [Kubernetes Agent Sandbox](https://github.com/kubernetes-sigs/agent-sandbox)
- [Kyverno docs](https://kyverno.io/docs/)
- [OPA Gatekeeper docs](https://open-policy-agent.github.io/gatekeeper/)
