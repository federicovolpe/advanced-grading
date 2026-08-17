#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato scheduling-pdb (DO380, Cap. 3.7
"Deploy Highly Available Applications with Affinity Rules and Pod Disruption
Budgets"). La classe SchedulingPdb nel pacchetto do380 ha un commento
esplicito "# Grading tasks / none": nessun grading ufficiale.

IMPORTANTE - questo e' un check "sul momento", non a posteriori: l'ultimo
passo della guida (punto 7.1, pag. 262) fa cancellare esplicitamente allo
studente il progetto scheduling-pdb ("oc delete project scheduling-pdb"),
PRIMA ancora di lanciare `lab finish`. Quindi lo stato finale "corretto"
dell'esercizio coincide con lo stato iniziale (nessun progetto, nessuna
risorsa) - esattamente come pods-containers in DO180. Questo script da' un
risultato utile solo se eseguito PRIMA del passo 7 della guida (mentre il
deployment e la PodDisruptionBudget sono ancora presenti); un FAIL dopo che
lo studente ha completato l'esercizio per intero (incluso il cleanup) e'
normale e non indica un errore.

Specifica presa da materials/solutions/scheduling-pdb/ (diff verificato
riga per riga contro materials/labs/scheduling-pdb/, entrambi con
CHANGE_ME sostituiti nella soluzione) e confermata dal testo della guida
(punti 4.2 e 5.1-5.3, pag. 258-260):
- Deployment "nginx", 6 repliche, con podAntiAffinity/preferred... che usa
  topologyKey "rack" (la label custom applicata ai nodi da start()) e
  matchExpressions su "app In [nginx]".
- PodDisruptionBudget "nginx" con minAvailable "80%" e selector app=nginx.

Uso: scheduling-pdb.py [nome-progetto]   (default: scheduling-pdb)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "scheduling-pdb"
DEPLOYMENT_NAME = "nginx"
PDB_NAME = "nginx"
EXPECTED_REPLICAS = 6
EXPECTED_TOPOLOGY_KEY = "rack"
EXPECTED_AFFINITY_LABEL_VALUE = "nginx"
EXPECTED_MIN_AVAILABLE = "80%"
EXPECTED_SELECTOR_LABEL = {"app": "nginx"}


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(
                f"Progetto '{project}' non trovato: se hai gia' completato "
                "il punto 7 della guida (cleanup) o eseguito 'lab finish', "
                "e' normale - non resta nulla da verificare"
            )

    deployment = oc_get_json("deployment", DEPLOYMENT_NAME, "-n", project)

    with GradingStep(
        f"Il deployment '{DEPLOYMENT_NAME}' ha {EXPECTED_REPLICAS} repliche "
        "con pod anti-affinity sulla label 'rack' (punti 4.2-4.4)"
    ) as step:
        if deployment is None:
            step.fail(f"Deployment '{DEPLOYMENT_NAME}' non trovato in '{project}'")
        else:
            spec = deployment.get("spec", {})
            if spec.get("replicas") != EXPECTED_REPLICAS:
                step.add_error(
                    f"replicas={spec.get('replicas')}, atteso {EXPECTED_REPLICAS}"
                )

            pod_spec = spec.get("template", {}).get("spec", {})
            anti_affinity = (
                pod_spec.get("affinity", {})
                .get("podAntiAffinity", {})
                .get("preferredDuringSchedulingIgnoredDuringExecution", [])
            )
            if not anti_affinity:
                step.add_error(
                    "Manca 'affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution': "
                    "va aggiunta modificando deployment-affinity.yaml (punto 4.2 della guida)"
                )
            else:
                term = anti_affinity[0].get("podAffinityTerm", {})
                if term.get("topologyKey") != EXPECTED_TOPOLOGY_KEY:
                    step.add_error(
                        f"topologyKey='{term.get('topologyKey')}', atteso "
                        f"'{EXPECTED_TOPOLOGY_KEY}' (la label custom del failure domain)"
                    )
                match_expressions = term.get("labelSelector", {}).get(
                    "matchExpressions", []
                )
                values = match_expressions[0].get("values", []) if match_expressions else []
                if EXPECTED_AFFINITY_LABEL_VALUE not in values:
                    step.add_error(
                        f"labelSelector.matchExpressions non seleziona "
                        f"'app={EXPECTED_AFFINITY_LABEL_VALUE}' (trovato: {values})"
                    )

    pdb = oc_get_json("poddisruptionbudget", PDB_NAME, "-n", project)

    with GradingStep(
        f"La PodDisruptionBudget '{PDB_NAME}' ha minAvailable={EXPECTED_MIN_AVAILABLE} "
        "e seleziona i pod nginx (punti 5.1-5.3)"
    ) as step:
        if pdb is None:
            step.fail(f"PodDisruptionBudget '{PDB_NAME}' non trovata in '{project}'")
        else:
            pdb_spec = pdb.get("spec", {})
            min_available = pdb_spec.get("minAvailable")
            if str(min_available) != EXPECTED_MIN_AVAILABLE:
                step.add_error(
                    f"minAvailable='{min_available}', atteso '{EXPECTED_MIN_AVAILABLE}'"
                )
            selector = pdb_spec.get("selector", {}).get("matchLabels", {})
            if selector != EXPECTED_SELECTOR_LABEL:
                step.add_error(
                    f"selector.matchLabels={selector}, atteso {EXPECTED_SELECTOR_LABEL}"
                )


if __name__ == "__main__":
    main()
