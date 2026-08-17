#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise basics-accessing (corso DO188), priva
di `lab grade` ufficiale (la classe BasicsAccessing nel pacchetto do188
implementa solo start()/finish(), non grade()).

ATTENZIONE SULLA CONFIDENZA DELLA FONTE: per questo esercizio non esiste
ne' un `materials/solutions/basics-accessing/` ne' un `materials/labs/
basics-accessing/` (il modulo ufficiale copia solo i file del container
source "podman-nginx-helloworld" via copy_container_files(), senza materiali
specifici della lab). L'unica fonte oggettiva e':
  - do188/basics-accessing.py (start()/finish()): richiede la porta 8080
    libera, fa login al registry della classroom, copia il container source
    "podman-nginx-helloworld"; finish() rimuove forzatamente un container
    chiamato "nginx".
  - do188/materials/container-sources/podman-nginx-helloworld/Containerfile:
    immagine ubi8-minimal + nginx, EXPOSE 8080, USER 1001.

NON verifico il contenuto HTTP servito dal container: leggendo per intero il
Containerfile e nginx.conf del container source, la direttiva "root" nel
server block punta a /usr/share/nginx/html/public, mentre "ADD index.html
/usr/share/nginx/html" copia il file un livello sopra (senza "public"). Non
posso stabilire con certezza, senza il testo della guida (che non ho a
disposizione), se questo sia un mismatch intenzionale dell'esercizio (di cui
lo studente deve accorgersi/discutere) o un dettaglio ignorabile: qualsiasi
assunzione sul body restituito da una GET sarebbe un'invenzione. Mi limito
quindi, come consentito dalle istruzioni, al controllo di container+porta.

Uso: basics-accessing.py   (nessun progetto OpenShift: e' un esercizio Podman)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (
    GradingStep,
    container_is_running,
    container_port_mappings,
)

LAB_NAME = "basics-accessing"
CONTAINER = "nginx"


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


if __name__ == "__main__":
    main()
