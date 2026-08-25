"""
Cap. 7 — Manage Application Updates
Crea un ImageStream e importa un tag da un'immagine esterna.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, oc_get_json, ensure_project, run_cli

CHAPTER = "Cap. 7 — Manage Application Updates"
TITLE = "Crea un ImageStream e importa un tag"
PROJECT = "training-updates-imagestream"
SOURCE_IMAGE = "registry.access.redhat.com/ubi9/httpd-24:latest"

TASK = f"""\
Nel progetto "{PROJECT}", crea un ImageStream chiamato "myapp" e
importa in esso il tag "v1" a partire dall'immagine {SOURCE_IMAGE}.

Comando suggerito (1):
  oc import-image myapp:v1 --from={SOURCE_IMAGE} --confirm -n {PROJECT}
"""


def setup():
    ensure_project(PROJECT)


def grade():
    imgstream = oc_get_json("imagestream", "myapp", "-n", PROJECT)

    with GradingStep("L'ImageStream myapp esiste") as step:
        if not imgstream:
            step.fail("ImageStream 'myapp' non trovato")

    with GradingStep("Il tag v1 e' stato importato con successo") as step:
        if not imgstream:
            step.fail("ImageStream 'myapp' non trovato")
        else:
            tags = imgstream.get("status", {}).get("tags", []) or []
            v1 = next((t for t in tags if t.get("tag") == "v1"), None)
            if not v1:
                step.add_error("Nessun tag 'v1' in status.tags")
            elif not v1.get("items"):
                step.add_error("Il tag 'v1' esiste ma non ha risolto nessuna immagine (items vuoto)")


if __name__ == "__main__":
    run_cli(setup, grade)
