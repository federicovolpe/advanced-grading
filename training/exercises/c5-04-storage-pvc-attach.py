"""
Cap. 5 — Manage Storage for Application Configuration and Data
Collega una nuova PVC a un Deployment esistente.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import (
    GradingStep, oc, oc_get_json, parse_quantity,
    find_pvc_name_for_deployment, reset_project, run_cli,
)

CHAPTER = "Cap. 5 — Manage Storage for Application Configuration and Data"
TITLE = "Collega una PVC a un Deployment"
PROJECT = "training-storage-pvc-attach"
IMAGE = "registry.access.redhat.com/ubi9/ubi:latest"
MOUNT_PATH = "/data"
CLAIM_SIZE_GI = 1

TASK = f"""\
Nel progetto "{PROJECT}" trovi il Deployment "writer". Crea una PVC di
{CLAIM_SIZE_GI}Gi e collegala al Deployment "writer", montata nel path
{MOUNT_PATH}.

Comando suggerito (1):
  oc set volume deployment/writer --add --type=pvc --claim-size={CLAIM_SIZE_GI}Gi \\
      --mount-path={MOUNT_PATH} -n {PROJECT}

(Il nome della PVC non conta: il grading lo scopre da solo guardando cosa
e' montato su {MOUNT_PATH}.)
"""


def setup():
    reset_project(PROJECT)
    oc(
        "create", "deployment", "writer", f"--image={IMAGE}", "-n", PROJECT,
        "--", "sleep", "infinity", check=True,
    )


def grade():
    dep = oc_get_json("deployment", "writer", "-n", PROJECT)
    pvc_name = find_pvc_name_for_deployment(dep, mount_path=MOUNT_PATH) if dep else None

    with GradingStep(f"Il Deployment writer ha una PVC montata su {MOUNT_PATH}") as step:
        if not dep:
            step.fail("Deployment 'writer' non trovato")
        elif not pvc_name:
            step.fail(f"Nessuna PersistentVolumeClaim montata su {MOUNT_PATH}")

    with GradingStep(f"La PVC richiede almeno {CLAIM_SIZE_GI}Gi") as step:
        if not pvc_name:
            step.fail("Nessuna PVC da controllare (vedi check precedente)")
        else:
            pvc = oc_get_json("pvc", pvc_name, "-n", PROJECT)
            requested = (pvc or {}).get("spec", {}).get("resources", {}).get("requests", {}).get("storage")
            if not pvc:
                step.fail(f"PVC '{pvc_name}' non trovata")
            elif (parse_quantity(requested) or 0) < parse_quantity(f"{CLAIM_SIZE_GI}Gi"):
                step.add_error(f"resources.requests.storage = {requested!r}, attesi almeno {CLAIM_SIZE_GI}Gi")

    with GradingStep("Il Deployment writer e' Running con la PVC montata") as step:
        available = (dep or {}).get("status", {}).get("availableReplicas", 0)
        if not available:
            step.fail("Nessuna replica disponibile (PVC non ancora Bound o pod non Running?)")


if __name__ == "__main__":
    run_cli(setup, grade)
