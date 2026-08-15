#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "logs-maintain" (sezione PDF
5.10 "Maintain Synchronized Time", pag. 138-141), sprovvista di
`lab grade` ufficiale. Nessuna materials/solutions ne' resources.txt:
specifica presa dal testo della guida, su servera.

Stato finale atteso:
- Fuso orario impostato a America/Port-au-Prince (passo 2.2).
- /etc/chrony.conf contiene "server classroom.example.com iburst" (passo
  3.1).
- NTP abilitato (timedatectl set-ntp true, passo 3.2): "System clock
  synchronized: yes" e "NTP service: active".
- chronyc sources -v mostra classroom.example.com come sorgente corrente
  (simbolo '*' nella colonna di stato, passo 4.2).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

HOST = "servera"
_EXPECTED_TZ = "America/Port-au-Prince"
_EXPECTED_NTP_LINE = "server classroom.example.com iburst"


def main():
    print(f"🔧 Grading personalizzato per 'logs-maintain' (host: {HOST})")

    with GradingStep(f"Il fuso orario e' impostato a {_EXPECTED_TZ}") as step:
        result = run("timedatectl show --property=Timezone --value", host=HOST)
        if result.stdout.strip() != _EXPECTED_TZ:
            step.add_error(f"Atteso '{_EXPECTED_TZ}', trovato: '{result.stdout.strip()}'")

    with GradingStep("/etc/chrony.conf usa classroom.example.com come sorgente NTP") as step:
        result = run("cat /etc/chrony.conf", host=HOST, sudo=True)
        if _EXPECTED_NTP_LINE not in result.stdout:
            step.add_error(
                f"Riga attesa '{_EXPECTED_NTP_LINE}' non trovata in /etc/chrony.conf"
            )

    with GradingStep("La sincronizzazione NTP e' abilitata e attiva") as step:
        result = run("timedatectl", host=HOST)
        if "System clock synchronized: yes" not in result.stdout:
            step.add_error("System clock non risulta synchronized")
        if "NTP service: active" not in result.stdout:
            step.add_error("NTP service non risulta active")

    with GradingStep("chronyc sources mostra classroom.example.com come sorgente corrente (*)") as step:
        result = run("chronyc sources", host=HOST)
        matching = [
            l for l in result.stdout.splitlines()
            if "classroom.example.com" in l
        ]
        if not matching:
            step.fail("classroom.example.com non trovato tra le sorgenti chrony")
        elif not matching[0].strip().startswith("^*"):
            step.add_error(
                f"classroom.example.com non e' la sorgente corrente (atteso '^*'): {matching[0].strip()}"
            )


if __name__ == "__main__":
    main()
