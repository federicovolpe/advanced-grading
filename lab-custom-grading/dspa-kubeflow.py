"""
Grading personalizzato per 'dspa-kubeflow' (AI0019L - Kubeflow Pipelines).

`lab start` (ai0019l/exercises/dspa_kubeflow.py) crea gia' lui il progetto e
la DataSciencePipelinesApplication (DSPA, storage MariaDB). Il compito dello
studente e' completare i TODO in pipeline.py (componenti + funzione
pipeline(), confrontati con materials/solutions/dspa-kubeflow/pipeline.py per
la specifica esatta), compilarla e importarla/eseguirla dalla dashboard
RHOAI.

Verificato end-to-end su cluster reale (namespace di test, poi eliminato):
KFP v2 su OpenShift AI esegue le run tramite Argo Workflow indipendentemente
dal pipeline_store (qui 'database'), quindi la run completata resta visibile
via `oc get workflows.argoproj.io` anche se Pipeline/PipelineVersion non
sono CR native. Il nome del Workflow e' sempre <nome-pipeline>-<suffisso>,
dove <nome-pipeline> e' quello passato a @dsl.pipeline(name=...) (qui
'sentiment-analysis').
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists, lab_materials_dir, read_text_file

LAB_NAME = "dspa-kubeflow"
PIPELINE_NAME = "sentiment-analysis"


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    materials_dir = lab_materials_dir(LAB_NAME)
    with GradingStep("pipeline.py definisce componenti e pipeline completi") as step:
        content = read_text_file(os.path.join(materials_dir, "pipeline.py"))
        if content is None:
            step.fail(f"File pipeline.py non trovato in {materials_dir}")
        else:
            if "TODO" in content:
                step.add_error("Sono ancora presenti dei TODO non completati")
            for marker in ("@dsl.component", "@dsl.pipeline", "compiler.Compiler().compile("):
                if marker not in content:
                    step.add_error(f"Non trovato '{marker}'")

    with GradingStep(
        f"Una run della pipeline '{PIPELINE_NAME}' e' stata completata con successo"
    ) as step:
        workflows = oc_get_json("workflows.argoproj.io", "-n", project)
        if not workflows:
            step.fail("Nessun Argo Workflow trovato nel progetto (nessuna run eseguita)")
        else:
            items = workflows.get("items", [])
            matching = [
                w for w in items
                if w.get("metadata", {}).get("name", "").startswith(PIPELINE_NAME)
            ]
            if not matching:
                step.fail(f"Nessuna run della pipeline '{PIPELINE_NAME}' trovata")
            elif not any(w.get("status", {}).get("phase") == "Succeeded" for w in matching):
                phases = {w.get("status", {}).get("phase") for w in matching}
                step.add_error(
                    f"Nessuna run di '{PIPELINE_NAME}' e' completata con successo "
                    f"(stati trovati: {sorted(p for p in phases if p)})"
                )


if __name__ == "__main__":
    main()
