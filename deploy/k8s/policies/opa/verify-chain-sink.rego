# OPA Gatekeeper Rego policy: REQUIRE a ChainSink in any namespace
# carrying an AuditChain.
#
# Equivalent to deploy/k8s/policies/kyverno/verify-chain-sink.yaml.
# Use this variant when your cluster runs OPA Gatekeeper as the admission
# controller. The constraint fires on AuditChain CREATE / UPDATE; the
# Pod-admission path is intentionally NOT covered here (Pods that
# accidentally land in a chain-less namespace are caught by the
# require-audit-chain policy above).
#
# Cross-namespace lookups require Gatekeeper's `referential` sync
# configured for the finserv.io/v1 ChainSink resource.
#
# Pairs with ADR-0017 (audit-chain retention).
---
# ConstraintTemplate.
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: finservverifychainsink
spec:
  crd:
    spec:
      names:
        kind: FinservVerifyChainSink
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package finserv.verifychainsink

        # Defensive sync-check: if Gatekeeper Config has not synced the
        # namespaced ChainSink inventory, fail closed. Without the sync
        # chain_sinks_in_namespace() always returns [] and the deny
        # rule below would fire on every AuditChain — but only because
        # the policy is blind, not because the sink is actually absent.
        # Make the misconfiguration explicit in the deny message.
        violation[{"msg": msg}] {
          input.review.kind.kind == "AuditChain"
          ns := input.review.object.metadata.namespace
          not data.inventory.namespace[ns]
          msg := sprintf("Gatekeeper Config sync is missing data.inventory.namespace[%q]; policy cannot enumerate ChainSink CRDs. Configure the finserv.io/v1/ChainSink sync per deploy/k8s/README.md. Failing closed.", [ns])
        }

        # Deny AuditChain creation when the target namespace has no
        # ChainSink CRD instances.
        violation[{"msg": msg}] {
          input.review.kind.kind == "AuditChain"
          ns := input.review.object.metadata.namespace
          data.inventory.namespace[ns]
          count(chain_sinks_in_namespace(ns)) == 0
          msg := sprintf(
            "Namespace %q is being assigned an AuditChain %q but has no ChainSink CRD instances. Create at least one ChainSink so chain events are emitted to a long-term retention substrate. See ADR-0017.",
            [ns, input.review.object.metadata.name],
          )
        }

        chain_sinks_in_namespace(ns) = sinks {
          sinks := [sink |
            sink := data.inventory.namespace[ns]["finserv.io/v1"]["ChainSink"][_]
          ]
        }
---
# Constraint.
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: FinservVerifyChainSink
metadata:
  name: finserv-verify-chain-sink
spec:
  enforcementAction: deny
  match:
    kinds:
      - apiGroups: ["finserv.io"]
        kinds: ["AuditChain"]
