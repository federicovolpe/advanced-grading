#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "scripts-write" (sezione PDF
1.4 "Write Simple Bash Scripts", pag. 28-30), sprovvista di `lab grade`
ufficiale. Nessuna materials/solutions ne' resources.txt: specifica presa
dal testo della guida, su servera.

Stato finale atteso (passo 3.1): ~/firstscript.sh esiste, eseguibile,
contiene i comandi lsblk/df -h con le intestazioni richieste; eseguendolo
produce ~/output.txt con le sezioni "LIST BLOCK DEVICES" e "FILESYSTEM FREE
SPACE STATUS" (i valori numerici di lsblk/df variano da sistema a sistema,
quindi si verifica solo la struttura/intestazioni, non i numeri).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, file_exists

HOST = "servera"
SCRIPT_PATH = "~/firstscript.sh"
OUTPUT_PATH = "~/output.txt"


def main():
    print(f"🔧 Grading personalizzato per 'scripts-write' (host: {HOST})")

    with GradingStep(f"{SCRIPT_PATH} esiste ed e' eseguibile") as step:
        if not file_exists(SCRIPT_PATH, host=HOST):
            step.fail(f"{SCRIPT_PATH} non trovato")
        elif run(f"test -x {SCRIPT_PATH}", host=HOST).returncode != 0:
            step.fail(f"{SCRIPT_PATH} esiste ma non e' eseguibile")

    with GradingStep(f"{SCRIPT_PATH} include i comandi richiesti (lsblk, df -h)") as step:
        content = run(f"cat {SCRIPT_PATH}", host=HOST).stdout
        if "lsblk" not in content:
            step.add_error("Comando 'lsblk' non trovato nello script")
        if "df -h" not in content:
            step.add_error("Comando 'df -h' non trovato nello script")

    with GradingStep(f"{OUTPUT_PATH} contiene le sezioni attese generate dallo script") as step:
        content = run(f"cat {OUTPUT_PATH}", host=HOST).stdout
        if not content:
            step.fail(f"{OUTPUT_PATH} non trovato o vuoto")
        else:
            for marker in (
                "This is my first bash script",
                "LIST BLOCK DEVICES",
                "FILESYSTEM FREE SPACE STATUS",
            ):
                if marker not in content:
                    step.add_error(f"Sezione attesa '{marker}' non trovata in {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
