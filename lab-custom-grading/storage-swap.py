#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "storage-swap" (sezione PDF
10.4 "Manage Swap Space", pag. 255-258), sprovvista di `lab grade`
ufficiale. Nessuna materials/solutions ne' resources.txt: specifica presa
dal testo della guida, su servera.

Stato finale atteso:
- /dev/sdb2 esiste come partizione swap (nome "myswap", passo 3).
- /etc/fstab ha una entry UUID che monta lo swap (passo 6.2, UUID non
  fissato perche' varia per macchina).
- Lo swap e' attivo (swapon --show mostra /dev/sdb2, passi 6.4/7.3).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

HOST = "servera"


def main():
    print(f"🔧 Grading personalizzato per 'storage-swap' (host: {HOST})")

    with GradingStep("/dev/sdb2 esiste come partizione swap") as step:
        result = run("lsblk -no FSTYPE /dev/sdb2", host=HOST, sudo=True)
        if result.returncode != 0:
            step.fail("/dev/sdb2 non trovato")
        elif result.stdout.strip() != "swap":
            step.add_error(f"Atteso FSTYPE 'swap', trovato: '{result.stdout.strip()}'")

    with GradingStep("/etc/fstab ha una entry UUID per lo swap") as step:
        result = run("grep -E '^UUID=\\S+\\s+swap\\s+swap' /etc/fstab", host=HOST, sudo=True)
        if result.returncode != 0:
            step.add_error("Nessuna entry 'UUID=... swap swap ...' trovata in /etc/fstab")

    with GradingStep("Lo swap su /dev/sdb2 e' attivo") as step:
        result = run("swapon --show=NAME --noheadings", host=HOST, sudo=True)
        if "/dev/sdb2" not in result.stdout:
            step.add_error(f"/dev/sdb2 non risulta attivo in swapon --show: {result.stdout.strip()}")


if __name__ == "__main__":
    main()
