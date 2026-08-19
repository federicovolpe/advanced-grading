"""
Grading personalizzato per 'dspa-artifacts' (AI0020L - KFP Artifacts).

Stesso schema di 'dspa-kubeflow' (vedi quello script per i dettagli sulla
verifica via Argo Workflow, validata end-to-end su cluster reale): `lab
start` crea gia' progetto/bucket MinIO/DSPA/venv, lo studente completa i
TODO in pipeline.py (tipi Input/Output degli artifact, lettura/scrittura dei
path, logging delle metriche - confrontati con
materials/solutions/dspa-artifacts/pipeline.py) e importa/esegue la pipeline
'sentiment-artifacts' dalla dashboard RHOAI.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists, lab_materials_dir, read_text_file

LAB_NAME = "dspa-artifacts"
PIPELINE_NAME = "sentiment-artifacts"

REQUIRED_SNIPPETS = [
    "dataset: Input[Dataset]",
    "train_dataset: Output[Dataset]",
    "test_dataset: Output[Dataset]",
    "dataset.path",
    "train_dataset.path",
    "test_dataset.path",
    "model: Output[Model]",
    "model.path",
    "metrics: Output[Metrics]",
    "classification_metrics: Output[ClassificationMetrics]",
    "report: Output[Markdown]",
    "metrics.log_metric(",
    "classification_metrics.log_confusion_matrix(",
    "report.path",
    "importer(",
]


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    materials_dir = lab_materials_dir(LAB_NAME)
    with GradingStep("pipeline.py dichiara e usa correttamente gli artifact") as step:
        content = read_text_file(os.path.join(materials_dir, "pipeline.py"))
        if content is None:
            step.fail(f"File pipeline.py non trovato in {materials_dir}")
        else:
            if "TODO" in content:
                step.add_error("Sono ancora presenti dei TODO non completati")
            for snippet in REQUIRED_SNIPPETS:
                if snippet not in content:
                    step.add_error(f"Non trovato '{snippet}'")

    with GradingStep(
        f"Una run della pipeline '{PIPELINE_NAME}' e' stata completata con successo"
    ) as step:
        workflows = oc_get_json("workflows.argoproj.io", "-n", project)
        if not workflows:
            step.fail("Nessun Argo Workflow trovato nel progetto (nessuna run eseguita)")
        else:
            matching = [
                w for w in workflows.get("items", [])
                if w.get("metadata", {}).get("name", "").startswith(PIPELINE_NAME)
            ]
            if not matching:
                step.fail(f"Nessuna run della pipeline '{PIPELINE_NAME}' trovata")
            elif not any(w.get("status", {}).get("phase") == "Succeeded" for w in matching):
                phases = sorted({w.get("status", {}).get("phase") for w in matching} - {None})
                step.add_error(
                    f"Nessuna run di '{PIPELINE_NAME}' e' completata con successo "
                    f"(stati trovati: {phases})"
                )


if __name__ == "__main__":
    main()
