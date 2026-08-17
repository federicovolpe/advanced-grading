#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato install-rhacm (DO432, Cap. 1.6),
sprovvisto di `lab grade` ufficiale (la classe InstallRHACM nel pacchetto
do0011l implementa solo start()/finish(), non grade()).

Specifica ricavata dal testo della guida studente (DO432-RHACM2.13-en-2,
Cap. 1.6, pag. 40-44): non esiste materials/labs/install-rhacm né
materials/solutions/install-rhacm in cache (l'esercizio e' puro
OperatorHub/console, nessun file di partenza), quindi non c'era una
fonte 1/2 da usare.

La guida chiede di installare l'operator "Advanced Cluster Management for
Kubernetes" (lasciando i valori di default della subscription) e poi di
creare un oggetto MultiClusterHub lasciando anch'esso i valori di default,
verificando poi lo stato in `oc get all -n open-cluster-management`.
L'installazione di default dell'operator OLM crea la subscription e il CSV
nel namespace `open-cluster-management` e il nome standard dell'oggetto
creato dalla console con "Create MultiClusterHub" (default) e'
`multiclusterhub`: questi due nomi sono costanti del prodotto, non scelte
dello studente, quindi e' corretto gradarli come valori fissi.

A differenza degli altri esercizi DO432, l'installazione di RHACM qui non
viene rimossa da finish() (resta l'infrastruttura condivisa usata da tutti
i capitoli successivi): il check e' quindi valido anche molto dopo
`lab finish install-rhacm`, non solo "sul momento".

Uso: install-rhacm.py [ignorato]   (l'esercizio non usa un project OpenShift
dedicato: la verifica riguarda sempre il namespace open-cluster-management
sull'hub cluster, indipendentemente dagli argomenti passati)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json

NAMESPACE = "open-cluster-management"
HUB_NAME = "multiclusterhub"


def find_acm_csv():
    """Il nome del CSV include la versione (es. advanced-cluster-management.v2.13.x),
    quindi va cercato per prefisso invece che per nome esatto."""
    csvs = oc_get_json("csv", "-n", NAMESPACE)
    if not csvs:
        return None
    for item in csvs.get("items", []):
        if item.get("metadata", {}).get("name", "").startswith("advanced-cluster-management"):
            return item
    return None


def main():
    print(f"🔧 Grading personalizzato per 'install-rhacm' (namespace: {NAMESPACE})")

    with GradingStep(f"Il namespace {NAMESPACE} esiste") as step:
        ns = oc_get_json("namespace", NAMESPACE)
        if ns is None:
            step.fail(f"Namespace '{NAMESPACE}' non trovato: l'operator non risulta installato")

    csv = find_acm_csv()

    with GradingStep("L'operator Advanced Cluster Management e' installato") as step:
        if csv is None:
            step.fail(f"Nessun ClusterServiceVersion 'advanced-cluster-management*' trovato in {NAMESPACE}")
        elif csv.get("status", {}).get("phase") != "Succeeded":
            step.add_error(
                f"CSV '{csv['metadata']['name']}' in fase "
                f"'{csv.get('status', {}).get('phase')}', attesa 'Succeeded'"
            )

    hub = oc_get_json("multiclusterhub", HUB_NAME, "-n", NAMESPACE)

    with GradingStep(f"L'oggetto MultiClusterHub '{HUB_NAME}' esiste") as step:
        if hub is None:
            step.fail(f"MultiClusterHub '{HUB_NAME}' non trovato in {NAMESPACE}")

    with GradingStep("Il MultiClusterHub e' nella fase 'Running'") as step:
        if hub is None:
            step.fail()
        else:
            phase = hub.get("status", {}).get("phase")
            if phase != "Running":
                step.add_error(f"Fase attuale: '{phase}', attesa 'Running'")


if __name__ == "__main__":
    main()
