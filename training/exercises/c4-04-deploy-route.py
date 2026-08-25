"""
Cap. 4 — Deploy Managed and Networked Applications on Kubernetes
Crea una Route per esporre un Service all'esterno del cluster.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, oc, oc_get_json, reset_project, run_cli

CHAPTER = "Cap. 4 — Deploy Managed and Networked Applications"
TITLE = "Crea una Route"
PROJECT = "training-deploy-route"
IMAGE = "registry.access.redhat.com/ubi9/httpd-24:latest"
PORT = 8080

TASK = f"""\
Nel progetto "{PROJECT}" trovi il Deployment "web" e il Service "web"
(porta {PORT}), gia' pronti. Crea una Route per il Service "web" cosi'
che l'app sia raggiungibile dall'esterno del cluster.

Comando suggerito (1):
  oc expose service web -n {PROJECT}
"""


def setup():
    reset_project(PROJECT)
    oc("create", "deployment", "web", f"--image={IMAGE}", "-n", PROJECT, check=True)
    oc("expose", "deployment", "web", f"--port={PORT}", f"--target-port={PORT}", "-n", PROJECT, check=True)


def grade():
    routes = oc_get_json("route", "-n", PROJECT)
    items = (routes or {}).get("items", [])
    route = next((r for r in items if r.get("spec", {}).get("to", {}).get("name") == "web"), None)

    with GradingStep("Esiste una Route verso il Service web") as step:
        if not route:
            step.fail("Nessuna Route trova il Service 'web' come target")

    with GradingStep("La Route e' stata ammessa dal router") as step:
        if not route:
            step.fail("Nessuna Route trovata")
        else:
            ingress = route.get("status", {}).get("ingress", [])
            admitted = any(
                c.get("type") == "Admitted" and c.get("status") == "True"
                for ing in ingress
                for c in ing.get("conditions", [])
            )
            if not admitted:
                step.add_error("Nessuna condizione Admitted=True nello status della Route")


if __name__ == "__main__":
    run_cli(setup, grade)
