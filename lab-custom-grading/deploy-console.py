#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise deploy-console (DO288), priva di
`lab grade` ufficiale (il modulo do288/deploy_console.py implementa solo
start()/finish(), __LAB__ = "deploy-console").

La guida (Cap. 2.3, "Deploying Applications by Using the Red Hat OpenShift
Web Console") chiede di distribuire due applicazioni dalla console web, nel
progetto "deploy-console":

- "hello-world": app PHP importata da Git (repo DO288-apps, context dir
  apps/deploy-console/php-helloworld), porta target 8080, con Route creata
  dal wizard. Risponde con un testo che contiene "Hello, World!".
- "todo-list": app Node.js da immagine
  registry.ocp4.example.com:8443/redhattraining/openshift-dev-deploy-console-todo-list,
  porta target 3000, con Route creata dal wizard. Espone un endpoint REST
  /todos (GET/POST) che risponde con un array JSON.

Il wizard "Add" della console crea Deployment+Service(+Route) con lo stesso
nome dato all'applicazione: qui si assume quindi che Deployment e Route si
chiamino "hello-world" e "todo-list" rispettivamente (nomi scelti dallo
studente seguendo la guida, non generati automaticamente dalla console).
Non si verifica il contenuto di eventuali todo creati con una POST di test:
basta che l'endpoint risponda con una lista JSON valida, anche vuota.

Uso: deploy-console.py [nome-progetto]   (default: deploy-console)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, http_get, http_get_json, oc_get_json, project_exists

LAB_NAME = "deploy-console"

HELLO_NAME = "hello-world"
HELLO_TEXT = "Hello, World!"

TODO_NAME = "todo-list"
TODO_PATH = "/todos"


def check_deployment_and_route(project, name):
    """Verifica che il Deployment (disponibile) e la Route esistano.
    Ritorna (host, lista-errori); host e' None se manca qualcosa."""
    errors = []
    deployment = oc_get_json("deployment", name, "-n", project)
    if not deployment:
        errors.append(f"Deployment '{name}' non trovato")
    elif (deployment.get("status") or {}).get("availableReplicas", 0) < 1:
        errors.append(f"Il Deployment '{name}' non ha repliche disponibili")

    route = oc_get_json("route", name, "-n", project)
    host = None
    if not route:
        errors.append(f"Route '{name}' non trovata")
    else:
        host = (route.get("spec") or {}).get("host")

    return host, errors


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(
        f"L'app '{HELLO_NAME}' e' distribuita e la Route risponde con {HELLO_TEXT!r}"
    ) as step:
        host, errors = check_deployment_and_route(project, HELLO_NAME)
        for e in errors:
            step.add_error(e)
        if host:
            ok, body = http_get(f"http://{host}/")
            if not ok:
                step.add_error(f"Nessuna risposta HTTP da '{host}'")
            elif HELLO_TEXT not in body:
                step.add_error(
                    f"La risposta non contiene {HELLO_TEXT!r} (risposta: {body!r})"
                )

    with GradingStep(
        f"L'app '{TODO_NAME}' e' distribuita e {TODO_PATH} risponde con una lista JSON"
    ) as step:
        host, errors = check_deployment_and_route(project, TODO_NAME)
        for e in errors:
            step.add_error(e)
        if host:
            ok, data = http_get_json(f"http://{host}{TODO_PATH}")
            if not ok:
                step.add_error(
                    f"Nessuna risposta JSON valida da 'http://{host}{TODO_PATH}'"
                )
            elif not isinstance(data, list):
                step.add_error(
                    f"La risposta di {TODO_PATH} deve essere una lista JSON "
                    f"(trovato: {type(data).__name__})"
                )


if __name__ == "__main__":
    main()
