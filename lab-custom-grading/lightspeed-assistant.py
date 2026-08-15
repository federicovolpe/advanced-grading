#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH124 "lightspeed-assistant"
(sku rh0003l, RH124 sezione 5.2 "Ask Questions and Evaluate Answers from
the Command-line Assistant"), sprovvista di `lab grade` ufficiale (la
classe LightspeedAssistant eredita da GuidedExercise, non da Lab: solo
start()/finish()).

start() installa httpd e command-line-assistant su servera, poi introduce
deliberatamente un errore di sintassi in /etc/httpd/conf/httpd.conf (riga
47: "Listen" diventa "Lissten") cosi' che httpd non parta. Lo studente deve
usare l'assistente da riga di comando (`c chat "..."`) per diagnosticare il
problema, correggere la riga con sed, e riavviare il servizio.

Specifica presa dal testo della guida (RH124 5.2, passi 5.3-5.6): dopo la
correzione, la riga 47 di httpd.conf deve contenere "Listen" (non piu'
"Lissten"), e systemctl deve mostrare httpd.service attivo (la guida
verifica solo lo stato "active", il servizio resta "disabled" al boot:
non e' richiesto abilitarlo).

Nessuna materials/solutions ne' resources.txt per questo esercizio.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, service_is_active

LAB_NAME = "lightspeed-assistant"
HOST = "servera"
CONF_FILE = "/etc/httpd/conf/httpd.conf"


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (host: {HOST})")

    with GradingStep("httpd e' installato su servera") as step:
        result = run(f"rpm -q httpd", host=HOST)
        if result.returncode != 0:
            step.fail("Pacchetto httpd non trovato su servera")

    with GradingStep(f"La riga 47 di {CONF_FILE} non contiene piu' l'errore 'Lissten'") as step:
        result = run(f"sed -n '47p' {CONF_FILE}", host=HOST)
        line47 = result.stdout.strip()
        if "lissten" in line47.lower():
            step.add_error(
                f"Riga 47 ancora errata: '{line47}' (atteso 'Listen ...', non 'Lissten')"
            )
        elif "listen" not in line47.lower():
            step.add_error(
                f"Riga 47 inattesa: '{line47}' (atteso che contenga la direttiva 'Listen')"
            )

    with GradingStep("Il servizio httpd e' attivo su servera") as step:
        if not service_is_active("httpd", host=HOST):
            step.fail("httpd non risulta 'active' su servera (systemctl is-active)")


if __name__ == "__main__":
    main()
