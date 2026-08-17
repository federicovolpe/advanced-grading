#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise images-registry (DO288), priva di
`lab grade` ufficiale (il modulo do288/images_registry.py implementa solo
start()/finish(), __LAB__ = "images-registry").

La guida (Cap. 3.3, "Managing Container Images by Using an External
Registry") chiede di:
1. creare un secret Docker-registry "registry-credentials" con le
   credenziali di un robot account del registry esterno
   (registry.ocp4.example.com:8443) — le credenziali sono generate
   dinamicamente dal robot account, quindi non note/verificabili in
   anticipo: si controlla solo che il secret esista e sia del tipo
   corretto, non il suo contenuto;
2. collegarlo al service account "default" per il pull:
   `oc secrets link default registry-credentials --for=pull`;
3. creare `oc create deployment hello-world-nginx
   --image=registry.ocp4.example.com:8443/redhattraining/hello-world-nginx:latest`.

Il segnale definitivo che l'autenticazione al registry funziona davvero e'
che il Deployment "hello-world-nginx" abbia repliche disponibili: senza
credenziali valide collegate al SA "default", il pod resterebbe bloccato in
ImagePullBackOff.

Uso: images-registry.py [nome-progetto]   (default: images-registry)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "images-registry"
SECRET_NAME = "registry-credentials"
SECRET_TYPE = "kubernetes.io/dockerconfigjson"
SERVICE_ACCOUNT = "default"
DEPLOYMENT_NAME = "hello-world-nginx"


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(f"Il Secret '{SECRET_NAME}' esiste ed e' di tipo {SECRET_TYPE}") as step:
        secret = oc_get_json("secret", SECRET_NAME, "-n", project)
        if not secret:
            step.fail(f"Secret '{SECRET_NAME}' non trovato")
        elif secret.get("type") != SECRET_TYPE:
            step.add_error(f"Tipo del secret: {secret.get('type')!r}, atteso {SECRET_TYPE!r}")

    with GradingStep(
        f"Il ServiceAccount '{SERVICE_ACCOUNT}' ha collegato il secret '{SECRET_NAME}' per il pull"
    ) as step:
        sa = oc_get_json("sa", SERVICE_ACCOUNT, "-n", project)
        if not sa:
            step.fail(f"ServiceAccount '{SERVICE_ACCOUNT}' non trovato")
        else:
            names = [s.get("name", "") for s in sa.get("secrets", []) or []]
            # `oc secrets link` mantiene il nome esatto; per sicurezza si
            # accetta anche un eventuale suffisso generato da OpenShift.
            if SECRET_NAME not in names and not any(n.startswith(SECRET_NAME) for n in names):
                step.add_error(
                    f"Nessun secret '{SECRET_NAME}' (o con prefisso corrispondente) "
                    f"trovato in .secrets del ServiceAccount (trovati: {names})"
                )

    deployment = oc_get_json("deployment", DEPLOYMENT_NAME, "-n", project)
    with GradingStep(
        f"Il Deployment '{DEPLOYMENT_NAME}' ha repliche disponibili "
        "(prova che il pull dell'immagine autenticata ha funzionato)"
    ) as step:
        if not deployment:
            step.fail(f"Deployment '{DEPLOYMENT_NAME}' non trovato")
        elif (deployment.get("status") or {}).get("availableReplicas", 0) < 1:
            step.add_error(
                f"Il Deployment '{DEPLOYMENT_NAME}' non ha repliche disponibili "
                "(controllare eventuale ImagePullBackOff)"
            )


if __name__ == "__main__":
    main()
