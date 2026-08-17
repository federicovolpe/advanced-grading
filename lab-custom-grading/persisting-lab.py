#!/usr/bin/env python3
"""
Grading "custom" per la lab guidata (Guided Exercise) persisting-lab,
sprovvista di `lab grade` ufficiale (la classe PersistingLab nel pacchetto
do188 implementa solo start()/finish(), non grade()).

La specifica viene dagli stessi watch_items che start() usa per il monitor
live (vedi do188/persisting-lab.py): un volume "postgres-vol" popolato con un
dump importato, un container "persisting-db" che lo monta su
/var/lib/pgsql/data, un backend che risponde "pong" su :8080/ping, un
frontend che serve la pagina "URL Shortener" su :3000/, e un redirect
funzionante (:8080/api/shorturl/<shortcode>) che dimostra che l'import dei
dati e' andato a buon fine.

Uso: persisting-lab.py   (nessun progetto OpenShift: e' un esercizio Podman)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (
    GradingStep,
    container_is_running,
    container_mounts,
    http_get,
    http_get_follow,
    podman_volume_exists,
    podman_volume_mountpoint,
)

LAB_NAME = "persisting-lab"
VOLUME = "postgres-vol"
DB_CONTAINER = "persisting-db"
BACKEND_CONTAINER = "persisting-backend"
FRONTEND_CONTAINER = "persisting-frontend"
BE_PORT = "8080"
FE_PORT = "3000"
DB_MOUNT_DEST = "/var/lib/pgsql/data"
SHORTCODE = "a9yi4rcl5uuzunv"


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    with GradingStep(f"Il volume '{VOLUME}' esiste ed e' stato popolato") as step:
        if not podman_volume_exists(VOLUME):
            step.fail(f"Volume '{VOLUME}' non trovato")
        else:
            mountpoint = podman_volume_mountpoint(VOLUME)
            if not mountpoint or not os.path.isdir(mountpoint):
                step.add_error(f"Mountpoint del volume '{VOLUME}' non trovato sul filesystem")
            elif not os.listdir(mountpoint):
                step.add_error(f"Il volume '{VOLUME}' e' vuoto: i dati non sono stati importati")

    with GradingStep(f"Il container '{DB_CONTAINER}' e' in esecuzione con il volume montato") as step:
        if not container_is_running(DB_CONTAINER):
            step.fail(f"Container '{DB_CONTAINER}' non in esecuzione")
        else:
            mounts = container_mounts(DB_CONTAINER)
            matching = [
                m for m in mounts
                if m.get("Name") == VOLUME and m.get("Destination") == DB_MOUNT_DEST
            ]
            if not matching:
                step.add_error(
                    f"Il volume '{VOLUME}' non risulta montato su '{DB_MOUNT_DEST}' nel container"
                )

    with GradingStep(f"Il container '{BACKEND_CONTAINER}' risponde su :{BE_PORT}/ping") as step:
        if not container_is_running(BACKEND_CONTAINER):
            step.fail(f"Container '{BACKEND_CONTAINER}' non in esecuzione")
        else:
            ok, body = http_get(f"http://localhost:{BE_PORT}/ping")
            if not ok or "pong" not in body.lower():
                step.add_error(f"http://localhost:{BE_PORT}/ping non risponde con 'pong'")

    with GradingStep(f"Il container '{FRONTEND_CONTAINER}' risponde su :{FE_PORT}/") as step:
        if not container_is_running(FRONTEND_CONTAINER):
            step.fail(f"Container '{FRONTEND_CONTAINER}' non in esecuzione")
        else:
            ok, body = http_get(f"http://localhost:{FE_PORT}/")
            if not ok or "url shortener" not in body.lower():
                step.add_error(f"http://localhost:{FE_PORT}/ non contiene 'URL Shortener'")

    with GradingStep("L'applicazione funziona end-to-end (redirect shorturl)") as step:
        url = f"http://localhost:{BE_PORT}/api/shorturl/{SHORTCODE}"
        # Il backend risponde con un redirect verso il frontend: seguiamo il
        # redirect (curl -L) esattamente come fa requests.get() nel modulo
        # ufficiale, per verificare che l'import dei dati sia stato letto.
        ok, body = http_get_follow(url)
        if not ok or "data import has been successful" not in body.lower():
            step.add_error(
                f"GET {url} (con redirect) non contiene 'Data import has been successful'"
            )


if __name__ == "__main__":
    main()
