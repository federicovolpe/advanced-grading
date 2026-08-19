"""
Grading personalizzato per 'serving-openvino' (AI0016L - Deploy and Serve
Models with OpenVINO).

Da testo guida studente: lo studente esporta un modello PyTorch in ONNX,
lo carica su S3 (connessione 'models-s3', path models/image-classifier/1/),
e lo distribuisce con OpenVINO Model Server come 'image-classifier'.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists, condition_true

LAB_NAME = "serving-openvino"
INFERENCESERVICE_NAME = "image-classifier"


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(
        f"Il modello '{INFERENCESERVICE_NAME}' e' distribuito con OpenVINO ed e' pronto"
    ) as step:
        svc = oc_get_json("inferenceservice", INFERENCESERVICE_NAME, "-n", project)
        if not svc:
            step.fail(f"InferenceService '{INFERENCESERVICE_NAME}' non trovata")
        elif not condition_true(svc, "Ready"):
            step.add_error(f"InferenceService '{INFERENCESERVICE_NAME}' non e' Ready")


if __name__ == "__main__":
    main()
