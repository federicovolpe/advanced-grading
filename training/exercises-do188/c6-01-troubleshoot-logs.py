"""
Cap. 6 — Troubleshooting Containers: Container Logging and Troubleshooting.
Un container si ferma subito dopo l'avvio per un comando sbagliato
(verificato dal vivo: il comando di avvio reale di questa immagine e'
'run-httpd', non 'httpd-foreground' come in altre immagini httpd simili —
usare quest'ultimo da' 'exec: httpd-foreground: not found' nei log). Il
compito e' diagnosticare via
'podman logs' e avviare un nuovo container funzionante con il comando
corretto — non modificare quello rotto, cosi' il grading puo' distinguere
"ha solo corretto il typo al volo" da "ha letto i log per capire l'errore".
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import (
    GradingStep, podman, podman_reset, podman_container,
    container_is_running, podman_logs, run_cli,
)

IMAGE = "registry.access.redhat.com/ubi9/httpd-24"
BROKEN_NAME = "training-broken"
BROKEN_CMD = "httpd-foreground"  # comando plausibile ma sbagliato per questa immagine
FIXED_NAME = "training-fixed"
FIXED_CMD = "run-httpd"

TASK = f"""\
Il container "{BROKEN_NAME}" si e' fermato subito dopo l'avvio. Controlla i
log per capire perche' (podman logs {BROKEN_NAME}), poi avvia un NUOVO
container funzionante chiamato "{FIXED_NAME}" dalla stessa immagine con il
comando corretto.

Comandi suggeriti (2, dopo aver letto i log):
  podman logs {BROKEN_NAME}
  podman run -d --name {FIXED_NAME} {IMAGE} {FIXED_CMD}
"""

CHAPTER = "Cap. 6 — Troubleshooting Containers"
TITLE = "Diagnostica un container rotto dai log e correggilo"
PROJECT = None


def setup():
    podman_reset(containers=[BROKEN_NAME, FIXED_NAME])
    podman("run", "-d", "--name", BROKEN_NAME, IMAGE, BROKEN_CMD)


def grade():
    with GradingStep(f"Il container {BROKEN_NAME} mostra l'errore atteso nei log") as step:
        logs = podman_logs(BROKEN_NAME)
        if BROKEN_CMD not in logs:
            step.add_error(f"log attuali di '{BROKEN_NAME}': {logs.strip()[:200]!r}")

    with GradingStep(f"E' stato avviato un nuovo container {FIXED_NAME} funzionante") as step:
        c = podman_container(FIXED_NAME)
        if not c or not container_is_running(FIXED_NAME):
            step.fail(f"Container '{FIXED_NAME}' non trovato o non in esecuzione")

    with GradingStep(f"{FIXED_NAME} usa il comando corretto ({FIXED_CMD})") as step:
        c = podman_container(FIXED_NAME)
        if not c:
            step.fail("Container non trovato")
        else:
            cmd = c.get("Config", {}).get("Cmd") or []
            if not any(FIXED_CMD in str(part) for part in cmd):
                step.add_error(f"comando effettivo: {cmd}")


def cleanup():
    podman_reset(containers=[BROKEN_NAME, FIXED_NAME])


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
