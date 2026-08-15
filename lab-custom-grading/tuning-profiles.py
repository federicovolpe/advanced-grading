#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "tuning-profiles" (sezione
PDF 9.2 "Set a Tuning Profile", pag. 220-222), sprovvista di `lab grade`
ufficiale. Nessuna materials/solutions ne' resources.txt: specifica presa
dal testo della guida, su servera.

Stato finale atteso (passo 5.2-5.5): il profilo tuned attivo, in modo
persistente, e' "latency-performance"; vm.dirty_ratio=10 e
vm.swappiness=10 (i valori esatti definiti da quel profilo).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

HOST = "servera"
_EXPECTED_PROFILE = "latency-performance"


def main():
    print(f"🔧 Grading personalizzato per 'tuning-profiles' (host: {HOST})")

    with GradingStep(f"Il profilo tuned attivo e' '{_EXPECTED_PROFILE}'") as step:
        result = run("tuned-adm active", host=HOST)
        if _EXPECTED_PROFILE not in result.stdout:
            step.add_error(f"Atteso profilo '{_EXPECTED_PROFILE}', trovato: {result.stdout.strip()}")

    with GradingStep("vm.dirty_ratio e' impostato a 10") as step:
        result = run("sysctl -n vm.dirty_ratio", host=HOST)
        if result.stdout.strip() != "10":
            step.add_error(f"Atteso 10, trovato: {result.stdout.strip()}")

    with GradingStep("vm.swappiness e' impostato a 10") as step:
        result = run("sysctl -n vm.swappiness", host=HOST)
        if result.stdout.strip() != "10":
            step.add_error(f"Atteso 10, trovato: {result.stdout.strip()}")


if __name__ == "__main__":
    main()
