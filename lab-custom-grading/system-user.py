#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise AU294 "system-user" (sku au0026l,
sezione 8.6 "Automating User Management and Authentication Tasks"),
sprovvista di `lab grade` ufficiale. Specifica presa da
materials/labs/system-user/solutions/users.yml.sol (diff completo con lo
starter, che ha solo file/vars di supporto) e da
materials/labs/system-user/vars/users_vars.yml (utenti/gruppo gia' fissi,
non a scelta dello studente).

Stato finale atteso su servera:
- gruppo 'webadmin' esistente.
- utenti user1..user5, membri del gruppo webadmin, con la authorized_key
  fornita in materials/labs/system-user/files/userN.key.pub (confrontata
  con la copia locale sotto ~/system-user/files/, sincronizzata da
  `lab start` sulla workstation).
- /etc/sudoers.d/webadmin con la riga
  "%webadmin ALL=(ALL) NOPASSWD: ALL" (mode 0440).
- /etc/ssh/sshd_config con "PermitRootLogin no".
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, user_exists, group_exists

HOST = "servera"
_USERS = ["user1", "user2", "user3", "user4", "user5"]
_EXERCISE_DIR = os.path.expanduser("~/system-user")


def user_in_group(username, group, host=HOST):
    result = run(f"id -nG {username}", host=host)
    return result.returncode == 0 and group in result.stdout.split()


def authorized_key_matches(username, host=HOST):
    local_pub_path = os.path.join(_EXERCISE_DIR, "files", f"{username}.key.pub")
    if not os.path.exists(local_pub_path):
        return None  # non verificabile: file di partenza mancante/rinominato
    with open(local_pub_path) as f:
        expected_key = f.read().split()[1]  # solo il blob base64, non il commento
    result = run(f"cat ~{username}/.ssh/authorized_keys", host=host, sudo=True)
    if result.returncode != 0:
        return False
    return expected_key in result.stdout


def main():
    print(f"🔧 Grading personalizzato per 'system-user' (host: {HOST})")

    with GradingStep("Il gruppo webadmin esiste su servera") as step:
        if not group_exists("webadmin", host=HOST):
            step.fail("Gruppo 'webadmin' non trovato")

    for username in _USERS:
        with GradingStep(f"L'utente {username} esiste ed e' nel gruppo webadmin") as step:
            if not user_exists(username, host=HOST):
                step.fail(f"Utente '{username}' non trovato")
            elif not user_in_group(username, "webadmin"):
                step.add_error(f"'{username}' esiste ma non e' nel gruppo webadmin")

        with GradingStep(f"La authorized_key di {username} corrisponde a quella fornita") as step:
            match = authorized_key_matches(username)
            if match is None:
                step.add_error(
                    f"File locale ~/system-user/files/{username}.key.pub non trovato: "
                    "chiave attesa non verificabile"
                )
            elif not match:
                step.fail(f"authorized_keys di '{username}' non contiene la chiave attesa")

    with GradingStep("/etc/sudoers.d/webadmin consente sudo senza password al gruppo webadmin") as step:
        result = run("cat /etc/sudoers.d/webadmin", host=HOST, sudo=True)
        if result.returncode != 0:
            step.fail("/etc/sudoers.d/webadmin non trovato")
        elif "%webadmin ALL=(ALL) NOPASSWD: ALL" not in result.stdout:
            step.add_error("Riga '%webadmin ALL=(ALL) NOPASSWD: ALL' non trovata")

    with GradingStep("Il login SSH di root e' disabilitato su servera") as step:
        result = run("cat /etc/ssh/sshd_config", host=HOST, sudo=True)
        if result.returncode != 0:
            step.fail("Impossibile leggere /etc/ssh/sshd_config")
        elif not any(
            line.strip().lower() == "permitrootlogin no"
            for line in result.stdout.splitlines()
        ):
            step.add_error("'PermitRootLogin no' non impostato in /etc/ssh/sshd_config")


if __name__ == "__main__":
    main()
