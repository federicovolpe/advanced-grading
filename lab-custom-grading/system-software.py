#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise AU294 "system-software" (sku
au0026l, sezione 8.4 "Automating Software and Subscription Tasks"),
sprovvista di `lab grade` ufficiale. Specifica presa da
materials/labs/system-software/solutions/repo.yml.sol (diff con lo
starter, che non ha alcun playbook): il playbook definitivo crea il repo
"example-internal" puntato su serverb e installa il pacchetto
"simple-agent" (fornito in materials/labs/system-software/repository/,
pacchetto RPM creato apposta per questo esercizio, innocuo).

Il testo della guida (passo 6, "Remove the simple-agent package... and
then run the playbook again") conferma che lo stato finale atteso e' con
il pacchetto di nuovo installato: il playbook viene rieseguito dopo la
rimozione dimostrativa.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, package_installed

HOST = "servera"
_REPO_BASEURL = "serverb.lab.example.com/yum/repository"


def main():
    print(f"🔧 Grading personalizzato per 'system-software' (host: {HOST})")

    with GradingStep("Il repo 'example-internal' e' configurato su servera") as step:
        result = run("cat /etc/yum.repos.d/*.repo", host=HOST, sudo=True)
        if result.returncode != 0:
            step.fail("Impossibile leggere /etc/yum.repos.d su servera")
        else:
            if "example-internal" not in result.stdout:
                step.add_error("Nessuna sezione repo 'example-internal' trovata")
            if _REPO_BASEURL not in result.stdout:
                step.add_error(f"baseurl atteso verso {_REPO_BASEURL} non trovato")

    with GradingStep("Il pacchetto simple-agent e' installato su servera") as step:
        if not package_installed("simple-agent", host=HOST):
            step.fail("Pacchetto 'simple-agent' non installato su servera")


if __name__ == "__main__":
    main()
