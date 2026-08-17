#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato gitops-deploy (DO432/do0015l),
sprovvisto di `lab grade` ufficiale (la classe GitOpsDeploy implementa solo
start()/finish()).

Specifica ricavata dal testo della guida studente (PDF DO432-RHACM2.13,
Cap. 5.6 "Deploy and Manage Multicluster Application Resources with RHACM"):
lo studente crea, dalla console RHACM, un ApplicationSet "todo-app" (modello
Push) che seleziona i due cluster con label tier=front (impostata da
start()) e distribuisce l'overlay Kustomize kustomize/overlays/prod del
repo https://git.ocp4.example.com/do0015l/gitops-deploy.git (3 replica,
Route con terminazione TLS edge) nel namespace "todo-app". Alla fine
dell'esercizio lo studente riabilita la sincronizzazione automatica di
Argo CD, cosi' che una modifica manuale al Deployment (fatta apposta per
osservare il comportamento) venga ripristinata a 3 replica.

Nel modello Push l'istanza Argo CD dell'hub riconcilia direttamente le
risorse anche sul cluster locale (local-cluster e' uno dei due cluster
selezionati dal Placement), quindi il namespace applicativo e' verificabile
con il contesto oc corrente senza autenticarsi sul cluster gestito.

Uso: gitops-deploy.py [nome-progetto-app]   (default: todo-app)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json

LAB_NAME = "gitops-deploy"
GITOPS_NS = "openshift-gitops"
EXPECTED_REPO = "https://git.ocp4.example.com/do0015l/gitops-deploy.git"
EXPECTED_PATH = "kustomize/overlays/prod"


def find_applicationset():
    """Il nome dell'ApplicationSet e' scelto dallo studente nel wizard della
    console (la guida chiede "todo-app"): cerca per nome esatto, altrimenti
    per corrispondenza col repo Git atteso, come fa la stessa gitops-deploy.py
    ufficiale in fase di cleanup (ricerca per sottostringa "todo")."""
    appsets = oc_get_json("applicationset.argoproj.io", "-n", GITOPS_NS)
    if not appsets:
        return None
    items = appsets.get("items", [])
    for item in items:
        if item.get("metadata", {}).get("name") == "todo-app":
            return item
    for item in items:
        sources = item.get("spec", {}).get("template", {}).get("spec", {}).get(
            "sources", []
        )
        if any(EXPECTED_REPO in (s.get("repoURL") or "") for s in sources):
            return item
    return None


def main():
    namespace = sys.argv[1] if len(sys.argv) > 1 else "todo-app"
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (namespace app: {namespace})")

    appset = find_applicationset()

    with GradingStep(
        "L'ApplicationSet 'todo-app' esiste e punta al repository/percorso corretti"
    ) as step:
        if appset is None:
            step.fail(f"Nessun ApplicationSet trovato nel namespace {GITOPS_NS}")
        else:
            sources = appset.get("spec", {}).get("template", {}).get("spec", {}).get(
                "sources", []
            )
            if not any(EXPECTED_REPO in (s.get("repoURL") or "") for s in sources):
                step.add_error(f"repoURL atteso {EXPECTED_REPO} non trovato")
            if not any(s.get("path") == EXPECTED_PATH for s in sources):
                step.add_error(
                    f"path atteso {EXPECTED_PATH} non trovato tra le source"
                )

    with GradingStep(
        "Il Placement generato seleziona i cluster con label tier=front"
    ) as step:
        if appset is None:
            step.fail()
        else:
            generators = appset.get("spec", {}).get("generators", [])
            cdr = None
            for g in generators:
                if "clusterDecisionResource" in g:
                    cdr = g["clusterDecisionResource"]
                    break
            if cdr is None:
                step.fail(
                    "Nessun generator clusterDecisionResource (basato su Placement) trovato"
                )
            else:
                placement_label = (cdr.get("labelSelector", {}) or {}).get(
                    "matchLabels", {}
                ).get("cluster.open-cluster-management.io/placement")
                placement = (
                    oc_get_json("placement", placement_label, "-n", GITOPS_NS)
                    if placement_label
                    else None
                )
                if placement is None:
                    step.add_error(
                        f"Placement '{placement_label}' referenziato dal generator non trovato"
                    )
                else:
                    predicates = placement.get("spec", {}).get("predicates", [])
                    selectors = [
                        expr
                        for p in predicates
                        for expr in p.get("requiredClusterSelector", {})
                        .get("labelSelector", {})
                        .get("matchExpressions", [])
                    ]
                    if not any(
                        e.get("key") == "tier" and "front" in (e.get("values") or [])
                        for e in selectors
                    ):
                        step.add_error(
                            "Il Placement non seleziona i cluster con label tier=front"
                        )

    with GradingStep(
        f"L'applicazione todo-app e' distribuita in produzione nel namespace {namespace} "
        "(3 replica, route TLS edge)"
    ) as step:
        deployment = oc_get_json("deployment", "todo-app", "-n", namespace)
        if deployment is None:
            step.fail(f"Deployment 'todo-app' non trovato nel namespace {namespace}")
        else:
            replicas = deployment.get("spec", {}).get("replicas")
            if replicas != 3:
                step.add_error(
                    f"Il deployment ha {replicas} replica, attese 3 (l'ambiente di "
                    "produzione, e Argo CD deve aver ripristinato la modifica manuale)"
                )
            available = deployment.get("status", {}).get("availableReplicas", 0)
            if available != 3:
                step.add_error(f"Solo {available} replica disponibili su 3")

        route = oc_get_json("route", "todo-app", "-n", namespace)
        if route is None:
            step.add_error("Route 'todo-app' non trovata")
        elif route.get("spec", {}).get("tls", {}).get("termination") != "edge":
            step.add_error("La route non usa la terminazione TLS 'edge'")

    with GradingStep(
        "La sincronizzazione automatica di Argo CD e' abilitata (passo finale della guida)"
    ) as step:
        if appset is None:
            step.fail()
        else:
            sync_policy = (
                appset.get("spec", {})
                .get("template", {})
                .get("spec", {})
                .get("syncPolicy", {})
            )
            if not sync_policy.get("automated"):
                step.add_error(
                    "syncPolicy.automated non impostata: la guida chiede di "
                    "riattivare 'Automatically sync when cluster state changes'"
                )


if __name__ == "__main__":
    main()
