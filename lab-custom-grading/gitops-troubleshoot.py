#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato gitops-troubleshoot (DO432/do0015l),
sprovvisto di `lab grade` ufficiale (la classe GitOpsTroubeshoot, nome con
un typo nel codice ufficiale, implementa solo start()/finish()).

Specifica ricavata dal confronto materials/labs/gitops-troubleshoot/lab-start
(stato rotto iniziale) con materials/solutions/gitops-troubleshoot (soluzione),
incrociato col testo della guida studente (PDF DO432-RHACM2.13, Cap. 5.8
"Troubleshoot Common Issues for Application Lifecycle Management in RHACM").
L'esercizio usa il modello GitOps Pull: lo studente deve correggere due
manifest applicati da start() nel namespace openshift-gitops dell'hub:

- placement.yaml (Placement "task-list-placement"): deve escludere
  local-cluster (con un matchExpressions "name NotIn [local-cluster]", nello
  starter e' commentato) e selezionare un solo cluster (numberOfClusters: 1,
  nello starter e' 2) -- col modello Pull non si puo' distribuire sull'hub.
- applicationset.yaml (ApplicationSet "task-list"): il path Kustomize della
  source deve essere "kustomize/overlays/dev" (nello starter e' "DEV").
- Un terzo problema (schedule del CronJob non valido) va corretto in Git,
  fuori cluster: non e' verificabile da qui, ma si riflette nello stato
  finale Healthy/Synced dell'Application generata, che quindi lo grada
  indirettamente.

Nel modello Pull le risorse applicative vengono effettivamente create sul
cluster gestito, ma l'ApplicationSet genera sull'hub (namespace
openshift-gitops) un oggetto Application "task-list-<nome-cluster>" il cui
.status viene aggiornato dal controller di stato ACM: e' quindi verificabile
interamente dall'hub, senza autenticarsi sul cluster gestito.

Uso: gitops-troubleshoot.py   (nessun argomento: le risorse sono tutte
nel namespace openshift-gitops, non in un progetto dedicato all'esercizio)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json

LAB_NAME = "gitops-troubleshoot"
GITOPS_NS = "openshift-gitops"
APPSET_NAME = "task-list"
PLACEMENT_NAME = "task-list-placement"
EXPECTED_PATH = "kustomize/overlays/dev"


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (namespace: {GITOPS_NS})")

    appset = oc_get_json("applicationset.argoproj.io", APPSET_NAME, "-n", GITOPS_NS)
    placement = oc_get_json("placement", PLACEMENT_NAME, "-n", GITOPS_NS)

    with GradingStep(
        f"L'ApplicationSet '{APPSET_NAME}' punta al percorso Kustomize corretto"
    ) as step:
        if appset is None:
            step.fail(f"ApplicationSet '{APPSET_NAME}' non trovato nel namespace {GITOPS_NS}")
        else:
            sources = appset.get("spec", {}).get("template", {}).get("spec", {}).get(
                "sources", []
            )
            if not any(s.get("path") == EXPECTED_PATH for s in sources):
                found = [s.get("path") for s in sources]
                step.add_error(
                    f"Path atteso '{EXPECTED_PATH}', trovato {found} "
                    "(il valore iniziale rotto era 'DEV')"
                )

    decision_cluster = None
    with GradingStep(
        f"Il Placement '{PLACEMENT_NAME}' esclude local-cluster e seleziona un solo cluster"
    ) as step:
        if placement is None:
            step.fail(f"Placement '{PLACEMENT_NAME}' non trovato nel namespace {GITOPS_NS}")
        else:
            if placement.get("spec", {}).get("numberOfClusters") != 1:
                step.add_error(
                    "numberOfClusters deve essere 1 (con il modello Pull non si "
                    "distribuisce sull'hub, quindi un solo cluster gestito rimane "
                    "selezionabile)"
                )
            predicates = placement.get("spec", {}).get("predicates", [])
            selectors = [
                expr
                for p in predicates
                for expr in p.get("requiredClusterSelector", {})
                .get("labelSelector", {})
                .get("matchExpressions", [])
            ]
            excludes_local = any(
                e.get("key") == "name"
                and e.get("operator") == "NotIn"
                and "local-cluster" in (e.get("values") or [])
                for e in selectors
            )
            if not excludes_local:
                step.add_error(
                    "Manca (o e' ancora commentata) la regola che esclude "
                    "local-cluster (key=name, operator=NotIn, values=[local-cluster])"
                )

            decisions = placement.get("status", {}).get("decisions", []) or []
            if len(decisions) != 1:
                step.add_error(
                    f"Il Placement ha selezionato {len(decisions)} cluster, attesi 1"
                )
            elif decisions[0].get("clusterName") == "local-cluster":
                step.add_error(
                    "Il Placement ha selezionato local-cluster, che il modello "
                    "Pull non supporta"
                )
            else:
                decision_cluster = decisions[0].get("clusterName")

    with GradingStep(
        "L'applicazione task-list e' distribuita correttamente (Healthy/Synced)"
    ) as step:
        if not decision_cluster:
            step.fail("Nessun cluster gestito selezionato dal Placement, impossibile verificare l'Application")
        else:
            app_name = f"{APPSET_NAME}-{decision_cluster}"
            app = oc_get_json("application.argoproj.io", app_name, "-n", GITOPS_NS)
            if app is None:
                step.fail(f"Application '{app_name}' non trovata nel namespace {GITOPS_NS}")
            else:
                health = app.get("status", {}).get("health", {}).get("status")
                sync = app.get("status", {}).get("sync", {}).get("status")
                if health != "Healthy":
                    step.add_error(
                        f"Stato dell'applicazione: {health or 'sconosciuto'} (atteso Healthy "
                        "-- verifica anche il parametro schedule del CronJob nel repo Git)"
                    )
                if sync != "Synced":
                    step.add_error(f"Stato di sincronizzazione: {sync or 'sconosciuto'} (atteso Synced)")


if __name__ == "__main__":
    main()
