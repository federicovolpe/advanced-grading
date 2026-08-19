"""
Grading personalizzato per 'serving-custom' (AI0017L - Custom ServingRuntime).

`lab start` (ai0017l/exercises/serving_custom.py) provisiona gia' progetto,
bucket MinIO 'custom-models' (precaricato col modello diabetes) e data
connection; il compito dello studente e':

1. Creare un ServingRuntime Template custom (Seldon MLServer) chiamato
   'my-seldon-mlserver' nel namespace 'redhat-ods-applications' (dashboard
   RHOAI, sezione "Serving runtimes"). Il nome esatto e' confermato dalla
   stessa logica di ricerca usata in `finish()` per pulirlo (vedi
   ai0017l/common.py -> find_template_by_serving_runtime), qui riprodotta:
   un Template il cui campo objects[] contiene un oggetto kind=ServingRuntime
   con questo nome esatto.
2. Distribuire il modello diabetes con quel runtime (un InferenceService
   pronto nel progetto che lo referenzia).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists, condition_true

LAB_NAME = "serving-custom"
SERVING_RUNTIME_NAME = "my-seldon-mlserver"
TEMPLATES_NAMESPACE = "redhat-ods-applications"


def _find_template_with_serving_runtime(serving_runtime_name):
    templates = oc_get_json("templates", "-n", TEMPLATES_NAMESPACE)
    if not templates:
        return None
    for template in templates.get("items", []):
        for obj in template.get("objects", []) or []:
            if (
                obj.get("kind") == "ServingRuntime"
                and obj.get("metadata", {}).get("name") == serving_runtime_name
            ):
                return template.get("metadata", {}).get("name")
    return None


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(
        f"Il ServingRuntime Template custom '{SERVING_RUNTIME_NAME}' e' stato creato"
    ) as step:
        template_name = _find_template_with_serving_runtime(SERVING_RUNTIME_NAME)
        if not template_name:
            step.fail(
                f"Nessun Template in '{TEMPLATES_NAMESPACE}' contiene un "
                f"ServingRuntime chiamato '{SERVING_RUNTIME_NAME}'"
            )

    with GradingStep("Il modello diabetes e' distribuito con il runtime custom ed e' pronto") as step:
        services = oc_get_json("inferenceservice", "-n", project)
        if not services:
            step.fail(f"Nessuna InferenceService trovata nel progetto '{project}'")
        else:
            matching = [
                svc for svc in services.get("items", [])
                if svc.get("spec", {}).get("predictor", {}).get("model", {}).get("runtime")
                == SERVING_RUNTIME_NAME
            ]
            if not matching:
                step.fail(
                    f"Nessuna InferenceService usa il runtime '{SERVING_RUNTIME_NAME}'"
                )
            elif not any(condition_true(svc, "Ready") for svc in matching):
                step.add_error(
                    "La InferenceService che usa il runtime custom non e' Ready"
                )


if __name__ == "__main__":
    main()
