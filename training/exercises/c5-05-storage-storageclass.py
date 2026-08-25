"""
Cap. 5 — Manage Storage for Application Configuration and Data
Seleziona esplicitamente una storage class diversa da quella di default.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import (
    GradingStep, oc, oc_get_json,
    find_pvc_name_for_deployment, reset_project, run_cli,
)

CHAPTER = "Cap. 5 — Manage Storage for Application Configuration and Data"
TITLE = "Scegli una storage class specifica"
PROJECT = "training-storage-class"
IMAGE = "registry.access.redhat.com/ubi9/ubi:latest"
MOUNT_PATH = "/var/lib/data"
STORAGE_CLASS = "lvms-vg1"

TASK = f"""\
Nel progetto "{PROJECT}" trovi il Deployment "db". Collegagli una PVC
di 1Gi che usi ESPLICITAMENTE la storage class "{STORAGE_CLASS}" (non
quella di default del cluster), montata su {MOUNT_PATH}.

Comando suggerito (1):
  oc set volume deployment/db --add --type=pvc --claim-size=1Gi \\
      --claim-class={STORAGE_CLASS} --mount-path={MOUNT_PATH} -n {PROJECT}
"""


def setup():
    reset_project(PROJECT)
    oc(
        "create", "deployment", "db", f"--image={IMAGE}", "-n", PROJECT,
        "--", "sleep", "infinity", check=True,
    )


def grade():
    dep = oc_get_json("deployment", "db", "-n", PROJECT)
    pvc_name = find_pvc_name_for_deployment(dep, mount_path=MOUNT_PATH) if dep else None

    with GradingStep(f"Il Deployment db ha una PVC montata su {MOUNT_PATH}") as step:
        if not dep:
            step.fail("Deployment 'db' non trovato")
        elif not pvc_name:
            step.fail(f"Nessuna PersistentVolumeClaim montata su {MOUNT_PATH}")

    with GradingStep(f"La PVC usa esplicitamente la storage class {STORAGE_CLASS}") as step:
        if not pvc_name:
            step.fail("Nessuna PVC da controllare (vedi check precedente)")
        else:
            pvc = oc_get_json("pvc", pvc_name, "-n", PROJECT)
            sc = (pvc or {}).get("spec", {}).get("storageClassName")
            if not pvc:
                step.fail(f"PVC '{pvc_name}' non trovata")
            elif sc != STORAGE_CLASS:
                step.add_error(f"storageClassName = {sc!r}, attesa {STORAGE_CLASS!r}")

    with GradingStep("Il Deployment db e' Running con la PVC montata") as step:
        available = (dep or {}).get("status", {}).get("availableReplicas", 0)
        if not available:
            step.fail("Nessuna replica disponibile (PVC non ancora Bound o pod non Running?)")


if __name__ == "__main__":
    run_cli(setup, grade)
