"""
Grading personalizzato per 'dspa-intro' (AI0019L - Configuring a Pipeline
Server).

A differenza di tutti gli altri esercizi dspa-* (dove `create_dspa_step` e'
gia' chiamato da `start()`), qui `lab start` (ai0019l/exercises/
dspa_intro.py) crea SOLO il progetto e la data connection 's3-minio' verso
il bucket 'data-science-pipelines' - senza configurare il pipeline server.
Questo e' l'indizio che il compito dello studente e' proprio configurare la
Data Science Pipeline Application dalla dashboard, usando quella data
connection.

Il nome della risorsa non e' a scelta: il default RHOAI (sia via dashboard
che via rht_labs_rhoai.pipelines.create_dspa_step) e' sempre 'dspa'.
Verificato lo schema status.conditions (type=Ready) applicando una DSPA di
test su un progetto temporaneo, poi eliminato.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists, condition_true

LAB_NAME = "dspa-intro"
DSPA_NAME = "dspa"


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(
        f"Il pipeline server ('{DSPA_NAME}') e' stato configurato ed e' pronto"
    ) as step:
        dspa = oc_get_json("datasciencepipelinesapplication", DSPA_NAME, "-n", project)
        if not dspa:
            step.fail(f"DataSciencePipelinesApplication '{DSPA_NAME}' non trovata")
        elif not condition_true(dspa, "Ready"):
            step.add_error("La DataSciencePipelinesApplication non e' nello stato Ready")


if __name__ == "__main__":
    main()
