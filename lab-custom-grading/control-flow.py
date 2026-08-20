#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise AU294 "control-flow" (Cap. 4.2
"Using Loops and Conditional Tasks"), sprovvista di `lab grade` ufficiale
(control-flow.py del pacchetto au0022l implementa solo start()/finish()).

Specifica presa da materials/labs/control-flow/solutions/users.yml.sol
(identico al testo guida, Cap. 4.2 punto 3.6) e dall'inventory dell'esercizio
(materials/labs/control-flow/inventory): host group datacenter_west con
servera.lab.example.com e serverb.lab.example.com.

Stato finale atteso in users.yml:
- play su datacenter_west, become: true, vars prod_users/dev_users come da
  guida (mary/wheel, nick/kvm; webdev/developer, dbdev/developer).
- task 1: ansible.builtin.debug che mostra la SELinux mode via ansible_facts.
- task 2: ansible.builtin.user in loop su prod_users, when selinux mode
  "enforcing".
- task 3: ansible.builtin.user in loop su dev_users, when selinux mode
  "permissive".

In questa sessione servera.lab.example.com risulta Enforcing e
serverb.lab.example.com Permissive (verificato via `getenforce` in sola
lettura): la mode e' interrogata dinamicamente invece di essere hardcoded,
cosi' lo script resta corretto anche se una futura classroom la invertisse.
Il controllo "live" e' in sola lettura (getent passwd/group): se lo studente
ha gia' eseguito users.yml, verifica che gli utenti giusti siano stati creati
sull'host con la SELinux mode giusta.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, user_exists

LAB_NAME = "control-flow"
PLAYBOOK_NAME = "users.yml"
HOST_A = "servera"
HOST_B = "serverb"

EXPECTED_PROD_USERS = [
    {"user": "mary", "group": "wheel"},
    {"user": "nick", "group": "kvm"},
]
EXPECTED_DEV_USERS = [
    {"user": "webdev", "group": "developer"},
    {"user": "dbdev", "group": "developer"},
]


def load_playbook(path):
    """Carica il playbook YAML. None se il file manca o non e' YAML valido."""
    import yaml

    try:
        with open(path) as f:
            return yaml.safe_load(f)
    except (OSError, yaml.YAMLError):
        return None


def get_first_play(playbook):
    if isinstance(playbook, list) and playbook:
        return playbook[0]
    return None


def hosts_include(hosts_field, expected):
    if isinstance(hosts_field, list):
        return expected in hosts_field
    return hosts_field == expected


def find_tasks(tasks, module):
    return [t for t in (tasks or []) if isinstance(t, dict) and module in t]


def references(value, *substrings):
    """True se il valore templated (stringa Jinja) contiene tutte le
    substring cercate (case-insensitive) - usato per non essere troppo
    rigidi sulla sintassi esatta (dot vs bracket notation)."""
    text = str(value or "").lower()
    return all(s.lower() in text for s in substrings)


def selinux_mode(host):
    """Interroga getenforce in sola lettura (nessuna modifica)."""
    result = run("getenforce", host=host)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def user_in_group(username, groupname, host):
    """Legge in sola lettura i gruppi secondari dell'utente (id -nG)."""
    result = run(f"id -nG {username}", host=host)
    if result.returncode != 0:
        return False
    return groupname in result.stdout.split()


