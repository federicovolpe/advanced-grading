#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "selinux-opsmode" (sezione
PDF 6.2 "Operate SELinux", pag. 156-157), sprovvista di `lab grade`
ufficiale. Nessuna materials/solutions ne' resources.txt: specifica presa
dal testo della guida, su servera.

L'esercizio fa passare temporaneamente a permissive (passi 2) e poi
richiede di tornare a enforcing sia a runtime che in configurazione (passi
3-4, con reboot per rendere persistente la modifica). Stato finale atteso:
- /etc/selinux/config ha SELINUX=enforcing.
- getenforce restituisce "Enforcing" (a runtime, dopo l'eventuale reboot).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

HOST = "servera"


def main():
    print(f"🔧 Grading personalizzato per 'selinux-opsmode' (host: {HOST})")

    with GradingStep("/etc/selinux/config ha SELINUX=enforcing") as step:
        result = run("grep -E '^SELINUX=' /etc/selinux/config", host=HOST, sudo=True)
        if result.stdout.strip() != "SELINUX=enforcing":
            step.add_error(
                f"Atteso 'SELINUX=enforcing', trovato: '{result.stdout.strip()}'"
            )

    with GradingStep("getenforce restituisce Enforcing a runtime") as step:
        result = run("getenforce", host=HOST)
        if result.stdout.strip() != "Enforcing":
            step.add_error(f"Atteso 'Enforcing', trovato: '{result.stdout.strip()}'")


if __name__ == "__main__":
    main()
