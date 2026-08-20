#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise AU294 "develop-multiplay" (sku
au0020l, sez. 2.6 "Developing Playbooks with Multiple Plays"), sprovvista
di `lab grade` ufficiale. Specifica presa da materials/labs/
develop-multiplay/solutions/intranet.yml.sol: play 1 su servera installa
httpd+firewalld e pubblica una pagina "intranet"; play 2 su serverb (senza
become) verifica che servera risponda in HTTP.

Grada l'effetto reale (pacchetti/servizi/firewall su servera, connettivita'
HTTP da serverb) invece del testo YAML, per lo stesso motivo di
develop-singleplay.py.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, package_installed, service_is_active, service_is_enabled

# Sez. 2.6, contenuto letterale del task "Test html page is installed".
_EXPECTED_INDEX = "Welcome to the example.com intranet!"


def main():
    print("🔧 Grading personalizzato per 'develop-multiplay' (host: servera, serverb)")

    for pkg in ("httpd", "firewalld"):
        with GradingStep(f"{pkg} e' installato su servera") as step:
            if not package_installed(pkg, host="servera"):
                step.fail(f"Pacchetto '{pkg}' non installato su servera")

    with GradingStep("/var/www/html/index.html su servera ha il contenuto atteso") as step:
        result = run("cat /var/www/html/index.html", host="servera", sudo=True)
        if result.returncode != 0:
            step.fail("Impossibile leggere /var/www/html/index.html su servera")
        elif result.stdout.strip() != _EXPECTED_INDEX:
            step.add_error("Contenuto della pagina diverso da quello atteso")

    for service in ("httpd", "firewalld"):
        with GradingStep(f"{service} e' avviato e abilitato su servera") as step:
            if not service_is_active(service, host="servera"):
                step.add_error(f"Servizio {service} non attivo su servera")
            if not service_is_enabled(service, host="servera"):
                step.add_error(f"Servizio {service} non abilitato al boot su servera")

    with GradingStep("Il firewall di servera permette il servizio http") as step:
        result = run("firewall-cmd --query-service=http", host="servera", sudo=True)
        if result.returncode != 0:
            step.fail("Servizio 'http' non permesso nel firewall di servera")

    with GradingStep("serverb raggiunge servera in HTTP (play di test dell'intranet)") as step:
        result = run("curl -s -o /dev/null -w '%{http_code}' http://servera.lab.example.com", host="serverb")
        if result.returncode != 0 or result.stdout.strip() != "200":
            step.fail(f"Richiesta HTTP da serverb a servera non riuscita (esito: {result.stdout.strip() or result.stderr.strip()})")


if __name__ == "__main__":
    main()