def main():
    dirname = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    workdir = os.path.expanduser(f"~/{dirname}")
    playbook_path = os.path.join(workdir, PLAYBOOK_NAME)
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (cartella: {workdir})")

    playbook = load_playbook(playbook_path)
    play = None
    tasks = []

    with GradingStep(f"Il file {PLAYBOOK_NAME} esiste ed e' YAML valido") as step:
        if playbook is None:
            step.fail(f"'{playbook_path}' non trovato o non e' YAML valido")
        else:
            play = get_first_play(playbook)
            if play is None:
                step.fail("Il playbook non contiene nessun play")
            else:
                tasks = play.get("tasks") or []

    with GradingStep("Il play punta a datacenter_west con become abilitato") as step:
        if play is None:
            step.fail()
        else:
            if not hosts_include(play.get("hosts"), "datacenter_west"):
                step.add_error(
                    f"hosts atteso 'datacenter_west', trovato '{play.get('hosts')}'"
                )
            if play.get("become") is not True:
                step.add_error("become: true mancante o non impostato sul play")

    with GradingStep("Le variabili prod_users e dev_users sono definite correttamente") as step:
        if play is None:
            step.fail()
        else:
            pvars = (play.get("vars") or {})
            if pvars.get("prod_users") != EXPECTED_PROD_USERS:
                step.add_error(
                    f"prod_users atteso {EXPECTED_PROD_USERS}, trovato {pvars.get('prod_users')}"
                )
            if pvars.get("dev_users") != EXPECTED_DEV_USERS:
                step.add_error(
                    f"dev_users atteso {EXPECTED_DEV_USERS}, trovato {pvars.get('dev_users')}"
                )

    with GradingStep("Un task ansible.builtin.debug mostra la SELinux mode dai facts") as step:
        debug_tasks = find_tasks(tasks, "ansible.builtin.debug")
        found = False
        for t in debug_tasks:
            msg = (t["ansible.builtin.debug"] or {}).get("msg", "")
            if references(msg, "ansible_facts", "selinux", "mode"):
                found = True
                break
        if not found:
            step.fail("Nessun task debug che usi ansible_facts['selinux']['mode']")

    with GradingStep("Il task 'Create prod users' usa loop su prod_users e when enforcing") as step:
        user_tasks = find_tasks(tasks, "ansible.builtin.user")
        found = False
        for t in user_tasks:
            params = t["ansible.builtin.user"] or {}
            loop = t.get("loop")
            when = t.get("when")
            if (
                references(loop, "prod_users")
                and references(when, "selinux", "mode", "enforcing")
                and references(params.get("name"), "item")
                and references(params.get("groups"), "item", "group")
            ):
                found = True
                break
        if not found:
            step.fail(
                "Nessun task ansible.builtin.user con loop su prod_users e "
                "when selinux mode == enforcing"
            )

    with GradingStep("Il task 'Create dev users' usa loop su dev_users e when permissive") as step:
        user_tasks = find_tasks(tasks, "ansible.builtin.user")
        found = False
        for t in user_tasks:
            params = t["ansible.builtin.user"] or {}
            loop = t.get("loop")
            when = t.get("when")
            if (
                references(loop, "dev_users")
                and references(when, "selinux", "mode", "permissive")
                and references(params.get("name"), "item")
                and references(params.get("groups"), "item", "group")
            ):
                found = True
                break
        if not found:
            step.fail(
                "Nessun task ansible.builtin.user con loop su dev_users e "
                "when selinux mode == permissive"
            )

    # --- Controllo live (sola lettura): se lo studente ha gia' eseguito
    # users.yml, gli utenti giusti devono esistere sull'host con la SELinux
    # mode corrispondente. Interroghiamo la mode dal vivo invece di
    # assumere servera=enforcing/serverb=permissive, cosi' il controllo
    # resta valido anche se la classroom venisse riconfigurata.
    mode_a = selinux_mode(HOST_A)
    mode_b = selinux_mode(HOST_B)
    host_enforcing = HOST_A if mode_a == "Enforcing" else (HOST_B if mode_b == "Enforcing" else None)
    host_permissive = HOST_B if mode_b == "Permissive" else (HOST_A if mode_a == "Permissive" else None)

    with GradingStep("(live, sola lettura) prod_users creati sull'host in enforcing mode") as step:
        if host_enforcing is None:
            step.fail(
                "Nessuno dei due host risulta in modalita' 'Enforcing' al momento "
                "(getenforce non raggiungibile o modalita' cambiata rispetto alla "
                "guida): impossibile verificare dal vivo dove vadano creati i prod_users"
            )
        else:
            for u in EXPECTED_PROD_USERS:
                if not user_exists(u["user"], host=host_enforcing):
                    step.add_error(f"Utente '{u['user']}' non trovato su {host_enforcing}")
                elif not user_in_group(u["user"], u["group"], host_enforcing):
                    step.add_error(
                        f"Utente '{u['user']}' su {host_enforcing} non appartiene al gruppo '{u['group']}'"
                    )

    with GradingStep("(live, sola lettura) dev_users creati sull'host in permissive mode") as step:
        if host_permissive is None:
            step.fail(
                "Nessuno dei due host risulta in modalita' 'Permissive' al momento "
                "(getenforce non raggiungibile o modalita' cambiata rispetto alla "
                "guida): impossibile verificare dal vivo dove vadano creati i dev_users"
            )
        else:
            for u in EXPECTED_DEV_USERS:
                if not user_exists(u["user"], host=host_permissive):
                    step.add_error(f"Utente '{u['user']}' non trovato su {host_permissive}")
                elif not user_in_group(u["user"], u["group"], host_permissive):
                    step.add_error(
                        f"Utente '{u['user']}' su {host_permissive} non appartiene al gruppo '{u['group']}'"
                    )


if __name__ == "__main__":
    main()
