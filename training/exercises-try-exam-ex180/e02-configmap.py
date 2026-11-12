"""
Try-exam EX180, 2 — crea una ConfigMap.

Scostamenti dal tema annotato: il tema dice solo "crea una configmap".
Progetto, nome e chiavi sono scelte NOSTRE per renderla gradabile (la stessa
ConfigMap e' poi creata gia' pronta dal setup() dell'esercizio 4).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ex180_common import (  # noqa: F401
    CHAPTER, SETUP_TIMEOUT, GradingStep, oc, oc_get_json, reset_project, delete_project,
    check_project, run_cli,
)

SLUG = "e02"
PROJECT = "ex180-e02"
TITLE = "2) Crea una ConfigMap"
CM = "app-config"
DATA = {"GREETING": "ciao", "APP_ENV": "exam"}

TASK = f"""\
Nel progetto {PROJECT} crea una ConfigMap di nome {CM} con queste
due chiavi:
    GREETING = {DATA['GREETING']}
    APP_ENV  = {DATA['APP_ENV']}
"""

SOLUTION = f"""\
oc project {PROJECT}
oc create configmap {CM} \\
    --from-literal=GREETING={DATA['GREETING']} \\
    --from-literal=APP_ENV={DATA['APP_ENV']}
oc get configmap {CM} -o yaml
"""


def setup():
    reset_project(PROJECT)


def grade():
    check_project(PROJECT)
    cm = oc_get_json("configmap", CM, "-n", PROJECT)
    with GradingStep(f"La ConfigMap {CM} esiste") as step:
        if not cm:
            step.fail(f"ConfigMap '{CM}' non trovata in {PROJECT}")
    for key, value in DATA.items():
        with GradingStep(f"La chiave {key} vale {value!r}") as step:
            if not cm:
                step.fail("ConfigMap non trovata")
            else:
                got = (cm.get("data") or {}).get(key)
                if got != value:
                    step.add_error(f"{key} = {got!r}")


def cleanup():
    delete_project(PROJECT)


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
