#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise AU294 "control-handlers" (Cap. 4.4
"Implementing Handlers"), sprovvista di `lab grade` ufficiale.

Specifica presa da
materials/labs/control-handlers/solutions/configure_webapp.yml.sol
(identico al testo guida, Cap. 4.4 punti 3.1-4.4): il file starter gia'
contiene hosts/vars, lo studente aggiunge SOLO tasks e handlers, quindi
gradiamo solo quelle due sezioni.
Inventory (materials/labs/control-handlers/inventory): gruppo webapp con il
solo servera.lab.example.com.

Tasks attesi (in configure_webapp.yml):
- ansible.builtin.dnf per installare i pacchetti in "packages".
- ansible.builtin.copy del file web (notify "Restart web service").
- ansible.builtin.copy del file app (notify "Restart app service").
- ansible.builtin.systemd_service in loop su web/app/firewall_service,
  state started + enabled true.
- ansible.posix.firewalld in loop su firewall_service_rules.
Handlers attesi:
- "Restart web service" e "Restart app service" (systemd_service restarted).

Controllo live (sola lettura, su servera): se lo studente ha gia' eseguito
il playbook, pacchetti installati, servizi attivi/abilitati e regola
firewalld "http" presente sono osservabili senza bisogno di rieseguire nulla.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, package_installed, service_is_active, service_is_enabled, file_exists

LAB_NAME = "control-handlers"
PLAYBOOK_NAME = "configure_webapp.yml"
HOST = "servera"

EXPECTED_PACKAGES = ["nginx", "php-fpm", "firewalld"]
EXPECTED_SERVICES = ["nginx", "php-fpm", "firewalld"]
EXPECTED_FIREWALL_RULE = "http"
WEB_CONFIG_DST = "/etc/nginx/nginx.conf"
APP_CONFIG_DST = "/etc/php-fpm.conf"


def load_playbook(path):
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


def find_tasks(tasks, module):
    return [t for t in (tasks or []) if isinstance(t, dict) and module in t]


def references(value, *substrings):
    text = str(value or "").lower()
    return all(s.lower() in text for s in substrings)


def notify_list(task):
    """Normalizza il campo notify (stringa singola o lista) in lista."""
    notify = task.get("notify")
    if notify is None:
        return []
    return notify if isinstance(notify, list) else [notify]


