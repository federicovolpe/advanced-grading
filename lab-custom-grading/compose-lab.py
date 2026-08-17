#!/usr/bin/env python3
"""
Grading "custom" per la LAB (non guided exercise) compose-lab, sprovvista di
`lab grade` ufficiale (la classe ComposeLab implementa solo start()/finish()).

Qui la specifica e' del tutto esplicita: start() definisce direttamente una
lista di watch_items (do188/compose-lab.py, funzioni in do188/common/
watch_functions.py) usata dal monitor live "Watching Compose Lab" mentre lo
studente lavora. Questo script ricalca esattamente quegli stessi controlli:

- tre container in esecuzione: quotes-provider, quotes-api, quotes-ui;
- quotes-provider ha un bind mount di ~/DO188/labs/compose-lab/wiremock/stubs
  su /home/wiremock nel container (con contesto SELinux container_file_t,
  impostato dall'opzione ":Z" nel compose.yaml);
- reti: quotes-provider solo su backend-net, quotes-api su backend-net e
  frontend-net, quotes-ui solo su frontend-net (nomi effettivi con prefisso
  "compose-lab_" perche' il compose.yaml ha "name: compose-lab" in testa);
- quotes-api ha la env QUOTES_SERVICE=http://quotes-provider:8080;
- quotes-ui pubblica la porta host 3000 sulla porta 8080 del container.

Uso: compose-lab.py   (nessun progetto OpenShift: Podman Compose)
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
    selinux_label_ok,
)

LAB_NAME = "compose-lab"

QUOTES_PROVIDER = "quotes-provider"
QUOTES_API = "quotes-api"
QUOTES_UI = "quotes-ui"
CONTAINERS = [QUOTES_PROVIDER, QUOTES_API, QUOTES_UI]

BACKEND_NETWORK = "compose-lab_backend-net"
FRONTEND_NETWORK = "compose-lab_frontend-net"

BIND_SOURCE = os.path.expanduser(f"~/DO188/labs/{LAB_NAME}/wiremock/stubs")
BIND_DEST = "/home/wiremock"

EXPECTED_NETWORKS = {
    QUOTES_PROVIDER: {BACKEND_NETWORK},
    QUOTES_API: {BACKEND_NETWORK, FRONTEND_NETWORK},
    QUOTES_UI: {FRONTEND_NETWORK},
}


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    with GradingStep("I tre container quotes-* sono in esecuzione") as step:
        for name in CONTAINERS:
            if not container_is_running(name):
                step.add_error(f"Container '{name}' non in esecuzione")

    with GradingStep(f"'{QUOTES_PROVIDER}' ha accesso al bind mount degli stub Wiremock") as step:
        if not container_is_running(QUOTES_PROVIDER):
            step.fail(f"Container '{QUOTES_PROVIDER}' non in esecuzione")
        else:
            mounts = container_mounts(QUOTES_PROVIDER)
            bind_found = any(
                m.get("Type") == "bind"
                and os.path.normpath(m.get("Source", "")) == os.path.normpath(BIND_SOURCE)
                and m.get("Destination") == BIND_DEST
                for m in mounts
            )
            if not bind_found:
                step.add_error(f"Nessun bind mount da '{BIND_SOURCE}' a '{BIND_DEST}'")
            elif not selinux_label_ok(BIND_SOURCE):
                step.add_error(
                    f"'{BIND_SOURCE}' non ha il contesto SELinux container_file_t "
                    "(manca l'opzione ':Z' sul volume nel compose.yaml)"
                )

    with GradingStep("I container sono collegati alle reti corrette") as step:
        for name, expected in EXPECTED_NETWORKS.items():
            if not container_is_running(name):
                step.add_error(f"Container '{name}' non in esecuzione")
                continue
            actual = container_networks(name)
            if actual != expected:
                step.add_error(
                    f"'{name}' e' collegato a {sorted(actual)}, atteso {sorted(expected)}"
                )

    with GradingStep(f"'{QUOTES_API}' consuma '{QUOTES_PROVIDER}' via QUOTES_SERVICE") as step:
        if not container_is_running(QUOTES_API):
            step.fail(f"Container '{QUOTES_API}' non in esecuzione")
        else:
            env = container_env(QUOTES_API)
            if env.get("QUOTES_SERVICE") != "http://quotes-provider:8080":
                step.add_error(
                    f"Env var QUOTES_SERVICE errata (trovata: {env.get('QUOTES_SERVICE')!r})"
                )

    with GradingStep(f"'{QUOTES_UI}' pubblica la porta host 3000 sulla 8080 del container") as step:
        if not container_is_running(QUOTES_UI):
            step.fail(f"Container '{QUOTES_UI}' non in esecuzione")
        else:
            ports = container_port_mappings(QUOTES_UI)
            if "3000" not in ports.get("8080/tcp", []):
                step.add_error("Porta 3000 (host) -> 8080 (container) non trovata")


if __name__ == "__main__":
    main()
