#!/usr/bin/env python3
"""
Grading "custom" per la lab guidata (Guided Exercise, non Lab) basics-podman,
sprovvista di `lab grade` ufficiale (la classe BasicsPodman nel pacchetto
do188 implementa solo start()/finish(), non grade()).

La specifica viene dagli stessi watch_items che start() usa per il monitor
live (vedi do188/basics-podman.py): estrazione di un secret da un container,
creazione di una rete lab-net, e due container (server/client) collegati a
quella rete, con il server che pubblica la porta 8080 e serve un index.html
custom.

Uso: basics-podman.py   (nessun progetto OpenShift: e' un esercizio Podman)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (
    GradingStep,
    container_is_running,
    container_networks,
    container_port_mappings,
    podman_exec,
    podman_network_exists,
)

LAB_NAME = "basics-podman"
NETWORK = "lab-net"
SERVER = "basics-podman-server"
CLIENT = "basics-podman-client"
SERVER_IMAGE_HINT = "ubi9/httpd-24"
EXPECTED_SECRET = "Mastering containers step by step"
SOLUTION_FILE = os.path.expanduser(f"~/DO188/labs/{LAB_NAME}/solution")
LOCAL_INDEX_FILE = os.path.expanduser(f"~/DO188/labs/{LAB_NAME}/index.html")


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    with GradingStep("Il file solution contiene il secret estratto") as step:
        if not os.path.isfile(SOLUTION_FILE):
            step.fail(f"File '{SOLUTION_FILE}' non trovato")
        else:
            with open(SOLUTION_FILE, encoding="utf-8", errors="replace") as f:
                content = f.read()
            if EXPECTED_SECRET not in content:
                step.add_error(
                    f"Il file non contiene il testo atteso ({EXPECTED_SECRET!r})"
                )

    with GradingStep(f"La rete Podman '{NETWORK}' esiste") as step:
        if not podman_network_exists(NETWORK):
            step.fail(f"Rete '{NETWORK}' non trovata")

    with GradingStep(f"Il container '{SERVER}' e' configurato correttamente") as step:
        if not container_is_running(SERVER):
            step.fail(f"Container '{SERVER}' non in esecuzione")
        else:
            networks = container_networks(SERVER)
            if NETWORK not in networks:
                step.add_error(f"Il container non e' collegato alla rete '{NETWORK}'")
            ports = container_port_mappings(SERVER)
            if "8080/tcp" not in ports or "8080" not in ports.get("8080/tcp", []):
                step.add_error("La porta 8080 non e' pubblicata su 8080 host")

    with GradingStep(f"Il container '{CLIENT}' e' configurato correttamente") as step:
        if not container_is_running(CLIENT):
            step.fail(f"Container '{CLIENT}' non in esecuzione")
        else:
            networks = container_networks(CLIENT)
            if NETWORK not in networks:
                step.add_error(f"Il container non e' collegato alla rete '{NETWORK}'")

    with GradingStep("Il file index.html nel container server e' quello corretto") as step:
        if not container_is_running(SERVER):
            step.fail(f"Container '{SERVER}' non in esecuzione")
        elif not os.path.isfile(LOCAL_INDEX_FILE):
            step.fail(f"File locale '{LOCAL_INDEX_FILE}' non trovato per il confronto")
        else:
            with open(LOCAL_INDEX_FILE, encoding="utf-8", errors="replace") as f:
                expected = f.read()
            result = podman_exec(SERVER, "cat", "/var/www/html/index.html")
            if result.returncode != 0 or result.stdout != expected:
                step.add_error(
                    "Il contenuto di /var/www/html/index.html nel container "
                    "non corrisponde al file index.html locale"
                )


if __name__ == "__main__":
    main()
