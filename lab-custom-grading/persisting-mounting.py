#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise persisting-mounting, sprovvista di
`lab grade` ufficiale (la classe PersistingMounting nel pacchetto do188
implementa solo start()/finish(), non grade()).

Nessun watch_items e nessuna materials/solutions per questo esercizio: la
guida (Cap. 5.2, "Volume Mounting") chiede due verifiche in sequenza, prima
con un bind mount su ~/www (container podman-server), poi con un volume
nominato html-vol popolato da `podman volume import .../index.tar.gz` — ma
il container viene sempre fermato con Ctrl+c subito dopo il test manuale
(vedi passi 5.3 e 7.3 della guida), quindi non resta nulla in esecuzione a
fine esercizio. L'unico stato che sopravvive fino a `lab finish` e' il
volume html-vol stesso (rimosso solo da finish() -> steps.remove_volumes).

Verifica quindi solo l'esistenza del volume e il contenuto del file
index.html importato (quello dentro index.tar.gz, "Documents" — DIVERSO dal
file index.html copiato in ~/www al passo 2, che ha contenuto "Podman for
Developers" e serve solo per il test via bind mount, non gradabile perche'
non persiste).

Uso: persisting-mounting.py   (nessun progetto OpenShift: esercizio Podman)
"""

import os
import sys
import tarfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, podman_volume_exists, podman_volume_mountpoint

LAB_NAME = "persisting-mounting"
VOLUME = "html-vol"
ARCHIVE = os.path.expanduser(f"~/DO188/labs/{LAB_NAME}/index.tar.gz")


def _expected_index_html():
    """Estrae ./index.html dall'archivio fornito allo studente, senza
    scrivere file temporanei (letto direttamente dal tar in memoria)."""
    with tarfile.open(ARCHIVE) as tar:
        member = tar.getmember("./index.html")
        return tar.extractfile(member).read().decode("utf-8", errors="replace")


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    with GradingStep(f"Il volume Podman '{VOLUME}' esiste") as step:
        if not podman_volume_exists(VOLUME):
            step.fail(f"Volume '{VOLUME}' non trovato")
            mountpoint = None
        else:
            mountpoint = podman_volume_mountpoint(VOLUME)
            if not mountpoint:
                step.fail("Impossibile determinare il mountpoint del volume")

    with GradingStep(f"Il volume '{VOLUME}' contiene l'index.html importato") as step:
        if not mountpoint:
            step.fail()
        elif not os.path.isfile(ARCHIVE):
            step.fail(f"File '{ARCHIVE}' non trovato per confrontare il contenuto atteso")
        else:
            target = os.path.join(mountpoint, "index.html")
            if not os.path.isfile(target):
                step.add_error(f"'{target}' non trovato nel volume")
            else:
                with open(target, encoding="utf-8", errors="replace") as f:
                    actual = f.read()
                if actual != _expected_index_html():
                    step.add_error(
                        "Il contenuto di index.html nel volume non corrisponde "
                        "a quello di index.tar.gz"
                    )


if __name__ == "__main__":
    main()
