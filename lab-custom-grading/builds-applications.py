#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise builds-applications (DO288), priva
di `lab grade` ufficiale (il modulo do288/builds_applications.py implementa
solo start()/finish()).

Testo della guida: lo studente crea l'app con
`oc new-app --name vertx-site --build-env
MAVEN_MIRROR_URL=http://nexus-infra.apps.ocp4.example.com/repository/java
--env JAVA_APP_JAR=vertx-site-1.0.0-SNAPSHOT-fat.jar -i
redhat-openjdk18-openshift:1.8 --context-dir apps/builds-applications/vertx-site
https://git.ocp4.example.com/developer/DO288-apps`. Il primo build fallisce
(o comunque non scarica le dipendenze Maven) perche' l'URL del mirror
inizialmente NON include il path "/repository/"; il fix esplicito richiesto
dalla guida e' correggere il BuildConfig ($MAVEN_MIRROR_URL deve includere
"/repository/") e poi modificare il codice applicativo per passare dalla
v1.0 (col bug) alla v2.0, rebuildare e riverificare la Route.

Lo stato finale atteso e' quindi duplice: 1) il BuildConfig ha
MAVEN_MIRROR_URL corretto (contiene "/repository/"); 2) l'app rebuildata
risponde con il testo aggiornato "Vert.x v2.0" (prova che il rebuild con il
fix del codice e' stato completato davvero, non solo dichiarato nel
BuildConfig).

Uso: builds-applications.py [nome-progetto]   (default: builds-applications)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, http_get, oc_get_json, project_exists

LAB_NAME = "builds-applications"
BUILDCONFIG = "vertx-site"
DEPLOYMENT = "vertx-site"
ROUTE = "vertx-site"
MIRROR_ENV = "MAVEN_MIRROR_URL"
EXPECTED_MIRROR_SNIPPET = "/repository/"
EXPECTED_BODY = "Vert.x v2.0"


def strategy_env(buildconfig):
    """Ritorna la lista degli EnvVar della build strategy, sia che sia
    source (S2I, il caso di questo esercizio) sia docker -- per robustezza."""
    strategy = (buildconfig.get("spec") or {}).get("strategy") or {}
    for key in ("sourceStrategy", "dockerStrategy", "customStrategy"):
        if key in strategy:
            return strategy[key].get("env", []) or []
    return []


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    buildconfig = oc_get_json("buildconfig", BUILDCONFIG, "-n", project)
    with GradingStep(
        f"Il BuildConfig '{BUILDCONFIG}' ha {MIRROR_ENV} corretto (con '{EXPECTED_MIRROR_SNIPPET}')"
    ) as step:
        if buildconfig is None:
            step.fail(f"BuildConfig '{BUILDCONFIG}' non trovato")
        else:
            env_map = {e.get("name"): e.get("value", "") for e in strategy_env(buildconfig)}
            value = env_map.get(MIRROR_ENV)
            if value is None:
                step.add_error(f"Variabile {MIRROR_ENV} non definita nella build strategy")
            elif EXPECTED_MIRROR_SNIPPET not in value:
                step.add_error(
                    f"{MIRROR_ENV}={value!r} non contiene '{EXPECTED_MIRROR_SNIPPET}': "
                    "il fix dell'URL Maven non e' stato applicato"
                )

    deployment = oc_get_json("deployment", DEPLOYMENT, "-n", project)
    with GradingStep(f"Il Deployment '{DEPLOYMENT}' ha almeno una replica disponibile") as step:
        if deployment is None:
            step.fail(f"Deployment '{DEPLOYMENT}' non trovato")
        elif (deployment.get("status") or {}).get("availableReplicas", 0) < 1:
            step.add_error(f"Il Deployment '{DEPLOYMENT}' non ha replica disponibili")

    with GradingStep(f"L'app rebuildata risponde con il testo aggiornato ({EXPECTED_BODY!r})") as step:
        route = oc_get_json("route", ROUTE, "-n", project)
        if not route:
            step.fail(f"Route '{ROUTE}' non trovata")
        else:
            host = (route.get("spec") or {}).get("host", "")
            ok, body = http_get(f"http://{host}")
            if not ok:
                step.fail(f"Nessuna risposta da '{host}'")
            elif EXPECTED_BODY not in body:
                step.add_error(
                    f"La risposta non contiene {EXPECTED_BODY!r} (rebuild con il fix del "
                    f"codice non completato?): risposta ottenuta: {body!r}"
                )


if __name__ == "__main__":
    main()
