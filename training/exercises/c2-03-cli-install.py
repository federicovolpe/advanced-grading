"""
Cap. 2 — Kubernetes and OpenShift CLI and APIs
Installa il client oc in una directory specifica (tema uscito all'esame:
posizionare i binari del client in un percorso preciso).

Nessun cluster/progetto coinvolto: lo stato verificato e' solo locale (il
binario copiato sulla workstation). Il compito NON tocca l'oc di sistema
gia' in PATH (usato da 'lab'/'training' e da tutti gli altri esercizi di
questo repo): lo studente ne fa una copia in una directory dedicata, non lo
sposta ne' lo disinstalla.
"""
import os
import shutil
import subprocess
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, run_cli

CHAPTER = "Cap. 2 — Kubernetes and OpenShift CLI and APIs"
TITLE = "Installa il client oc in una directory specifica"
PROJECT = None

TARGET_DIR = os.path.expanduser("~/oc-client")
TARGET_BIN = os.path.join(TARGET_DIR, "oc")
# Un vero binario oc pesa decine di MB: soglia bassa per scartare placeholder
# (es. uno script che si limita a stampare "Client Version" per ingannare il check).
MIN_SIZE_BYTES = 10 * 1024 * 1024

TASK = f"""\
Installa il client a riga di comando di OpenShift ("oc") nella directory
"{TARGET_DIR}", cosi' che il binario si trovi esattamente in
"{TARGET_BIN}" e funzioni correttamente.

Comandi suggeriti (2):
  mkdir -p {TARGET_DIR}
  cp "$(which oc)" {TARGET_BIN}
"""


def setup():
    shutil.rmtree(TARGET_DIR, ignore_errors=True)


def grade():
    with GradingStep(f"Il file {TARGET_BIN} esiste") as step:
        if not os.path.isfile(TARGET_BIN):
            step.fail(f"'{TARGET_BIN}' non trovato")

    with GradingStep("E' un binario oc vero (non un file segnaposto)") as step:
        if not os.path.isfile(TARGET_BIN):
            step.fail("File non trovato")
        else:
            size = os.path.getsize(TARGET_BIN)
            if size < MIN_SIZE_BYTES:
                step.add_error(
                    f"Dimensione {size} byte, un binario oc reale ne pesa "
                    f"almeno {MIN_SIZE_BYTES}"
                )
            if not os.access(TARGET_BIN, os.X_OK):
                step.add_error("Il file non ha permesso di esecuzione")

    with GradingStep("Il binario copiato funziona (oc version --client)") as step:
        if not (os.path.isfile(TARGET_BIN) and os.access(TARGET_BIN, os.X_OK)):
            step.fail("Binario non eseguibile")
        else:
            try:
                result = subprocess.run(
                    [TARGET_BIN, "version", "--client"],
                    capture_output=True, text=True, timeout=10,
                )
            except (subprocess.TimeoutExpired, OSError) as exc:
                step.add_error(f"Esecuzione fallita: {exc}")
            else:
                if result.returncode != 0 or "Client Version" not in result.stdout:
                    step.add_error(
                        f"'oc version --client' -> rc={result.returncode}, "
                        f"stdout={result.stdout.strip()!r}"
                    )


def cleanup():
    shutil.rmtree(TARGET_DIR, ignore_errors=True)


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
