#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise openshift-multipod, sprovvista di
`lab grade` ufficiale (la classe OpenshiftMultipod nel pacchetto do188
implementa solo start()/finish(), non grade()).

Il modulo ufficiale (do188/openshift-multipod.py) usa
`project = "ocp-multipod"` (commento: "oc cannot create openshift-
projects"), diverso dal nome esercizio __LAB__ = "openshift-multipod".

Non c'e' materials/labs per questo esercizio (e' interamente basato su
comandi `oc` imperativi che lo studente digita, senza manifest di partenza):
l'unico file in materials/solutions/openshift-multipod/ e' postgres.yaml, che
conferma immagine/porta/env del database (Cap. 8.4). Per gitea (nome
Deployment/immagine/porta) e per Service/Route ci si basa sul manuale
studente ufficiale, gia' confermato dall'utente, e sui default di
`oc create deployment` (label app=<nome> su pod/matchLabels) usati dalla
guida per questi comandi.

Stato finale atteso a `lab finish`:
- Deployment "gitea" (immagine registry.ocp4.example.com:8443/redhattraining/
  podman-gitea:latest, porta container 3030 — confermata da EXPOSE
  ${GITEA_PORT}=3030 nel Containerfile del corso) con pod Running.
- Deployment "gitea-postgres" (immagine registry.ocp4.example.com:8443/
  rhel9/postgresql-13:1, porta container 5432, env POSTGRESQL_USER=gitea,
  POSTGRESQL_PASSWORD=gitea, POSTGRESQL_DATABASE=gitea — da postgres.yaml)
  con pod Running.
- Service "gitea-postgres" esposto sulla porta 5432.
- Service "gitea" esposto.
- Route "gitea" esposta, host nel formato "gitea-<project>.apps.ocp4.example.com"
  (dipende dal nome del progetto reale), porta 3030.

Uso: openshift-multipod.py [nome-progetto]   (default: ocp-multipod, nome
REALE del progetto usato dal modulo ufficiale, diverso dal nome esercizio)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "openshift-multipod"
PROJECT = "ocp-multipod"

GITEA_DEPLOYMENT = "gitea"
GITEA_IMAGE_PREFIX = "registry.ocp4.example.com:8443/redhattraining/podman-gitea"
GITEA_PORT = 3030

POSTGRES_DEPLOYMENT = "gitea-postgres"
POSTGRES_IMAGE_PREFIX = "registry.ocp4.example.com:8443/rhel9/postgresql-13"
POSTGRES_PORT = 5432
POSTGRES_ENV = {
    "POSTGRESQL_USER": "gitea",
    "POSTGRESQL_PASSWORD": "gitea",
    "POSTGRESQL_DATABASE": "gitea",
}


def _deployment_container(deployment):
    """Ritorna il primo container del template del Deployment, o {}."""
    containers = (
        ((deployment.get("spec") or {}).get("template") or {}).get("spec") or {}
    ).get("containers") or []
    return containers[0] if containers else {}


def _container_port(container, port):
    """True se il container espone quella containerPort."""
    return any(p.get("containerPort") == port for p in container.get("ports") or [])


def _pod_running_for(project, label_selector):
    """True se almeno un pod che matcha il selector e' in stato Running."""
    data = oc_get_json("pods", "-n", project, "-l", label_selector)
    if not data:
        return False
    return any(
        (pod.get("status") or {}).get("phase") == "Running"
        for pod in data.get("items", [])
    )


def _check_deployment(step, project, name, image_prefix, port, env_expected=None):
    deployment = oc_get_json("deployment", name, "-n", project)
    if not deployment:
        step.fail(f"Deployment '{name}' non trovato")
        return

    container = _deployment_container(deployment)
    image = container.get("image", "")
    if not image.startswith(image_prefix):
        step.add_error(f"Immagine del Deployment '{name}' errata: {image!r}")

    if not _container_port(container, port):
        step.add_error(f"Il Deployment '{name}' non espone la containerPort {port}")

    if env_expected:
        env = {e.get("name"): e.get("value") for e in container.get("env") or []}
        for key, value in env_expected.items():
            if env.get(key) != value:
                step.add_error(f"Env var {key} errata (trovata: {env.get(key)!r})")

    if not _pod_running_for(project, f"app={name}"):
        step.add_error(f"Nessun pod Running per il Deployment '{name}' (label app={name})")


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else PROJECT
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(
        f"Il Deployment '{GITEA_DEPLOYMENT}' e' configurato correttamente e in esecuzione"
    ) as step:
        _check_deployment(step, project, GITEA_DEPLOYMENT, GITEA_IMAGE_PREFIX, GITEA_PORT)

    with GradingStep(
        f"Il Deployment '{POSTGRES_DEPLOYMENT}' e' configurato correttamente e in esecuzione"
    ) as step:
        _check_deployment(
            step, project, POSTGRES_DEPLOYMENT, POSTGRES_IMAGE_PREFIX, POSTGRES_PORT, POSTGRES_ENV
        )

    with GradingStep(f"Il Service '{POSTGRES_DEPLOYMENT}' espone la porta {POSTGRES_PORT}") as step:
        svc = oc_get_json("service", POSTGRES_DEPLOYMENT, "-n", project)
        if not svc:
            step.fail(f"Service '{POSTGRES_DEPLOYMENT}' non trovato")
        else:
            ports = (svc.get("spec") or {}).get("ports") or []
            if not any(p.get("port") == POSTGRES_PORT for p in ports):
                step.add_error(f"Nessuna porta {POSTGRES_PORT} nel Service '{POSTGRES_DEPLOYMENT}'")

    with GradingStep(f"Il Service '{GITEA_DEPLOYMENT}' esiste") as step:
        svc = oc_get_json("service", GITEA_DEPLOYMENT, "-n", project)
        if not svc:
            step.fail(f"Service '{GITEA_DEPLOYMENT}' non trovato")

    with GradingStep(
        f"La Route '{GITEA_DEPLOYMENT}' e' esposta sull'host corretto e sulla porta {GITEA_PORT}"
    ) as step:
        route = oc_get_json("route", GITEA_DEPLOYMENT, "-n", project)
        if not route:
            step.fail(f"Route '{GITEA_DEPLOYMENT}' non trovata")
        else:
            spec = route.get("spec") or {}
            host = spec.get("host", "")
            # Il pattern esatto dipende dal nome del progetto reale, non da
            # quello dell'esercizio (che "oc" non permetterebbe come progetto).
            expected_host = f"{GITEA_DEPLOYMENT}-{project}.apps.ocp4.example.com"
            if host != expected_host:
                step.add_error(f"Host della Route errato: {host!r}, atteso {expected_host!r}")
            target_port = (spec.get("port") or {}).get("targetPort")
            if str(target_port) != str(GITEA_PORT):
                step.add_error(f"targetPort della Route errata: {target_port!r}, atteso {GITEA_PORT}")


if __name__ == "__main__":
    main()
