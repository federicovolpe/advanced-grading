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

Uso: custom-advanced.py   (nessun progetto OpenShift: e' un esercizio Podman)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (
    GradingStep,
    container_env,
    container_is_running,
    container_mounts,
    podman_container,
)

LAB_NAME = "custom-advanced"
CONTAINER = "custom-advanced"
EXPECTED_FILE_ENV = "/redhat/materials/numbers.txt"
EXPECTED_WORKDIR = "/redhat"
EXPECTED_USER = "default"
EXPECTED_VOLUME_DEST = "/redhat/materials"


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    with GradingStep(f"Il container '{CONTAINER}' e' in esecuzione") as step:
        if not container_is_running(CONTAINER):
            step.fail(f"Container '{CONTAINER}' non trovato o non in esecuzione")

    with GradingStep("La variabile d'ambiente FILE e' impostata correttamente") as step:
        if not container_is_running(CONTAINER):
            step.fail(f"Container '{CONTAINER}' non in esecuzione")
        else:
            env = container_env(CONTAINER)
            if env.get("FILE") != EXPECTED_FILE_ENV:
                step.add_error(
                    f"FILE={env.get('FILE')!r}, attesa {EXPECTED_FILE_ENV!r} "
                    "(senza questa env var main.py termina con RuntimeError)"
                )

    with GradingStep("WORKDIR e USER del container sono quelli attesi") as step:
        if not container_is_running(CONTAINER):
            step.fail(f"Container '{CONTAINER}' non in esecuzione")
        else:
            c = podman_container(CONTAINER)
            config = c.get("Config", {}) if c else {}
            workdir = config.get("WorkingDir")
            user = config.get("User")
            if workdir != EXPECTED_WORKDIR:
                step.add_error(f"WorkingDir={workdir!r}, atteso {EXPECTED_WORKDIR!r}")
            if user != EXPECTED_USER:
                step.add_error(f"User={user!r}, atteso {EXPECTED_USER!r}")

    with GradingStep("Il volume /redhat/materials (da VOLUME nel Containerfile) e' montato") as step:
        if not container_is_running(CONTAINER):
            step.fail(f"Container '{CONTAINER}' non in esecuzione")
        else:
            mounts = container_mounts(CONTAINER)
            destinations = [m.get("Destination") for m in mounts]
            if EXPECTED_VOLUME_DEST not in destinations:
                step.add_error(
                    f"Nessun mount con destinazione {EXPECTED_VOLUME_DEST!r} "
                    f"(mount trovati: {destinations})"
                )

    with GradingStep("Il comando eseguito dal container include main.py") as step:
        if not container_is_running(CONTAINER):
            step.fail(f"Container '{CONTAINER}' non in esecuzione")
        else:
            c = podman_container(CONTAINER)
            cmd = (c.get("Config", {}) or {}).get("Cmd") or []
            joined = " ".join(cmd)
            if "main.py" not in joined:
                step.add_error(f"Cmd={cmd!r} non contiene 'main.py'")


if __name__ == "__main__":
    main()
