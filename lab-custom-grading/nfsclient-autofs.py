#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "nfsclient-autofs" (sezione
PDF 15.4 "Automount Storage Devices", pag. 372-375), sprovvista di
`lab grade` ufficiale. Nessuna materials/solutions ne' resources.txt:
specifica presa dal testo della guida, su servera.

Stato finale atteso:
- autofs installato, attivo ed enabled (passi 1.2, 3.5).
- /etc/auto.master contiene le due righe per il mount diretto e indiretto
  (passo 3.2).
- /etc/auto.direct e /etc/auto.indirect hanno il contenuto esatto (passi
  3.3-3.4).
- Accedendo a /home/student/direct e /home/student/indirect (automount on
  demand), il contenuto NFS e' realmente raggiungibile (grep "RED" produce
  risultati, passi 4.2/5.5).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, package_installed, service_is_active, service_is_enabled

HOST = "servera"
_AUTO_MASTER_LINES = [
    "/- /etc/auto.direct",
    "/home/student/indirect /etc/auto.indirect",
]
_AUTO_DIRECT_LINE = "/home/student/direct -fstype=nfs,rw,sync serverb:/shares"
_AUTO_INDIRECT_LINE = "* -fstype=nfs,rw,sync serverb:/shares/&"


def main():
    print(f"🔧 Grading personalizzato per 'nfsclient-autofs' (host: {HOST})")

    with GradingStep("Il pacchetto autofs e' installato") as step:
        if not package_installed("autofs", host=HOST):
            step.fail("Pacchetto 'autofs' non installato")

    with GradingStep("Il servizio autofs e' attivo ed enabled") as step:
        if not service_is_active("autofs", host=HOST):
            step.add_error("autofs non e' active")
        if not service_is_enabled("autofs", host=HOST):
            step.add_error("autofs non e' enabled")

    with GradingStep("/etc/auto.master contiene le entry dirette e indirette") as step:
        result = run("cat /etc/auto.master", host=HOST, sudo=True)
        lines = [" ".join(l.split()) for l in result.stdout.splitlines()]
        for expected in _AUTO_MASTER_LINES:
            if expected not in lines:
                step.add_error(f"Entry attesa '{expected}' non trovata in /etc/auto.master")

    with GradingStep("/etc/auto.direct ha il contenuto atteso") as step:
        result = run("cat /etc/auto.direct", host=HOST, sudo=True)
        lines = [" ".join(l.split()) for l in result.stdout.splitlines() if l.strip()]
        if _AUTO_DIRECT_LINE not in lines:
            step.add_error(f"Atteso '{_AUTO_DIRECT_LINE}', trovato: {lines}")

    with GradingStep("/etc/auto.indirect ha il contenuto atteso") as step:
        result = run("cat /etc/auto.indirect", host=HOST, sudo=True)
        lines = [" ".join(l.split()) for l in result.stdout.splitlines() if l.strip()]
        if _AUTO_INDIRECT_LINE not in lines:
            step.add_error(f"Atteso '{_AUTO_INDIRECT_LINE}', trovato: {lines}")

    with GradingStep("Il mount diretto (/home/student/direct) e' realmente raggiungibile via NFS") as step:
        result = run("grep -rl RED /home/student/direct", host=HOST)
        if result.returncode != 0 or not result.stdout.strip():
            step.add_error("Nessun contenuto NFS trovato in /home/student/direct (automount non funzionante)")

    with GradingStep("Il mount indiretto (/home/student/indirect) e' realmente raggiungibile via NFS") as step:
        run("ls /home/student/indirect/west /home/student/indirect/south", host=HOST)
        result = run("grep -rl RED /home/student/indirect", host=HOST)
        if result.returncode != 0 or not result.stdout.strip():
            step.add_error("Nessun contenuto NFS trovato in /home/student/indirect (automount non funzionante)")


if __name__ == "__main__":
    main()
