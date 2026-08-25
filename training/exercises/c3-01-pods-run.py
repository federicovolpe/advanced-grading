"""
Cap. 3 — Run Applications as Containers and Pods
Crea un pod da riga di comando con un'immagine e un comando specifici.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, oc_get_json, reset_project, run_cli

CHAPTER = "Cap. 3 — Run Applications as Containers and Pods"
TITLE = "Crea un pod con oc run"
PROJECT = "training-pods-run"
IMAGE = "registry.access.redhat.com/ubi9/ubi:latest"

TASK = f"""\
Nel progetto "{PROJECT}", crea un pod chiamato "runner" che usa
l'immagine {IMAGE} ed esegue il comando "sleep infinity" (cosi' resta
in esecuzione invece di terminare subito).

Comando suggerito (1):
  oc run runner --image={IMAGE} -n {PROJECT} --command -- sleep infinity
"""


def setup():
    reset_project(PROJECT)


def grade():
    pod = oc_get_json("pod", "runner", "-n", PROJECT)

    with GradingStep("Il pod runner esiste") as step:
        if not pod:
            step.fail("Pod 'runner' non trovato")

    with GradingStep("Il pod runner usa l'immagine corretta") as step:
        if not pod:
            step.fail("Pod 'runner' non trovato")
        else:
            containers = pod.get("spec", {}).get("containers", [])
            image = containers[0].get("image", "") if containers else ""
            if IMAGE.split(":")[0] not in image:
                step.add_error(f"Immagine attuale: {image!r}, attesa una derivata da {IMAGE!r}")

    with GradingStep("Il pod runner e' in esecuzione (Running)") as step:
        if not pod:
            step.fail("Pod 'runner' non trovato")
        elif (pod.get("status") or {}).get("phase") != "Running":
            step.add_error(f"Fase attuale: {(pod.get('status') or {}).get('phase')!r}")


if __name__ == "__main__":
    run_cli(setup, grade)
