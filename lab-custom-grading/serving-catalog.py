"""
Grading personalizzato per 'serving-catalog' (AI0016L - Model Catalog).

`lab start` (ai0016l/exercises/serving_catalog.py) abilita solo la pagina
AI Hub > Catalog; nessun modello viene distribuito automaticamente. Da testo
guida studente: lo studente distribuisce Qwen3-0.6B dal catalogo con vLLM,
producendo una InferenceService 'qwen3-06b' (nome confermato dal pod
'qwen3-06b-predictor-...' e dalla Route 'qwen3-06b-serving-catalog...'
mostrati nella guida).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists, condition_true

LAB_NAME = "serving-catalog"
INFERENCESERVICE_NAME = "qwen3-06b"


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(
        f"Il modello '{INFERENCESERVICE_NAME}' e' distribuito dal catalogo ed e' pronto"
    ) as step:
        svc = oc_get_json("inferenceservice", INFERENCESERVICE_NAME, "-n", project)
        if not svc:
            step.fail(f"InferenceService '{INFERENCESERVICE_NAME}' non trovata")
        elif not condition_true(svc, "Ready"):
            step.add_error(f"InferenceService '{INFERENCESERVICE_NAME}' non e' Ready")


if __name__ == "__main__":
    main()
