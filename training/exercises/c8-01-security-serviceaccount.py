"""
Extra — Sicurezza e RBAC (non e' un capitolo del manuale DO180: argomento
comune negli esami di certificazione OpenShift/Kubernetes, aggiunto per
coprire piu' terreno rispetto al solo programma DO180).
Crea un ServiceAccount.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, oc_get_json, ensure_project, run_cli

CHAPTER = "Extra — Sicurezza e RBAC"
TITLE = "Crea un ServiceAccount"
PROJECT = "training-security-serviceaccount"

TASK = f"""\
Nel progetto "{PROJECT}", crea un ServiceAccount chiamato "myapp-sa".

Comando suggerito (1):
  oc create serviceaccount myapp-sa -n {PROJECT}
"""


def setup():
    ensure_project(PROJECT)


def grade():
    with GradingStep("Il ServiceAccount myapp-sa esiste") as step:
        if not oc_get_json("serviceaccount", "myapp-sa", "-n", PROJECT):
            step.fail("ServiceAccount 'myapp-sa' non trovato")


if __name__ == "__main__":
    run_cli(setup, grade)
