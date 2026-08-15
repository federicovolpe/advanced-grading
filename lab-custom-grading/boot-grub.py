#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "boot-grub" (sezione PDF
12.2 "Manage the Boot Loader and Kernel Command Line", pag. 303-304),
sprovvista di `lab grade` ufficiale. Nessuna materials/solutions ne'
resources.txt: specifica presa dal testo della guida, su servera.

L'esercizio fa un giro completo: cambia il kernel di default (passo 3),
aggiunge "rhgb quiet" (passo 4.1), poi al passo 6 ripristina sia l'indice
di default originale (1) sia rimuove "rhgb quiet". Lo stato finale atteso
coincide quindi con quello iniziale:
- grubby --default-index restituisce 1.
- Nessun kernel installato ha "rhgb quiet" tra gli argomenti (residuo
  dimenticato del passo 4.1 non rimosso al passo 6.3).
Non viene forzato alcun reboot dal grading: i passi 1.x/4.2/6.4 richiedono
interazione con la console grafica, che lo studente esegue da se'.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

HOST = "servera"


def main():
    print(f"🔧 Grading personalizzato per 'boot-grub' (host: {HOST})")

    with GradingStep("Il kernel di default (grubby --default-index) e' tornato a 1") as step:
        result = run("grubby --default-index", host=HOST, sudo=True)
        if result.stdout.strip() != "1":
            step.add_error(f"Atteso indice di default '1', trovato: '{result.stdout.strip()}'")

    with GradingStep("Nessun kernel ha ancora l'argomento 'rhgb quiet' residuo") as step:
        result = run("grubby --info=ALL", host=HOST, sudo=True)
        offending = [l for l in result.stdout.splitlines() if l.startswith("args=") and "rhgb" in l and "quiet" in l]
        if offending:
            step.add_error(f"Argomento 'rhgb quiet' ancora presente: {offending}")


if __name__ == "__main__":
    main()
