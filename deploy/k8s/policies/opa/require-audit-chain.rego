# OPA Gatekeeper Rego policy: REQUIRE an AuditChain in agent namespaces.
#
# Equivalent to deploy/k8s/policies/kyverno/require-audit-chain.yaml.
# Use this variant when your cluster runs OPA Gatekeeper as the admission
# controller. Ship the matching ConstraintTemplate + Constraint pair.
#
# Cross-namespace lookups (AuditChain CRD count for the Pod's namespace)
# require Gatekeeper's `referential` sync configured for the
# finserv.io/v1 AuditChain resource. Without the sync, data.inventory
# is empty and the policy short-circuits to allow — production deployers
# MUST configure the sync (see deploy/k8s/README.md section "OPA
# Gatekeeper sync configuration").
#
# Pairs with ADR-0003 (hash-chained audit ledger) + ADR-0014 (persistence
# witness timestamp).
---
# ConstraintTemplate. Defines the schema + Rego.
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: finservrequireauditchain
spec:
  crd:
    spec:
      names:
        kind: FinservRequireAuditChain
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package finserv.requireauditchain

        # Deny Pod admission when the namespace is labeled
        # finserv.io/agent-namespace=true and has zero AuditChain CRD
        # instances.
        violation[{"msg": msg}] {
          input.review.kind.kind == "Pod"
          ns := input.review.object.metadata.namespace
          namespace_obj := data.inventory.cluster["v1"]["Namespace"][ns]
          namespace_obj.metadata.labels["finserv.io/agent-namespace"] == "true"
          count(audit_chains_in_namespace(ns)) == 0
          msg := sprintf(
            "Namespace %q is labeled finserv.io/agent-namespace=true but has no AuditChain CRD instances. Create at least one AuditChain before deploying agent Pods. See ADR-0003.",
            [ns],
          )
        }

        # Collect AuditChain CRDs in the target namespace via Gatekeeper's
        # synced inventory. The sync must be configured for
        # finserv.io/v1/AuditChain — see deploy/k8s/README.md.
        audit_chains_in_namespace(ns) = chains {
          chains := [chain |
            chain := data.inventory.namespace[ns]["finserv.io/v1"]["AuditChain"][_]
          ]
        }
---
# Constraint. Targets Pod admission with the namespace-label selector
# Kyverno's `namespaceSelector` expresses inline.
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: FinservRequireAuditChain
metadata:
  name: finserv-require-audit-chain
spec:
  enforcementAction: deny
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
    namespaceSelector:
      matchLabels:
        finserv.io/agent-namespace: "true"
