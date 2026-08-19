"""
Grading personalizzato per 'monitoring-bias' (AI0018L - TrustyAI Fairness).

Da testo guida studente (script forniti in ~/course/labs/monitoring-bias/
scripts/): lo studente invia dati di training/reali ai modelli
'demo-loan-nn-onnx-alpha'/'beta' e programma il calcolo periodico dello
Statistical Parity Difference (SPD) con
POST <trustyai>/metrics/group/fairness/spd/request (schedule_spd.sh).

Verifica dal vivo: interroga GET <trustyai>/metrics/group/fairness/spd/requests
(endpoint standard TrustyAI per elencare le richieste di metrica
programmate) e controlla che esista una richiesta per ciascun modello. Non
richiede oc apply/create: legge solo lo stato del servizio TrustyAI gia'
distribuito da `lab start`.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, project_exists, get_route_host, oc_whoami_token, http_get_json_auth

LAB_NAME = "monitoring-bias"
TRUSTYAI_ROUTE_NAME = "trustyai-service"
MODELS = ["demo-loan-nn-onnx-alpha", "demo-loan-nn-onnx-beta"]


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(
        "Il monitoraggio SPD e' programmato per i modelli alpha e beta"
    ) as step:
        host = get_route_host(TRUSTYAI_ROUTE_NAME, project)
        if not host:
            step.fail(f"Route '{TRUSTYAI_ROUTE_NAME}' non trovata")
        else:
            token = oc_whoami_token()
            ok, body = http_get_json_auth(
                f"https://{host}/metrics/group/fairness/spd/requests", token
            )
            if not ok or body is None:
                step.fail("Impossibile interrogare l'endpoint SPD di TrustyAI")
            else:
                scheduled_models = {
                    r.get("request", {}).get("modelId")
                    for r in body.get("requests", []) or []
                }
                missing = [m for m in MODELS if m not in scheduled_models]
                if missing:
                    step.add_error(
                        f"Nessuna richiesta SPD programmata per: {', '.join(missing)}"
                    )


if __name__ == "__main__":
    main()
