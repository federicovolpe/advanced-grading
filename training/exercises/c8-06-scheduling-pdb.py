"""
Extra — Scheduling e disponibilita' (non e' un capitolo del manuale
DO180: la PodDisruptionBudget e' trattata in DO380 "Pod Scheduling",
aggiunta qui per coprire piu' terreno rispetto al solo programma DO180).
Proteggi un'app dagli sfratti volontari con una PodDisruptionBudget.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, oc, oc_get_json, reset_project, run_cli

CHAPTER = "Extra — Scheduling e disponibilita'"
TITLE = "Crea una PodDisruptionBudget"
PROJECT = "training-scheduling-pdb"
IMAGE = "registry.access.redhat.com/ubi9/httpd-24:latest"
REPLICAS = 2

TASK = f"""\
Nel progetto "{PROJECT}" trovi il Deployment "app" (label app=app,
{REPLICAS} repliche). Crea una PodDisruptionBudget chiamata "myapp-pdb"
che garantisca almeno 1 pod disponibile in ogni momento per quei pod.

Salva questo contenuto in pdb.yaml:

  apiVersion: policy/v1
  kind: PodDisruptionBudget
  metadata:
    name: myapp-pdb
  spec:
    minAvailable: 1
    selector:
      matchLabels:
        app: app

Poi applicalo (1 comando):
  oc apply -f pdb.yaml -n {PROJECT}
"""


def setup():
    reset_project(PROJECT)
    oc("create", "deployment", "app", f"--image={IMAGE}", f"--replicas={REPLICAS}", "-n", PROJECT, check=True)


def grade():
    pdb = oc_get_json("poddisruptionbudget", "myapp-pdb", "-n", PROJECT)

    with GradingStep("La PodDisruptionBudget myapp-pdb esiste") as step:
        if not pdb:
            step.fail("PodDisruptionBudget 'myapp-pdb' non trovata")

    with GradingStep("Garantisce almeno 1 pod disponibile per app=app") as step:
        if not pdb:
            step.fail("PodDisruptionBudget 'myapp-pdb' non trovata")
        else:
            spec = pdb.get("spec", {})
            if spec.get("minAvailable") not in (1, "1"):
                step.add_error(f"spec.minAvailable = {spec.get('minAvailable')!r}, attesa 1")
            selector = spec.get("selector", {}).get("matchLabels", {})
            if selector.get("app") != "app":
                step.add_error(f"selector.matchLabels = {selector!r}, attesa app=app")

    with GradingStep("Lo status della PDB traccia davvero i pod dell'app") as step:
        if not pdb:
            step.fail("PodDisruptionBudget 'myapp-pdb' non trovata")
        else:
            expected = pdb.get("status", {}).get("expectedPods", 0)
            if expected < 1:
                step.add_error(
                    f"status.expectedPods = {expected}, atteso almeno 1 "
                    "(il selector non seleziona nessun pod reale?)"
                )


if __name__ == "__main__":
    run_cli(setup, grade)
