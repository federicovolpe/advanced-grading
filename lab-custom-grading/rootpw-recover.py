#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "rootpw-recover" (sezione
PDF 13.2 "Regain Superuser Access and Reset the Root Password", pag.
329-330), sprovvista di `lab grade` ufficiale. Nessuna materials/solutions
ne' resources.txt: specifica presa dal testo della guida, su servera.

Stato finale atteso: la password dell'utente root su servera e' "redhat"
(passo 5), verificata confrontando l'hash in /etc/shadow senza mai
stampare la password in chiaro.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, password_matches

HOST = "servera"


def main():
    print(f"🔧 Grading personalizzato per 'rootpw-recover' (host: {HOST})")

    with GradingStep("La password di root su servera e' stata reimpostata correttamente") as step:
        if not password_matches("root", "redhat", host=HOST):
            step.fail("La password di root non corrisponde a 'redhat'")


if __name__ == "__main__":
    main()
