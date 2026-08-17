#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise deploy-introduction (DO288), priva di
`lab grade` ufficiale (il modulo do288/deploy_introduction.py implementa solo
start()/finish(), __LAB__ = "deploy-introduction").

start() applica gia' un manifest fornito (sample-node-app.yaml) che crea il
Deployment "node-server" (service sulla porta 4000, route "node-server" che
espone 80->4000): lo studente non crea nessuna risorsa nuova durante
l'esercizio. La guida ufficiale (Cap. 2.2 "Navigating the Web Console",
punto 1.7) chiede l'UNICA azione che modifica lo stato del cluster:
"Increase the number of replicas to three" tramite la console web.

Si verifica quindi solo che lo studente abbia aumentato le replicas del
Deployment "node-server" a 3: si controlla spec.replicas (l'intento
dichiarato dello studente), non status.availableReplicas, perche' il
rollout potrebbe non essere ancora completo al momento del grading (il
monitor grafico chiama questo script ogni 30s mentre lo studente lavora, e
non deve dare FAIL solo perche' i pod nuovi non sono ancora Ready).

Uso: deploy-introduction.py [nome-progetto]   (default: deploy-introduction)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "deploy-introduction"
DEPLOYMENT = "node-server"
EXPECTED_REPLICAS = 3


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    deployment = oc_get_json("deployment", DEPLOYMENT, "-n", project)
    with GradingStep(
        f"Il Deployment '{DEPLOYMENT}' e' stato scalato a {EXPECTED_REPLICAS} replicas"
    ) as step:
        if not deployment:
            step.fail(f"Deployment '{DEPLOYMENT}' non trovato")
        else:
            replicas = (deployment.get("spec") or {}).get("replicas", 0)
            if replicas < EXPECTED_REPLICAS:
                step.add_error(
                    f"spec.replicas e' {replicas}, atteso >= {EXPECTED_REPLICAS} "
                    "(aumentare le repliche dalla console web, Cap. 2.2 punto 1.7)"
                )


if __name__ == "__main__":
    main()
