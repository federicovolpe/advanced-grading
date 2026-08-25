"""
Cap. 7 — Manage Application Updates
Configura un image change trigger fra un ImageStream e un Deployment.
"""
import json
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, oc, oc_get_json, reset_project, run_cli

CHAPTER = "Cap. 7 — Manage Application Updates"
TITLE = "Configura un image change trigger"
PROJECT = "training-updates-trigger"
SOURCE_IMAGE = "registry.access.redhat.com/ubi9/httpd-24:latest"
CONTAINER_NAME = "httpd-24"  # nome derivato dall'immagine da "oc create deployment"
TRIGGER_TAG = "myapp:v1"

TASK = f"""\
Nel progetto "{PROJECT}" trovi l'ImageStream "myapp" (con il tag "v1"
gia' importato) e il Deployment "app" (container chiamato
"{CONTAINER_NAME}"). Configura un trigger cosi' che il container si
aggiorni automaticamente quando l'immagine puntata da {TRIGGER_TAG}
cambia.

Comando suggerito (1):
  oc set triggers deployment/app --from-image={TRIGGER_TAG} --containers={CONTAINER_NAME} -n {PROJECT}
"""


def setup():
    reset_project(PROJECT)
    oc("create", "deployment", "app", f"--image={SOURCE_IMAGE}", "-n", PROJECT, check=True)
    oc("import-image", TRIGGER_TAG, f"--from={SOURCE_IMAGE}", "--confirm", "-n", PROJECT, check=True)


def grade():
    dep = oc_get_json("deployment", "app", "-n", PROJECT)

    with GradingStep("Il Deployment app esiste") as step:
        if not dep:
            step.fail("Deployment 'app' non trovato")

    with GradingStep(f"E' configurato un trigger da {TRIGGER_TAG} sul container {CONTAINER_NAME}") as step:
        if not dep:
            step.fail("Deployment 'app' non trovato")
        else:
            raw = dep.get("metadata", {}).get("annotations", {}).get("image.openshift.io/triggers")
            triggers = []
            if raw:
                try:
                    triggers = json.loads(raw)
                except json.JSONDecodeError:
                    triggers = []
            match = next(
                (
                    t for t in triggers
                    if t.get("from", {}).get("kind") == "ImageStreamTag"
                    and t.get("from", {}).get("name") == TRIGGER_TAG
                    and CONTAINER_NAME in t.get("fieldPath", "")
                ),
                None,
            )
            if not match:
                step.add_error(f"Nessun trigger verso {TRIGGER_TAG} per il container '{CONTAINER_NAME}' (trovati: {triggers})")
            elif match.get("paused") is True:
                step.add_error("Il trigger esiste ma e' in pausa (paused=true)")


if __name__ == "__main__":
    run_cli(setup, grade)
