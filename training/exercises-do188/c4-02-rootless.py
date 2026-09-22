"""
Cap. 4 — Custom Container Images: Rootless Podman.
Avvia un container e verifica il comportamento rootless: il processo gira
come root (UID 0) DENTRO il container, ma e' mappato a un utente non
privilegiato SULL'HOST — verificato dal vivo con 'podman top huser' prima di
scrivere questo script (su questa workstation UID 1000/student).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import (
    GradingStep, podman, podman_reset, podman_container,
    container_is_running, podman_exec, run_cli,
)

IMAGE = "registry.access.redhat.com/ubi9/ubi:latest"
NAME = "training-rootless"

TASK = f"""\
Avvia in background un container chiamato "{NAME}" dall'immagine "{IMAGE}"
che resti in esecuzione (es. eseguendo "sleep infinity"). Verifica poi con
"podman top {NAME} huser" che, pur girando come root (UID 0) dentro il
container, sull'host sia mappato a un utente non-root (rootless Podman).

Comandi suggeriti (2):
  podman run -d --name {NAME} {IMAGE} sleep infinity
  podman top {NAME} huser
"""

CHAPTER = "Cap. 4 — Custom Container Images"
TITLE = "Verifica il mapping UID di un container rootless"
PROJECT = None


def setup():
    podman_reset(containers=[NAME])


def grade():
    with GradingStep(f"Il container {NAME} e' in esecuzione") as step:
        if not container_is_running(NAME):
            step.fail(f"Container '{NAME}' non trovato o non in esecuzione")

    with GradingStep("Dentro il container il processo gira come root (UID 0)") as step:
        if not container_is_running(NAME):
            step.fail("Container non in esecuzione")
        else:
            result = podman_exec(NAME, "id", "-u")
            uid = (result.stdout or "").strip()
            if result.returncode != 0 or uid != "0":
                step.add_error(f"UID interno trovato: {uid!r} (atteso 0)")

    with GradingStep("Sull'host il processo NON gira come root (mapping rootless)") as step:
        if not container_is_running(NAME):
            step.fail("Container non in esecuzione")
        else:
            result = podman("top", NAME, "huser")
            lines = [l.strip() for l in (result.stdout or "").splitlines() if l.strip()]
            host_users = lines[1:] if len(lines) > 1 else []
            if result.returncode != 0 or not host_users:
                step.add_error(f"impossibile leggere l'utente host: {result.stderr.strip()}")
            elif any(u in ("0", "root") for u in host_users):
                step.add_error(f"utenti host trovati: {host_users} — il container non e' rootless")


def cleanup():
    podman_reset(containers=[NAME])


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
