"""
Cap. 5 — Persisting Data: Volume Mounting.
Crea un volume Podman con nome, montalo in un container e scrivi un file al
suo interno — il grading legge il file direttamente dal Mountpoint del
volume sull'host (verificato dal vivo: e' un path leggibile dal proprietario
del volume in Podman rootless, sotto ~/.local/share/containers/storage/
volumes/<nome>/_data), cosi' il check e' indipendente dal container usato
per scriverci (puo' anche essere gia' terminato).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import (
    GradingStep, podman_reset, podman_volume_exists,
    podman_volume_mountpoint, run_cli,
)

VOLUME = "training-vol"
MARKER_FILE = "marker.txt"
MARKER_CONTENT = "persisted"

TASK = f"""\
Crea un volume Podman chiamato "{VOLUME}", poi usalo per far scrivere a un
container il file "/data/{MARKER_FILE}" con dentro esattamente il testo
"{MARKER_CONTENT}".

Comandi suggeriti (2):
  podman volume create {VOLUME}
  podman run --rm -v {VOLUME}:/data:Z registry.access.redhat.com/ubi9/ubi \\
      sh -c 'echo {MARKER_CONTENT} > /data/{MARKER_FILE}'
"""

CHAPTER = "Cap. 5 — Persisting Data"
TITLE = "Crea un volume e scrivici dei dati da un container"
PROJECT = None


def setup():
    podman_reset(volumes=[VOLUME])


def grade():
    with GradingStep(f"Il volume {VOLUME} esiste") as step:
        if not podman_volume_exists(VOLUME):
            step.fail(f"Volume '{VOLUME}' non trovato")

    with GradingStep(f"Il file {MARKER_FILE} e' stato scritto nel volume con il contenuto atteso") as step:
        if not podman_volume_exists(VOLUME):
            step.fail("Volume non trovato")
        else:
            mountpoint = podman_volume_mountpoint(VOLUME)
            path = os.path.join(mountpoint or "", MARKER_FILE)
            if not mountpoint or not os.path.isfile(path):
                step.add_error(f"File non trovato in {path!r}")
            else:
                try:
                    content = open(path).read().strip()
                except OSError as exc:
                    step.add_error(f"impossibile leggere il file: {exc}")
                    content = None
                if content is not None and content != MARKER_CONTENT:
                    step.add_error(f"contenuto trovato: {content!r}, atteso: {MARKER_CONTENT!r}")


def cleanup():
    podman_reset(volumes=[VOLUME])


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
