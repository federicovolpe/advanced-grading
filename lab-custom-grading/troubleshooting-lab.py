#!/usr/bin/env python3
"""
Grading "custom" per la lab guidata (Guided Exercise) troubleshooting-lab,
sprovvista di `lab grade` ufficiale (la classe TroubleshootingLab nel
pacchetto do188 implementa solo start()/finish(), non grade()).

start() crea gia' tutto tranne la riconfigurazione richiesta allo studente:
due wiremock (quotes-api-v1, quotes-api-v2) e una UI "quotes-ui" (pubblicata
su :3000, non ancora collegata alla rete "troubleshooting-lab"). Lo studente
deve ricollegare la UI alla rete, impostarne la env var QUOTES_API_VERSION=v2,
montare un nginx.conf corretto su /etc/nginx/nginx.conf e verificare che la
UI raggiunga davvero la v2 (che risponde con citazioni di Hawking) sia da
dentro il container che dall'host (dove pero' l'endpoint restituisce anche
citazioni di Einstein, incluse nello stub v2).

La specifica viene dagli stessi watch_items usati dal monitor live (vedi
do188/troubleshooting-lab.py, che si appoggia a do188/common/watch_functions.py).

Uso: troubleshooting-lab.py   (nessun progetto OpenShift: e' un esercizio Podman)
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
    http_get,
    podman_exec,
)

LAB_NAME = "troubleshooting-lab"
API_V1 = "quotes-api-v1"
API_V2 = "quotes-api-v2"
UI = "quotes-ui"
LAB_CONTAINERS = [API_V1, API_V2, UI]
NETWORK = "troubleshooting-lab"
NGINX_SRC = os.path.expanduser(f"~/DO188/labs/{LAB_NAME}/nginx.conf")
NGINX_DEST = "/etc/nginx/nginx.conf"


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    with GradingStep(f"I container {', '.join(LAB_CONTAINERS)} sono in esecuzione") as step:
        for name in LAB_CONTAINERS:
            if not container_is_running(name):
                step.add_error(f"Container '{name}' non in esecuzione")

    with GradingStep(f"'{UI}' e' collegato solo alla rete '{NETWORK}'") as step:
        if not container_is_running(UI):
            step.fail(f"Container '{UI}' non in esecuzione")
        else:
            networks = container_networks(UI)
            if networks != {NETWORK}:
                step.add_error(f"Reti attese: {{'{NETWORK}'}}, trovate: {networks}")

    with GradingStep(f"'{UI}' ha la env var QUOTES_API_VERSION=v2") as step:
        if not container_is_running(UI):
            step.fail(f"Container '{UI}' non in esecuzione")
        else:
            env = container_env(UI)
            if env.get("QUOTES_API_VERSION") != "v2":
                step.add_error(
                    f"QUOTES_API_VERSION='{env.get('QUOTES_API_VERSION')}' (atteso 'v2')"
                )

    with GradingStep(f"'{UI}' monta {NGINX_SRC} su {NGINX_DEST}") as step:
        if not container_is_running(UI):
            step.fail(f"Container '{UI}' non in esecuzione")
        else:
            mounts = container_mounts(UI)
            matching = [
                m for m in mounts
                if m.get("Type") == "bind"
                and m.get("Source") == NGINX_SRC
                and m.get("Destination") == NGINX_DEST
            ]
            if not matching:
                step.add_error(f"Nessun bind mount {NGINX_SRC} -> {NGINX_DEST} trovato")

    with GradingStep(f"Da dentro '{UI}', :8080/api/v2/quotes raggiunge la v2 (Hawking)") as step:
        if not container_is_running(UI):
            step.fail(f"Container '{UI}' non in esecuzione")
        else:
            result = podman_exec(UI, "curl", "-s", "http://localhost:8080/api/v2/quotes")
            if result.returncode != 0 or "Hawking" not in result.stdout:
                step.add_error("curl interno a :8080/api/v2/quotes non contiene 'Hawking'")

    with GradingStep("Da host, :3000/api/v2/quotes e' accessibile (Einstein)") as step:
        ok, body = http_get("http://localhost:3000/api/v2/quotes")
        if not ok or "Einstein" not in body:
            step.add_error("GET http://localhost:3000/api/v2/quotes non contiene 'Einstein'")


if __name__ == "__main__":
    main()
