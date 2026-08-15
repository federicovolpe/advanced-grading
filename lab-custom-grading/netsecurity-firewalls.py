#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "netsecurity-firewalls"
(sezione PDF 14.2 "Manage a Server Firewall", pag. 342-344), sprovvista di
`lab grade` ufficiale. Nessuna materials/solutions ne' resources.txt:
specifica presa dal testo della guida, su servera (+ verifica HTTPS da
workstation).

Stato finale atteso:
- Il servizio "https" e' aggiunto in modo permanente alla zona firewalld
  "public" (passo 7.3).
- httpd attivo, serve "I am servera." (passo 3).
- curl -k https://servera.lab.example.com da workstation restituisce "I am
  servera." (prova end-to-end, passo 9.2): la porta 443 e' aperta, la 80
  resta bloccata (non richiesto di aprirla).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, service_is_active

HOST = "servera"
_EXPECTED_CONTENT = "I am servera."


def main():
    print(f"🔧 Grading personalizzato per 'netsecurity-firewalls' (host: {HOST})")

    with GradingStep("Il servizio 'https' e' abilitato in modo permanente sulla zona public") as step:
        result = run("firewall-cmd --permanent --zone=public --list-services", host=HOST, sudo=True)
        if "https" not in result.stdout.split():
            step.add_error(f"'https' non presente tra i servizi della zona public: {result.stdout.strip()}")

    with GradingStep("httpd e' attivo") as step:
        if not service_is_active("httpd", host=HOST):
            step.fail("httpd non risulta attivo")

    with GradingStep("curl -k https://servera.lab.example.com restituisce il contenuto atteso") as step:
        result = run("curl -sk https://servera.lab.example.com")
        if result.stdout.strip() != _EXPECTED_CONTENT:
            step.add_error(
                f"Risposta HTTPS inattesa (atteso '{_EXPECTED_CONTENT}'): {result.stdout.strip()[:200]}"
            )


if __name__ == "__main__":
    main()
