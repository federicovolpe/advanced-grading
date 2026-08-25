"""
Cap. 6 — Configure Applications for Reliability
Limita la capacita' di calcolo massima di un'app con le resource limits.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import (
    GradingStep, oc, oc_get_json, deployment_container,
    parse_quantity, reset_project, run_cli,
)

CHAPTER = "Cap. 6 — Configure Applications for Reliability"
TITLE = "Limita le risorse con le resource limits"
PROJECT = "training-reliability-limits"
IMAGE = "registry.access.redhat.com/ubi9/httpd-24:latest"
MAX_CPU = "500m"
MAX_MEMORY = "256Mi"

TASK = f"""\
Nel progetto "{PROJECT}" trovi il Deployment "api". Imposta sul suo
container un limite massimo di {MAX_CPU} di CPU e {MAX_MEMORY} di
memoria.

Comando suggerito (1):
  oc set resources deployment/api --limits=cpu={MAX_CPU},memory={MAX_MEMORY} -n {PROJECT}
"""


def setup():
    reset_project(PROJECT)
    oc("create", "deployment", "api", f"--image={IMAGE}", "-n", PROJECT, check=True)


def grade():
    dep = oc_get_json("deployment", "api", "-n", PROJECT)
    container = deployment_container(dep) if dep else None
    limits = (container or {}).get("resources", {}).get("limits", {})

    with GradingStep("Il Deployment api esiste") as step:
        if not dep:
            step.fail("Deployment 'api' non trovato")

    with GradingStep(f"Il limite di CPU e' {MAX_CPU}") as step:
        cpu = parse_quantity(limits.get("cpu"))
        if cpu is None or cpu != parse_quantity(MAX_CPU):
            step.add_error(f"limits.cpu = {limits.get('cpu')!r}, attesi {MAX_CPU}")

    with GradingStep(f"Il limite di memoria e' {MAX_MEMORY}") as step:
        memory = parse_quantity(limits.get("memory"))
        if memory is None or memory != parse_quantity(MAX_MEMORY):
            step.add_error(f"limits.memory = {limits.get('memory')!r}, attesi {MAX_MEMORY}")


if __name__ == "__main__":
    run_cli(setup, grade)
