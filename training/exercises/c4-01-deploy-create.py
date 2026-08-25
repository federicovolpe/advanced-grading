"""
Cap. 4 — Deploy Managed and Networked Applications on Kubernetes
Crea un Deployment con un'immagine e un numero di repliche specifici.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, oc_get_json, deployment_container, ensure_project, run_cli

CHAPTER = "Cap. 4 — Deploy Managed and Networked Applications"
TITLE = "Crea un Deployment"
PROJECT = "training-deploy-create"
IMAGE = "registry.access.redhat.com/ubi9/httpd-24:latest"

TASK = f"""\
Nel progetto "{PROJECT}", crea un Deployment chiamato "web" che usa
l'immagine {IMAGE} con 2 repliche.

Comando suggerito (1):
  oc create deployment web --image={IMAGE} --replicas=2 -n {PROJECT}
"""


def setup():
    ensure_project(PROJECT)


def grade():
    dep = oc_get_json("deployment", "web", "-n", PROJECT)

    with GradingStep("Il Deployment web esiste") as step:
        if not dep:
            step.fail("Deployment 'web' non trovato")

    with GradingStep("Il Deployment web usa l'immagine corretta") as step:
        if not dep:
            step.fail("Deployment 'web' non trovato")
        else:
            container = deployment_container(dep)
            image = (container or {}).get("image", "")
            if IMAGE.split(":")[0] not in image:
                step.add_error(f"Immagine attuale: {image!r}, attesa una derivata da {IMAGE!r}")

    with GradingStep("Il Deployment web ha 2 repliche disponibili") as step:
        if not dep:
            step.fail("Deployment 'web' non trovato")
        else:
            spec_replicas = dep.get("spec", {}).get("replicas")
            available = dep.get("status", {}).get("availableReplicas", 0)
            if spec_replicas != 2:
                step.add_error(f"spec.replicas = {spec_replicas}, attese 2")
            if available != 2:
                step.add_error(f"status.availableReplicas = {available}, attese 2")


if __name__ == "__main__":
    run_cli(setup, grade)
