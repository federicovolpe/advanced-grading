#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "archive-manage" (sezione
PDF 7.2 "Manage Compressed Tar Archives", pag. 189-191), sprovvista di
`lab grade` ufficiale. Nessuna materials/solutions ne' resources.txt:
specifica presa dal testo della guida, su servera.

Stato finale atteso:
- /tmp/etc.tar, /tmp/etc.tar.gz, /tmp/etc.tar.bz2, /tmp/etc.tar.xz esistono
  (passo 2).
- /backuptest/etc esiste (estrazione di etc.tar.gz, passo 4).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, file_exists

HOST = "servera"
_ARCHIVES = ["/tmp/etc.tar", "/tmp/etc.tar.gz", "/tmp/etc.tar.bz2", "/tmp/etc.tar.xz"]


def main():
    print(f"🔧 Grading personalizzato per 'archive-manage' (host: {HOST})")

    with GradingStep("I 4 archivi di /etc (tar, gzip, bzip2, xz) esistono in /tmp") as step:
        for path in _ARCHIVES:
            if not file_exists(path, host=HOST, sudo=True):
                step.add_error(f"Manca {path}")

    with GradingStep("/backuptest/etc esiste (estrazione di etc.tar.gz)") as step:
        if not file_exists("/backuptest/etc", host=HOST, sudo=True):
            step.fail("/backuptest/etc non trovato")
        else:
            result = run("ls /backuptest/etc | wc -l", host=HOST, sudo=True)
            try:
                count = int(result.stdout.strip())
            except ValueError:
                count = 0
            if count < 1:
                step.add_error("/backuptest/etc esiste ma e' vuota")


if __name__ == "__main__":
    main()
