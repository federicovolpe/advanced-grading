#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise architecture-setup (DO288), priva di
`lab grade` ufficiale (il modulo do288/architecture_setup.py implementa solo
start()/finish()).

La specifica viene dal testo della guida (Cap. 1.4, "Setting up the Developer
Environment"): l'unico passo che lascia uno stato verificabile sul cluster e'
il punto 4, che chiede di validare la configurazione di odo distribuendo
l'app di esempio "hello-flask" con `odo deploy` da
~/DO288/labs/architecture-setup/hello-flask. Gli altri passi (login GitLab,
generazione di una encrypted password per il registry, apertura di VSCodium)
non lasciano nessuna risorsa OpenShift verificabile.

Uso: architecture-setup.py [nome-progetto]   (default: architecture-setup)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, http_get, oc_get_json, project_exists

LAB_NAME = "architecture-setup"
DEPLOYMENT = "hello-flask"
EXPECTED_BODY = "Hello World!"


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    deployment = oc_get_json("deployment", DEPLOYMENT, "-n", project)
    with GradingStep(f"Il Deployment '{DEPLOYMENT}' e' stato distribuito con odo") as step:
        if not deployment:
            step.fail(f"Deployment '{DEPLOYMENT}' non trovato")
        elif (deployment.get("status") or {}).get("availableReplicas", 0) < 1:
            step.add_error(f"Il Deployment '{DEPLOYMENT}' non ha replica disponibili")

    with GradingStep(f"L'app '{DEPLOYMENT}' risponde correttamente tramite la Route") as step:
        route = oc_get_json("route", DEPLOYMENT, "-n", project)
        if not route:
            step.fail(f"Route '{DEPLOYMENT}' non trovata")
        else:
            host = (route.get("spec") or {}).get("host", "")
            ok, body = http_get(f"http://{host}")
            if not ok or EXPECTED_BODY not in body:
                step.add_error(
                    f"La risposta da '{host}' non contiene il testo atteso ({EXPECTED_BODY!r})"
                )


if __name__ == "__main__":
    main()
