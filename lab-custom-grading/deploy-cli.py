#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise deploy-cli (DO288), priva di
`lab grade` ufficiale (il modulo do288/deploy_cli.py implementa solo
start()/finish()). Da notare (confermato leggendo il modulo ufficiale):
l'esercizio usa DUE progetti OpenShift, "deploy-cli" (__LAB__, creato da
start()) e "odo-deploy-cli" (hardcoded in finish():
`delete_projects_step([LAB, "odo-deploy-cli"])`), quest'ultimo creato dallo
studente con `odo deploy`.

La guida (Cap. 2.4, "Deploying Applications by Using the CLI") chiede:

- in "deploy-cli": `oc new-app --name openshift-dev-deploy-cli-weather
  --image=registry.ocp4.example.com:8443/redhattraining/openshift-dev-deploy-cli-weather:1.0`
  crea Deployment+Service "openshift-dev-deploy-cli-weather" (stesso nome
  anche senza --name, dedotto dall'immagine); poi `oc expose --name=weather
  service/openshift-dev-deploy-cli-weather` crea la Route "weather".
- in "odo-deploy-cli": `odo deploy` da un devfile crea Service, Deployment e
  Route tutti chiamati "weather" (nome fisso del devfile, non scelto dallo
  studente).

In entrambi i progetti l'app risponde a GET /tomorrow con un JSON che
contiene le chiavi "rain_chance" e "weather" (valori non deterministici: si
verifica solo la presenza delle chiavi).

Uso: deploy-cli.py [nome-progetto-oc] [nome-progetto-odo]
     (default: deploy-cli, odo-deploy-cli — il wrapper di fallback invoca
     comunque lo script con un solo argomento, quindi il secondo nome usa
     sempre il default)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, http_get_json, oc_get_json, project_exists

LAB_NAME = "deploy-cli"
ODO_LAB_NAME = "odo-deploy-cli"

ROUTE_NAME = "weather"
WEATHER_PATH = "/tomorrow"
EXPECTED_KEYS = ("rain_chance", "weather")


def check_weather_route(project):
    """Verifica che la Route 'weather' esista e che GET /tomorrow risponda
    con un JSON contenente le chiavi attese. Ritorna la lista di errori."""
    errors = []
    route = oc_get_json("route", ROUTE_NAME, "-n", project)
    if not route:
        errors.append(f"Route '{ROUTE_NAME}' non trovata nel progetto '{project}'")
        return errors

    host = (route.get("spec") or {}).get("host")
    ok, data = http_get_json(f"http://{host}{WEATHER_PATH}")
    if not ok or not isinstance(data, dict):
        errors.append(f"'http://{host}{WEATHER_PATH}' non risponde con un JSON valido")
        return errors

    for key in EXPECTED_KEYS:
        if key not in data:
            errors.append(f"Chiave '{key}' assente nella risposta JSON: {data!r}")

    return errors


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    odo_project = sys.argv[2] if len(sys.argv) > 2 else ODO_LAB_NAME
    print(
        f"🔧 Grading personalizzato per '{LAB_NAME}' "
        f"(progetti: {project}, {odo_project})"
    )

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(
        f"[{project}] La Route '{ROUTE_NAME}' esiste e {WEATHER_PATH} risponde correttamente"
    ) as step:
        for e in check_weather_route(project):
            step.add_error(e)

    with GradingStep(f"Il progetto {odo_project} esiste") as step:
        if not project_exists(odo_project):
            step.fail(f"Progetto '{odo_project}' non trovato")

    with GradingStep(
        f"[{odo_project}] La Route '{ROUTE_NAME}' (creata con 'odo deploy') esiste e "
        f"{WEATHER_PATH} risponde correttamente"
    ) as step:
        for e in check_weather_route(odo_project):
            step.add_error(e)


if __name__ == "__main__":
    main()
