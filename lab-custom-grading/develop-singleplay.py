#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise AU294 "develop-singleplay" (sku
au0020l, sez. 2.4 "Developing Playbooks"), sprovvista di `lab grade`
ufficiale. Specifica presa da materials/labs/develop-singleplay/
solutions/site.yml.sol: un playbook che installa/avvia httpd sul gruppo
"web" (servera+serverb), pubblica files/index.html come pagina di test e
apre il servizio http nel firewall.

Grada l'EFFETTO reale su servera/serverb (pacchetto, contenuto pagina,
servizio, firewall) invece del testo YAML del playbook: piu' robusto a
variazioni di stile equivalenti (ordine task, moduli alternativi, ecc.)
che la guida stessa non vincola.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, package_installed, service_is_active, service_is_enabled

HOSTS = ["servera", "serverb"]  # gruppo "web" (inventory di develop-singleplay)

# Sez. 2.4, contenuto letterale di files/index.html copiato da site.yml.sol.
_EXPECTED_INDEX = "Hello, World!\n\nThis is a test page by Ansible!"


def main():
    print(f"🔧 Grading personalizzato per 'develop-singleplay' (host: {', '.join(HOSTS)})")

    for host in HOSTS:
        with GradingStep(f"httpd e' installato su {host}") as step:
            if not package_installed("httpd", host=host):
                step.fail(f"Pacchetto 'httpd' non installato su {host}")

        with GradingStep(f"/var/www/html/index.html su {host} ha il contenuto atteso") as step:
            result = run("cat /var/www/html/index.html", host=host, sudo=True)
            if result.returncode != 0:
                step.fail(f"Impossibile leggere /var/www/html/index.html su {host}")
            elif result.stdout.strip() != _EXPECTED_INDEX.strip():
                step.add_error("Contenuto della pagina diverso da quello di files/index.html")

        with GradingStep(f"httpd e' avviato e abilitato su {host}") as step:
            if not service_is_active("httpd", host=host):
                step.add_error(f"Servizio httpd non attivo su {host}")
            if not service_is_enabled("httpd", host=host):
                step.add_error(f"Servizio httpd non abilitato al boot su {host}")

        with GradingStep(f"Il firewall di {host} permette il servizio http") as step:
            result = run("firewall-cmd --query-service=http", host=host, sudo=True)
            if result.returncode != 0:
                step.fail(f"Servizio 'http' non permesso nel firewall di {host}")


if __name__ == "__main__":
    main()
