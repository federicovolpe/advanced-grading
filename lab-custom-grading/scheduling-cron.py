#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "scheduling-cron" (sezione
PDF 3.4 "Schedule Recurring User Jobs", pag. 73-74), sprovvista di
`lab grade` ufficiale. Nessuna materials/solutions ne' resources.txt:
specifica presa dal testo della guida, su servera.

Stato finale atteso:
- ~/my_first_cron_job.txt esiste e non e' vuoto (prova che il job cron
  "*/2 * * * Tue-Thu /usr/bin/date >> ..." ha effettivamente girato,
  passo 5).
- Il crontab dello user student e' stato rimosso con `crontab -r` (passo
  6.1): `crontab -l` deve risultare vuoto.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

HOST = "servera"


def main():
    print(f"🔧 Grading personalizzato per 'scheduling-cron' (host: {HOST})")

    with GradingStep("~/my_first_cron_job.txt esiste e contiene output (job cron eseguito, passo 5)") as step:
        result = run("cat ~/my_first_cron_job.txt", host=HOST)
        if result.returncode != 0 or not result.stdout.strip():
            step.fail("~/my_first_cron_job.txt non trovato o vuoto")

    with GradingStep("Il crontab dello user student e' stato rimosso (crontab -r, passo 6.1)") as step:
        result = run("crontab -l", host=HOST)
        if result.returncode == 0 and result.stdout.strip():
            step.add_error(
                f"crontab -l mostra ancora job pendenti: {result.stdout.strip()}"
            )


if __name__ == "__main__":
    main()
