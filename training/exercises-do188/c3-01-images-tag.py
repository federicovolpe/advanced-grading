"""
Cap. 3 — Container Images: Container Image Registries.
Scarica un'immagine da un registry e taggala con un nome locale.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, podman, podman_reset, podman_image, run_cli

SOURCE_IMAGE = "registry.access.redhat.com/ubi9/ubi:latest"
LOCAL_TAG = "training/ubi-local:v1"

TASK = f"""\
Scarica l'immagine "{SOURCE_IMAGE}" e taggala localmente come
"{LOCAL_TAG}".

Comandi suggeriti (2):
  podman pull {SOURCE_IMAGE}
  podman tag {SOURCE_IMAGE} {LOCAL_TAG}
"""

CHAPTER = "Cap. 3 — Container Images"
TITLE = "Scarica e tagga un'immagine"
PROJECT = None


def setup():
    podman_reset(images=[LOCAL_TAG])


def grade():
    with GradingStep(f"L'immagine {SOURCE_IMAGE} e' presente localmente") as step:
        if not podman_image(SOURCE_IMAGE):
            step.fail(f"Immagine '{SOURCE_IMAGE}' non trovata — serve un 'podman pull'")

    with GradingStep(f"Esiste il tag locale {LOCAL_TAG}") as step:
        img = podman_image(LOCAL_TAG)
        if not img:
            step.fail(f"Tag '{LOCAL_TAG}' non trovato")


def cleanup():
    podman_reset(images=[LOCAL_TAG])


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
