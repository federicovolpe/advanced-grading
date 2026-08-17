#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise deployments-applications (DO288),
priva di `lab grade` ufficiale (il modulo do288/deployments_applications.py
implementa solo start()/finish()).

do288/deployments_applications.py.start() distribuisce gia' un database
PostgreSQL (`oc new-app postgresql-ephemeral --name=postgres`, poi attende
`deploymentconfig/postgresql`), che genera un Secret "postgresql" con le
chiavi database-name/database-user/database-password valori casuali.

Testo della guida: lo studente crea
`oc new-app --name=expense-service --image=.../ocpdev-expense-service:4.18`,
che fallisce inizialmente perche' l'immagine ha credenziali DB hardcoded
sbagliate (il pod va in CrashLoopBackOff, non riesce a connettersi al
database reale). Il fix esplicito e'
`oc set env deploy/expense-service --from=secret/postgresql`, che inietta le
env var DATABASE_USER/DATABASE_PASSWORD/DATABASE_NAME come valueFrom.
secretKeyRef verso il Secret "postgresql" (chiavi database-user/
database-password/database-name). Poi lo studente espone l'app con
`oc expose svc expense-service`. Il segnale che il fix ha funzionato e' che
il Deployment abbia almeno una replica disponibile (altrimenti resterebbe
in CrashLoopBackOff) e che GET /expenses risponda con un array JSON (prova
che l'app si connette davvero al database).

Uso: deployments-applications.py [nome-progetto]   (default: deployments-applications)
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, http_get, oc_get_json, project_exists

LAB_NAME = "deployments-applications"
DEPLOYMENT = "expense-service"
ROUTE = "expense-service"
SECRET_NAME = "postgresql"
EXPECTED_ENV_TO_KEY = {
    "DATABASE_USER": "database-user",
    "DATABASE_PASSWORD": "database-password",
    "DATABASE_NAME": "database-name",
}


def get_container(deployment):
    containers = (deployment.get("spec") or {}).get("template", {}).get("spec", {}).get("containers", [])
    return containers[0] if containers else None


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    deployment = oc_get_json("deployment", DEPLOYMENT, "-n", project)
    container = get_container(deployment) if deployment else None

    with GradingStep(
        f"Il Deployment '{DEPLOYMENT}' usa le credenziali dal Secret '{SECRET_NAME}'"
    ) as step:
        if container is None:
            step.fail(f"Deployment '{DEPLOYMENT}' non trovato o senza container")
        else:
            env_by_name = {e.get("name"): e for e in container.get("env", []) or []}
            for env_name, expected_key in EXPECTED_ENV_TO_KEY.items():
                entry = env_by_name.get(env_name)
                if entry is None:
                    step.add_error(f"Variabile d'ambiente {env_name} non definita")
                    continue
                secret_ref = (entry.get("valueFrom") or {}).get("secretKeyRef") or {}
                if secret_ref.get("name") != SECRET_NAME:
                    step.add_error(
                        f"{env_name} non proviene dal Secret '{SECRET_NAME}' "
                        f"(secretKeyRef.name={secret_ref.get('name')!r})"
                    )
                elif secret_ref.get("key") != expected_key:
                    step.add_error(
                        f"{env_name}: secretKeyRef.key={secret_ref.get('key')!r}, "
                        f"atteso {expected_key!r}"
                    )

    with GradingStep(f"Il Deployment '{DEPLOYMENT}' ha almeno una replica disponibile") as step:
        if deployment is None:
            step.fail()
        elif (deployment.get("status") or {}).get("availableReplicas", 0) < 1:
            step.add_error(
                f"Nessuna replica disponibile per '{DEPLOYMENT}' (probabile CrashLoopBackOff: "
                "il fix delle credenziali non ha funzionato)"
            )

    with GradingStep(f"L'app '{DEPLOYMENT}' risponde con un array JSON su /expenses") as step:
        route = oc_get_json("route", ROUTE, "-n", project)
        if not route:
            step.fail(f"Route '{ROUTE}' non trovata")
        else:
            host = (route.get("spec") or {}).get("host", "")
            ok, body = http_get(f"http://{host}/expenses")
            if not ok:
                step.fail(f"Nessuna risposta da '{host}/expenses'")
            else:
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    step.fail(f"Risposta non e' JSON valido: {body!r}")
                else:
                    if not isinstance(data, list):
                        step.add_error(
                            f"La risposta non e' un array JSON (tipo: {type(data).__name__})"
                        )


if __name__ == "__main__":
    main()
