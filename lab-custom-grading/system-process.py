#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise AU294 "system-process" (sku
au0026l, sezione 8.8 "Automating the Boot Process and Scheduled
Processes"), sprovvista di `lab grade` ufficiale. Specifica presa dal
diff solutions/*.sol dello starter (5 playbook forniti in sequenza) e
dall'ordine di esecuzione descritto nella guida (passi 2-7), che determina
lo stato FINALE atteso su servera:

1. create_crontab_file.yml crea /etc/cron.d/add-date-time (passo 2).
2. remove_cron_job.yml lo rimuove di nuovo (passo 3, "Verify... file has
   been removed") -> stato finale: il file NON esiste piu'.
3. schedule_at_task.yml pianifica un job `at` una tantum che scrive
   ~devops/my_at_date_time (passo 4) -> dopo l'esecuzione (il job scatta
   entro 1 minuto) il file resta come prova permanente.
4. set_default_boot_target_graphical.yml + reboot_hosts.yml impostano
   graphical.target e riavviano per dimostrare la persistenza (passi 5-6).
5. set_default_boot_target_multi-user.yml riporta il target a
   multi-user.target "to maintain consistency throughout the remaining
   exercises" (passo 7, esplicito nel testo) -> stato finale atteso:
   multi-user.target.

Il riavvio (passo 6) e' solo dimostrativo e non lascia stato verificabile
di per se': non viene gradato.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, file_exists

HOST = "servera"


def main():
    print(f"🔧 Grading personalizzato per 'system-process' (host: {HOST})")

    with GradingStep("Il cron job dimostrativo e' stato rimosso (/etc/cron.d/add-date-time)") as step:
        if file_exists("/etc/cron.d/add-date-time", host=HOST, sudo=True):
            step.fail(
                "/etc/cron.d/add-date-time esiste ancora: andava rimosso con "
                "remove_cron_job.yml (passo 3 della guida)"
            )

    with GradingStep("Il job 'at' una tantum ha creato ~devops/my_at_date_time") as step:
        if not file_exists("/home/devops/my_at_date_time", host=HOST, sudo=True):
            step.fail(
                "/home/devops/my_at_date_time non trovato: il job schedulato con "
                "schedule_at_task.yml non risulta eseguito"
            )

    with GradingStep("Il target di boot predefinito e' multi-user.target") as step:
        result = run("systemctl get-default", host=HOST)
        if result.returncode != 0:
            step.fail("Impossibile eseguire systemctl get-default su servera")
        elif result.stdout.strip() != "multi-user.target":
            step.add_error(
                f"Target predefinito attuale '{result.stdout.strip()}', "
                "atteso 'multi-user.target' (passo 7: riportato da graphical.target)"
            )


if __name__ == "__main__":
    main()
