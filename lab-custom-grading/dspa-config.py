"""
Grading personalizzato per 'dspa-config' (AI0020L - kfp-kubernetes config).

Stesso schema di 'dspa-kubeflow' (vedi quello script per i dettagli sulla
verifica via Argo Workflow, validata end-to-end su cluster reale): `lab
start` crea gia' progetto/bucket MinIO/DSPA/Secret 'db-credentials'/venv, lo
studente completa i TODO in pipeline.py (iniezione del secret come env,
disabilitazione della cache, richieste di risorse - confrontati con
materials/solutions/dspa-config/pipeline.py) e importa/esegue la pipeline
'dspa-config-pipeline' dalla dashboard RHOAI.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists, lab_materials_dir, read_text_file

LAB_NAME = "dspa-config"
PIPELINE_NAME = "dspa-config-pipeline"

REQUIRED_SNIPPETS = [
    'secret_name="db-credentials"',
    '"username": "DB_USER"',
    '"password": "DB_PASSWORD"',
    "load_task.set_caching_options(False)",
    'train_task.set_memory_request("512Mi")',
    'train_task.set_cpu_request("250m")',
]


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    materials_dir = lab_materials_dir(LAB_NAME)
    with GradingStep("pipeline.py inietta il secret e configura le risorse") as step:
        content = read_text_file(os.path.join(materials_dir, "pipeline.py"))
        if content is None:
            step.fail(f"File pipeline.py non trovato in {materials_dir}")
        else:
            # NB: il docstring del file menziona "TODO" anche a soluzione
            # completata (descrive cosa faceva l'esercizio), quindi non
            # possiamo usare "TODO" in content come indicatore: si verificano
            # solo gli snippet di codice specifici richiesti.
            if content.count("kubernetes.use_secret_as_env(") < 2:
                step.add_error(
                    "Servono due chiamate a kubernetes.use_secret_as_env() "
                    "(una per DB_USER, una per DB_PASSWORD)"
                )
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
