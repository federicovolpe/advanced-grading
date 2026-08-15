#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH124 "processes-monitor" (sku
rh0023l, RH124 sezione 15.8 "Monitor Process Activity"), sprovvista di
`lab grade` ufficiale. Nessuna materials/solutions ne' resources.txt:
specifica presa dal testo della guida (RH124 15.8, passi 2, 13-14), su
servera.

Lo studente crea ~/bin/monitor (script bash con loop infinito che genera
carico CPU artificiale e poi dorme 1s), lo rende eseguibile, ne avvia piu'
istanze in background con `top` per osservarle, e infine le termina tutte
dall'interno di `top` (tasto K, passi 13-14). Come in processes-kill, i
processi 'monitor' sopravvivono alla chiusura della sessione SSH se non
terminati esplicitamente: verificabili a posteriori.

Controlliamo solo il contenuto minimo significativo dello script (loop
infinito + sleep), non il testo esatto: la formattazione del calcolo
aritmetico puo' variare senza cambiare il comportamento richiesto.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, file_exists

HOST = "servera"
SCRIPT_PATH = "~/bin/monitor"


def main():
    print(f"🔧 Grading personalizzato per 'processes-monitor' (host: {HOST})")

    with GradingStep(f"Lo script {SCRIPT_PATH} esiste ed e' eseguibile") as step:
        if not file_exists(SCRIPT_PATH, host=HOST):
            step.fail(f"{SCRIPT_PATH} non trovato")
        elif not run(f"test -x {SCRIPT_PATH}", host=HOST).returncode == 0:
            step.fail(f"{SCRIPT_PATH} esiste ma non e' eseguibile (chmod a+x mancante)")

    with GradingStep(f"Lo script {SCRIPT_PATH} genera un carico CPU con un loop e sleep") as step:
        content = run(f"cat {SCRIPT_PATH}", host=HOST).stdout
        if "while true" not in content and "while :" not in content:
            step.add_error("Nessun loop infinito ('while true'/'while :') trovato nello script")
        if "sleep" not in content:
            step.add_error("Nessuna chiamata a 'sleep' trovata nello script")

    with GradingStep("Nessun processo 'monitor' e' rimasto in esecuzione") as step:
        result = run("pgrep -x monitor -a", host=HOST)
        if result.returncode == 0:
            step.fail(
                f"Processi 'monitor' ancora attivi (andavano terminati da top con "
                f"il tasto K): {result.stdout.strip()}"
            )


if __name__ == "__main__":
    main()
