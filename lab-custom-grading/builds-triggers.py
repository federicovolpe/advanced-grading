#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise builds-triggers (DO288), priva di
`lab grade` ufficiale (il modulo do288/builds_triggers.py implementa solo
start()/finish()).

Fonte OTTIMA: do288/builds-triggers.test.adoc, uno script di test formale
usato internamente da Red Hat per validare la guida stessa — contiene i
comandi esatti e l'output atteso passo per passo. Riassunto:
- `oc new-app --name hello --image=.../ocpdev-builds-triggers-hello:latest`
  crea Deployment+Service "hello".
- `oc expose service/hello` crea la Route "hello".
- `oc set triggers deploy/hello --from-image=hello:latest -c hello` aggiunge
  un trigger che ridistribuisce il Deployment quando l'ImageStreamTag
  hello:latest cambia.
- `oc tag .../ocpdev-builds-triggers-hello:v2 hello:latest` aggiorna il tag,
  scatenando il trigger: il Deployment si aggiorna automaticamente e l'app
  serve "Hello, world from v2!" invece di "v1!".

Lo stato finale atteso e' quindi: trigger configurato sul Deployment, e la
Route che risponde con il testo della v2 (prova che il trigger ha funzionato
davvero, non solo che e' stato dichiarato).

Uso: builds-triggers.py [nome-progetto]   (default: builds-triggers)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, http_get, oc_get_json, project_exists

LAB_NAME = "builds-triggers"
DEPLOYMENT = "hello"
EXPECTED_BODY = "Hello, world from v2!"


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    deployment = oc_get_json("deployment", DEPLOYMENT, "-n", project)
    with GradingStep(f"Il Deployment '{DEPLOYMENT}' ha un trigger sull'ImageStreamTag hello:latest") as step:
        if not deployment:
            step.fail(f"Deployment '{DEPLOYMENT}' non trovato")
        else:
            annotations = (deployment.get("metadata") or {}).get("annotations") or {}
            triggers_raw = annotations.get("image.openshift.io/triggers", "[]")
            try:
                import json as _json

                triggers = _json.loads(triggers_raw)
            except ValueError:
                triggers = []
            has_trigger = any(
                (t.get("from") or {}).get("kind") == "ImageStreamTag"
                and (t.get("from") or {}).get("name") == "hello:latest"
                for t in triggers
            )
            if not has_trigger:
                step.add_error(
                    "Nessun trigger da ImageStreamTag 'hello:latest' trovato "
                    "nell'annotazione image.openshift.io/triggers"
                )

    with GradingStep("La Route 'hello' serve la versione v2 dell'immagine") as step:
        route = oc_get_json("route", DEPLOYMENT, "-n", project)
        if not route:
            step.fail(f"Route '{DEPLOYMENT}' non trovata")
        else:
            host = (route.get("spec") or {}).get("host", "")
            ok, body = http_get(f"http://{host}")
            if not ok:
                step.fail(f"Nessuna risposta da '{host}'")
            elif EXPECTED_BODY not in body:
                step.add_error(
                    f"La risposta non contiene {EXPECTED_BODY!r} (il trigger non ha "
                    f"ridistribuito l'app dopo il retag a v2, oppure il tag non e' stato "
                    f"aggiornato): risposta ottenuta: {body!r}"
                )


if __name__ == "__main__":
    main()
