#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "storage-partitions" (sezione
PDF 10.2 "Create and Manage File Systems on Standard Partitions", pag.
246-248), sprovvista di `lab grade` ufficiale. Nessuna materials/solutions
ne' resources.txt: specifica presa dal testo della guida, su servera.

Stato finale atteso:
- /dev/sdb1 esiste come partizione primaria MBR, filesystem xfs (passi
  2-6).
- /etc/fstab ha una entry che monta /archive in xfs tramite UUID (il valore
  esatto dell'UUID varia per macchina, quindi si verifica solo la
  struttura della riga, non l'UUID letterale, passo 7.3).
- /archive e' montato da /dev/sdb1 come xfs (passi 7.5-7.6, verificato
  anche dopo un eventuale reboot al passo 8).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

HOST = "servera"


def main():
    print(f"🔧 Grading personalizzato per 'storage-partitions' (host: {HOST})")

    with GradingStep("/dev/sdb1 esiste con filesystem xfs") as step:
        result = run("lsblk -no FSTYPE /dev/sdb1", host=HOST, sudo=True)
        if result.returncode != 0:
            step.fail("/dev/sdb1 non trovato")
        elif result.stdout.strip() != "xfs":
            step.add_error(f"Atteso filesystem 'xfs', trovato: '{result.stdout.strip()}'")

    with GradingStep("/etc/fstab ha una entry UUID per /archive in xfs") as step:
        result = run("grep -E '^UUID=\\S+\\s+/archive\\s+xfs' /etc/fstab", host=HOST, sudo=True)
        if result.returncode != 0:
            step.add_error("Nessuna entry 'UUID=... /archive xfs ...' trovata in /etc/fstab")

    with GradingStep("/archive e' montato da /dev/sdb1 (xfs)") as step:
        result = run("findmnt -no SOURCE,FSTYPE /archive", host=HOST, sudo=True)
        if result.returncode != 0:
            step.fail("/archive non risulta montato")
        elif "/dev/sdb1" not in result.stdout or "xfs" not in result.stdout:
            step.add_error(f"Atteso '/dev/sdb1 ... xfs', trovato: {result.stdout.strip()}")


if __name__ == "__main__":
    main()
