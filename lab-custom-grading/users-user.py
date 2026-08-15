#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH124 "users-user" (sku rh0019l,
RH124 sezione 10.6 "Manage Local User Accounts"), sprovvista di `lab grade`
ufficiale. Nessuna materials/solutions ne' resources.txt: specifica presa
dal testo della guida (RH124 10.6, passi 1-4), eseguita su servera.

Stato finale atteso:
- operator1: esiste, password "redhat", commento "Operator One".
- operator2: esiste, password "redhat", commento "Operator Two".
- operator3: NON esiste piu' (rimosso con `userdel -r`, home dir compresa).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, user_exists, password_matches, file_exists

LAB_NAME = "users-user"
HOST = "servera"
_PASSWORD = "redhat"


def get_comment(username):
    result = run(f"getent passwd {username}", host=HOST)
    if result.returncode != 0:
        return None
    fields = result.stdout.strip().split(":")
    return fields[4] if len(fields) > 4 else ""


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (host: {HOST})")

    for user, comment in (("operator1", "Operator One"), ("operator2", "Operator Two")):
        with GradingStep(f"L'utente {user} esiste con commento '{comment}'") as step:
            if not user_exists(user, host=HOST):
                step.fail(f"Utente '{user}' non trovato")
            elif get_comment(user) != comment:
                step.add_error(
                    f"Commento GECOS atteso '{comment}', trovato '{get_comment(user)}'"
                )

        with GradingStep(f"La password di {user} e' impostata correttamente") as step:
            if not password_matches(user, _PASSWORD, host=HOST):
                step.fail(f"La password di '{user}' non corrisponde a quella richiesta")

    with GradingStep("L'utente operator3 e' stato rimosso") as step:
        if user_exists("operator3", host=HOST):
            step.fail("'operator3' esiste ancora: andava rimosso con userdel -r")

    with GradingStep("La home directory di operator3 e' stata rimossa") as step:
        if file_exists("/home/operator3", host=HOST, sudo=True):
            step.fail("/home/operator3 esiste ancora")


if __name__ == "__main__":
    main()
