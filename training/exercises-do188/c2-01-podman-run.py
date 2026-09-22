"""
Cap. 2 — Podman Basics: Creating Containers with Podman
Avvia un container in background pubblicando una porta sull'host.

Non richiede un cluster: tutto lo stato e' locale (Podman sulla workstation).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import (
    GradingStep, podman, podman_reset, podman_container,
    container_is_running, container_port_mappings, run_cli,
)

IMAGE = "registry.access.redhat.com/ubi9/httpd-24"
NAME = "training-webserver"

TASK = f"""\
Avvia in background un container chiamato esattamente "{NAME}" dall'immagine
"{IMAGE}", pubblicando la porta 8080 del container sulla porta 8080 dell'host.

Comando suggerito (1):
  podman run -d --name {NAME} -p 8080:8080 {IMAGE}
"""

CHAPTER = "Cap. 2 — Podman Basics"
TITLE = "Avvia un container con Podman"
PROJECT = None


def setup():
    podman_reset(containers=[NAME])


def grade():
    c = podman_container(NAME)
    with GradingStep(f"Il container {NAME} esiste") as step:
        if not c:
            step.fail(f"Container '{NAME}' non trovato")

    with GradingStep(f"Il container {NAME} e' in esecuzione") as step:
        if not container_is_running(NAME):
            step.fail("Container non in stato 'running'")

    with GradingStep(f"Usa l'immagine {IMAGE}") as step:
        if not c:
            step.fail("Container non trovato")
        else:
            image_name = (c.get("ImageName") or "")
            if IMAGE not in image_name:
                step.add_error(f"immagine effettiva: {image_name!r}")

    with GradingStep("La porta 8080 e' pubblicata sull'host come 8080") as step:
        ports = container_port_mappings(NAME)
        host_ports = ports.get("8080/tcp", [])
        if "8080" not in host_ports:
            step.add_error(f"porte pubblicate per 8080/tcp: {host_ports}")


def cleanup():
    podman_reset(containers=[NAME])


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
