#!/usr/bin/env python3
"""
Grading "custom" per la lab guidata (Guided Exercise) custom-rootless,
sprovvista di `lab grade` ufficiale (la classe CustomRootless nel pacchetto
do188 implementa solo start()/finish(), non grade()).

A differenza degli altri esercizi Podman di questo corso, qui NON c'e' nulla
di verificabile "in esecuzione" a fine esercizio: la guida (Cap. 4.6) chiede
di costruire l'immagine "gitea" sia come utente student (rootless, container
"gitea") sia con `sudo podman build` (rootful, container "root-gitea"), ma
entrambi i container vengono fermati durante l'esercizio stesso, e finish()
li rimuove comunque (steps.force_remove_containers("root-gitea", "gitea")).
Cio' che persiste fino a `lab finish` sono le due IMMAGINI locali costruite
a partire da materials/container-sources/gitea/Containerfile:
"localhost/gitea:latest" nel namespace di student e la stessa immagine, ma
costruita da root, visibile solo a `sudo podman images` (nessun tag diverso
e' definito nel modulo ufficiale: il nome "localhost/gitea:latest" e' quello
confermato dalla guida testuale, non deducibile dal solo .py).

Richiede che questo script venga eseguito con privilegi sudo passwordless
(come e' tipico sulla workstation del corso), perche' il controllo
sull'immagine rootful usa `sudo podman inspect`.

Uso: custom-rootless.py   (nessun progetto OpenShift: e' un esercizio Podman)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, podman_image

LAB_NAME = "custom-rootless"
IMAGE = "localhost/gitea:latest"


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    with GradingStep(f"L'immagine '{IMAGE}' esiste per l'utente corrente (rootless)") as step:
        if podman_image(IMAGE, sudo=False) is None:
            step.fail(f"Immagine '{IMAGE}' non trovata (podman images)")

    with GradingStep(f"L'immagine '{IMAGE}' esiste anche per root (rootful)") as step:
        if podman_image(IMAGE, sudo=True) is None:
            step.fail(f"Immagine '{IMAGE}' non trovata (sudo podman images)")


if __name__ == "__main__":
    main()
