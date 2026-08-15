#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "rcopy-sync" (sezione PDF
8.4 "Synchronize Content Between Systems", pag. 204-206), sprovvista di
`lab grade` ufficiale. Nessuna materials/solutions ne' resources.txt:
specifica presa dal testo della guida, su serverb.

Stato finale atteso: ~/serverlogs/log/messages su serverb esiste e
contiene la riga "Log files synchronized" (generata da `logger` su servera
al passo 4, poi sincronizzata con rsync al passo 5 — prova che sia la
prima che la seconda sincronizzazione incrementale sono avvenute).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

HOST = "serverb"


def main():
    print(f"🔧 Grading personalizzato per 'rcopy-sync' (host: {HOST})")

    with GradingStep("~/serverlogs/log/messages su serverb contiene la riga sincronizzata da servera") as step:
        result = run("cat ~/serverlogs/log/messages", host=HOST)
        if result.returncode != 0:
            step.fail("~/serverlogs/log/messages non trovato su serverb")
        elif "Log files synchronized" not in result.stdout:
            step.add_error(
                "'Log files synchronized' non trovato in ~/serverlogs/log/messages: "
                "la seconda sincronizzazione incrementale non risulta avvenuta"
            )


if __name__ == "__main__":
    main()
