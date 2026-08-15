#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "boot-repairing" (sezione
PDF 12.6 "Repair a Damaged File System at Boot Time", pag. 317-318),
sprovvista di `lab grade` ufficiale. Nessuna materials/solutions ne'
resources.txt: specifica presa dal testo della guida, su servera.

`lab start` rompe deliberatamente /etc/fstab puntando la root a
/fakeroot invece che a / (passo 6-7). Stato finale atteso:
- /etc/fstab non contiene piu' "/fakeroot".
- /etc/fstab ha una entry che monta "/" in xfs (passo 7.1).
- Il filesystem radice e' montato in read-write (prova che il boot e'
  arrivato a termine correttamente dopo la correzione, passo 9-10).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

HOST = "servera"


def main():
    print(f"🔧 Grading personalizzato per 'boot-repairing' (host: {HOST})")

    with GradingStep("/etc/fstab non contiene piu' il mount point errato /fakeroot") as step:
        result = run("grep -F /fakeroot /etc/fstab", host=HOST, sudo=True)
        if result.returncode == 0:
            step.add_error(f"'/fakeroot' ancora presente in /etc/fstab: {result.stdout.strip()}")

    with GradingStep("/etc/fstab monta correttamente / come xfs") as step:
        result = run("grep -E '^UUID=\\S+\\s+/\\s+xfs' /etc/fstab", host=HOST, sudo=True)
        if result.returncode != 0:
            step.add_error("Nessuna entry 'UUID=... / xfs ...' trovata in /etc/fstab")

    with GradingStep("Il filesystem radice e' montato in read-write") as step:
        result = run("findmnt -no OPTIONS /", host=HOST, sudo=True)
        options = result.stdout.strip().split(",")
        if not options or options[0] != "rw":
            step.add_error(f"Atteso 'rw' come prima opzione di mount, trovato: {result.stdout.strip()}")


if __name__ == "__main__":
    main()
