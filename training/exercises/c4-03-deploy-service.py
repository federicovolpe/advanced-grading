"""
Cap. 4 — Deploy Managed and Networked Applications on Kubernetes
Esponi un Deployment con un Service ClusterIP.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, oc, oc_get_json, reset_project, run_cli

CHAPTER = "Cap. 4 — Deploy Managed and Networked Applications"
TITLE = "Esponi un Deployment con un Service"
PROJECT = "training-deploy-service"
IMAGE = "registry.access.redhat.com/ubi9/httpd-24:latest"
PORT = 8080

TASK = f"""\
Nel progetto "{PROJECT}" trovi il Deployment "web" (ascolta sulla
porta {PORT}). Esponilo con un Service ClusterIP chiamato "web" sulla
porta {PORT}.

Comando suggerito (1):
  oc expose deployment web --port={PORT} --target-port={PORT} -n {PROJECT}
"""


def setup():
    reset_project(PROJECT)
    oc("create", "deployment", "web", f"--image={IMAGE}", "-n", PROJECT, check=True)


def grade():
    svc = oc_get_json("service", "web", "-n", PROJECT)

    with GradingStep("Il Service web esiste ed e' di tipo ClusterIP") as step:
        if not svc:
            step.fail("Service 'web' non trovato")
        elif svc.get("spec", {}).get("type", "ClusterIP") != "ClusterIP":
            step.add_error(f"spec.type = {svc['spec']['type']!r}, attesa 'ClusterIP'")

    with GradingStep(f"Il Service web espone la porta {PORT}") as step:
        if not svc:
            step.fail("Service 'web' non trovato")
        else:
            ports = svc.get("spec", {}).get("ports", [])
            if not any(p.get("port") == PORT for p in ports):
                step.add_error(f"Porte esposte: {[p.get('port') for p in ports]}, attesa {PORT}")

    with GradingStep("Il Service ha almeno un endpoint attivo") as step:
        ep = oc_get_json("endpoints", "web", "-n", PROJECT)
        addresses = []
        for subset in (ep or {}).get("subsets", []) or []:
            addresses += subset.get("addresses", []) or []
        if not addresses:
            step.fail("Nessun endpoint pronto (il pod dietro il Service non e' Ready?)")


if __name__ == "__main__":
    run_cli(setup, grade)
