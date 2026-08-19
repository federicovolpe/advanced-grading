"""
Grading personalizzato per 'dspa-experiments' (AI0020L - RHOAI Experiments).

Diversamente dagli altri esercizi dspa-*, pipeline.py qui NON ha TODO: e'
gia' completo (parametro classifier_name configurabile). Il compito dello
studente e' usare la feature "Experiments" della dashboard RHOAI per
lanciare la pipeline 'sentiment' piu' volte con classifier_name diverso
(MultinomialNB vs DecisionTreeClassifier) e confrontare le metriche.

Verificato end-to-end su cluster reale (namespace di test, poi eliminato)
lanciando due run con parametri diversi: entrambe producono un Argo Workflow
'sentiment-<suffisso>'. Il valore di classifier_name usato in ciascuna run
non e' recuperabile in modo affidabile dall'oggetto Workflow (finisce
serializzato dentro la componentSpec compilata, non come parametro
top-level leggibile), quindi si verifica solo che siano state completate
con successo ALMENO due run distinte della pipeline 'sentiment' - coerente
con l'obiettivo dell'esercizio di confrontarne piu' di una.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "dspa-experiments"
PIPELINE_NAME = "sentiment"
MIN_SUCCESSFUL_RUNS = 2


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(
        f"Almeno {MIN_SUCCESSFUL_RUNS} run della pipeline '{PIPELINE_NAME}' "
        "sono state completate con successo"
    ) as step:
        workflows = oc_get_json("workflows.argoproj.io", "-n", project)
        if not workflows:
            step.fail("Nessun Argo Workflow trovato nel progetto (nessuna run eseguita)")
        else:
            succeeded = [
                w for w in workflows.get("items", [])
                if w.get("metadata", {}).get("name", "").startswith(PIPELINE_NAME)
                and w.get("status", {}).get("phase") == "Succeeded"
            ]
            if len(succeeded) < MIN_SUCCESSFUL_RUNS:
                step.add_error(
                    f"Trovate solo {len(succeeded)} run completate con successo "
                    f"di '{PIPELINE_NAME}' (richieste almeno {MIN_SUCCESSFUL_RUNS})"
                )


if __name__ == "__main__":
    main()
