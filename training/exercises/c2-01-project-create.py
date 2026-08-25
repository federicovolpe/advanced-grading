"""
Cap. 2 — Kubernetes and OpenShift CLI and APIs
Crea un progetto e una ConfigMap al suo interno dalla riga di comando.

Nota: la versione iniziale di questo esercizio chiedeva di etichettare il
progetto con "oc label namespace ...", ma sull'account "developer" (quello
con cui viene tipicamente eseguita questa suite di training) quel comando
e' Forbidden — puo' creare il progetto (via ProjectRequest) ma non patchare
il core Namespace risultante. Verificato dal vivo su questo cluster prima
di scrivere lo script: per questo l'esercizio gradua invece una risorsa
namespaced qualunque (ConfigMap), sempre permessa al creatore del progetto.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, oc_get_json, oc, project_exists, run_cli

CHAPTER = "Cap. 2 — Kubernetes and OpenShift CLI and APIs"
TITLE = "Crea un progetto dalla riga di comando"
PROJECT = "training-project-demo"

TASK = f"""\
Crea un nuovo progetto OpenShift chiamato esattamente "{PROJECT}", poi
crea al suo interno una ConfigMap chiamata "info" con la chiave
owner=training.

Comandi suggeriti (2):
  oc new-project {PROJECT}
  oc create configmap info --from-literal=owner=training -n {PROJECT}
"""


def setup():
    # L'obiettivo dell'esercizio E' creare il progetto: se esiste gia' da
    # un tentativo precedente lo ricreiamo vuoto, per uno stato di partenza
    # deterministico (coerente con "Ricomincia esercizio").
    if project_exists(PROJECT):
        oc("delete", "project", PROJECT, "--wait=true", "--timeout=60s")
        import time
        deadline = time.time() + 60
        while project_exists(PROJECT) and time.time() < deadline:
            time.sleep(2)


def grade():
    with GradingStep(f"Il progetto {PROJECT} esiste") as step:
        if not project_exists(PROJECT):
            step.fail(f"Progetto '{PROJECT}' non trovato")

    with GradingStep("La ConfigMap info esiste con la chiave giusta") as step:
        cm = oc_get_json("configmap", "info", "-n", PROJECT)
        if not cm:
            step.fail("ConfigMap 'info' non trovata")
        else:
            data = cm.get("data", {}) or {}
            if data.get("owner") != "training":
                step.add_error(f"data.owner = {data.get('owner')!r}, attesa 'training'")


if __name__ == "__main__":
    run_cli(setup, grade)
