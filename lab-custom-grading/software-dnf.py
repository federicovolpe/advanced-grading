#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH124 "software-dnf" (sku rh0021l,
RH124 sezione 12.4 "Install and Update Packages with DNF"), sprovvista di
`lab grade` ufficiale. Nessuna materials/solutions ne' resources.txt:
specifica presa dal testo della guida (RH124 12.4, passi 2-3), su servera.

L'esercizio e' un ciclo installa-verifica-rimuovi (nmap al passo 2, il
gruppo di componenti "Security Tools" al passo 3): lo stato finale del
pacchetto/gruppo coincide con quello iniziale (assente), quindi non e'
sufficiente controllare lo stato attuale per capire se lo studente ha
davvero eseguito i passi. Il log persistente `dnf history` (mai
azzerato tra un esercizio e l'altro sulla stessa macchina servera) e'
l'unica evidenza oggettiva delle azioni realmente eseguite: verifichiamo
che contenga sia l'installazione sia la rimozione.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

HOST = "servera"


def history_lines(filter_arg=None):
    cmd = "dnf history list" + (f" {filter_arg}" if filter_arg else "")
    result = run(cmd, host=HOST, sudo=True)
    return result.stdout.lower()


def main():
    print(f"🔧 Grading personalizzato per 'software-dnf' (host: {HOST})")

    with GradingStep("Il pacchetto nmap risulta installato e poi rimosso (dnf history)") as step:
        hist = history_lines("nmap")
        if "no transaction" in hist or not hist.strip():
            step.fail("Nessuna transazione dnf coinvolge il pacchetto nmap")
        else:
            if "install" not in hist:
                step.add_error("Non risulta un'installazione di nmap nella cronologia dnf")
            if "remov" not in hist and "eras" not in hist:
                step.add_error("Non risulta una rimozione di nmap nella cronologia dnf")

    with GradingStep("Il pacchetto nmap non e' installato ora (rimosso al passo 2.6)") as step:
        if run("rpm -q nmap", host=HOST).returncode == 0:
            step.fail("nmap risulta ancora installato: andava rimosso a fine esercizio")

    with GradingStep("Il gruppo 'Security Tools' risulta installato e poi rimosso (dnf history)") as step:
        hist = history_lines()
        matching = [l for l in hist.splitlines() if "security t" in l]
        if not matching:
            step.fail("Nessuna transazione dnf menziona il gruppo 'Security Tools'")
        else:
            joined = " ".join(matching)
            if "install" not in joined:
                step.add_error("Non risulta un'installazione del gruppo 'Security Tools'")
            if "remov" not in joined:
                step.add_error("Non risulta una rimozione del gruppo 'Security Tools'")

    with GradingStep("Il gruppo 'Security Tools' non e' installato ora (rimosso al passo 3.5)") as step:
        result = run("dnf group list --installed", host=HOST, sudo=True)
        if "security tools" in result.stdout.lower():
            step.fail("Il gruppo 'Security Tools' risulta ancora installato")


if __name__ == "__main__":
    main()
