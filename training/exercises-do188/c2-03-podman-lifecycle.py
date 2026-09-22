"""
Cap. 2 — Podman Basics: Managing the Container Lifecycle.
Un container viene avviato dal setup() gia' in esecuzione: il compito e'
fermarlo con grazia (podman stop), mantenendolo pero' nell'elenco dei
container (niente rm) cosi' da poterlo poi eventualmente far ripartire.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import (
    GradingStep, podman, podman_reset, podman_container,
    container_is_running, run_cli,
)

IMAGE = "registry.access.redhat.com/ubi9/httpd-24"
NAME = "training-lifecycle"

TASK = f"""\
Il container "{NAME}" e' gia' in esecuzione. Fermalo (senza cancellarlo:
deve restare visibile in "podman ps -a").

Comando suggerito (1):
  podman stop {NAME}
"""

CHAPTER = "Cap. 2 — Podman Basics"
TITLE = "Ferma un container mantenendolo nell'elenco"
PROJECT = None


def setup():
    podman_reset(containers=[NAME])
    podman("run", "-d", "--name", NAME, IMAGE, check=True)


def grade():
    c = podman_container(NAME)

    with GradingStep(f"Il container {NAME} esiste ancora (non cancellato)") as step:
        if not c:
            step.fail(f"Container '{NAME}' non trovato — non deve essere rimosso, solo fermato")

    with GradingStep(f"Il container {NAME} e' fermo") as step:
        if not c:
            step.fail("Container non trovato")
        elif container_is_running(NAME):
            step.add_error("il container risulta ancora in esecuzione")


def cleanup():
    podman_reset(containers=[NAME])


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
