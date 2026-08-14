#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato reliability-probes, sprovvisto di
`lab grade` ufficiale (la classe ReliabilityProbes nel pacchetto do180
implementa solo start()/finish(), non grade()).

Ricalca lo stile e alcuni controlli del grading ufficiale di
reliability-review.py (stesso deployment "long-load", stesso schema a
GradingStep), ma verifica quanto richiesto da questa guided exercise:
startup/liveness/readiness probe sul container long-load, con controllo
HTTP GET su /health:3000 (vedi DO180/solutions/reliability-probes).

Uso: reliability-probes.py [nome-progetto]   (default: reliability-probes)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "reliability-probes"
EXPECTED_PATH = "/health"
EXPECTED_PORT = "3000"


def get_container(deployment, name="long-load"):
    containers = deployment["spec"]["template"]["spec"]["containers"]
    for c in containers:
        if c.get("name") == name:
            return c
    return containers[0] if containers else None


def check_probe(container, probe_name, step):
    probe = container.get(probe_name)
    if probe is None:
        step.add_error(f"Il container non definisce {probe_name}")
        return
    http_get = probe.get("httpGet")
    if http_get is None:
        step.add_error(f"{probe_name} non usa un controllo HTTP GET")
        return
    if http_get.get("path") != EXPECTED_PATH:
        step.add_error(
            f"{probe_name}: il path deve essere {EXPECTED_PATH} "
            f"(trovato: {http_get.get('path')})"
        )
    if str(http_get.get("port")) != EXPECTED_PORT:
        step.add_error(
            f"{probe_name}: la porta deve essere {EXPECTED_PORT} "
            f"(trovata: {http_get.get('port')})"
        )


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    deployment = oc_get_json("deployment", "long-load", "-n", project)
    container = None

    with GradingStep("Il deployment long-load esiste") as step:
        if deployment is None:
            step.fail("Deployment 'long-load' non trovato nel progetto")
        else:
            container = get_container(deployment)
            if container is None:
                step.fail("Nessun container trovato nel deployment")

    with GradingStep("Lo startup probe e' configurato correttamente") as step:
        if container is None:
            step.fail()
        else:
            check_probe(container, "startupProbe", step)

    with GradingStep("La liveness probe e' configurata correttamente") as step:
        if container is None:
            step.fail()
        else:
            check_probe(container, "livenessProbe", step)

    with GradingStep("La readiness probe e' configurata correttamente") as step:
        if container is None:
            step.fail()
        else:
            check_probe(container, "readinessProbe", step)


if __name__ == "__main__":
    main()
