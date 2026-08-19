"""
Grading personalizzato per 'workbench-working' (AI0015L - Work in
Workbenches).

Da testo guida studente: lo studente esegue un notebook nel workbench
'model-training' che intenzionalmente esaurisce la memoria (OOM), osserva il
riavvio automatico del workbench, poi corregge il modello e verifica che la
cella non vada piu' in OOM. Questo e' un check dal vivo valido solo PRIMA di
`lab finish` (il progetto/pod spariscono dopo): si verifica che il pod
'model-training' abbia un lastState.terminated.reason=OOMKilled (prova che
l'esperimento OOM e' stato eseguito) E che sia di nuovo in stato Running
(prova che il modello e' stato corretto e il workbench si e' ristabilizzato).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "workbench-working"


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(
        "Il pod 'model-training' ha subito un OOMKilled ed e' di nuovo Running"
    ) as step:
        pods = oc_get_json("pod", "-l", "app=model-training", "-n", project)
        if not pods or not pods.get("items"):
            step.fail("Nessun pod con label app=model-training trovato")
        else:
            pod = pods["items"][0]
            statuses = pod.get("status", {}).get("containerStatuses", []) or []
            oom_found = any(
                (cs.get("lastState", {}).get("terminated", {}) or {}).get("reason")
                == "OOMKilled"
                for cs in statuses
            )
            if not oom_found:
                step.add_error(
                    "Nessun container del pod mostra lastState.terminated.reason=OOMKilled "
                    "(l'esperimento di out-of-memory non risulta eseguito)"
                )
            if pod.get("status", {}).get("phase") != "Running":
                step.add_error(
                    f"Il pod non e' in stato Running (fase attuale: {pod.get('status', {}).get('phase')})"
                )


if __name__ == "__main__":
    main()
