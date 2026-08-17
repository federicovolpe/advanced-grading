#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise troubleshooting-debugging, sprovvista
di `lab grade` ufficiale (la classe TroubleshootingDebugging nel pacchetto
do188 implementa solo start()/finish(), non grade()).

start() (vedi do188/troubleshooting-debugging.py) richiede libere le porte
8080 e 9229 e assicura che nessun container si chiami "nodebug"; finish()
rimuove forzatamente il container "nodebug". Il nome del container e le due
porte sono quindi confermati dal modulo ufficiale.

La guida (Cap. 6.4) fa partire il container in modalita' debug (node
--inspect=0.0.0.0:9229, porta 9229 pubblicata) per individuare un bug
nell'endpoint /snacks (la ricerca "apple" non trova "Apple pie" per un
confronto case-sensitive), poi corregge il codice e ricrea il container in
modalita' NORMALE: solo `-p 8080:8080`, senza la 9229. Lo stato finale atteso
a `lab finish` e' quindi: container "nodebug" in esecuzione, SENZA la porta di
debug pubblicata, che risponde correttamente su /snacks.

E' un check "a caldo": valido solo mentre l'esercizio e' in corso (prima di
`lab finish`, che rimuove il container) — coerente con quanto descritto in
CLAUDE.md per questo tipo di esercizio.

Uso: troubleshooting-debugging.py   (nessun progetto OpenShift: esercizio Podman)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (
    GradingStep,
    container_is_running,
    container_port_mappings,
    http_get,
)

LAB_NAME = "troubleshooting-debugging"
CONTAINER = "nodebug"
APP_PORT = "8080/tcp"
DEBUG_PORT = "9229/tcp"
EXPECTED_TEXT = "yes, we have apples!"


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    container_running = container_is_running(CONTAINER)
    with GradingStep(
        f"Il container '{CONTAINER}' e' in esecuzione senza la modalita' debug"
    ) as step:
        if not container_running:
            step.fail(f"Container '{CONTAINER}' non in esecuzione")
        else:
            ports = container_port_mappings(CONTAINER)
            if APP_PORT not in ports or "8080" not in ports.get(APP_PORT, []):
                step.add_error("La porta 8080 non e' pubblicata su 8080 host")
            if DEBUG_PORT in ports:
                step.add_error(
                    "La porta di debug 9229 e' ancora pubblicata: il debug "
                    "mode va disattivato ricreando il container senza -p 9229"
                )

    with GradingStep("L'endpoint /snacks?search=apple risponde con il bug corretto") as step:
        if not container_running:
            step.fail(f"Container '{CONTAINER}' non in esecuzione")
        else:
            ports = container_port_mappings(CONTAINER)
            host_ports = ports.get(APP_PORT, [])
            if not host_ports:
                step.fail("Nessuna porta host mappata sulla 8080 del container")
            else:
                ok, body = http_get(
                    f"http://localhost:{host_ports[0]}/snacks?search=apple"
                )
                if not ok:
                    step.add_error("La richiesta a /snacks e' fallita")
                elif EXPECTED_TEXT not in body:
                    step.add_error(
                        f"/snacks non contiene il testo atteso ({EXPECTED_TEXT!r}): "
                        "il bug nell'endpoint non e' stato corretto"
                    )


if __name__ == "__main__":
    main()
