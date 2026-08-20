#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise AU294 "variables-facts" (sku
au0021l, sez. guida 3.4 "Gathering Host Information from Facts"), sprovvista
di `lab grade` ufficiale.

Fonte primaria: materials/labs/variables-facts/solutions/install-httpd.yml.sol
e il testo guida (passo 5, contenuto letterale del custom fact), che
richiedono di creare /etc/ansible/facts.d/custom.fact su servera con:

    [general]
    package = httpd
    service = httpd
    state = started
    enabled = true

e poi un playbook install-httpd.yml che usa
ansible_facts['ansible_local']['custom']['general'] per installare/avviare
quel pacchetto/servizio. Gradiamo l'EFFETTO reale (il file di fact e il
risultato dell'esecuzione), non il testo del playbook: e' cio' che la guida
stessa chiede di verificare (systemctl status httpd).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, package_installed, service_is_active, service_is_enabled

LAB_NAME = "variables-facts"
HOST = "servera"
_EXPECTED_FACT_LINES = [
    "package = httpd",
    "service = httpd",
    "state = started",
    "enabled = true",
]


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (host: {HOST})")

    with GradingStep(f"/etc/ansible/facts.d/custom.fact esiste su {HOST} con i valori richiesti") as step:
        result = run("cat /etc/ansible/facts.d/custom.fact", host=HOST, sudo=True)
        if result.returncode != 0:
            step.fail(f"/etc/ansible/facts.d/custom.fact non trovato su {HOST}")
        else:
            content = result.stdout
            if "[general]" not in content:
                step.add_error("Sezione '[general]' mancante")
            for line in _EXPECTED_FACT_LINES:
                if line not in content:
                    step.add_error(f"Riga attesa '{line}' non trovata")

    with GradingStep(f"httpd installato, attivo e abilitato su {HOST} (effetto di install-httpd.yml)") as step:
        if not package_installed("httpd", host=HOST):
            step.fail(f"Pacchetto httpd non installato su {HOST}")
        else:
            if not service_is_active("httpd", host=HOST):
                step.add_error(f"Servizio httpd non attivo su {HOST}")
            if not service_is_enabled("httpd", host=HOST):
                step.add_error(f"Servizio httpd non abilitato al boot su {HOST}")


if __name__ == "__main__":
    main()
