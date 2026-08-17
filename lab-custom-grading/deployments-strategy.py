#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise deployments-strategy (DO288), priva
di `lab grade` ufficiale (il modulo do288/deployments_strategy.py implementa
solo start()/finish()).

Testo della guida: lo studente genera un manifest con
`oc new-app --name users-db -e MYSQL_USER=developer -e MYSQL_PASSWORD=redhat
-e MYSQL_DATABASE=users https://git.ocp4.example.com/developer/DO288-apps
--context-dir=apps/deployments-strategy/users-db -o yaml > application.yaml`,
lo applica, scala l'app a 5 repliche, e infine MODIFICA esplicitamente la
strategy del Deployment nel manifest da RollingUpdate (il default generato
da `oc new-app`) a "Recreate", riapplicando il manifest. I due segnali
espliciti richiesti dall'esercizio sono quindi la strategy Recreate e le 5
repliche.

Uso: deployments-strategy.py [nome-progetto]   (default: deployments-strategy)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "deployments-strategy"
DEPLOYMENT = "users-db"
EXPECTED_STRATEGY = "Recreate"
EXPECTED_REPLICAS = 5


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    deployment = oc_get_json("deployment", DEPLOYMENT, "-n", project)
    with GradingStep(f"Il Deployment '{DEPLOYMENT}' usa la strategy '{EXPECTED_STRATEGY}'") as step:
        if deployment is None:
            step.fail(f"Deployment '{DEPLOYMENT}' non trovato")
        else:
            strategy_type = (deployment.get("spec") or {}).get("strategy", {}).get("type")
            if strategy_type != EXPECTED_STRATEGY:
                step.add_error(
                    f"spec.strategy.type={strategy_type!r}, atteso {EXPECTED_STRATEGY!r} "
                    "(la strategy non e' stata modificata nel manifest)"
                )

    with GradingStep(f"Il Deployment '{DEPLOYMENT}' e' scalato a {EXPECTED_REPLICAS} repliche") as step:
        if deployment is None:
            step.fail()
        else:
            replicas = (deployment.get("spec") or {}).get("replicas")
            if replicas != EXPECTED_REPLICAS:
                step.add_error(
                    f"spec.replicas={replicas!r}, atteso {EXPECTED_REPLICAS}"
                )


if __name__ == "__main__":
    main()
