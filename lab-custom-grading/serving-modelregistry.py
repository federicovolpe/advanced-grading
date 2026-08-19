"""
Grading personalizzato per 'serving-modelregistry' (AI0016L - Model
Registry).

Da testo guida studente: lo studente pacchettizza il modello diabetes in
due versioni OCI (v1, v2), le registra nel Model Registry come 'diabetes'
v1/v2, e distribuisce entrambe le versioni. I nomi delle InferenceService
risultanti sono deterministici (mostrati nella guida via `oc get route
diabetes-v1`/`diabetes-v2` e nelle richieste di inferenza KServe V2).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists, condition_true

LAB_NAME = "serving-modelregistry"
INFERENCESERVICE_NAMES = ["diabetes-v1", "diabetes-v2"]


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    for name in INFERENCESERVICE_NAMES:
        with GradingStep(f"Il modello '{name}' e' registrato/distribuito ed e' pronto") as step:
            svc = oc_get_json("inferenceservice", name, "-n", project)
            if not svc:
                step.fail(f"InferenceService '{name}' non trovata")
            elif not condition_true(svc, "Ready"):
                step.add_error(f"InferenceService '{name}' non e' Ready")


if __name__ == "__main__":
    main()
