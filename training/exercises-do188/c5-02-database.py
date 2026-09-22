"""
Cap. 5 — Persisting Data: Working with Databases.
Avvia un database containerizzato con le variabili d'ambiente richieste E un
volume dedicato per la persistenza dei dati, poi verifica che risponda
davvero alle query (non solo che il container sia "running": un container DB
mal configurato puo' restare up ma con l'inizializzazione fallita).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import (
    GradingStep, podman_reset, podman_container, container_is_running,
    container_mounts, container_env, podman_exec, run_cli,
)

IMAGE = "docker.io/library/mysql:8"
NAME = "training-db"
VOLUME = "training-db-data"
ROOT_PASSWORD = "training"
DB_NAME = "trainingdb"
DATA_PATH = "/var/lib/mysql"

TASK = f"""\
Avvia in background un container MySQL chiamato "{NAME}" dall'immagine
"{IMAGE}", con:
  - variabile d'ambiente MYSQL_ROOT_PASSWORD={ROOT_PASSWORD}
  - variabile d'ambiente MYSQL_DATABASE={DB_NAME}
  - il volume "{VOLUME}" montato su {DATA_PATH} (persistenza dei dati)

Comandi suggeriti (2):
  podman volume create {VOLUME}
  podman run -d --name {NAME} \\
      -e MYSQL_ROOT_PASSWORD={ROOT_PASSWORD} -e MYSQL_DATABASE={DB_NAME} \\
      -v {VOLUME}:{DATA_PATH}:Z {IMAGE}

Nota: dopo l'avvio, MySQL impiega qualche secondo a inizializzarsi — il
grading ricontrolla automaticamente ogni pochi secondi.
"""

CHAPTER = "Cap. 5 — Persisting Data"
TITLE = "Avvia un database con dati persistenti su volume"
PROJECT = None


def setup():
    podman_reset(containers=[NAME], volumes=[VOLUME])


def grade():
    c = podman_container(NAME)

    with GradingStep(f"Il container {NAME} e' in esecuzione") as step:
        if not c or not container_is_running(NAME):
            step.fail(f"Container '{NAME}' non trovato o non in esecuzione")

    with GradingStep("Le variabili d'ambiente MYSQL_ROOT_PASSWORD/MYSQL_DATABASE sono corrette") as step:
        if not c:
            step.fail("Container non trovato")
        else:
            env = container_env(NAME)
            if env.get("MYSQL_ROOT_PASSWORD") != ROOT_PASSWORD:
                step.add_error(f"MYSQL_ROOT_PASSWORD = {env.get('MYSQL_ROOT_PASSWORD')!r}")
            if env.get("MYSQL_DATABASE") != DB_NAME:
                step.add_error(f"MYSQL_DATABASE = {env.get('MYSQL_DATABASE')!r}")

    with GradingStep(f"Il volume {VOLUME} e' montato su {DATA_PATH}") as step:
        if not c:
            step.fail("Container non trovato")
        else:
            mounted = any(
                m.get("Name") == VOLUME and m.get("Destination") == DATA_PATH
                for m in container_mounts(NAME)
            )
            if not mounted:
                step.add_error(f"mount trovati: {container_mounts(NAME)}")

    with GradingStep(f"Il database {DB_NAME} risponde alle query") as step:
        if not c or not container_is_running(NAME):
            step.fail("Container non in esecuzione")
        else:
            result = podman_exec(
                NAME, "mysql", f"-uroot", f"-p{ROOT_PASSWORD}",
                "-N", "-e", "SHOW DATABASES;",
            )
            databases = (result.stdout or "").split()
            if result.returncode != 0:
                step.add_error(f"query fallita (il DB potrebbe non essere ancora pronto): {result.stderr.strip()[:200]}")
            elif DB_NAME not in databases:
                step.add_error(f"database trovati: {databases}")


def cleanup():
    podman_reset(containers=[NAME], volumes=[VOLUME])


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
