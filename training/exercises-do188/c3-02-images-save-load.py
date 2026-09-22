"""
Cap. 3 — Container Images: Managing Images.
Archivia un'immagine in un file tar e poi rimuovi il tag locale — lo stato
finale verificabile e' "tar presente, tag locale assente" (un round-trip
completo save+rmi+load non sarebbe verificabile a posteriori: il load
riporterebbe lo stato finale identico a quello di partenza, indistinguibile
da chi non ha mai rimosso l'immagine — bug di progettazione scoperto e
corretto durante il test dal vivo di questo script).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, podman, podman_reset, podman_image, run_cli

SOURCE_IMAGE = "registry.access.redhat.com/ubi9/ubi:latest"
WORK_TAG = "training/images-manage:v1"
TAR_PATH = os.path.expanduser("~/training-images-manage.tar")

TASK = f"""\
L'immagine "{WORK_TAG}" e' gia' pronta in locale. Archiviala in un file tar
e poi rimuovi il tag locale (l'immagine resta solo nel tar).

Comandi suggeriti (2):
  podman save -o {TAR_PATH} {WORK_TAG}
  podman rmi {WORK_TAG}
"""

CHAPTER = "Cap. 3 — Container Images"
TITLE = "Archivia un'immagine ed elimina il tag locale (save/rmi)"
PROJECT = None


def setup():
    podman_reset(images=[WORK_TAG])
    try:
        os.remove(TAR_PATH)
    except OSError:
        pass
    if not podman_image(SOURCE_IMAGE):
        podman("pull", SOURCE_IMAGE, check=True)
    podman("tag", SOURCE_IMAGE, WORK_TAG, check=True)


def grade():
    with GradingStep(f"E' stato creato il file tar {TAR_PATH} ('podman save')") as step:
        if not os.path.isfile(TAR_PATH) or os.path.getsize(TAR_PATH) == 0:
            step.fail("File tar non trovato o vuoto — serve 'podman save'")

    with GradingStep(f"Il tag locale {WORK_TAG} e' stato rimosso ('podman rmi')") as step:
        if podman_image(WORK_TAG):
            step.add_error(f"il tag '{WORK_TAG}' e' ancora presente nello storage locale")


def cleanup():
    podman_reset(images=[WORK_TAG])
    try:
        os.remove(TAR_PATH)
    except OSError:
        pass


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
