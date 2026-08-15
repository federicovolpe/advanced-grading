#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "systasks-timers" (sezione
PDF 4.2 "Manage Repeating Jobs by Using Systemd Timer Units", pag. 84-86),
sprovvista di `lab grade` ufficiale. Nessuna materials/solutions ne'
resources.txt: specifica presa dal testo della guida, su servera.

Stato finale atteso:
- sysstat installato (passo 2.1).
- /etc/systemd/system/sysstat-collect.timer esiste e OnCalendar e' impostato
  a "*:00/2" (ogni 2 minuti, non piu' i 10 minuti di default, passo 3.2).
- Il timer sysstat-collect.timer e' enabled e active (passo 3.4).
- /var/log/sa contiene almeno un file di raccolta dati (passo 4).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, package_installed, service_is_active, service_is_enabled

HOST = "servera"
TIMER_UNIT = "sysstat-collect.timer"
TIMER_FILE = "/etc/systemd/system/sysstat-collect.timer"


def main():
    print(f"🔧 Grading personalizzato per 'systasks-timers' (host: {HOST})")

    with GradingStep("Il pacchetto sysstat e' installato") as step:
        if not package_installed("sysstat", host=HOST):
            step.fail("Pacchetto 'sysstat' non installato")

    with GradingStep(f"{TIMER_FILE} esiste con OnCalendar impostato a ogni 2 minuti") as step:
        result = run(f"cat {TIMER_FILE}", host=HOST, sudo=True)
        if result.returncode != 0:
            step.fail(f"{TIMER_FILE} non trovato")
        elif "OnCalendar=*:00/2" not in result.stdout:
            step.add_error(
                f"Atteso 'OnCalendar=*:00/2' (ogni 2 minuti), trovato: {result.stdout.strip()}"
            )

    with GradingStep(f"Il timer {TIMER_UNIT} e' enabled e active") as step:
        if not service_is_enabled(TIMER_UNIT, host=HOST):
            step.add_error(f"{TIMER_UNIT} non e' enabled")
        if not service_is_active(TIMER_UNIT, host=HOST):
            step.add_error(f"{TIMER_UNIT} non e' active")

    with GradingStep("/var/log/sa contiene almeno un file di raccolta dati") as step:
        result = run("ls -1 /var/log/sa 2>/dev/null | wc -l", host=HOST, sudo=True)
        try:
            count = int(result.stdout.strip())
        except ValueError:
            count = 0
        if count < 1:
            step.fail("/var/log/sa e' vuota: il timer non ha ancora raccolto dati")


if __name__ == "__main__":
    main()
