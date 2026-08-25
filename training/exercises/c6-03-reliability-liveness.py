"""
Cap. 6 — Configure Applications for Reliability
Aggiungi una liveness probe a un Deployment.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, oc, oc_get_json, deployment_container, reset_project, run_cli

CHAPTER = "Cap. 6 — Configure Applications for Reliability"
TITLE = "Aggiungi una liveness probe"
PROJECT = "training-reliability-liveness"
IMAGE = "registry.access.redhat.com/ubi9/httpd-24:latest"
PORT = 8080

TASK = f"""\
Nel progetto "{PROJECT}" trovi il Deployment "web" (ascolta sulla
porta {PORT}). Aggiungigli una liveness probe TCP sulla porta {PORT}.

Comando suggerito (1):
  oc set probe deployment/web --liveness --open-tcp={PORT} -n {PROJECT}
"""


def setup():
    reset_project(PROJECT)
    oc("create", "deployment", "web", f"--image={IMAGE}", "-n", PROJECT, check=True)


def grade():
    dep = oc_get_json("deployment", "web", "-n", PROJECT)
    container = deployment_container(dep) if dep else None
    probe = (container or {}).get("livenessProbe")

    with GradingStep("Il Deployment web esiste") as step:
        if not dep:
            step.fail("Deployment 'web' non trovato")

    with GradingStep(f"Il container ha una liveness probe sulla porta {PORT}") as step:
        if not probe:
            step.fail("Nessuna livenessProbe definita")
        else:
            port = probe.get("tcpSocket", {}).get("port") or probe.get("httpGet", {}).get("port")
            if port != PORT:
                step.add_error(f"Porta configurata: {port!r}, attesa {PORT}")

    with GradingStep("Il Deployment web e' disponibile (probe non la blocca)") as step:
        available = (dep or {}).get("status", {}).get("availableReplicas", 0)
        if not available:
            step.fail("Nessuna replica disponibile")


if __name__ == "__main__":
    run_cli(setup, grade)
