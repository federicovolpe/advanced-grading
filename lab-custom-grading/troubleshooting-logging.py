#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise troubleshooting-logging, sprovvista
di `lab grade` ufficiale (la classe TroubleshootingLogging nel pacchetto
do188 implementa solo start()/finish(), non grade()).

Nessun watch_items e nessuna materials/solutions: start() crea già
smart-home-db (funzionante) e smart-home-api (che FALLISCE di proposito,
senza rete/env DB_*), copiando anche automations.yaml nella cartella
dell'esercizio. La guida (Cap. 6.2) chiede di ricreare smart-home-api più
volte fino a un'ultima versione funzionante — con rete, env corrette, la
porta giusta (8000 nel container, non 8080) e il file automations.yaml
montato con l'opzione :Z per il contesto SELinux corretto.

E' un check "a caldo": valido solo mentre l'esercizio e' in corso (prima di
`lab finish`, che rimuove containers/rete/volume) — coerente con quanto
descritto in CLAUDE.md per questo tipo di esercizio.

Uso: troubleshooting-logging.py   (nessun progetto OpenShift: esercizio Podman)
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
    http_get,
    podman_network_exists,
)

LAB_NAME = "troubleshooting-logging"
NETWORK = "troubleshooting-lab"
API_CONTAINER = "smart-home-api"
DB_CONTAINER = "smart-home-db"
EXPECTED_ENV = {
    "DB_HOST": "smart-home-db",
    "DB_USER": "backend",
    "DB_PASSWORD": "secret_pass",
}
AUTOMATIONS_DEST = "/config/automations.yaml"
EXPECTED_AUTOMATION_TEXT = "Turn garage lights ON when presence detected"


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    with GradingStep(f"La rete Podman '{NETWORK}' esiste") as step:
        if not podman_network_exists(NETWORK):
            step.fail(f"Rete '{NETWORK}' non trovata")

    with GradingStep(f"Il container '{DB_CONTAINER}' e' in esecuzione") as step:
        if not container_is_running(DB_CONTAINER):
            step.fail(f"Container '{DB_CONTAINER}' non in esecuzione")

    api_running = container_is_running(API_CONTAINER)
    with GradingStep(f"Il container '{API_CONTAINER}' e' configurato correttamente") as step:
        if not api_running:
            step.fail(f"Container '{API_CONTAINER}' non in esecuzione")
        else:
            networks = container_networks(API_CONTAINER)
            if NETWORK not in networks:
                step.add_error(f"Il container non e' collegato alla rete '{NETWORK}'")

            env = container_env(API_CONTAINER)
            for key, value in EXPECTED_ENV.items():
                if env.get(key) != value:
                    step.add_error(f"Env var {key} errata (trovata: {env.get(key)!r})")

            ports = container_port_mappings(API_CONTAINER)
            if "8000/tcp" not in ports:
                step.add_error(
                    "La porta host non e' mappata sulla porta 8000 del container "
                    "(uvicorn ascolta su 8000, non 8080)"
                )

            mounts = container_mounts(API_CONTAINER)
            if not any(m.get("Destination") == AUTOMATIONS_DEST for m in mounts):
                step.add_error(f"Nessun bind mount su '{AUTOMATIONS_DEST}'")

    with GradingStep("L'endpoint /automations risponde con la configurazione corretta") as step:
        if not api_running:
            step.fail()
        else:
            ports = container_port_mappings(API_CONTAINER)
            host_ports = ports.get("8000/tcp", [])
            if not host_ports:
                step.fail("Nessuna porta host mappata sulla 8000 del container")
            else:
                ok, body = http_get(f"http://localhost:{host_ports[0]}/automations")
                if not ok:
                    step.add_error("La richiesta a /automations e' fallita")
                elif EXPECTED_AUTOMATION_TEXT not in body:
                    step.add_error(
                        f"/automations non contiene il testo atteso ({EXPECTED_AUTOMATION_TEXT!r})"
                    )

    with GradingStep("L'endpoint /device/1 risponde correttamente") as step:
        if not api_running:
            step.fail()
        else:
            ports = container_port_mappings(API_CONTAINER)
            host_ports = ports.get("8000/tcp", [])
            if not host_ports:
                step.fail("Nessuna porta host mappata sulla 8000 del container")
            else:
                ok, body = http_get(f"http://localhost:{host_ports[0]}/device/1")
                if not ok or '"id":1' not in body.replace(" ", ""):
                    step.add_error("/device/1 non risponde con i dati attesi")


if __name__ == "__main__":
    main()
