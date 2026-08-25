"""
Cap. 5 — Manage Storage for Application Configuration and Data
Crea una PersistentVolumeClaim con una dimensione e un access mode dati.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, oc_get_json, parse_quantity, ensure_project, run_cli

CHAPTER = "Cap. 5 — Manage Storage for Application Configuration and Data"
TITLE = "Crea una PersistentVolumeClaim"
PROJECT = "training-storage-pvc"
CLAIM_SIZE_GI = 2

TASK = f"""\
Nel progetto "{PROJECT}", crea una PersistentVolumeClaim chiamata
"data-claim" da {CLAIM_SIZE_GI}Gi in modalita' ReadWriteOnce, usando la
storage class di default del cluster.

Salva questo contenuto in pvc.yaml:

  apiVersion: v1
  kind: PersistentVolumeClaim
  metadata:
    name: data-claim
  spec:
    accessModes:
      - ReadWriteOnce
    resources:
      requests:
        storage: {CLAIM_SIZE_GI}Gi

Poi applicalo (1 comando):
  oc apply -f pvc.yaml -n {PROJECT}
"""


def setup():
    ensure_project(PROJECT)


def grade():
    pvc = oc_get_json("pvc", "data-claim", "-n", PROJECT)

    with GradingStep("La PVC data-claim esiste") as step:
        if not pvc:
            step.fail("PVC 'data-claim' non trovata")

    with GradingStep(f"La PVC data-claim richiede {CLAIM_SIZE_GI}Gi in ReadWriteOnce") as step:
        if not pvc:
            step.fail("PVC 'data-claim' non trovata")
        else:
            spec = pvc.get("spec", {})
            requested = spec.get("resources", {}).get("requests", {}).get("storage")
            if parse_quantity(requested) != parse_quantity(f"{CLAIM_SIZE_GI}Gi"):
                step.add_error(f"resources.requests.storage = {requested!r}, attesi {CLAIM_SIZE_GI}Gi")
            if "ReadWriteOnce" not in (spec.get("accessModes") or []):
                step.add_error(f"accessModes = {spec.get('accessModes')!r}, attesa 'ReadWriteOnce'")

    with GradingStep("La PVC data-claim e' Bound") as step:
        if not pvc:
            step.fail("PVC 'data-claim' non trovata")
        elif pvc.get("status", {}).get("phase") != "Bound":
            step.add_error(f"status.phase = {pvc.get('status', {}).get('phase')!r}, attesa 'Bound'")


if __name__ == "__main__":
    run_cli(setup, grade)
