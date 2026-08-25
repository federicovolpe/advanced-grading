"""
Extra — Sicurezza e RBAC (vedi c8-01-security-serviceaccount.py).
Collega un ServiceAccount a un Deployment esistente.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, oc, oc_get_json, reset_project, run_cli

CHAPTER = "Extra — Sicurezza e RBAC"
TITLE = "Usa un ServiceAccount in un Deployment"
PROJECT = "training-security-serviceaccount-use"
IMAGE = "registry.access.redhat.com/ubi9/httpd-24:latest"
SERVICE_ACCOUNT = "myapp-sa"

TASK = f"""\
Nel progetto "{PROJECT}" trovi il Deployment "app" e il ServiceAccount
"{SERVICE_ACCOUNT}", gia' pronti. Configura il Deployment "app" perche'
i suoi pod usino il ServiceAccount "{SERVICE_ACCOUNT}" invece di quello
di default.

Comando suggerito (1):
  oc set serviceaccount deployment/app {SERVICE_ACCOUNT} -n {PROJECT}
"""


def setup():
    reset_project(PROJECT)
    oc("create", "serviceaccount", SERVICE_ACCOUNT, "-n", PROJECT, check=True)
    oc("create", "deployment", "app", f"--image={IMAGE}", "-n", PROJECT, check=True)


def grade():
    dep = oc_get_json("deployment", "app", "-n", PROJECT)

    with GradingStep("Il Deployment app esiste") as step:
        if not dep:
            step.fail("Deployment 'app' non trovato")

    with GradingStep(f"Il Deployment app usa il ServiceAccount {SERVICE_ACCOUNT}") as step:
        if not dep:
            step.fail("Deployment 'app' non trovato")
        else:
            sa = dep.get("spec", {}).get("template", {}).get("spec", {}).get("serviceAccountName")
            if sa != SERVICE_ACCOUNT:
                step.add_error(f"serviceAccountName = {sa!r}, attesa {SERVICE_ACCOUNT!r}")

    with GradingStep("Il pod e' Running con il ServiceAccount corretto") as step:
        pods = oc_get_json("pods", "-n", PROJECT, "-l", "app=app")
        items = (pods or {}).get("items", [])
        running = [
            p for p in items
            if p.get("status", {}).get("phase") == "Running"
            and p.get("spec", {}).get("serviceAccountName") == SERVICE_ACCOUNT
        ]
        if not running:
            step.fail(f"Nessun pod Running con serviceAccountName={SERVICE_ACCOUNT!r}")


if __name__ == "__main__":
    run_cli(setup, grade)