def main():
    dirname = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    workdir = os.path.expanduser(f"~/{dirname}")
    playbook_path = os.path.join(workdir, PLAYBOOK_NAME)
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (cartella: {workdir})")

    playbook = load_playbook(playbook_path)
    play = None
    tasks = []
    handlers = []

    with GradingStep(f"Il file {PLAYBOOK_NAME} esiste ed e' YAML valido") as step:
        if playbook is None:
            step.fail(f"'{playbook_path}' non trovato o non e' YAML valido")
        else:
            play = get_first_play(playbook)
            if play is None:
                step.fail("Il playbook non contiene nessun play")
            else:
                tasks = play.get("tasks") or []
                handlers = play.get("handlers") or []

    with GradingStep("Un task ansible.builtin.dnf installa la variabile packages") as step:
        dnf_tasks = find_tasks(tasks, "ansible.builtin.dnf")
        found = any(
            references((t["ansible.builtin.dnf"] or {}).get("name"), "packages")
            for t in dnf_tasks
        )
        if not found:
            step.fail("Nessun task ansible.builtin.dnf con name: \"{{ packages }}\"")

    with GradingStep("Il task che copia il file web notifica 'Restart web service'") as step:
        copy_tasks = find_tasks(tasks, "ansible.builtin.copy")
        found = False
        for t in copy_tasks:
            params = t["ansible.builtin.copy"] or {}
            if (
                references(params.get("src"), "web_config_src")
                and references(params.get("dest"), "web_config_dst")
                and "Restart web service" in notify_list(t)
            ):
                found = True
                break
        if not found:
            step.fail(
                "Nessun task ansible.builtin.copy (web_config_src -> web_config_dst) "
                "con notify: Restart web service"
            )

    with GradingStep("Il task che copia il file app notifica 'Restart app service'") as step:
        copy_tasks = find_tasks(tasks, "ansible.builtin.copy")
        found = False
        for t in copy_tasks:
            params = t["ansible.builtin.copy"] or {}
            if (
                references(params.get("src"), "app_config_src")
                and references(params.get("dest"), "app_config_dst")
                and "Restart app service" in notify_list(t)
            ):
                found = True
                break
        if not found:
            step.fail(
                "Nessun task ansible.builtin.copy (app_config_src -> app_config_dst) "
                "con notify: Restart app service"
            )

    with GradingStep("Un task systemd_service avvia/abilita web/app/firewall service in loop") as step:
        svc_tasks = find_tasks(tasks, "ansible.builtin.systemd_service")
        found = False
        for t in svc_tasks:
            params = t["ansible.builtin.systemd_service"] or {}
            loop = t.get("loop")
            if not isinstance(loop, list) or len(loop) != 3:
                continue
            loop_text = " ".join(str(x) for x in loop)
            if (
                references(loop_text, "web_service")
                and references(loop_text, "app_service")
                and references(loop_text, "firewall_service")
                and references(params.get("name"), "item")
                and params.get("state") == "started"
                and params.get("enabled") is True
            ):
                found = True
                break
        if not found:
            step.fail(
                "Nessun task ansible.builtin.systemd_service con loop su "
                "web_service/app_service/firewall_service, state started, enabled true"
            )

    with GradingStep("Un task ansible.posix.firewalld abilita firewall_service_rules") as step:
        fw_tasks = find_tasks(tasks, "ansible.posix.firewalld")
        found = False
        for t in fw_tasks:
            params = t["ansible.posix.firewalld"] or {}
            if (
                references(t.get("loop"), "firewall_service_rules")
                and references(params.get("service"), "item")
                and params.get("state") == "enabled"
                and params.get("immediate") is True
                and params.get("permanent") is True
            ):
                found = True
                break
        if not found:
            step.fail(
                "Nessun task ansible.posix.firewalld con loop su firewall_service_rules, "
                "state enabled, immediate/permanent true"
            )

    with GradingStep("Gli handler 'Restart web service' e 'Restart app service' sono definiti") as step:
        by_name = {h.get("name"): h for h in handlers if isinstance(h, dict)}
        for hname, var_name in (
            ("Restart web service", "web_service"),
            ("Restart app service", "app_service"),
        ):
            h = by_name.get(hname)
            if h is None:
                step.add_error(f"Handler '{hname}' non trovato")
                continue
            params = h.get("ansible.builtin.systemd_service") or {}
            if not references(params.get("name"), var_name):
                step.add_error(f"Handler '{hname}' non riavvia {{{{ {var_name} }}}}")
            if params.get("state") != "restarted":
                step.add_error(f"Handler '{hname}' non ha state: restarted")

    # --- Controllo live (sola lettura, su servera): osserva l'effetto reale
    # se lo studente ha gia' eseguito configure_webapp.yml.
    with GradingStep("(live, sola lettura) i pacchetti richiesti sono installati su servera") as step:
        for pkg in EXPECTED_PACKAGES:
            if not package_installed(pkg, host=HOST):
                step.add_error(f"Pacchetto '{pkg}' non risulta installato su {HOST}")

    with GradingStep("(live, sola lettura) i servizi sono attivi e abilitati su servera") as step:
        for svc in EXPECTED_SERVICES:
            if not service_is_active(svc, host=HOST):
                step.add_error(f"Servizio '{svc}' non attivo su {HOST}")
            if not service_is_enabled(svc, host=HOST):
                step.add_error(f"Servizio '{svc}' non abilitato su {HOST}")

    with GradingStep("(live, sola lettura) il servizio http e' consentito nel firewall su servera") as step:
        result = run("firewall-cmd --list-services", host=HOST, sudo=True)
        if result.returncode != 0 or EXPECTED_FIREWALL_RULE not in result.stdout.split():
            step.fail(f"Il servizio '{EXPECTED_FIREWALL_RULE}' non risulta abilitato in firewalld su {HOST}")

    with GradingStep("(live, sola lettura) i file di configurazione sono stati distribuiti su servera") as step:
        if not file_exists(WEB_CONFIG_DST, host=HOST):
            step.add_error(f"'{WEB_CONFIG_DST}' non trovato su {HOST}")
        if not file_exists(APP_CONFIG_DST, host=HOST):
            step.add_error(f"'{APP_CONFIG_DST}' non trovato su {HOST}")


if __name__ == "__main__":
    main()
