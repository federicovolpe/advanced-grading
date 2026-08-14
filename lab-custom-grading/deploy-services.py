#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato deploy-services, sprovvisto di
`lab grade` ufficiale (la classe DeployServices nel pacchetto do180
implementa solo start()/finish(), non grade()).

L'esercizio non ha una cartella materials/solutions (e' puramente
imperativo, niente manifest YAML da applicare): lo studente crea un pod
mysql chiamato db-pod, lo espone con un service omonimo sulla porta 3306,
e inizializza il database "items" con un Job "mysql-init" (vedi
DO180/materials/labs/deploy-services/resources.txt per i comandi di
riferimento, e deploy-services.py per l'immagine rhel8/mysql-80 richiesta).
Il secondo progetto "deploy-services-2" usato per testare la risoluzione
DNS cross-namespace del service e' solo un test interattivo (pod --rm) e
non lascia stato persistente da gradare.

Uso: deploy-services.py [nome-progetto]   (default: deploy-services)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "deploy-services"
POD_NAME = "db-pod"
SERVICE_NAME = "db-pod"
JOB_NAME = "mysql-init"
EXPECTED_IMAGE_SUBSTR = "mysql-80"
EXPECTED_ENV = {
    "MYSQL_USER": "user1",
    "MYSQL_PASSWORD": "mypa55w0rd",
    "MYSQL_DATABASE": "items",
}
EXPECTED_PORT = 3306


def get_container(pod, name=POD_NAME):
    containers = pod["spec"]["containers"]
    for c in containers:
        if c.get("name") == name:
            return c
    return containers[0] if containers else None


def check_env(container, step):
    env_map = {e.get("name"): e.get("value") for e in container.get("env", []) or []}
    for key, expected in EXPECTED_ENV.items():
        actual = env_map.get(key)
        if actual != expected:
            step.add_error(f"{key} deve essere '{expected}' (trovato: {actual!r})")


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    pod = oc_get_json("pod", POD_NAME, "-n", project)
    container = None

    with GradingStep(f"Il pod {POD_NAME} esiste ed e' in esecuzione") as step:
        if pod is None:
            step.fail(f"Pod '{POD_NAME}' non trovato nel progetto")
        else:
            phase = pod.get("status", {}).get("phase")
            if phase != "Running":
                step.add_error(f"Il pod e' in stato '{phase}', atteso 'Running'")
            container = get_container(pod)
            if container is None:
                step.add_error("Nessun container trovato nel pod")

    with GradingStep(f"Il pod {POD_NAME} usa l'immagine mysql-80 corretta") as step:
        if container is None:
            step.fail()
        elif EXPECTED_IMAGE_SUBSTR not in container.get("image", ""):
            step.add_error(
                f"Immagine inattesa: {container.get('image')} "
                f"(deve contenere '{EXPECTED_IMAGE_SUBSTR}')"
            )

    with GradingStep("Le variabili d'ambiente del database sono configurate correttamente") as step:
        if container is None:
            step.fail()
        else:
            check_env(container, step)

    service = oc_get_json("service", SERVICE_NAME, "-n", project)

    with GradingStep(f"Il service {SERVICE_NAME} espone correttamente la porta {EXPECTED_PORT}") as step:
        if service is None:
            step.fail(f"Service '{SERVICE_NAME}' non trovato nel progetto")
        else:
            ports = service.get("spec", {}).get("ports", [])
            if not ports:
                step.add_error("Il service non definisce alcuna porta")
            else:
                port = ports[0]
                if port.get("port") != EXPECTED_PORT:
                    step.add_error(f"Porta {port.get('port')}, attesa {EXPECTED_PORT}")
                if str(port.get("targetPort")) != str(EXPECTED_PORT):
                    step.add_error(
                        f"targetPort {port.get('targetPort')}, atteso {EXPECTED_PORT}"
                    )
                if port.get("protocol", "TCP") != "TCP":
                    step.add_error(f"Protocollo {port.get('protocol')}, atteso TCP")

    job = oc_get_json("job", JOB_NAME, "-n", project)

    with GradingStep(f"Il job {JOB_NAME} ha inizializzato correttamente il database") as step:
        if job is None:
            step.fail(f"Job '{JOB_NAME}' non trovato nel progetto")
        elif not job.get("status", {}).get("succeeded"):
            step.add_error("Il job non risulta completato con successo (status.succeeded)")


if __name__ == "__main__":
    main()
