"""
Cap. 2 — Kubernetes and OpenShift CLI and APIs
Applica una label a una risorsa esistente.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, oc_get_json, oc, reset_project, run_cli

CHAPTER = "Cap. 2 — Kubernetes and OpenShift CLI and APIs"
TITLE = "Applica una label a un pod"
PROJECT = "training-pod-label"

TASK = f"""\
Nel progetto "{PROJECT}" trovi un pod chiamato "app". Applicagli
l'etichetta tier=frontend.

Comando suggerito (1):
  oc label pod app tier=frontend -n {PROJECT}
"""


def setup():
    reset_project(PROJECT)
    oc(
        "run", "app",
        "--image=registry.access.redhat.com/ubi9/ubi:latest",
        "-n", PROJECT,
        "--command", "--", "sleep", "infinity",
        check=True,
    )


def grade():
    with GradingStep("Il pod app esiste") as step:
        pod = oc_get_json("pod", "app", "-n", PROJECT)
        if not pod:
            step.fail("Pod 'app' non trovato")

    with GradingStep("Il pod app ha la label tier=frontend") as step:
        pod = oc_get_json("pod", "app", "-n", PROJECT)
        if not pod:
            step.fail("Pod 'app' non trovato")
        else:
            labels = pod.get("metadata", {}).get("labels", {}) or {}
            if labels.get("tier") != "frontend":
                step.add_error(f"labels.tier = {labels.get('tier')!r}, attesa 'frontend'")


if __name__ == "__main__":
    run_cli(setup, grade)
