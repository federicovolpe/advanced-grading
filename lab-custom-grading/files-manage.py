#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH124 "files-manage" (sku rh0016l,
RH124 sezione 7.2 "Manage Files with Command-line Tools"), sprovvista di
`lab grade` ufficiale. Nessuna materials/solutions ne' resources.txt:
specifica presa dal testo della guida (RH124 7.2, passi 2-7), eseguita
interamente sull'host servera nella home di student.

Stato finale atteso a fine esercizio:
- Music/, Pictures/, Videos/ contengono rispettivamente i 6 file
  songN.mp3, snapN.jpg, filmN.avi (spostati con mv dalla home).
- friends/, family/, work/ sono state create al passo 4, popolate con cp
  ai passi 5-6, e infine RIMOSSE con `rm -rf` al passo 7.2 (pulizia
  finale): a esercizio completato non devono piu' esistere.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, file_exists

LAB_NAME = "files-manage"
HOST = "servera"

_MEDIA_DIRS = {
    "Music": [f"song{i}.mp3" for i in range(1, 7)],
    "Pictures": [f"snap{i}.jpg" for i in range(1, 7)],
    "Videos": [f"film{i}.avi" for i in range(1, 7)],
}
_CLEANED_UP_DIRS = ["friends", "family", "work"]


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (host: {HOST})")

    for directory, files in _MEDIA_DIRS.items():
        with GradingStep(f"~/{directory} contiene i file attesi") as step:
            for f in files:
                if not file_exists(f"~/{directory}/{f}", host=HOST):
                    step.add_error(f"Manca ~/{directory}/{f}")

    for directory in _CLEANED_UP_DIRS:
        with GradingStep(f"~/{directory} e' stata rimossa (pulizia finale)") as step:
            if file_exists(f"~/{directory}", host=HOST):
                step.fail(
                    f"~/{directory} esiste ancora: il passo 7.2 (rm -rf) non e' stato completato"
                )

    with GradingStep("Nessun file multimediale residuo nella home") as step:
        result = run("ls ~/*.mp3 ~/*.jpg ~/*.avi 2>/dev/null", host=HOST)
        leftover = result.stdout.strip()
        if leftover:
            step.add_error(f"File non spostati trovati nella home: {leftover}")


if __name__ == "__main__":
    main()
