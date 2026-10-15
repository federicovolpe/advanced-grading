#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise custom-advanced (corso DO188), priva
di `lab grade` ufficiale (la classe CustomAdvanced implementa solo
start()/finish()).

CONFIDENZA DELLA FONTE: qui esiste sia `materials/labs/custom-advanced/`
(file di partenza copiati allo studente) sia `materials/solutions/
custom-advanced/Containerfile` (la soluzione ufficiale), quindi la specifica
e' solida — e' il diff tra i due, letto per intero:

  labs/custom-advanced/Containerfile (starter, un solo stage):
      FROM .../ubi8/python-38:1-96
      USER default
      WORKDIR /redhat
      COPY /app/numbers.txt materials/numbers.txt   # file statico gia' pronto
      COPY main.py .
      CMD python3 main.py

  solutions/custom-advanced/Containerfile (soluzione, multi-stage):
      FROM .../podman-random-numbers as generator
      RUN python3 random_generator.py               # genera /app/numbers.txt
      FROM .../ubi8/python-38:1-96
      ENV FILE="/redhat/materials/numbers.txt"       # <-- aggiunta chiave
      USER default
      WORKDIR /redhat
      COPY --from=generator ... materials/numbers.txt
      COPY main.py .
      VOLUME /redhat/materials                       # <-- aggiunta chiave
      CMD python3 main.py

Il vero compito dello studente (rispetto allo starter) e' quindi: introdurre
un build stage che generi numbers.txt dinamicamente, impostare la env var
FILE letta da main.py (altrimenti main.py fallisce con RuntimeError, vedi
labs/custom-advanced/main.py), e dichiarare il volume /redhat/materials.
Questi sono i soli 3 elementi che verifico a runtime via `podman inspect`
sul container "custom-advanced" (WorkingDir e USER erano gia' nello starter,
quindi non discriminano il lavoro fatto, ma li controllo comunque perche'
sono valori concreti e verificabili con certezza dal Containerfile).

CONTAINER CHE TERMINA SUBITO: main.py aggiunge un numero a numbers.txt e
termina (exit 0, ~60ms dall'avvio, verificato dal vivo), quindi il
container non e' MAI in esecuzione quando passa un poll. La versione
precedente richiedeva 'container_is_running' per tutti i check e dava 0/5
anche a esercizio svolto bene. Ora verifico l'esecuzione dal registro
eventi di Podman (start + died con ContainerExitCode 0, per questo
tentativo) e leggo env/WORKDIR/USER/VOLUME/CMD dal container anche se
terminato, oppure, se e' stato lanciato con --rm e non esiste piu',
dall'immagine dell'ultimo avvio (VOLUME → Config.Volumes, che e' cio' che
genera il mount anonimo).

Uso: custom-advanced.py   (nessun progetto OpenShift: e' un esercizio Podman)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (
    GradingStep,
    attempt_started_at,
    podman_container,
    podman_events,
    podman_image,
)

LAB_NAME = "custom-advanced"
CONTAINER = "custom-advanced"
EXPECTED_FILE_ENV = "/redhat/materials/numbers.txt"
EXPECTED_WORKDIR = "/redhat"
EXPECTED_USER = "default"
EXPECTED_VOLUME_DEST = "/redhat/materials"


def _container_events(events, status):
    return [
        ev for ev in events
        if ev.get("Type") == "container" and ev.get("Name") == CONTAINER and ev.get("Status") == status
    ]


def _env_dict(config):
    result = {}
    for item in config.get("Env") or []:
        if "=" in item:
            k, v = item.split("=", 1)
            result[k] = v
    return result


def _source(events):
    """Ritorna (config, volumi, descrizione) dal container (anche terminato)
    o, se rimosso, dall'immagine dell'ultimo avvio; (None, None, None) se
    nessuno dei due e' disponibile."""
    c = podman_container(CONTAINER)
    if c:
        volumes = [m.get("Destination") for m in c.get("Mounts") or []]
        return c.get("Config") or {}, volumes, f"container '{CONTAINER}'"
    starts = _container_events(events, "start")
    image_ref = starts[-1].get("Image") if starts else None
    img = podman_image(image_ref) if image_ref else None
    if not img:
        return None, None, None
    config = img.get("Config") or {}
    return config, list((config.get("Volumes") or {}).keys()), f"immagine '{image_ref}'"


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    events = podman_events(since=attempt_started_at(LAB_NAME))
    config, volumes, source = _source(events)

    with GradingStep(f"Il container '{CONTAINER}' e' stato eseguito ed e' terminato senza errori") as step:
        c = podman_container(CONTAINER)
        state = (c or {}).get("State") or {}
        died = _container_events(events, "died")
        if state.get("Running"):
            pass
        elif c and state.get("StartedAt", "").startswith("0001-"):
            step.fail(f"Container '{CONTAINER}' creato ma mai avviato")
        elif c:
            if state.get("ExitCode") != 0:
                step.add_error(
                    f"Il container e' terminato con exit code {state.get('ExitCode')} "
                    f"(main.py fallisce senza la env var FILE: vedi 'podman logs {CONTAINER}')"
                )
        elif not _container_events(events, "start"):
            step.fail(f"Nessun avvio di un container '{CONTAINER}' registrato per questo tentativo")
        elif died and died[-1].get("ContainerExitCode") != 0:
            step.add_error(f"L'ultima esecuzione e' terminata con exit code {died[-1].get('ContainerExitCode')}")

    def _need_source(step):
        if config is None:
            step.fail(f"Nessun container o immagine '{CONTAINER}' da ispezionare per questo tentativo")
            return False
        return True

    with GradingStep("La variabile d'ambiente FILE e' impostata correttamente") as step:
        if _need_source(step):
            env = _env_dict(config)
            if env.get("FILE") != EXPECTED_FILE_ENV:
                step.add_error(
                    f"FILE={env.get('FILE')!r} ({source}), attesa {EXPECTED_FILE_ENV!r} "
                    "(senza questa env var main.py termina con RuntimeError)"
                )

    with GradingStep("WORKDIR e USER del container sono quelli attesi") as step:
        if _need_source(step):
            workdir = config.get("WorkingDir")
            user = config.get("User")
            if workdir != EXPECTED_WORKDIR:
                step.add_error(f"WorkingDir={workdir!r} ({source}), atteso {EXPECTED_WORKDIR!r}")
            if user != EXPECTED_USER:
                step.add_error(f"User={user!r} ({source}), atteso {EXPECTED_USER!r}")

    with GradingStep("Il volume /redhat/materials (da VOLUME nel Containerfile) e' montato") as step:
        if _need_source(step) and EXPECTED_VOLUME_DEST not in volumes:
            step.add_error(
                f"Nessun volume con destinazione {EXPECTED_VOLUME_DEST!r} "
                f"({source}, volumi trovati: {volumes})"
            )

    with GradingStep("Il comando eseguito dal container include main.py") as step:
        if _need_source(step):
            cmd = config.get("Cmd") or []
            if "main.py" not in " ".join(cmd):
                step.add_error(f"Cmd={cmd!r} ({source}) non contiene 'main.py'")


if __name__ == "__main__":
    main()
