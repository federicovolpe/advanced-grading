"""
Grading personalizzato per 'dspa-elyra' (AI0019L - Creating Pipelines with
Elyra).

Da testo guida studente: lo studente costruisce nell'editor visuale Elyra
la pipeline 'issues_prediction' (3 nodi: data_ingestion.py,
data_preprocessing.py, data_training_and_forecasting.py) e la esegue dalla
dashboard RHOAI (Run Pipeline -> pipeline name 'issues_prediction').

Come per gli esercizi dspa-* basati su KFP, RHOAI esegue le pipeline Elyra
tramite Argo Workflow (confermato dalla guida: "RHOAI uses Argo Workflows
to run the pipeline as a Workflow"). Il nome del Workflow generato da Elyra
segue la stessa convenzione <nome-pipeline>-<suffisso>, ma Elyra normalizza
gli underscore in trattini per i nomi delle risorse Kubernetes: si accetta
quindi sia 'issues_prediction' che 'issues-prediction' come prefisso.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "dspa-elyra"
PIPELINE_NAME_VARIANTS = ("issues_prediction", "issues-prediction")


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(
        "Una run della pipeline Elyra 'issues_prediction' e' stata completata con successo"
    ) as step:
        workflows = oc_get_json("workflows.argoproj.io", "-n", project)
        if not workflows:
            step.fail("Nessun Argo Workflow trovato nel progetto (nessuna run eseguita)")
        else:
            matching = [
                w for w in workflows.get("items", [])
                if w.get("metadata", {}).get("name", "").startswith(PIPELINE_NAME_VARIANTS)
            ]
            if not matching:
                step.fail("Nessuna run della pipeline 'issues_prediction' trovata")
            elif not any(w.get("status", {}).get("phase") == "Succeeded" for w in matching):
                phases = sorted({w.get("status", {}).get("phase") for w in matching} - {None})
                step.add_error(
                    f"Nessuna run e' completata con successo (stati trovati: {phases})"
                )


if __name__ == "__main__":
    main()
