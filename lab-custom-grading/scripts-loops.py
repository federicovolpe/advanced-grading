#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "scripts-loops" (sezione PDF
1.6 "Run Loops and Conditional Commands", pag. 38-40), sprovvista di
`lab grade` ufficiale. Nessuna materials/solutions ne' resources.txt:
specifica presa dal testo della guida, su workstation.

Stato finale atteso (passo 3): ~/bin/printhostname.sh esiste, eseguibile,
in PATH; eseguito produce hostname di servera/serverb e il messaggio
if/then/else corretto, con exit code 0.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, file_exists

SCRIPT_PATH = os.path.expanduser("~/bin/printhostname.sh")


def main():
    print("🔧 Grading personalizzato per 'scripts-loops' (host: workstation)")

    with GradingStep(f"{SCRIPT_PATH} esiste ed e' eseguibile") as step:
        if not file_exists(SCRIPT_PATH):
            step.fail(f"{SCRIPT_PATH} non trovato")
        elif run(f"test -x {SCRIPT_PATH}").returncode != 0:
            step.fail(f"{SCRIPT_PATH} esiste ma non e' eseguibile")

    with GradingStep("~/bin e' incluso nella variabile PATH") as step:
        result = run("bash -lc 'echo $PATH'")
        home_bin = os.path.expanduser("~/bin")
        if home_bin not in result.stdout:
            step.add_error(f"'{home_bin}' non trovato in PATH: {result.stdout.strip()}")

    with GradingStep("Lo script produce l'output atteso ed esce con codice 0") as step:
        result = run(f"bash {SCRIPT_PATH}")
        if result.returncode != 0:
            step.add_error(f"Exit code {result.returncode} (atteso 0)")
        out = result.stdout
        if "servera" not in out or "serverb" not in out:
            step.add_error(f"Output non contiene entrambi gli hostname attesi: {out.strip()}")
        if "The host is servera" not in out:
            step.add_error("Messaggio 'The host is servera' non trovato nell'output")
        if "The host is not servera" not in out:
            step.add_error("Messaggio 'The host is not servera' non trovato nell'output")


if __name__ == "__main__":
    main()
