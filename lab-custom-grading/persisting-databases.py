#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise persisting-databases, sprovvista di
`lab grade` ufficiale (la classe PersistingDatabases nel pacchetto do188
implementa solo start()/finish(), non grade()).

Nessun watch_items e nessuna materials/solutions per questo esercizio: la
specifica viene dal testo della guida (Cap. 5.4, "Working with Databases"),
letto per intero. La guida fa passare lo studente per piu' container
(persisting-pg12 con dati non persistenti, poi persistenti via volume, poi
persisting-pgadmin), ma l'ULTIMO passo (6.9) chiede esplicitamente di
rimuovere persisting-pg12 e il suo volume dopo aver migrato i dati su
PostgreSQL 13. Lo stato finale atteso, quindi, e' persisting-pg12 GIA'
RIMOSSO e persisting-pg13 (con i dati migrati) + persisting-pgadmin ancora
in esecuzione, entrambi sulla rete persisting-network.

Uso: persisting-databases.py   (nessun progetto OpenShift: esercizio Podman)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (
    GradingStep,
    container_env,
    container_is_running,
    container_networks,
    container_port_mappings,
    podman_container,
    podman_exec,
    podman_network_exists,
)

LAB_NAME = "persisting-databases"
NETWORK = "persisting-network"
PG12_CONTAINER = "persisting-pg12"
PG13_CONTAINER = "persisting-pg13"
PGADMIN_CONTAINER = "persisting-pgadmin"
PG13_ENV = {
    "POSTGRESQL_USER": "backend",
    "POSTGRESQL_PASSWORD": "secret_pass",
    "POSTGRESQL_DATABASE": "rpi-store",
}
PGADMIN_ENV = {"PGADMIN_SETUP_EMAIL": "gls@example.com"}


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    with GradingStep(f"La rete Podman '{NETWORK}' esiste") as step:
        if not podman_network_exists(NETWORK):
            step.fail(f"Rete '{NETWORK}' non trovata")

    pg13_running = container_is_running(PG13_CONTAINER)
    with GradingStep(f"Il container '{PG13_CONTAINER}' e' configurato correttamente") as step:
        if not pg13_running:
            step.fail(f"Container '{PG13_CONTAINER}' non in esecuzione")
        else:
            image = (podman_container(PG13_CONTAINER) or {}).get("ImageName", "")
            if "postgresql-13" not in image:
                step.add_error(f"L'immagine non e' una PostgreSQL 13 (trovata: {image})")

            env = container_env(PG13_CONTAINER)
            for key, value in PG13_ENV.items():
                if env.get(key) != value:
                    step.add_error(f"Env var {key} errata (trovata: {env.get(key)!r})")

            if NETWORK not in container_networks(PG13_CONTAINER):
                step.add_error(f"Il container non e' collegato alla rete '{NETWORK}'")

    with GradingStep("Il container persisting-pg12 e' stato rimosso dopo la migrazione") as step:
        if podman_container(PG12_CONTAINER) is not None:
            step.add_error(
                f"'{PG12_CONTAINER}' esiste ancora: la guida chiede di rimuoverlo "
                "dopo aver migrato i dati su PostgreSQL 13 (passo 6.9)"
            )

    with GradingStep("I dati sono stati migrati correttamente nella tabella model") as step:
        if not pg13_running:
            step.fail()
        else:
            result = podman_exec(
                PG13_CONTAINER, "psql", "-d", "rpi-store", "-tAc", "select count(*) from model"
            )
            if result.returncode != 0:
                step.add_error("Query sulla tabella 'model' fallita (tabella assente o DB non pronto)")
            elif result.stdout.strip() != "5":
                step.add_error(
                    f"La tabella 'model' non contiene le 5 righe attese (trovate: {result.stdout.strip()!r})"
                )

    with GradingStep(f"Il container '{PGADMIN_CONTAINER}' e' configurato correttamente") as step:
        if not container_is_running(PGADMIN_CONTAINER):
            step.fail(f"Container '{PGADMIN_CONTAINER}' non in esecuzione")
        else:
            env = container_env(PGADMIN_CONTAINER)
            for key, value in PGADMIN_ENV.items():
                if env.get(key) != value:
                    step.add_error(f"Env var {key} errata (trovata: {env.get(key)!r})")

            if NETWORK not in container_networks(PGADMIN_CONTAINER):
                step.add_error(f"Il container non e' collegato alla rete '{NETWORK}'")

            ports = container_port_mappings(PGADMIN_CONTAINER)
            if "5050/tcp" not in ports or "5050" not in ports.get("5050/tcp", []):
                step.add_error("La porta 5050 non e' pubblicata su 5050 host")


if __name__ == "__main__":
    main()
