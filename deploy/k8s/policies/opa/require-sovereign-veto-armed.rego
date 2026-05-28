# OPA Gatekeeper Rego policy: REQUIRE a SovereignVeto reference on every agent Pod.
#
# Equivalent to deploy/k8s/policies/kyverno/require-sovereign-veto-armed.yaml.
# Use this variant when your cluster runs OPA Gatekeeper as the admission
# controller.
#
# Cross-namespace lookups (does the referenced SovereignVeto exist?)
# require Gatekeeper's `referential` sync configured for the
# finserv.io/v1 SovereignVeto resource. Without the sync, data.inventory
# is empty and the existence check short-circuits to allow — production
# deployers MUST configure the sync.
#
# Pairs with ADR-0002 (sovereign veto).
---
# ConstraintTemplate.
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: finservrequiresovereignvetoarmed
spec:
  crd:
    spec:
      names:
        kind: FinservRequireSovereignVetoArmed
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package finserv.requiresovereignvetoarmed

        # Deny agent Pod admission when the SovereignVeto annotation is
        # missing.
        violation[{"msg": msg}] {
          input.review.kind.kind == "Pod"
          pod := input.review.object
          pod.metadata.labels["app.kubernetes.io/component"] == "agent"
          not pod.metadata.annotations["finserv.io/sovereign-veto-ref"]
          msg := sprintf(
            "Pod %q is labeled app.kubernetes.io/component=agent but is missing required annotation finserv.io/sovereign-veto-ref. See ADR-0002.",
            [pod.metadata.name],
          )
        }

        # Deny agent Pod admission when the SovereignVeto annotation
        # references a CRD that does not exist in the Pod's namespace.
        violation[{"msg": msg}] {
          input.review.kind.kind == "Pod"
          pod := input.review.object
          pod.metadata.labels["app.kubernetes.io/component"] == "agent"
          veto_name := pod.metadata.annotations["finserv.io/sovereign-veto-ref"]
          veto_name != ""
          ns := pod.metadata.namespace
          not data.inventory.namespace[ns]["finserv.io/v1"]["SovereignVeto"][veto_name]
          msg := sprintf(
            "Pod %q references SovereignVeto %q which does not exist in namespace %q.",
            [pod.metadata.name, veto_name, ns],
          )
        }
---
# Constraint.
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: FinservRequireSovereignVetoArmed
metadata:
  name: finserv-require-sovereign-veto-armed
spec:
  enforcementAction: deny
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
    labelSelector:
      matchLabels:
        app.kubernetes.io/component: agent
