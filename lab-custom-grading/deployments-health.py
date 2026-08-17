#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise deployments-health (DO288), priva di
`lab grade` ufficiale (il modulo do288/deployments_health.py implementa solo
start()/finish()).

start() applica un manifest "project-dimensioning.yaml" come admin, che
configura LimitRange/ResourceQuota sul progetto che limitano la memoria
disponibile. La guida chiede allo studente di applicare piu' volte
application.yaml con richieste di memoria crescenti (50Mi -> 400Mi -> 200Mi
-> 160Mi) fino a trovare un valore che rispetti sia il LimitRange sia la
ResourceQuota del progetto (160Mi, con requests==limits per ottenere QoS
Guaranteed), poi scala a 3 repliche e configura readiness/liveness probe
tramite web console.

Specifica (fornita dall'utente, che ha letto la guida ufficiale):
- Deployment "expense": container ha resources.requests.memory ==
  resources.limits.memory == "160Mi".
- readinessProbe: httpGet.path == "/q/health/ready", failureThreshold == 3.
- livenessProbe: httpGet.path == "/q/health/live", failureThreshold == 2.
- .spec.replicas: la guida scala a 3 e poi torna a 2 per il test degli
  health check, ma per non rischiare un falso negativo su un dettaglio
  secondario (vedi nota dell'utente) verifichiamo solo che sia >= 1: il vero
  obiettivo pedagogico dell'esercizio sono le risorse/i probe, non il numero
  di repliche finale.

Uso: deployments-health.py [nome-progetto]   (default: deployments-health)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "deployments-health"
DEPLOYMENT = "expense"
EXPECTED_MEMORY = "160Mi"
READY_PATH = "/q/health/ready"
LIVE_PATH = "/q/health/live"
READY_FAILURE_THRESHOLD = 3
LIVE_FAILURE_THRESHOLD = 2


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    deployment = oc_get_json("deployment", DEPLOYMENT, "-n", project)
    with GradingStep(f"Il Deployment '{DEPLOYMENT}' esiste ed ha almeno una replica") as step:
        if not deployment:
            step.fail(f"Deployment '{DEPLOYMENT}' non trovato")
        else:
            replicas = (deployment.get("spec") or {}).get("replicas", 0)
            if replicas < 1:
                step.add_error(f"'.spec.replicas' e' {replicas!r}, atteso >= 1")

    container = None
    if deployment:
        containers = ((deployment.get("spec") or {}).get("template") or {}).get("spec", {}).get("containers") or []
        container = containers[0] if containers else None

    with GradingStep(
        f"Il container ha requests.memory == limits.memory == '{EXPECTED_MEMORY}' (QoS Guaranteed)"
    ) as step:
        if not container:
            step.fail(f"Nessun container trovato nel Deployment '{DEPLOYMENT}'")
        else:
            resources = container.get("resources") or {}
            requests_mem = (resources.get("requests") or {}).get("memory")
            limits_mem = (resources.get("limits") or {}).get("memory")
            if requests_mem != EXPECTED_MEMORY:
                step.add_error(f"requests.memory e' {requests_mem!r}, atteso '{EXPECTED_MEMORY}'")
            if limits_mem != EXPECTED_MEMORY:
                step.add_error(f"limits.memory e' {limits_mem!r}, atteso '{EXPECTED_MEMORY}'")

    with GradingStep(
        f"La readiness probe usa il path '{READY_PATH}' con failureThreshold={READY_FAILURE_THRESHOLD}"
    ) as step:
        if not container:
            step.fail(f"Nessun container trovato nel Deployment '{DEPLOYMENT}'")
        else:
            probe = container.get("readinessProbe") or {}
            path = (probe.get("httpGet") or {}).get("path")
            threshold = probe.get("failureThreshold")
            if path != READY_PATH:
                step.add_error(f"readinessProbe.httpGet.path e' {path!r}, atteso '{READY_PATH}'")
            if threshold != READY_FAILURE_THRESHOLD:
                step.add_error(
                    f"readinessProbe.failureThreshold e' {threshold!r}, atteso {READY_FAILURE_THRESHOLD}"
                )

    with GradingStep(
        f"La liveness probe usa il path '{LIVE_PATH}' con failureThreshold={LIVE_FAILURE_THRESHOLD}"
    ) as step:
        if not container:
            step.fail(f"Nessun container trovato nel Deployment '{DEPLOYMENT}'")
        else:
            probe = container.get("livenessProbe") or {}
            path = (probe.get("httpGet") or {}).get("path")
            threshold = probe.get("failureThreshold")
            if path != LIVE_PATH:
                step.add_error(f"livenessProbe.httpGet.path e' {path!r}, atteso '{LIVE_PATH}'")
            if threshold != LIVE_FAILURE_THRESHOLD:
                step.add_error(
                    f"livenessProbe.failureThreshold e' {threshold!r}, atteso {LIVE_FAILURE_THRESHOLD}"
                )


if __name__ == "__main__":
    main()
