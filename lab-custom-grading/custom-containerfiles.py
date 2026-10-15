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

STATO CHE LA GUIDA STESSA SMONTA: lo studente avvia un container alla volta
(tutti e 3 pubblicano la porta 3000 dell'host, quindi non possono nemmeno
coesistere), lo prova con curl e lo ferma prima di passare al successivo
(spesso e' un 'podman run --rm' interrotto con Ctrl+C). Un controllo del
solo stato ATTUALE dava percio' al massimo 2-3/7 e, a fine esercizio, 0/7
(bug reale: tutti e 3 i container avviati e rimossi correttamente, nessun
check verde). Quindi, per ciascun check:
  - "e' stato avviato": registro eventi di Podman (podman_events), che
    resta consultabile anche dopo la rimozione del container;
  - "ha risposto su /greet": osservabile solo dal vivo, persistito con
    ever_true() appena un poll lo vede (il monitor fa un poll ogni ~30s,
    basta lasciare il container acceso fino al semaforo verde);
  - env/WORKDIR/label di hello-best: se il container non c'e' piu' li leggo
    dall'immagine con cui e' stato avviato (Image dell'ultimo evento
    'start', resta in 'podman images'), che e' dove il Containerfile-best
    li definisce.

Uso: custom-containerfiles.py   (nessun progetto OpenShift, esercizio Podman)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (
    GradingStep,
    attempt_started_at,
    container_is_running,
    container_port_mappings,
    ever_true,
    http_get,
    podman_container,
    podman_events,
    podman_image,
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


def _start_events(events, name):
    return [
        ev for ev in events
        if ev.get("Type") == "container" and ev.get("Name") == name and ev.get("Status") == "start"
    ]


def _env_dict(config):
    result = {}
    for item in config.get("Env") or []:
        if "=" in item:
            k, v = item.split("=", 1)
            result[k] = v
    return result


def _best_config(events):
    """Config (Env/WorkingDir/Labels) di hello-best: dal container se esiste
    ancora, altrimenti dall'immagine dell'ultimo avvio registrato. Ritorna
    (config, origine); config None se non ricostruibile."""
    c = podman_container(BEST_CONTAINER)
    if c:
        return c.get("Config") or {}, f"container '{BEST_CONTAINER}'"
    starts = _start_events(events, BEST_CONTAINER)
    if not starts:
        return None, None
    image_ref = starts[-1].get("Image")
    # Negli eventi c'e' solo il riferimento, non l'ID: se nel frattempo il
    # tag e' stato riassegnato a un'altra build leggiamo quella (marginale).
    img = podman_image(image_ref) if image_ref else None
    if not img:
        return None, image_ref
    return img.get("Config") or {}, f"immagine '{image_ref}'"


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    events = podman_events(since=attempt_started_at(LAB_NAME), event="start")

    for name in CONTAINERS:
        running = container_is_running(name)

        with GradingStep(f"Il container '{name}' e' stato avviato pubblicando la porta {PORT}") as step:
            # La porta si vede solo dal vivo (non e' negli eventi): per un
            # container gia' rimosso la conferma arriva dal check /greet.
            if not running and not _start_events(events, name):
                step.fail(f"Nessun avvio di un container '{name}' registrato per questo tentativo")
            elif running and not _published_on_3000(name):
                step.add_error(
                    f"Nessuna porta pubblicata su {PORT} host "
                    f"(mapping trovati: {container_port_mappings(name)})"
                )

        with GradingStep(f"Il container '{name}' ha risposto su GET /greet con {{\"hello\":\"world\"}}") as step:
            # Interroghiamo localhost:3000 solo se e' proprio QUESTO container
            # a pubblicarla: un altro dei tre rimasto acceso risponderebbe
            # allo stesso URL.
            # 127.0.0.1 e non 'localhost': sulla workstation 'localhost' si
            # risolve prima in ::1, dove il port forwarding rootless resetta
            # la connessione (curl non ripiega su IPv4, verificato dal vivo).
            published = running and _published_on_3000(name)
            ok, body = http_get(f"http://127.0.0.1:{PORT}/greet") if published else (False, "")
            answered = ok and '"hello"' in body and '"world"' in body
            if not ever_true(LAB_NAME, f"{name}-greet", answered):
                if not running:
                    step.fail(
                        f"'{name}' non e' in esecuzione e nessun poll l'ha visto rispondere: "
                        f"avvialo e lascialo acceso finche' questo check non diventa verde"
                    )
                elif not published:
                    step.fail(f"'{name}' non pubblica la porta {PORT} dell'host")
                elif not ok:
                    step.fail(f"GET http://127.0.0.1:{PORT}/greet non ha risposto (HTTP)")
                else:
                    step.add_error(f"Risposta inattesa da /greet: {body!r}")

    with GradingStep(
        f"'{BEST_CONTAINER}': env, WORKDIR e label sono quelli del Containerfile-best"
    ) as step:
        config, source = _best_config(events)
        if config is None:
            if source:
                step.fail(f"'{BEST_CONTAINER}' avviato da '{source}', ma quell'immagine non esiste piu'")
            else:
                step.fail(f"Nessun avvio di un container '{BEST_CONTAINER}' registrato per questo tentativo")
        else:
            env = _env_dict(config)
            for key, expected in BEST_EXPECTED_ENV.items():
                if env.get(key) != expected:
                    step.add_error(f"Env {key}={env.get(key)!r} ({source}), attesa {expected!r}")

            workdir = config.get("WorkingDir")
            if workdir != BEST_EXPECTED_WORKDIR:
                step.add_error(f"WorkingDir={workdir!r} ({source}), atteso {BEST_EXPECTED_WORKDIR!r}")

            labels = config.get("Labels") or {}
            for key, expected in BEST_EXPECTED_LABELS.items():
                if labels.get(key) != expected:
                    step.add_error(f"Label {key}={labels.get(key)!r} ({source}), attesa {expected!r}")
            if BEST_AUTHOR_LABEL_KEY not in labels:
                step.add_error(f"Label '{BEST_AUTHOR_LABEL_KEY}' assente ({source})")


if __name__ == "__main__":
    main()
