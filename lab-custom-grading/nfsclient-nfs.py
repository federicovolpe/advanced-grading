#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "nfsclient-nfs" (sezione PDF
15.2 "Mount NFS File Systems", pag. 364), sprovvista di `lab grade`
ufficiale. Nessuna materials/solutions ne' resources.txt: specifica presa
dal testo della guida, su servera.

Stato finale atteso:
- /etc/fstab ha la entry "serverb:/shares/public /public nfs rw,sync 0 0"
  (passo 3.1).
- /public e' montato dall'export NFS di serverb (passi 3.3/4.2).
- /public/hello contiene "Hello, World!" (passo 4.3).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

HOST = "servera"
_EXPECTED_FSTAB_LINE = "serverb:/shares/public /public nfs rw,sync 0 0"


def main():
    print(f"🔧 Grading personalizzato per 'nfsclient-nfs' (host: {HOST})")

    with GradingStep("/etc/fstab ha la entry NFS attesa per /public") as step:
        result = run("cat /etc/fstab", host=HOST, sudo=True)
        lines = [" ".join(l.split()) for l in result.stdout.splitlines()]
        if _EXPECTED_FSTAB_LINE not in lines:
            step.add_error(f"Entry attesa '{_EXPECTED_FSTAB_LINE}' non trovata in /etc/fstab")

    with GradingStep("/public e' montato dall'export NFS serverb:/shares/public") as step:
        result = run("findmnt -no SOURCE /public", host=HOST, sudo=True)
        if result.stdout.strip() != "serverb:/shares/public":
            step.add_error(f"Atteso 'serverb:/shares/public', trovato: '{result.stdout.strip()}'")

    with GradingStep("/public/hello contiene il contenuto atteso") as step:
        result = run("cat /public/hello", host=HOST, sudo=True)
        if result.stdout.strip() != "Hello, World!":
            step.add_error(f"Atteso 'Hello, World!', trovato: '{result.stdout.strip()}'")


if __name__ == "__main__":
    main()
