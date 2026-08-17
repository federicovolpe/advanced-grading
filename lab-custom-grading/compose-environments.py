#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise compose-environments, sprovvista di
`lab grade` ufficiale (la classe ComposeEnvironments nel pacchetto do188
implementa solo start()/finish(), non grade() - e start() non definisce
nemmeno watch_items, solo il copy_lab_files iniziale).

La specifica viene quindi dal confronto diretto tra
materials/labs/compose-environments/compose.yml (che lo studente riceve con
solo dei commenti placeholder al posto delle direttive) e
materials/solutions/compose-environments/compose.yml (che le contiene): lo
studente deve scrivere due servizi Podman Compose, pgAdmin e PostgreSQL, con
container_name, environment, ports e volumes precisi.

I nomi container_name sono fissi nel compose.yml stesso ("compose_environments_
pgadmin"/"compose_environments_postgresql", nota l'underscore, diverso
dall'hyphen del nome esercizio). Rete e volume di default invece non sono
dichiarati esplicitamente nel compose.yml (nessuna sezione networks/volumes
con nome custom per la rete, e il volume "rpi" e' dichiarato senza "name:"):
Podman Compose li genera con il prefisso "<project>_", dove project e' il
nome della cartella del progetto in minuscolo ("compose-environments", con lo
hyphen originale - confermato sia dall'attributo networks=["compose-
environments_default"] nella classe ufficiale, sia leggendo la logica di
project_name/volume naming in podman_compose.py installato sul sistema).

Uso: compose-environments.py   (nessun progetto OpenShift: Podman Compose)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (
    GradingStep,
    container_env,
    container_is_running,
    container_mounts,
    container_networks,
    container_port_mappings,
    podman_network_exists,
    podman_volume_exists,
)

LAB_NAME = "compose-environments"
PROJECT = "compose-environments"
NETWORK = f"{PROJECT}_default"
VOLUME = f"{PROJECT}_rpi"

PGADMIN = "compose_environments_pgadmin"
POSTGRESQL = "compose_environments_postgresql"

PGADMIN_ENV = {
    "PGADMIN_SETUP_EMAIL": "user@example.com",
    "PGADMIN_SETUP_PASSWORD": "redhat",
}
POSTGRESQL_ENV = {
    "POSTGRESQL_USER": "backend",
    "POSTGRESQL_DATABASE": "rpi-store",
    "POSTGRESQL_PASSWORD": "redhat",
}
POSTGRESQL_VOLUME_DEST = "/var/lib/pgsql/data"
POSTGRESQL_BIND_SOURCE = os.path.expanduser(
    f"~/DO188/labs/{LAB_NAME}/database_scripts"
)
POSTGRESQL_BIND_DEST = "/opt/app-root/src/postgresql-start"


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    with GradingStep(f"La rete Podman '{NETWORK}' esiste") as step:
        if not podman_network_exists(NETWORK):
            step.fail(f"Rete '{NETWORK}' non trovata (creata da 'podman-compose up')")

    with GradingStep(f"Il container '{PGADMIN}' e' configurato correttamente") as step:
        if not container_is_running(PGADMIN):
            step.fail(f"Container '{PGADMIN}' non in esecuzione")
        else:
            networks = container_networks(PGADMIN)
            if NETWORK not in networks:
                step.add_error(f"Il container non e' collegato alla rete '{NETWORK}'")

            env = container_env(PGADMIN)
            for key, value in PGADMIN_ENV.items():
                if env.get(key) != value:
                    step.add_error(f"Env var {key} errata (trovata: {env.get(key)!r})")

            ports = container_port_mappings(PGADMIN)
            if "5050" not in ports.get("5050/tcp", []):
                step.add_error("La porta 5050 non e' pubblicata su 5050 host")

    with GradingStep(f"Il container '{POSTGRESQL}' e' configurato correttamente") as step:
        if not container_is_running(POSTGRESQL):
            step.fail(f"Container '{POSTGRESQL}' non in esecuzione")
        else:
            networks = container_networks(POSTGRESQL)
            if NETWORK not in networks:
                step.add_error(f"Il container non e' collegato alla rete '{NETWORK}'")

            env = container_env(POSTGRESQL)
            for key, value in POSTGRESQL_ENV.items():
                if env.get(key) != value:
                    step.add_error(f"Env var {key} errata (trovata: {env.get(key)!r})")

            ports = container_port_mappings(POSTGRESQL)
            if "5432" not in ports.get("5432/tcp", []):
                step.add_error("La porta 5432 non e' pubblicata su 5432 host")

    with GradingStep(f"Il volume '{VOLUME}' e' montato sul database in {POSTGRESQL_VOLUME_DEST}") as step:
        if not podman_volume_exists(VOLUME):
            step.fail(f"Volume '{VOLUME}' non trovato")
        elif not container_is_running(POSTGRESQL):
            step.fail(f"Container '{POSTGRESQL}' non in esecuzione")
        else:
            mounts = container_mounts(POSTGRESQL)
            found = any(
                m.get("Type") == "volume"
                and m.get("Name") == VOLUME
                and m.get("Destination") == POSTGRESQL_VOLUME_DEST
                for m in mounts
            )
            if not found:
                step.add_error(
                    f"Il volume '{VOLUME}' non risulta montato su {POSTGRESQL_VOLUME_DEST}"
                )

    with GradingStep("Il bind mount di database_scripts e' presente sul database") as step:
        if not container_is_running(POSTGRESQL):
            step.fail(f"Container '{POSTGRESQL}' non in esecuzione")
        else:
            mounts = container_mounts(POSTGRESQL)
            found = any(
                m.get("Type") == "bind"
                and os.path.normpath(m.get("Source", "")) == os.path.normpath(POSTGRESQL_BIND_SOURCE)
                and m.get("Destination") == POSTGRESQL_BIND_DEST
                for m in mounts
            )
            if not found:
                step.add_error(
                    f"Nessun bind mount da '{POSTGRESQL_BIND_SOURCE}' a '{POSTGRESQL_BIND_DEST}'"
                )


if __name__ == "__main__":
    main()
