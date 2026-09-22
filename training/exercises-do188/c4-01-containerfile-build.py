"""
Cap. 4 — Custom Container Images: Create Images with Containerfiles.
Scrivi un Containerfile e costruisci un'immagine personalizzata, verificando
il risultato FUNZIONALMENTE (un container avviato da quell'immagine produce
il contenuto atteso), non solo la presenza del tag — cosi' uno studente non
puo' superare il check taggando semplicemente l'immagine base senza scrivere
davvero il Containerfile.
"""
import sys, os, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, podman, podman_reset, podman_image, run_cli

BASE_IMAGE = "registry.access.redhat.com/ubi9/ubi:latest"
BUILD_DIR = os.path.expanduser("~/training-containerfile")
IMAGE_TAG = "training/custom-image:v1"
MARKER_CONTENT = "hello-training"

TASK = f"""\
Crea un Containerfile in "{BUILD_DIR}/Containerfile" che parte da
"{BASE_IMAGE}" e crea il file /training-marker.txt con dentro esattamente il
testo "{MARKER_CONTENT}". Costruisci l'immagine con tag "{IMAGE_TAG}".

Comandi suggeriti (2, dopo aver scritto il Containerfile):
  cat > {BUILD_DIR}/Containerfile <<'EOF'
  FROM {BASE_IMAGE}
  RUN echo "{MARKER_CONTENT}" > /training-marker.txt
  EOF
  podman build -t {IMAGE_TAG} {BUILD_DIR}
"""

CHAPTER = "Cap. 4 — Custom Container Images"
TITLE = "Costruisci un'immagine da un Containerfile"
PROJECT = None


def setup():
    podman_reset(images=[IMAGE_TAG])
    shutil.rmtree(BUILD_DIR, ignore_errors=True)
    os.makedirs(BUILD_DIR, exist_ok=True)
    if not podman_image(BASE_IMAGE):
        podman("pull", BASE_IMAGE, check=True)


def grade():
    with GradingStep(f"L'immagine {IMAGE_TAG} esiste") as step:
        if not podman_image(IMAGE_TAG):
            step.fail(f"Immagine '{IMAGE_TAG}' non trovata — serve 'podman build'")

    with GradingStep("Il contenuto del file creato nel Containerfile e' corretto") as step:
        if not podman_image(IMAGE_TAG):
            step.fail("Immagine non trovata")
        else:
            result = podman(
                "run", "--rm", IMAGE_TAG, "cat", "/training-marker.txt",
            )
            actual = (result.stdout or "").strip()
            if result.returncode != 0:
                step.add_error(f"impossibile leggere /training-marker.txt: {result.stderr.strip()}")
            elif actual != MARKER_CONTENT:
                step.add_error(f"contenuto trovato: {actual!r}, atteso: {MARKER_CONTENT!r}")


def cleanup():
    podman_reset(images=[IMAGE_TAG])
    shutil.rmtree(BUILD_DIR, ignore_errors=True)


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
