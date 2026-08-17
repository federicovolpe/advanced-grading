#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise images-managing (corso DO188), priva
di `lab grade` ufficiale (la classe ImagesManaging implementa solo
start()/finish()).

CONFIDENZA DELLA FONTE: esiste `materials/labs/images-managing/Containerfile`
(file di partenza copiato allo studente da start()), letto per intero:

    FROM .../ubi8/python-38:1-96
    RUN echo "Hello from the container" > hello.html
    CMD python -m http.server

Nessun materials/solutions per questo esercizio, ma il contenuto e' concreto
e non ambiguo: il container deve servire hello.html con il testo esatto
"Hello from the container" (nessuna approssimazione: e' il valore letto dal
Containerfile reale, non l'indizio). Il modulo ufficiale richiede la porta
8080 host libera (ensure_port_not_in_use) e finish() rimuove un container
chiamato "http-server".

Nota sulla porta: `python -m http.server` senza argomenti ascolta di default
sulla porta 8000 all'interno del container (comportamento documentato dello
stdlib Python, non modificato dal Containerfile). Lo studente deve quindi
pubblicare quella porta sull'host 8080 (es. `-p 8080:8000`). Per non
assumere con certezza assoluta quale porta *container* venga usata (nel caso
lo studente passi un argomento esplicito a http.server), verifico soltanto
che *qualche* mapping pubblichi la porta host 8080, e poi verifico
direttamente via HTTP che il contenuto sia quello atteso.

Uso: images-managing.py   (nessun progetto OpenShift: e' un esercizio Podman)
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

LAB_NAME = "images-managing"
CONTAINER = "http-server"
EXPECTED_TEXT = "Hello from the container"


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    with GradingStep(f"Il container '{CONTAINER}' e' in esecuzione") as step:
        if not container_is_running(CONTAINER):
            step.fail(f"Container '{CONTAINER}' non trovato o non in esecuzione")

    with GradingStep("La porta 8080 e' pubblicata sull'host") as step:
        if not container_is_running(CONTAINER):
            step.fail(f"Container '{CONTAINER}' non in esecuzione")
        else:
            ports = container_port_mappings(CONTAINER)
            published = {p for hosts in ports.values() for p in hosts if p}
            if "8080" not in published:
                step.add_error(
                    f"Nessuna porta del container '{CONTAINER}' e' pubblicata "
                    f"su 8080 host (mapping trovati: {ports})"
                )

    with GradingStep("hello.html contiene il testo esatto del Containerfile") as step:
        if not container_is_running(CONTAINER):
            step.fail(f"Container '{CONTAINER}' non in esecuzione")
        else:
            ok, body = http_get("http://localhost:8080/hello.html")
            if not ok:
                step.fail("GET http://localhost:8080/hello.html non ha risposto (HTTP)")
            elif EXPECTED_TEXT not in body:
                step.add_error(f"Contenuto inatteso in hello.html: {body!r}")


if __name__ == "__main__":
    main()
