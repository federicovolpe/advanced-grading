#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "regexes-regex" (sezione PDF
2.2 "Match Text with Regular Expressions", pag. 55-57), sprovvista di
`lab grade` ufficiale. Nessuna materials/solutions ne' resources.txt.

L'esercizio e' quasi interamente esplorativo (grep/systemctl status/ps ax/
vim su file e output preesistenti, senza modificarli): l'unico artefatto
persistente e oggettivamente verificabile a posteriori e' il passo 5.1, che
chiede di redirigere l'output di `grep httpd /var/log/messages` nel file
/tmp/httpd.log su servera.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, file_exists

HOST = "servera"
LOG_PATH = "/tmp/httpd.log"


def main():
    print(f"🔧 Grading personalizzato per 'regexes-regex' (host: {HOST})")

    with GradingStep(f"{LOG_PATH} esiste e contiene righe relative a httpd") as step:
        if not file_exists(LOG_PATH, host=HOST, sudo=True):
            step.fail(f"{LOG_PATH} non trovato su {HOST}")
        else:
            result = run(f"cat {LOG_PATH}", host=HOST, sudo=True)
            lines = [l for l in result.stdout.splitlines() if l.strip()]
            if not lines:
                step.add_error(f"{LOG_PATH} e' vuoto")
            elif not all("httpd" in l for l in lines):
                step.add_error(
                    f"{LOG_PATH} contiene righe non filtrate su 'httpd': {lines[:3]}"
                )


if __name__ == "__main__":
    main()
