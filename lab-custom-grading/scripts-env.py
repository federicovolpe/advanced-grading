#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "scripts-env" (sezione PDF 1.2
"Change the Shell Environment", pag. 21-23), sprovvista di `lab grade`
ufficiale. Nessuna materials/solutions ne' resources.txt: specifica presa
dal testo della guida, su servera.

L'unico effetto persistente e oggettivamente verificabile a posteriori e'
la riga PS1 aggiunta a ~/.bashrc (passo 1.2): "PS1='[\\u@\\h \\t \\w]$ '".
Le altre parti dell'esercizio (variabile "file", export EDITOR=vim) sono
transitorie: non sopravvivono a una nuova sessione SSH perche' non vengono
scritte in un file di configurazione dalla guida, quindi non sono
verificabili a posteriori e non vengono gradate.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

HOST = "servera"
_EXPECTED_PS1 = "PS1='[\\u@\\h \\t \\w]$ '"


def main():
    print(f"🔧 Grading personalizzato per 'scripts-env' (host: {HOST})")

    with GradingStep("~/.bashrc su servera imposta il PS1 richiesto") as step:
        result = run("cat ~/.bashrc", host=HOST)
        if result.returncode != 0:
            step.fail("Impossibile leggere ~/.bashrc su servera")
        elif _EXPECTED_PS1 not in result.stdout:
            step.add_error(
                f"Riga attesa '{_EXPECTED_PS1}' non trovata in ~/.bashrc"
            )


if __name__ == "__main__":
    main()
