"""
Cap. 7 — Manage Application Updates
Aggiorna l'immagine di un Deployment e verifica che il rollout sia riuscito.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, oc, oc_get_json, deployment_container, reset_project, run_cli

CHAPTER = "Cap. 7 — Manage Application Updates"
TITLE = "Aggiorna l'immagine e verifica il rollout"
PROJECT = "training-updates-rollout"
OLD_IMAGE = "registry.access.redhat.com/ubi9/httpd-24:latest"
NEW_IMAGE = "registry.access.redhat.com/ubi8/httpd-24:latest"
CONTAINER_NAME = "httpd-24"  # nome derivato dall'immagine da "oc create deployment"

TASK = f"""\
Nel progetto "{PROJECT}" trovi il Deployment "app" (immagine attuale:
{OLD_IMAGE}, container chiamato "{CONTAINER_NAME}"). Aggiornalo per
usare {NEW_IMAGE} e verifica che il rollout si completi con successo.

Comandi suggeriti (2):
  oc set image deployment/app {CONTAINER_NAME}={NEW_IMAGE} -n {PROJECT}
  oc rollout status deployment/app -n {PROJECT}
"""


def setup():
    reset_project(PROJECT)
    oc("create", "deployment", "app", f"--image={OLD_IMAGE}", "-n", PROJECT, check=True)


def grade():
    dep = oc_get_json("deployment", "app", "-n", PROJECT)
    container = deployment_container(dep) if dep else None

    with GradingStep("Il Deployment app esiste") as step:
        if not dep:
            step.fail("Deployment 'app' non trovato")

    with GradingStep("Il Deployment app usa la nuova immagine") as step:
        image = (container or {}).get("image", "")
        if NEW_IMAGE.split(":")[0] not in image:
            step.add_error(f"Immagine attuale: {image!r}, attesa una derivata da {NEW_IMAGE!r}")

    with GradingStep("Il rollout si e' completato con successo") as step:
        if not dep:
            step.fail("Deployment 'app' non trovato")
        else:
            status = dep.get("status", {})
            replicas = status.get("replicas", 0)
            updated = status.get("updatedReplicas", 0)
            available = status.get("availableReplicas", 0)
            if not (replicas and replicas == updated == available):
                step.add_error(
                    f"replicas={replicas}, updatedReplicas={updated}, "
                    f"availableReplicas={available} (devono coincidere e non essere 0)"
                )


if __name__ == "__main__":
    run_cli(setup, grade)
