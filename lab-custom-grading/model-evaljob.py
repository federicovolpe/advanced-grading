"""
Grading personalizzato per 'model-evaljob' (AI0021L - TrustyAI LMEval).

`lab start` (ai0021l/exercises/model_evaljob.py) distribuisce gia' lui il
modello 'granite' (ServingRuntime + InferenceService, attende
condition=Ready) e abilita LMEval sulla dashboard. Il compito dello studente
e' applicare materials/labs/model-evaljob/eval-1.yaml (fornito identico,
nessun TODO da completare: e' la specifica stessa) per lanciare una
LMEvalJob 'eval-1' sul task 'openbookqa' e verificare che completi.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "model-evaljob"
LMEVALJOB_NAME = "eval-1"


def _is_complete(lmevaljob):
    """Vero solo se lo stato e' 'Complete' con esito 'Succeeded' (schema
    verificato con `oc explain lmevaljob.status`: state/reason sono due
    campi stringa distinti, non conditions)."""
    status = lmevaljob.get("status", {}) or {}
    return status.get("state") == "Complete" and status.get("reason") == "Succeeded"


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(
        f"La LMEvalJob '{LMEVALJOB_NAME}' e' stata creata e completata"
    ) as step:
        job = oc_get_json("lmevaljob", LMEVALJOB_NAME, "-n", project)
        if not job:
            step.fail(f"LMEvalJob '{LMEVALJOB_NAME}' non trovata")
        else:
            model_args = {
                a.get("name"): a.get("value")
                for a in (job.get("spec", {}).get("modelArgs") or [])
            }
            if model_args.get("model") != "granite":
                step.add_error(
                    f"modelArgs.model non punta a 'granite' (trovato: {model_args.get('model')})"
                )
            tasks = job.get("spec", {}).get("taskList", {}).get("taskNames", [])
            if "openbookqa" not in tasks:
                step.add_error(f"taskList non contiene 'openbookqa' (trovato: {tasks})")
            if not _is_complete(job):
                status = job.get("status", {})
                step.add_error(
                    f"La LMEvalJob non e' completata con successo "
                    f"(state={status.get('state', '?')}, reason={status.get('reason', '?')})"
                )


if __name__ == "__main__":
    main()
