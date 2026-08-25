"""
Cap. 4 — Deploy Managed and Networked Applications on Kubernetes
Scala un Deployment esistente a un numero di repliche richiesto.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, oc, oc_get_json, reset_project, run_cli

CHAPTER = "Cap. 4 — Deploy Managed and Networked Applications"
TITLE = "Scala un Deployment"
PROJECT = "training-deploy-scale"
IMAGE = "registry.access.redhat.com/ubi9/httpd-24:latest"
TARGET_REPLICAS = 3

TASK = f"""\
Nel progetto "{PROJECT}" trovi il Deployment "api" con 1 replica.
Scalalo a {TARGET_REPLICAS} repliche.

Comando suggerito (1):
  oc scale deployment/api --replicas={TARGET_REPLICAS} -n {PROJECT}
"""


def setup():
    reset_project(PROJECT)
    oc("create", "deployment", "api", f"--image={IMAGE}", "--replicas=1", "-n", PROJECT, check=True)


def grade():
    dep = oc_get_json("deployment", "api", "-n", PROJECT)

    with GradingStep("Il Deployment api esiste") as step:
        if not dep:
            step.fail("Deployment 'api' non trovato")

    with GradingStep(f"Il Deployment api ha {TARGET_REPLICAS} repliche disponibili") as step:
        if not dep:
            step.fail("Deployment 'api' non trovato")
        else:
            spec_replicas = dep.get("spec", {}).get("replicas")
            available = dep.get("status", {}).get("availableReplicas", 0)
            if spec_replicas != TARGET_REPLICAS:
                step.add_error(f"spec.replicas = {spec_replicas}, attese {TARGET_REPLICAS}")
            if available != TARGET_REPLICAS:
                step.add_error(f"status.availableReplicas = {available}, attese {TARGET_REPLICAS}")


if __name__ == "__main__":
    run_cli(setup, grade)
