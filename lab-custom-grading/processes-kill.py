#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH124 "processes-kill" (sku
rh0023l, RH124 sezione 15.6 "Send Signals to Processes"), sprovvista di
`lab grade` ufficiale. Nessuna materials/solutions ne' resources.txt:
specifica presa dal testo della guida (RH124 15.6, passi 2-9), su servera.

Lo studente avvia in background tre processi (`instance network &`,
`instance interface &`, `instance connection &`, ognuno appende una riga
al minuto a ~/instance_outfile) e un `tail -f` per osservarli. Sono job
della shell SSH, ma se non terminati esplicitamente con i segnali richiesti
(passi 5-8) restano vivi come processi orfani su servera anche dopo che lo
studente si e' disconnesso: e' proprio questo il comportamento che rende
l'esercizio verificabile a posteriori. Stato finale atteso (passi 8-9):
nessun processo 'instance' e nessun 'tail' su instance_outfile ancora vivo.

Il comando `ps -eo comm,args` con match sul campo comm esatto evita il
falso positivo di `pgrep -f` che si autoincontrerebbe nel proprio
argv (contenente le stesse stringhe cercate).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

HOST = "servera"


def main():
    print(f"🔧 Grading personalizzato per 'processes-kill' (host: {HOST})")

    with GradingStep("Nessun processo 'instance' e' rimasto in esecuzione") as step:
        result = run("pgrep -x instance -a", host=HOST)
        if result.returncode == 0:
            step.fail(
                f"Processi 'instance' ancora attivi (andavano terminati con "
                f"kill/pkill): {result.stdout.strip()}"
            )

    with GradingStep("Il 'tail -f' su ~/instance_outfile e' stato terminato") as step:
        result = run(
            "ps -eo comm,args --no-headers | awk '$1==\"tail\"' | grep instance_outfile",
            host=HOST,
        )
        if result.returncode == 0:
            step.fail("Il processo 'tail -f ~/instance_outfile' e' ancora attivo")


if __name__ == "__main__":
    main()
