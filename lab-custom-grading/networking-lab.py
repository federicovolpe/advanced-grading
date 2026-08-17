#!/usr/bin/env python3
"""
Grading "custom" per la lab guidata (Guided Exercise) networking-lab,
sprovvista di `lab grade` ufficiale (la classe NetworkingLab nel pacchetto
do188 implementa solo start()/finish(), non grade()).

La specifica viene dagli stessi watch_items che start() usa per il monitor
live (vedi do188/networking-lab.py): creazione della rete Podman "lab-net" e
di tre container (custom_redis, quotes-api, quotes-ui) tutti collegati ad
essa, con verifica finale che la UI (che pubblica la porta 3000 sull'host)
riesca a fare da proxy verso l'API restituendo le citazioni (tra cui una di
Einstein).

Uso: networking-lab.py   (nessun progetto OpenShift: e' un esercizio Podman)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (
    GradingStep,
    container_is_running,
    http_get,
    podman_network_exists,
)

LAB_NAME = "networking-lab"
NETWORK = "lab-net"
REDIS_CONTAINER = "custom_redis"
API_CONTAINER = "quotes-api"
UI_CONTAINER = "quotes-ui"
EXPECTED_QUOTE = "Einstein"
UI_URL = "http://localhost:3000/api/quotes"


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    with GradingStep(f"La rete Podman '{NETWORK}' esiste") as step:
        if not podman_network_exists(NETWORK):
            step.fail(f"Rete '{NETWORK}' non trovata")

    with GradingStep(f"Il container '{REDIS_CONTAINER}' e' in esecuzione") as step:
        if not container_is_running(REDIS_CONTAINER):
            step.fail(f"Container '{REDIS_CONTAINER}' non in esecuzione")

    with GradingStep(f"Il container '{API_CONTAINER}' e' in esecuzione") as step:
        if not container_is_running(API_CONTAINER):
            step.fail(f"Container '{API_CONTAINER}' non in esecuzione")

    with GradingStep(f"Il container '{UI_CONTAINER}' e' in esecuzione e risponde") as step:
        if not container_is_running(UI_CONTAINER):
            step.fail(f"Container '{UI_CONTAINER}' non in esecuzione")
        else:
            ok, body = http_get(UI_URL)
            if not ok:
                step.add_error(f"GET {UI_URL} non ha risposto correttamente")
            elif EXPECTED_QUOTE not in body:
                step.add_error(
                    f"La risposta di {UI_URL} non contiene '{EXPECTED_QUOTE}' "
                    "(la UI non riesce a recuperare le citazioni dall'API)"
                )


if __name__ == "__main__":
    main()
