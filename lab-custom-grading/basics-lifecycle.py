#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise basics-lifecycle (corso DO188, "2.10.
Guided Exercise Managing the Container Lifecycle"), priva di `lab grade`
ufficiale. Fonte: testo integrale della guida fornito dall'utente
(DO188-RHOCP4.22-en-2-20260903).

La guida chiede allo studente di far passare un container di nome "httpd"
per QUATTRO fasi in sequenza, ognuna delle quali SMONTA quella precedente:
  1. Crea e avvia (podman run --name httpd -d -p 8080:8080 <img>)
  2. Verifica che sia in esecuzione (podman ps / podman inspect)
  3. Fermalo (podman stop httpd) — smonta la fase 1/2
  4. Verifica che sia fermo
  5. Riavvialo (podman restart httpd) — smonta la fase 3/4
  6. Verifica che sia di nuovo in esecuzione
  7. Rimuovilo forzatamente (podman rm httpd --force) — smonta tutto il resto
  8. Verifica che non esista piu'

Un controllo dello stato ATTUALE (com'e' fatto il resto di questo repo)
funzionerebbe solo per l'ULTIMA fase: dopo la rimozione finale, "e' stato
creato e avviato" e "e' stato fermato" tornerebbero FAIL anche se lo
studente li ha eseguiti perfettamente, perche' quello stato non esiste piu'.
Usiamo percio' il registro EVENTI di Podman (podman_ever_started/
podman_events in _common.py), che resta consultabile anche dopo che il
container e' sparito, invece di 'podman ps'/'podman inspect' da soli.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (
    GradingStep,
    podman_container,
    podman_events,
    podman_ever_started,
    attempt_started_at,
)

LAB_NAME = "basics-lifecycle"
CONTAINER = "httpd"
IMAGE = "registry.lab.example.com:8443/ubi9/httpd-24"


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (container: {CONTAINER})")

    since = attempt_started_at(LAB_NAME)
    events = podman_events(since=since)
    statuses = [
        ev.get("Status") for ev in events
        if ev.get("Type") == "container" and ev.get("Name") == CONTAINER
    ]
    start_count = statuses.count("start")
    stop_count = statuses.count("died")
    restart_count = statuses.count("restart")
    removed = "remove" in statuses

    with GradingStep("Il container e' stato creato e avviato (podman run --name httpd -d -p 8080:8080 ...)") as step:
        currently_running = bool(podman_container(CONTAINER) and podman_container(CONTAINER).get("State", {}).get("Running"))
        if start_count < 1 and not currently_running:
            step.fail(f"Nessun avvio di un container '{CONTAINER}' registrato per questo tentativo")

    with GradingStep("E' stato fermato (podman stop httpd)") as step:
        if stop_count < 1:
            step.add_error(f"Nessun arresto di '{CONTAINER}' registrato (eventi visti: {statuses or 'nessuno'})")

    with GradingStep("E' stato riavviato dopo essere stato fermato (podman restart httpd)") as step:
        # 'podman restart' emette un evento 'restart' esplicito; accettiamo
        # anche un secondo 'start' dopo il primo 'died' per chi usa
        # 'podman stop' + 'podman start' invece di 'podman restart' (stesso
        # risultato finale, non e' quello il compito da gradare per nome del
        # comando).
        if restart_count < 1 and start_count < 2:
            step.add_error(f"Nessun riavvio registrato dopo l'arresto (eventi visti: {statuses or 'nessuno'})")

    with GradingStep("E' stato rimosso forzatamente ed ora non esiste piu' (podman rm httpd --force)") as step:
        if not removed:
            step.add_error("Nessuna rimozione registrata per questo tentativo")
        current = podman_container(CONTAINER)
        if current is not None:
            step.add_error(f"Il container '{CONTAINER}' esiste ancora (stato: {current.get('State', {}).get('Status')})")


if __name__ == "__main__":
    main()
