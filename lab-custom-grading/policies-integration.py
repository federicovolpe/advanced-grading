#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato policies-integration (DO432/do0013l,
Cap. 3.10 "Integrate Other Policy Engines with RHACM"), sprovvisto di
`lab grade` ufficiale.

Fonte della specifica: testo della guida (Cap. 3.10), incrociato con
policies-integration.py (start()/finish(): confermano i nomi di Policy/
Placement/PlacementBinding rimossi da finish(), e che label_managed_clusters()
etichetta local-cluster con environment=stage e managed-cluster con
environment=production) e col diff labs/solutions di policy-latest.yaml
(l'unica differenza e' il placeholder CHANGE_ME nel Placement, da sostituire
con `key: environment, operator: In, values: [stage, production]`).

La guida chiede di creare, nel progetto policy-gatekeeper (hub):
- Policy "policy-gatekeeper-operator" (enforce) che installa l'operatore
  Gatekeeper su tutti i cluster del cluster set default, poi editata per
  escludere il namespace app-stage da tutti i constraint (sezione
  spec.config.matches[].excludedNamespaces del Gatekeeper CR annidato).
- Policy "policy-gatekeeper-containerimage-latest" (da policy-latest.yaml,
  enforce) che vieta l'uso del tag ":latest" nei workload, con Placement
  verso i cluster con label environment in [stage, production].

Poi lo studente dimostra l'enforcement creando stage-hello (namespace
app-stage, escluso: il deployment con tag latest viene creato) e hello-app
(namespace app-test, NON escluso: il Deployment viene bloccato da
Gatekeeper, restano solo Service/Route) sul hub, e prod-hello sul managed
cluster (bloccato con tag latest, poi creato con successo dopo il fix a
v1.0). Lo stato su app-prod (managed cluster) non e' verificabile senza un
kubeconfig separato: usiamo lo stato di compliance aggregato che RHACM
riporta sulla Policy stessa (propagato dal managed cluster al hub) come
prova indiretta, piu' un controllo best-effort locale.

Uso: policies-integration.py [nome-progetto]  (default: policy-gatekeeper)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "policies-integration"
OPERATOR_POLICY = "policy-gatekeeper-operator"
LATEST_POLICY = "policy-gatekeeper-containerimage-latest"
LATEST_PLACEMENT = "placement-policy-gatekeeper-containerimage-latest"
EXPECTED_ENV_VALUES = {"stage", "production"}


def is_policy_compliant(policy):
    status = policy.get("status", {}) or {}
    if "compliant" in status:
        return status.get("compliant") == "Compliant"
    per_cluster = status.get("status", []) or []
    if not per_cluster:
        return None
    return all(c.get("compliant") == "Compliant" for c in per_cluster)


def contains_excluded_namespace(obj, namespace="app-stage"):
    """Cerca ricorsivamente, in qualunque punto della struttura annidata
    della Policy, un elenco excludedNamespaces che includa il namespace
    dato (evita di dipendere dal path esatto policy-templates[]
    .objectDefinition.spec.config.matches[].excludedNamespaces)."""
    if isinstance(obj, dict):
        excluded = obj.get("excludedNamespaces")
        if isinstance(excluded, list) and namespace in excluded:
            return True
        return any(contains_excluded_namespace(v, namespace) for v in obj.values())
    if isinstance(obj, list):
        return any(contains_excluded_namespace(v, namespace) for v in obj)
    return False


