"""
Grading personalizzato per 'workbench-creating' (AI0015L - Create and Manage
Workbench Environments).

Da testo guida studente: lo studente crea un primo workbench
'workbench-creating-wb' (2GiB di storage dedicato, env DATA_FILE=data.csv),
poi lo elimina e ne crea un secondo, 'second-wb', riusando lo STESSO PVC
(workbench-creating-wb-storage) per verificare che i dati persistano. Lo
stato finale (prima di `lab finish`) e' quindi: il primo workbench NON
esiste piu', il secondo si', e usa il PVC del primo.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "workbench-creating"
STORAGE_NAME = "workbench-creating-wb-storage"
FINAL_WORKBENCH = "second-wb"


def _pvc_names(notebook):
    volumes = notebook.get("spec", {}).get("template", {}).get("spec", {}).get("volumes", []) or []
    return {
        v.get("persistentVolumeClaim", {}).get("claimName")
        for v in volumes
        if v.get("persistentVolumeClaim")
    }


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(f"Il PVC '{STORAGE_NAME}' (2Gi) esiste") as step:
        pvc = oc_get_json("pvc", STORAGE_NAME, "-n", project)
        if not pvc:
            step.fail(f"PVC '{STORAGE_NAME}' non trovato")
        else:
            size = pvc.get("spec", {}).get("resources", {}).get("requests", {}).get("storage")
            if size != "2Gi":
                step.add_error(f"Dimensione del PVC e' '{size}', attesa '2Gi'")

    with GradingStep(f"Il workbench '{FINAL_WORKBENCH}' esiste e riusa lo storage originale") as step:
        notebook = oc_get_json("notebook", FINAL_WORKBENCH, "-n", project)
        if not notebook:
            step.fail(f"Notebook '{FINAL_WORKBENCH}' non trovato")
        elif STORAGE_NAME not in _pvc_names(notebook):
            step.add_error(
                f"Il workbench '{FINAL_WORKBENCH}' non monta il PVC '{STORAGE_NAME}'"
            )


if __name__ == "__main__":
    main()
