"""
Grading personalizzato per 'monitoring-drift' (AI0018L - TrustyAI Data
Drift).

Da testo guida studente: lo studente carica il dataset di riferimento
(diabetes.csv convertito in formato TrustyAI) e programma il monitoraggio
mean shift con POST <trustyai>/metrics/drift/meanshift/request per il
modello 'diabetes'.

Verifica dal vivo: interroga GET <trustyai>/metrics/drift/meanshift/requests
(schema confermato leggendo l'esempio nella guida: {"requests":[{"id":...,
"request":{"modelId":"diabetes",...}}]}) e controlla che esista una
richiesta per 'diabetes'.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, project_exists, get_route_host, oc_whoami_token, http_get_json_auth

LAB_NAME = "monitoring-drift"
TRUSTYAI_ROUTE_NAME = "trustyai-service"
MODEL_NAME = "diabetes"


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(
        f"Il monitoraggio del data drift (mean shift) e' programmato per '{MODEL_NAME}'"
    ) as step:
        host = get_route_host(TRUSTYAI_ROUTE_NAME, project)
        if not host:
            step.fail(f"Route '{TRUSTYAI_ROUTE_NAME}' non trovata")
        else:
            token = oc_whoami_token()
            ok, body = http_get_json_auth(
                f"https://{host}/metrics/drift/meanshift/requests", token
            )
            if not ok or body is None:
                step.fail("Impossibile interrogare l'endpoint mean shift di TrustyAI")
            else:
                scheduled_models = {
                    r.get("request", {}).get("modelId")
                    for r in body.get("requests", []) or []
                }
                if MODEL_NAME not in scheduled_models:
                    step.add_error(
                        f"Nessuna richiesta mean shift programmata per '{MODEL_NAME}'"
                    )


if __name__ == "__main__":
    main()
