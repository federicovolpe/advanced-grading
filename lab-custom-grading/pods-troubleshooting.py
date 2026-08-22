#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato pods-troubleshooting, sprovvisto di
`lab grade` ufficiale (la classe PodsTroubleshooting nel pacchetto do180
implementa solo start()/finish(), non grade()).

Basato sul testo della guida ufficiale dello studente (DO180-RHOCP4.22-en-1,
Chapter 3, "Troubleshoot Containers and Pods"): lo studente crea un pod
"mariadb-server" che parte con un tag immagine rotto e inesistente
(rhel10/mariadb-118:1784040404), diagnostica l'errore con oc logs/oc get
events/skopeo inspect, lo corregge con oc edit al tag funzionante
1784149182 (confermato anche in start(), che verifica l'esistenza dei tag
"1784149182", "1783945307", "latest" per rhel10/mariadb-118), poi carica
world_x.sql nel database "world" (SOURCE /tmp/world_x.sql), popolando le
tabelle city/country/countryinfo/countrylanguage.

Uso: pods-troubleshooting.py [nome-progetto]   (default: pods-troubleshooting)
"""

import subprocess
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "pods-troubleshooting"
POD_NAME = "mariadb-server"
EXPECTED_IMAGE = "registry.lab.example.com:8443/rhel10/mariadb-118:1784149182"
EXPECTED_ENV = {
    "MYSQL_USER": "redhat",
    "MYSQL_PASSWORD": "redhat123",
    "MYSQL_DATABASE": "world",
}
EXPECTED_TABLES = {"city", "country", "countryinfo", "countrylanguage"}


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


def query_tables(project):
    """Esegue SHOW TABLES FROM world dentro il pod (sola lettura, nessuna
    modifica allo stato del cluster) e ritorna l'insieme dei nomi di
    tabella, o None se la query fallisce. L'immagine rhel10/mariadb-118
    fornisce il client come `mariadb` (non piu' `mysql`, come mostra la
    guida al passo 5.4)."""
    result = subprocess.run(
        [
            "oc", "exec", f"pod/{POD_NAME}", "-n", project, "--",
            "mariadb", "-u", EXPECTED_ENV["MYSQL_USER"],
            f"-p{EXPECTED_ENV['MYSQL_PASSWORD']}",
            "-N", "-e", "SHOW TABLES FROM world;",
        ],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        return None
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


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
            statuses = pod.get("status", {}).get("containerStatuses", [])
            not_ready = [c.get("name") for c in statuses if not c.get("ready")]
            if not_ready:
                step.add_error(f"Container non ready: {', '.join(not_ready)}")
            container = get_container(pod)
            if container is None:
                step.add_error("Nessun container trovato nel pod")

    with GradingStep(f"Il pod {POD_NAME} usa l'immagine corretta (tag 1784149182)") as step:
        if container is None:
            step.fail()
        elif container.get("image") != EXPECTED_IMAGE:
            step.add_error(
                f"Immagine inattesa: {container.get('image')} (attesa: {EXPECTED_IMAGE})"
            )

    with GradingStep("Le variabili d'ambiente del database sono configurate correttamente") as step:
        if container is None:
            step.fail()
        else:
            check_env(container, step)

    with GradingStep("Il database world e' stato popolato con le tabelle corrette") as step:
        if pod is None or pod.get("status", {}).get("phase") != "Running":
            step.fail("Il pod non e' Running: impossibile interrogare il database")
        else:
            tables = query_tables(project)
            if tables is None:
                step.add_error(
                    "Impossibile eseguire la query nel pod (mariadb non raggiungibile "
                    "o credenziali errate)"
                )
            elif not EXPECTED_TABLES.issubset(tables):
                missing = EXPECTED_TABLES - tables
                step.add_error(f"Tabelle mancanti nel database world: {', '.join(sorted(missing))}")


if __name__ == "__main__":
    main()
