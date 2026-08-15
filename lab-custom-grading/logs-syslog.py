#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "logs-syslog" (sezione PDF
5.4 "Interpret and Manage Syslog Events", pag. 116-117), sprovvista di
`lab grade` ufficiale. Nessuna materials/solutions ne' resources.txt:
specifica presa dal testo della guida, su servera.

Stato finale atteso:
- /etc/rsyslog.d/debug.conf contiene "*.debug /var/log/messages-debug"
  (passo 2.1).
- rsyslog attivo (riavviato al passo 2.2).
- /var/log/messages-debug contiene il messaggio di test generato dalla
  guida stessa al passo 3.1 ("logger -p user.debug 'Debug Message Test'"),
  prova che la redirezione funziona davvero.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, service_is_active

HOST = "servera"
CONF_FILE = "/etc/rsyslog.d/debug.conf"
_EXPECTED_LINE = "*.debug /var/log/messages-debug"


def main():
    print(f"🔧 Grading personalizzato per 'logs-syslog' (host: {HOST})")

    with GradingStep(f"{CONF_FILE} contiene la regola richiesta") as step:
        result = run(f"cat {CONF_FILE}", host=HOST, sudo=True)
        if result.returncode != 0:
            step.fail(f"{CONF_FILE} non trovato")
        elif _EXPECTED_LINE not in result.stdout:
            step.add_error(
                f"Riga attesa '{_EXPECTED_LINE}' non trovata, contenuto: {result.stdout.strip()}"
            )

    with GradingStep("Il servizio rsyslog e' attivo") as step:
        if not service_is_active("rsyslog", host=HOST):
            step.fail("rsyslog non risulta attivo")

    with GradingStep("/var/log/messages-debug contiene il messaggio di debug atteso") as step:
        result = run("cat /var/log/messages-debug", host=HOST, sudo=True)
        if result.returncode != 0 or "Debug Message Test" not in result.stdout:
            step.fail(
                "'Debug Message Test' non trovato in /var/log/messages-debug: "
                "la redirezione non risulta funzionante"
            )


if __name__ == "__main__":
    main()
