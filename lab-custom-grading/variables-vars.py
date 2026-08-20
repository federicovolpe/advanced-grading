#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise AU294 "variables-vars" (sku au0021l,
sez. guida 3.2 "Using Variables"), sprovvista di `lab grade` ufficiale.

Fonte primaria: materials/labs/variables-vars/solutions/ (playbook.yml.sol,
group_vars/{allservers,dev,prod}/vars.yml.sol), confermata dal testo guida.
Inventory di partenza: gruppo prod = servera/serverb, gruppo dev =
serverc/serverd, allservers = prod+dev.

Gradiamo l'EFFETTO reale sui 4 host gestiti (non il testo del playbook):
l'utente per-gruppo (alice/8888 su prod, bob/9999 su dev) con lo uid esatto
richiesto dai group_vars. NON gradiamo cockpit/firewalld: verificato dal
vivo (SSH read-only, prima di qualunque intervento dello studente) che su
questa classroom cockpit.socket e firewalld sono GIA' installati, attivi,
abilitati e con la regola "cockpit" gia' permanente su tutti e 4 gli host -
e' lo stato di default dell'immagine base, non un effetto del playbook.
Gradarlo darebbe sempre PASS anche a esercizio non svolto (vedi CLAUDE.md:
"gradua solo quello che l'esercizio chiede di fare/modificare, non dettagli
incidentali già presenti nello starter").
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

LAB_NAME = "variables-vars"
_GROUP_USERS = {
    "prod": (["servera", "serverb"], "alice", "8888"),
    "dev": (["serverc", "serverd"], "bob", "9999"),
}


def _uid_of(username, host):
    result = run(f"id -u {username}", host=host)
    return result.stdout.strip() if result.returncode == 0 else None


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    for group, (hosts, username, uid) in _GROUP_USERS.items():
        with GradingStep(f"Gruppo {group}: utente {username} esiste con UID {uid}") as step:
            for host in hosts:
                found_uid = _uid_of(username, host=host)
                if found_uid is None:
                    step.add_error(f"Utente '{username}' non trovato su {host}")
                elif found_uid != uid:
                    step.add_error(f"UID di '{username}' su {host} = {found_uid}, atteso {uid}")


if __name__ == "__main__":
    main()
