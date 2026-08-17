#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise images-ubi (DO288), priva di
`lab grade` ufficiale (il modulo do288/images_ubi.py, classe DeployConsole,
implementa solo start()/finish()).

Testo della guida: lo studente builda un'immagine Node.js a partire da un
Containerfile fornito (poi corretto per user/permessi non-root e porta di
ascolto), la pusha su
registry.ocp4.example.com:8443/developer/images-ubi-greetings (tag finale
1.0.1, dopo le correzioni), poi la distribuisce con
`oc new-app --name greetings --image=.../images-ubi-greetings:1.0.1` e la
espone con `oc expose svc/greetings`. Il segnale piu' significativo che i
problemi di permessi/porta siano stati risolti e' che il Deployment abbia
almeno una replica disponibile (altrimenti il pod resterebbe in
CrashLoopBackOff per l'utente non autorizzato o la porta sbagliata). Non
verifichiamo il tag esatto dell'immagine (solo lo studente corregge il
Containerfile passo dopo passo, il tag intermedio non e' garantito uguale
per tutti), ma la porzione di nome 'images-ubi-greetings'.

L'endpoint dell'app risponde con un JSON {"message": "<saluto casuale>"} in
una lingua diversa a ogni richiesta: verifichiamo solo che la chiave
'message' sia presente e non vuota, non il valore esatto.

Uso: images-ubi.py [nome-progetto]   (default: images-ubi)
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, http_get, oc_get_json, project_exists

LAB_NAME = "images-ubi"
DEPLOYMENT = "greetings"
EXPECTED_IMAGE_SNIPPET = "images-ubi-greetings"


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    deployment = oc_get_json("deployment", DEPLOYMENT, "-n", project)
    with GradingStep(
        f"Il Deployment '{DEPLOYMENT}' usa l'immagine {EXPECTED_IMAGE_SNIPPET} ed e' disponibile"
    ) as step:
        if deployment is None:
            step.fail(f"Deployment '{DEPLOYMENT}' non trovato")
        else:
            containers = deployment["spec"]["template"]["spec"].get("containers", [])
            images = [c.get("image", "") for c in containers]
            if not any(EXPECTED_IMAGE_SNIPPET in img for img in images):
                step.add_error(
                    f"Nessun container usa un'immagine con '{EXPECTED_IMAGE_SNIPPET}' "
                    f"nel nome (immagini trovate: {images})"
                )
            available = (deployment.get("status") or {}).get("availableReplicas", 0)
            if available < 1:
                step.add_error(
                    "Nessuna replica disponibile: il pod non e' Running/Ready "
                    "(probabile CrashLoopBackOff per permessi o porta non corretti "
                    "nel Containerfile)"
                )

    with GradingStep(f"L'app '{DEPLOYMENT}' risponde con un JSON valido contenente 'message'") as step:
        route = oc_get_json("route", DEPLOYMENT, "-n", project)
        if not route:
            step.fail(f"Route '{DEPLOYMENT}' non trovata")
        else:
            host = (route.get("spec") or {}).get("host", "")
            ok, body = http_get(f"http://{host}")
            if not ok:
                step.fail(f"Nessuna risposta da '{host}'")
            else:
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    step.fail(f"Risposta non e' JSON valido: {body!r}")
                else:
                    if not data.get("message"):
                        step.add_error(
                            f"Chiave 'message' assente o vuota nella risposta: {data!r}"
                        )


if __name__ == "__main__":
    main()