def find_environment_selector(placement):
    """Estrae i valori di un matchExpressions su 'environment' nei
    predicates del Placement, se presente."""
    for pred in placement.get("spec", {}).get("predicates", []) or []:
        expressions = (
            pred.get("requiredClusterSelector", {})
            .get("labelSelector", {})
            .get("matchExpressions", [])
            or []
        )
        for expr in expressions:
            if expr.get("key") == "environment" and expr.get("operator") == "In":
                return set(expr.get("values", []))
    return None


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else "policy-gatekeeper"
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(
        f"Il namespace {project} e' associato al cluster set 'default'"
    ) as step:
        bindings = oc_get_json("managedclustersetbinding", "-n", project)
        if not bindings or not any(
            b.get("spec", {}).get("clusterSet") == "default"
            for b in bindings.get("items", [])
        ):
            step.add_error(
                f"Nessuna ManagedClusterSetBinding verso 'default' nel namespace '{project}'"
            )

    op_policy = oc_get_json("policy", OPERATOR_POLICY, "-n", project)

    with GradingStep(
        f"La Policy '{OPERATOR_POLICY}' e' impostata su enforce ed e' Compliant"
    ) as step:
        if op_policy is None:
            step.fail(f"Policy '{OPERATOR_POLICY}' non trovata nel namespace '{project}'")
        else:
            if op_policy.get("spec", {}).get("remediationAction") != "enforce":
                step.add_error("remediationAction non e' 'enforce'")
            compliant = is_policy_compliant(op_policy)
            if compliant is False:
                step.add_error(
                    "La policy non e' Compliant: l'operatore Gatekeeper non risulta "
                    "installato correttamente su tutti i cluster"
                )
            elif compliant is None:
                step.add_error("Nessuno stato di compliance ancora riportato dalla policy")

    with GradingStep(
        f"Il namespace 'app-stage' e' escluso da tutti i constraint Gatekeeper "
        f"(passo 6: config.matches su '{OPERATOR_POLICY}')"
    ) as step:
        if op_policy is None:
            step.fail()
        elif not contains_excluded_namespace(op_policy, "app-stage"):
            step.add_error(
                "Nessun excludedNamespaces contenente 'app-stage' trovato nella "
                f"Policy '{OPERATOR_POLICY}' (il Gatekeeper CR annidato deve avere "
                "spec.config.matches[].excludedNamespaces: [app-stage])"
            )

    latest_policy = oc_get_json("policy", LATEST_POLICY, "-n", project)

    with GradingStep(
        f"La Policy '{LATEST_POLICY}' vieta il tag ':latest' (enforce)"
    ) as step:
        if latest_policy is None:
            step.fail(f"Policy '{LATEST_POLICY}' non trovata nel namespace '{project}'")
        elif latest_policy.get("spec", {}).get("remediationAction") != "enforce":
            step.add_error("remediationAction non e' 'enforce'")

    with GradingStep(
        f"Il Placement '{LATEST_PLACEMENT}' seleziona i cluster stage/production"
    ) as step:
        placement = oc_get_json("placement", LATEST_PLACEMENT, "-n", project)
        if placement is None:
            step.fail(f"Placement '{LATEST_PLACEMENT}' non trovato")
        else:
            values = find_environment_selector(placement)
            if values != EXPECTED_ENV_VALUES:
                step.add_error(
                    "Il matchExpressions su 'environment' non seleziona "
                    f"{sorted(EXPECTED_ENV_VALUES)} (trovato: {values}, "
                    "il placeholder CHANGE_ME del passo 7.2 non e' stato sostituito "
                    "correttamente)"
                )

    with GradingStep(
        "app-stage/stage-hello esiste (namespace escluso: il deployment con "
        "tag latest e' permesso)"
    ) as step:
        if not project_exists("app-stage"):
            step.fail("Namespace 'app-stage' non trovato")
        else:
            deployment = oc_get_json("deployment", "stage-hello", "-n", "app-stage")
            if deployment is None:
                step.add_error("Deployment 'stage-hello' non trovato in 'app-stage'")

    with GradingStep(
        "app-test/hello-app: il Deployment e' bloccato da Gatekeeper "
        "(devono esistere solo Service/Route, non il Deployment)"
    ) as step:
        if not project_exists("app-test"):
            step.fail("Namespace 'app-test' non trovato")
        else:
            service = oc_get_json("service", "hello-app", "-n", "app-test")
            if service is None:
                step.add_error("Service 'hello-app' non trovato in 'app-test'")
            deployment = oc_get_json("deployment", "hello-app", "-n", "app-test")
            if deployment is not None:
                step.add_error(
                    "Deployment 'hello-app' esiste in 'app-test': Gatekeeper avrebbe "
                    "dovuto bloccarne la creazione (immagine con tag ':latest' in un "
                    "namespace non escluso)"
                )

    with GradingStep(
        "La Policy risulta Compliant su tutti i cluster (prova indiretta che "
        "prod-hello sul managed cluster e' stato corretto al tag v1.0)"
    ) as step:
        if latest_policy is None:
            step.fail()
        else:
            compliant = is_policy_compliant(latest_policy)
            if compliant is False:
                step.add_error(
                    "La policy non e' Compliant su tutti i cluster: verificare che "
                    "prod-hello (managed cluster) non usi piu' il tag ':latest'"
                )
            elif compliant is None:
                step.add_error("Nessuno stato di compliance ancora riportato dalla policy")


if __name__ == "__main__":
    main()
