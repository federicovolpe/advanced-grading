#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise builds-s2i (DO288), priva di
`lab grade` ufficiale (il modulo do288/builds_s2i.py implementa solo
start()/finish(), __LAB__ = "builds-s2i").

La guida (Cap. 3.2, "Managing Source-to-Image Builds") chiede di creare
un'app S2I chiamata "bonjour" con:
`oc new-app --name bonjour --context-dir labs/builds-s2i/s2i-scripts
httpd:2.4-ubi9~https://git.ocp4.example.com/developer/DO288-apps`
che crea ImageStream+BuildConfig+Deployment+Service "bonjour", poi la
espone con `oc expose svc bonjour` (Route "bonjour"). Gli script S2I
personalizzati della cartella producono una index.html con il testo esatto
"Hello Class! DO288 rocks!!!" e una info.html con la versione di Apache
("Proudly served by Apache HTTP Server version 2.4").

Uso: builds-s2i.py [nome-progetto]   (default: builds-s2i)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, http_get, oc_get_json, project_exists

LAB_NAME = "builds-s2i"
APP_NAME = "bonjour"
EXPECTED_INDEX = "Hello Class! DO288 rocks!!!"
EXPECTED_INFO_SUBSTR = "Proudly served by Apache HTTP Server version 2.4"


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(f"Il BuildConfig '{APP_NAME}' esiste") as step:
        if not oc_get_json("buildconfig", APP_NAME, "-n", project):
            step.fail(f"BuildConfig '{APP_NAME}' non trovato")

    deployment = oc_get_json("deployment", APP_NAME, "-n", project)
    with GradingStep(f"Il Deployment '{APP_NAME}' ha almeno una replica disponibile") as step:
        if not deployment:
            step.fail(f"Deployment '{APP_NAME}' non trovato")
        elif (deployment.get("status") or {}).get("availableReplicas", 0) < 1:
            step.add_error(f"Il Deployment '{APP_NAME}' non ha repliche disponibili")

    route = oc_get_json("route", APP_NAME, "-n", project)
    host = (route.get("spec") or {}).get("host") if route else None
    with GradingStep(f"La Route '{APP_NAME}' esiste") as step:
        if not route:
            step.fail(f"Route '{APP_NAME}' non trovata")

    with GradingStep("GET / risponde con il testo esatto atteso") as step:
        if not host:
            step.fail("Nessuna Route disponibile per il test")
        else:
            ok, body = http_get(f"http://{host}/")
            if not ok:
                step.fail(f"Nessuna risposta da 'http://{host}/'")
            elif body.strip() != EXPECTED_INDEX:
                step.add_error(f"Testo ottenuto {body.strip()!r}, atteso {EXPECTED_INDEX!r}")

    with GradingStep("GET /info.html contiene la versione di Apache attesa") as step:
        if not host:
            step.fail("Nessuna Route disponibile per il test")
        else:
            ok, body = http_get(f"http://{host}/info.html")
            if not ok:
                step.fail(f"Nessuna risposta da 'http://{host}/info.html'")
            elif EXPECTED_INFO_SUBSTR not in body:
                step.add_error(
                    f"Il testo atteso {EXPECTED_INFO_SUBSTR!r} non e' presente nella "
                    f"risposta: {body!r}"
                )


if __name__ == "__main__":
    main()
