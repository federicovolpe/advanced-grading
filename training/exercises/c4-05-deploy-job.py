"""
Cap. 4 — Deploy Managed and Networked Applications on Kubernetes
Crea un Job "short-lived" che deve completarsi con successo.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, oc_get_json, ensure_project, run_cli

CHAPTER = "Cap. 4 — Deploy Managed and Networked Applications"
TITLE = "Crea un Job"
PROJECT = "training-deploy-job"
IMAGE = "registry.access.redhat.com/ubi9/ubi:latest"

TASK = f"""\
Nel progetto "{PROJECT}", crea un Job chiamato "hello-job" che usa
l'immagine {IMAGE} ed esegue il comando "echo Hello from the Job",
cosi' da completarsi con successo (a differenza di un Deployment, un
Job non deve restare in esecuzione all'infinito).

Comando suggerito (1):
  oc create job hello-job --image={IMAGE} -n {PROJECT} -- echo Hello from the Job
"""


def setup():
    ensure_project(PROJECT)


def grade():
    job = oc_get_json("job", "hello-job", "-n", PROJECT)

    with GradingStep("Il Job hello-job esiste") as step:
        if not job:
            step.fail("Job 'hello-job' non trovato")

    with GradingStep("Il Job hello-job si e' completato con successo") as step:
        if not job:
            step.fail("Job 'hello-job' non trovato")
        else:
            succeeded = job.get("status", {}).get("succeeded", 0)
            if succeeded < 1:
                failed = job.get("status", {}).get("failed", 0)
                step.add_error(f"status.succeeded = {succeeded}, status.failed = {failed}")


if __name__ == "__main__":
    run_cli(setup, grade)
