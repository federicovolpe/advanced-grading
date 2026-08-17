#!/usr/bin/env python3
"""
Grading "custom" per la LAB finale comprehensive-review (Cap. 10), sprovvista
di `lab grade` ufficiale (la classe ComprehensiveReview implementa solo
start()/finish()).

Anche qui la specifica e' del tutto esplicita nei watch_items definiti da
start() (do188/comprehensive-review.py, che usa le stesse funzioni di
do188/common/watch_functions.py viste in compose-lab): tre container Podman
puri (non Compose, quindi nomi volume/rete SENZA prefisso di progetto) che
compongono l'app "Beeper":

- beeper-db (Postgres): env POSTGRESQL_USER=beeper/PASSWORD=beeper123/
  DATABASE=beeper, solo sulla rete beeper-backend, volume beeper-data su
  /var/lib/pgsql/data;
- beeper-api: env DB_HOST=beeper-db, risponde 200 su
  http://localhost:8080/api/beeps DA DENTRO il container stesso (podman exec
  curl), reti beeper-backend + beeper-frontend;
- beeper-ui: solo rete beeper-frontend, porta host 8080 -> 8080 container,
  GET / contiene "<title>Beeper</title>", GET /api/beeps raggiungibile
  dall'host (proxato dalla UI verso l'api).

I due Containerfile in materials/solutions/comprehensive-review/ (build
multi-stage Maven/OpenJDK per l'API, npm/nginx per la UI) confermano che le
env vars/porte sopra sono proprio quelle che lo studente deve impostare in
fase di `podman run`, non valori di default dell'immagine.

Uso: comprehensive-review.py   (nessun progetto OpenShift: solo Podman)
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
    http_get,
    podman_exec,
)

LAB_NAME = "comprehensive-review"

DB_CONTAINER = "beeper-db"
API_CONTAINER = "beeper-api"
UI_CONTAINER = "beeper-ui"

BACK_NETWORK = "beeper-backend"
FRONT_NETWORK = "beeper-frontend"

DB_VOLUME = "beeper-data"
DB_VOLUME_DEST = "/var/lib/pgsql/data"

DB_ENV = {
    "POSTGRESQL_USER": "beeper",
    "POSTGRESQL_PASSWORD": "beeper123",
    "POSTGRESQL_DATABASE": "beeper",
}
API_ENV = {"DB_HOST": "beeper-db"}


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    with GradingStep(f"'{DB_CONTAINER}' e' in esecuzione con le env vars corrette") as step:
        if not container_is_running(DB_CONTAINER):
            step.fail(f"Container '{DB_CONTAINER}' non in esecuzione")
        else:
            env = container_env(DB_CONTAINER)
            for key, value in DB_ENV.items():
                if env.get(key) != value:
                    step.add_error(f"Env var {key} errata (trovata: {env.get(key)!r})")

    with GradingStep(f"'{DB_CONTAINER}' e' collegato solo alla rete '{BACK_NETWORK}'") as step:
        if not container_is_running(DB_CONTAINER):
            step.fail(f"Container '{DB_CONTAINER}' non in esecuzione")
        else:
            networks = container_networks(DB_CONTAINER)
            if networks != {BACK_NETWORK}:
                step.add_error(f"Reti trovate: {sorted(networks)}, atteso solo ['{BACK_NETWORK}']")

    with GradingStep(f"Il volume '{DB_VOLUME}' e' montato su {DB_VOLUME_DEST}") as step:
        if not container_is_running(DB_CONTAINER):
            step.fail(f"Container '{DB_CONTAINER}' non in esecuzione")
        else:
            mounts = container_mounts(DB_CONTAINER)
            found = any(
                m.get("Type") == "volume"
                and m.get("Name") == DB_VOLUME
                and m.get("Destination") == DB_VOLUME_DEST
                for m in mounts
            )
            if not found:
                step.add_error(f"Volume '{DB_VOLUME}' non montato su {DB_VOLUME_DEST}")

    with GradingStep(f"'{API_CONTAINER}' e' in esecuzione con DB_HOST corretto") as step:
        if not container_is_running(API_CONTAINER):
            step.fail(f"Container '{API_CONTAINER}' non in esecuzione")
        else:
            env = container_env(API_CONTAINER)
            for key, value in API_ENV.items():
                if env.get(key) != value:
                    step.add_error(f"Env var {key} errata (trovata: {env.get(key)!r})")

    with GradingStep(f"'{API_CONTAINER}' e' collegato a '{BACK_NETWORK}' e '{FRONT_NETWORK}'") as step:
        if not container_is_running(API_CONTAINER):
            step.fail(f"Container '{API_CONTAINER}' non in esecuzione")
        else:
            networks = container_networks(API_CONTAINER)
            if networks != {BACK_NETWORK, FRONT_NETWORK}:
                step.add_error(
                    f"Reti trovate: {sorted(networks)}, atteso ['{BACK_NETWORK}', '{FRONT_NETWORK}']"
                )

    with GradingStep(f"'{API_CONTAINER}' risponde 200 su /api/beeps (verificato dal suo interno)") as step:
        if not container_is_running(API_CONTAINER):
            step.fail(f"Container '{API_CONTAINER}' non in esecuzione")
        else:
            result = podman_exec(API_CONTAINER, "curl", "-Is", "http://localhost:8080/api/beeps")
            if result.returncode != 0 or "200" not in result.stdout:
                step.add_error("La richiesta curl interna a /api/beeps non ha risposto 200")

    with GradingStep(f"'{UI_CONTAINER}' e' collegato solo alla rete '{FRONT_NETWORK}'") as step:
        if not container_is_running(UI_CONTAINER):
            step.fail(f"Container '{UI_CONTAINER}' non in esecuzione")
        else:
            networks = container_networks(UI_CONTAINER)
            if networks != {FRONT_NETWORK}:
                step.add_error(f"Reti trovate: {sorted(networks)}, atteso solo ['{FRONT_NETWORK}']")

    with GradingStep(f"'{UI_CONTAINER}' pubblica la porta host 8080 sulla 8080 del container") as step:
        if not container_is_running(UI_CONTAINER):
            step.fail(f"Container '{UI_CONTAINER}' non in esecuzione")
        else:
            ports = container_port_mappings(UI_CONTAINER)
            if "8080" not in ports.get("8080/tcp", []):
                step.add_error("Porta 8080 (host) -> 8080 (container) non trovata")

    with GradingStep("GET http://localhost:8080/ contiene '<title>Beeper</title>'") as step:
        ok, body = http_get("http://localhost:8080/")
        if not ok:
            step.fail("La richiesta a http://localhost:8080/ e' fallita")
        elif "<title>Beeper</title>" not in body:
            step.add_error("La pagina non contiene il titolo atteso")

    with GradingStep("GET http://localhost:8080/api/beeps e' raggiungibile via proxy UI") as step:
        ok, _ = http_get("http://localhost:8080/api/beeps")
        if not ok:
            step.add_error("La richiesta a /api/beeps (via UI) e' fallita")


if __name__ == "__main__":
    main()
