"""
Grading personalizzato per 'dspa-containers' (AI0020L - Custom Container
Components).

Stesso schema di 'dspa-kubeflow' (vedi quello script per i dettagli sulla
verifica via Argo Workflow, validata end-to-end su cluster reale). A
differenza degli altri esercizi dspa-*, qui `lab start` compila e importa
GIA' la pipeline di partenza (rotta: il componente process_data usa
BASE_IMAGE, che non contiene il modulo locale 'utils.py', quindi fallisce a
runtime - vedi ai0020l/exercises/dspa_containers.py). Il compito dello
studente e' costruire l'immagine custom (Containerfile fornito), farne il
push, e modificare pipeline.py perche' process_data usi CONTAINER_IMAGE
invece di BASE_IMAGE (confrontato con
materials/solutions/dspa-containers/pipeline.py), poi ricompilare/ricaricare
ed eseguire la pipeline 'sentiment-analysis' con successo.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists, lab_materials_dir, read_text_file

LAB_NAME = "dspa-containers"
PIPELINE_NAME = "sentiment-analysis"


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    materials_dir = lab_materials_dir(LAB_NAME)
    with GradingStep("process_data usa l'immagine custom CONTAINER_IMAGE") as step:
        content = read_text_file(os.path.join(materials_dir, "pipeline.py"))
        if content is None:
            step.fail(f"File pipeline.py non trovato in {materials_dir}")
        else:
            if "CONTAINER_IMAGE" not in content:
                step.add_error("Non e' stata definita la variabile CONTAINER_IMAGE")
            if "@dsl.component(base_image=CONTAINER_IMAGE)" not in content:
                step.add_error(
                    "Il componente process_data non usa @dsl.component(base_image=CONTAINER_IMAGE)"
                )

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
                    f"(stati trovati: {phases}) - probabile immagine non ancora corretta"
                )


if __name__ == "__main__":
    main()
