#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "logs-preserve" (sezione PDF
5.8 "Configure a Persistent System Journal", pag. 129-130), sprovvista di
`lab grade` ufficiale. Nessuna materials/solutions ne' resources.txt:
specifica presa dal testo della guida, su servera.

Stato finale atteso (passo 3-4): /var/log/journal esiste e contiene una
sottodirectory (nome esadecimale variabile, dipende dal machine-id) con i
file system.journal/user-*.journal — prova che systemd-journald sta
scrivendo i log su storage persistente. Il grading e' di sola lettura: non
viene mai forzato un reboot di servera (lo fa lo studente stesso al passo
4.1 della guida).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, file_exists

HOST = "servera"
JOURNAL_DIR = "/var/log/journal"


def main():
    print(f"🔧 Grading personalizzato per 'logs-preserve' (host: {HOST})")

    with GradingStep(f"{JOURNAL_DIR} esiste") as step:
        if not file_exists(JOURNAL_DIR, host=HOST, sudo=True):
            step.fail(f"{JOURNAL_DIR} non trovato")

    with GradingStep(f"{JOURNAL_DIR} contiene una sottodirectory con i file di journal persistenti") as step:
        result = run(f"find {JOURNAL_DIR} -mindepth 1 -maxdepth 1 -type d", host=HOST, sudo=True)
        subdirs = [l for l in result.stdout.splitlines() if l.strip()]
        if not subdirs:
            step.fail(f"Nessuna sottodirectory trovata in {JOURNAL_DIR}")
        else:
            check = run(f"ls {subdirs[0]}", host=HOST, sudo=True)
            if "system.journal" not in check.stdout:
                step.add_error(
                    f"'system.journal' non trovato in {subdirs[0]}: {check.stdout.strip()}"
                )


if __name__ == "__main__":
    main()
