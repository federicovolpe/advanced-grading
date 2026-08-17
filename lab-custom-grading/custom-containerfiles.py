#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise custom-containerfiles (corso DO188),
priva di `lab grade` ufficiale (la classe CustomContainerfiles implementa
solo start()/finish()).

CONFIDENZA DELLA FONTE: esiste `materials/solutions/custom-containerfiles/`
con i 3 Containerfile di riferimento (-bad, -better, -best), letti per
intero. Non esiste un `materials/labs/custom-containerfiles/` (lo studente
scrive i Containerfile da zero), ma i container source copiati da start()
("hello-server", "podman-ubi9.5") sono la stessa identica app Node.js/
Fastify usata da tutte e 3 le soluzioni, e il suo codice (server.ts) e'
leggibile per intero:

    const port = process.env.SERVER_PORT ?? 3000;
    server.get("/greet", async () => ({ hello: "world" }));
    server.listen(port, "0.0.0.0");

Questo permette un test funzionale via HTTP identico e affidabile per tutti
e 3 i container (bad/better/best): devono essere in esecuzione, pubblicare
la porta 3000 (richiesta libera da start()) e rispondere su GET /greet con
{"hello":"world"} — indipendentemente da come internamente ciascun
Containerfile installa Node/npm (che e' l'unica differenza reale tra
-bad/-better, puramente stilistica/best-practice nel Containerfile, non
osservabile a runtime).

Solo Containerfile-best introduce differenze CONFERMATE anche nello stato
finale del container (non solo nello stile del Containerfile), quindi solo
per "hello-best" verifico anche, leggendo i valori esatti dal file reale:
  ENV SERVER_PORT=3000
  ENV NODE_ENV="production"
  WORKDIR /opt/app-root/src
  LABEL com.example.environment="production"
  LABEL com.example.version="0.0.1"
  LABEL org.opencontainers.image.authors=... (verifico solo la presenza della
    chiave, non il valore: nel file e' il placeholder letterale "Your Name",
    chiaramente un segnaposto per il nome dell'autore e non un valore che ha
    senso imporre allo studente).

Per "hello-bad" e "hello-better" non c'e' altro da verificare a runtime: la
guida chiede di confrontare stile/best practice dei Containerfile, non
producono differenze osservabili nel container in esecuzione.

Uso: custom-containerfiles.py   (nessun progetto OpenShift, esercizio Podman)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (
    GradingStep,
    container_env,
    container_is_running,
    container_port_mappings,
    http_get,
    podman_container,
)

LAB_NAME = "custom-containerfiles"
CONTAINERS = ["hello-bad", "hello-better", "hello-best"]
PORT = "3000"

BEST_CONTAINER = "hello-best"
BEST_EXPECTED_ENV = {"SERVER_PORT": "3000", "NODE_ENV": "production"}
BEST_EXPECTED_WORKDIR = "/opt/app-root/src"
BEST_EXPECTED_LABELS = {
    "com.example.environment": "production",
    "com.example.version": "0.0.1",
}
BEST_AUTHOR_LABEL_KEY = "org.opencontainers.image.authors"


def _published_on_3000(name):
    ports = container_port_mappings(name)
    published = {p for hosts in ports.values() for p in hosts if p}
    return PORT in published


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    for name in CONTAINERS:
        with GradingStep(f"Il container '{name}' e' in esecuzione e pubblica la porta {PORT}") as step:
            if not container_is_running(name):
                step.fail(f"Container '{name}' non trovato o non in esecuzione")
            elif not _published_on_3000(name):
                step.add_error(
                    f"Nessuna porta pubblicata su {PORT} host "
                    f"(mapping trovati: {container_port_mappings(name)})"
                )

        with GradingStep(f"Il container '{name}' risponde su GET /greet con {{\"hello\":\"world\"}}") as step:
            if not container_is_running(name):
                step.fail(f"Container '{name}' non in esecuzione")
            else:
                ok, body = http_get(f"http://localhost:{PORT}/greet")
                if not ok:
                    step.fail(f"GET http://localhost:{PORT}/greet non ha risposto (HTTP)")
                elif '"hello"' not in body or '"world"' not in body:
                    step.add_error(f"Risposta inattesa da /greet: {body!r}")

    with GradingStep(
        f"'{BEST_CONTAINER}': env, WORKDIR e label sono quelli del Containerfile-best"
    ) as step:
        if not container_is_running(BEST_CONTAINER):
            step.fail(f"Container '{BEST_CONTAINER}' non in esecuzione")
        else:
            env = container_env(BEST_CONTAINER)
            for key, expected in BEST_EXPECTED_ENV.items():
                if env.get(key) != expected:
                    step.add_error(f"Env {key}={env.get(key)!r}, attesa {expected!r}")

            c = podman_container(BEST_CONTAINER)
            config = c.get("Config", {}) if c else {}
            workdir = config.get("WorkingDir")
            if workdir != BEST_EXPECTED_WORKDIR:
                step.add_error(f"WorkingDir={workdir!r}, atteso {BEST_EXPECTED_WORKDIR!r}")

            labels = config.get("Labels") or {}
            for key, expected in BEST_EXPECTED_LABELS.items():
                if labels.get(key) != expected:
                    step.add_error(f"Label {key}={labels.get(key)!r}, attesa {expected!r}")
            if BEST_AUTHOR_LABEL_KEY not in labels:
                step.add_error(f"Label '{BEST_AUTHOR_LABEL_KEY}' assente")


if __name__ == "__main__":
    main()
