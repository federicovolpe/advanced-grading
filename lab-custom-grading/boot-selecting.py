#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "boot-selecting" (sezione
PDF 12.4 "Explore the Boot Process and Select a Boot Target", pag.
311-313), sprovvista di `lab grade` ufficiale. Nessuna materials/solutions
ne' resources.txt: specifica presa dal testo della guida, su workstation.

L'esercizio fa un giro completo sul target di default (graphical ->
multi-user -> di nuovo graphical, passi 4.1-4.5) e poi esplora il target
rescue senza modificarlo in modo persistente (passi 5-7). Stato finale
atteso: systemctl get-default torna a "graphical.target" (come
selinux-opsmode/boot-grub, il check non distingue "mai fatto" da "fatto e
ripristinato", ma individua uno stato finale lasciato sbagliato).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

_EXPECTED_TARGET = "graphical.target"


def main():
    print("🔧 Grading personalizzato per 'boot-selecting' (host: workstation)")

    with GradingStep(f"Il target di default e' tornato a {_EXPECTED_TARGET}") as step:
        result = run("systemctl get-default")
        if result.stdout.strip() != _EXPECTED_TARGET:
            step.add_error(f"Atteso '{_EXPECTED_TARGET}', trovato: '{result.stdout.strip()}'")


if __name__ == "__main__":
    main()
