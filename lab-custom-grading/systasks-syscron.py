#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "systasks-syscron" (sezione
PDF 4.6 "Schedule a Recurring System Task with Cron", pag. 97-98),
sprovvista di `lab grade` ufficiale. Nessuna materials/solutions ne'
resources.txt: specifica presa dal testo della guida, su servera.

Stato finale atteso:
- /etc/cron.d/usercount esiste con la entry esatta (root, ogni 3 minuti,
  comando logger con conteggio utenti attivi).
- /var/log/messages contiene almeno un messaggio "There are ... active
  users" generato dal job (la guida stessa chiede di attendere 3 minuti e
  confermarlo, passo 2.2).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

HOST = "servera"
CRON_FILE = "/etc/cron.d/usercount"
_EXPECTED_ENTRY = '*/3 * * * * root logger "There are `w -h | wc -l` active users"'


def main():
    print(f"🔧 Grading personalizzato per 'systasks-syscron' (host: {HOST})")

    with GradingStep(f"{CRON_FILE} contiene la entry cron richiesta") as step:
        result = run(f"cat {CRON_FILE}", host=HOST, sudo=True)
        if result.returncode != 0:
            step.fail(f"{CRON_FILE} non trovato")
        elif _EXPECTED_ENTRY not in result.stdout:
            step.add_error(
                f"Entry attesa non trovata. Contenuto attuale:\n{result.stdout.strip()}"
            )

    with GradingStep("Il job ha gia' loggato almeno un messaggio in /var/log/messages") as step:
        result = run('grep "There are" /var/log/messages', host=HOST, sudo=True)
        if result.returncode != 0 or not result.stdout.strip():
            step.fail("Nessun messaggio 'There are ... active users' trovato in /var/log/messages")


if __name__ == "__main__":
    main()
