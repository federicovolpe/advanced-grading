"""
Cap. 6 — Configure Applications for Reliability
Riserva capacita' di calcolo per un'app con le resource requests.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import (
    GradingStep, oc, oc_get_json, deployment_container,
    parse_quantity, reset_project, run_cli,
)

CHAPTER = "Cap. 6 — Configure Applications for Reliability"
TITLE = "Riserva risorse con le resource requests"
PROJECT = "training-reliability-requests"
IMAGE = "registry.access.redhat.com/ubi9/httpd-24:latest"
MIN_CPU = "100m"
MIN_MEMORY = "128Mi"

TASK = f"""\
Nel progetto "{PROJECT}" trovi il Deployment "api". Imposta sul suo
container una richiesta (request) di risorse di almeno {MIN_CPU} di CPU
e {MIN_MEMORY} di memoria.

Comando suggerito (1):
  oc set resources deployment/api --requests=cpu={MIN_CPU},memory={MIN_MEMORY} -n {PROJECT}
"""


def setup():
    reset_project(PROJECT)
    oc("create", "deployment", "api", f"--image={IMAGE}", "-n", PROJECT, check=True)


def grade():
    dep = oc_get_json("deployment", "api", "-n", PROJECT)
    container = deployment_container(dep) if dep else None
    requests = (container or {}).get("resources", {}).get("requests", {})

    with GradingStep("Il Deployment api esiste") as step:
        if not dep:
            step.fail("Deployment 'api' non trovato")

    with GradingStep(f"La richiesta di CPU e' almeno {MIN_CPU}") as step:
        cpu = parse_quantity(requests.get("cpu"))
        if cpu is None or cpu < parse_quantity(MIN_CPU):
            step.add_error(f"requests.cpu = {requests.get('cpu')!r}, atteso almeno {MIN_CPU}")

    with GradingStep(f"La richiesta di memoria e' almeno {MIN_MEMORY}") as step:
        memory = parse_quantity(requests.get("memory"))
        if memory is None or memory < parse_quantity(MIN_MEMORY):
            step.add_error(f"requests.memory = {requests.get('memory')!r}, atteso almeno {MIN_MEMORY}")


if __name__ == "__main__":
    run_cli(setup, grade)
