#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise basics-creating (corso DO188, "2.2.
Guided Exercise Creating Containers with Podman"), priva di `lab grade`
ufficiale. Fonte: testo integrale della guida fornito dall'utente
(DO188-RHOCP4.22-en-2-20260903).

La guida ha tre parti:
  1. `podman run --rm registry.lab.example.com:8443/ubi10/ubi:10.0 cat
     /etc/os-release` — container USA-E-GETTA (--rm), vive una frazione di
     secondo: un polling ogni 30s su 'podman ps' non lo vedrebbe MAI, per
     quanto lo studente lo esegua correttamente. Verificato dal vivo:
     'podman_ever_started()' (registro eventi di Podman) lo trova comunque,
     perche' l'evento resta registrato anche dopo che il container e' sparito.
  2. Stessa cosa con '-e GREET=Hello -e NAME="Red Hat" ... printenv GREET NAME'
     (stessa immagine base del punto 1: gli eventi Podman non registrano il
     comando/gli env eseguiti nel container, solo che un container da
     quell'immagine e' partito — non possiamo quindi distinguere con
     certezza il punto 1 dal punto 2 a posteriori. Per non inventare una
     distinzione che non possiamo verificare, gradiamo insieme "e' stato
     eseguito almeno un run da questa immagine", non i due singoli comandi).
  3. `podman run --rm -d -p 8080:8080 registry.lab.example.com:8443/ubi9/
     httpd-24` — a differenza dei primi due, questo resta IN ESECUZIONE in
     background fino a 'lab finish' (la guida stessa lo verifica con 'podman
     ps' subito dopo) — qui un controllo dal vivo "sul momento" (come
     pods-containers in DO180) funziona perfettamente, senza bisogno del
     registro eventi.
"""
import sys
import os
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (
    GradingStep,
    podman_image,
    podman_container,
    podman_ever_started,
    container_port_mappings,
    attempt_started_at,
)

LAB_NAME = "basics-creating"
UBI_IMAGE = "registry.lab.example.com:8443/ubi10/ubi:10.0"
HTTPD_IMAGE = "registry.lab.example.com:8443/ubi9/httpd-24"
HTTPD_PORT = "8080"


def _running_httpd_container():
    """Cerca un container in esecuzione dall'immagine httpd con la porta
    8080 pubblicata — nessun --name nel comando suggerito dalla guida, quindi
    cerchiamo per caratteristiche (immagine + porta) fra tutti i container
    in esecuzione, non per nome fisso. ('podman ps --filter publish=...' non
    e' un filtro valido su questa versione di Podman — verificato dal vivo,
    'Error: publish is an invalid filter' — per questo filtriamo lato
    Python invece di delegarlo a Podman.)"""
    result = subprocess.run(
        ["podman", "ps", "--format", "{{.ID}}"], capture_output=True, text=True,
    )
    for cid in result.stdout.split():
        c = podman_container(cid)
        if not c or HTTPD_IMAGE not in (c.get("ImageName") or ""):
            continue
        if HTTPD_PORT in container_port_mappings(cid).get(f"{HTTPD_PORT}/tcp", []):
            return c
    return None


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    since = attempt_started_at(LAB_NAME)

    with GradingStep(f"L'immagine {UBI_IMAGE} e' stata scaricata") as step:
        if not podman_image(UBI_IMAGE):
            step.fail("Immagine non trovata localmente — serve un 'podman pull'")

    with GradingStep("E' stato eseguito almeno un container da quell'immagine (podman run --rm ...)") as step:
        if not podman_ever_started(image=UBI_IMAGE, since=since):
            step.fail("Nessun avvio registrato per questo tentativo (registro eventi Podman)")

    with GradingStep(f"Il server httpd e' in esecuzione in background sulla porta {HTTPD_PORT}") as step:
        if not _running_httpd_container():
            step.fail(f"Nessun container in esecuzione da '{HTTPD_IMAGE}' con la porta {HTTPD_PORT} pubblicata")


if __name__ == "__main__":
    main()
