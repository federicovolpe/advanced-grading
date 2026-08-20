#!/usr/bin/env python3
"""
Grading personalizzato per la guided exercise AU294 "system-roles" (guida
studente, sez. 8.2 "Using System Roles", pag. 462-467), sprovvista di grading
ufficiale (au0026l/system-roles.py non ha def grade()).

Fonte primaria: materials/labs/system-roles/solutions/configure_time.yml.sol
e solutions/group_vars/all/timesync.sol nel pacchetto pip au0026l, che
coincidono parola per parola con il contenuto "must now contain" mostrato
passo-passo nella guida (stessa sezione). Nessun valore e' stato inventato.

Verifica SOLO i file statici scritti dallo studente sulla workstation
(~/system-roles/...): NON esegue mai il playbook, perche' farlo riavvia
servera e serverb (guida, passo 7.2/handler "Reboot host") - un rischio
inaccettabile su host condivisi con l'intera classe. In coda ci sono due
controlli "bonus" dal vivo che usano SOLO `timedatectl show` (comando in
sola lettura, non modifica nulla) per confermare se il playbook risulta gia'
eseguito con successo: falliscono in modo innocuo se non lo e' ancora,
senza inficiare gli altri controlli.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

LAB_NAME = "system-roles"


def _project_dir(name):
    return os.path.join(os.path.expanduser("~"), name)


def _load_yaml(path):
    import yaml
    try:
        with open(path) as f:
            return yaml.safe_load(f)
    except (OSError, yaml.YAMLError):
        return None


def _find_task(tasks, name):
    if not isinstance(tasks, list):
        return None
    for t in tasks:
        if isinstance(t, dict) and t.get("name") == name:
            return t
    return None


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    base = _project_dir(project)
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (dir: {base})")

    with GradingStep(f"La directory dell'esercizio {base} esiste") as step:
        if not os.path.isdir(base):
            step.fail(f"Directory '{base}' non trovata: eseguire 'lab start {LAB_NAME}'")

    with GradingStep("La collection redhat.rhel_system_roles e' installata in ./collections (passo 2.4)") as step:
        manifest = os.path.join(base, "collections", "ansible_collections", "redhat",
                                 "rhel_system_roles", "MANIFEST.json")
        if not os.path.isfile(manifest):
            step.fail("collections/ansible_collections/redhat/rhel_system_roles non trovata "
                       "('ansible-galaxy collection install' non eseguito)")

    with GradingStep("ansible.cfg cerca le collection anche in ./collections (passo 2.3)") as step:
        cfg_path = os.path.join(base, "ansible.cfg")
        try:
            with open(cfg_path) as f:
                content = f.read()
        except OSError:
            content = None
            step.fail("ansible.cfg non trovato")
        if content is not None:
            if "collections_path" not in content.lower():
                step.add_error("Nessuna direttiva collections_path(s) trovata in ansible.cfg")
            elif "./collections" not in content:
                step.add_error("collections_path(s) non include './collections'")

    playbook = _load_yaml(os.path.join(base, "configure_time.yml"))
    play = playbook[0] if isinstance(playbook, list) and playbook else None

    with GradingStep("configure_time.yml: play su database_servers con il ruolo timesync (passi 3-4)") as step:
        if not play:
            step.fail("configure_time.yml assente o non e' una lista di play valida")
        else:
            if play.get("hosts") != "database_servers":
                step.add_error(f"hosts atteso 'database_servers', trovato '{play.get('hosts')}'")
            roles = play.get("roles") or []
            role_names = [r if isinstance(r, str) else (r or {}).get("name") for r in roles]
            if "redhat.rhel_system_roles.timesync" not in role_names:
                step.add_error("Il ruolo redhat.rhel_system_roles.timesync non e' incluso in roles")

    with GradingStep("configure_time.yml: post_tasks get/set fuso orario (passo 5)") as step:
        if not play:
            step.fail("configure_time.yml assente")
        else:
            post_tasks = play.get("post_tasks") or []
            get_tz = _find_task(post_tasks, "Get time zone")
            set_tz = _find_task(post_tasks, "Set time zone")
            if not get_tz:
                step.add_error("Task 'Get time zone' non trovato in post_tasks")
            else:
                if get_tz.get("ansible.builtin.command") != "timedatectl show":
                    step.add_error("Task 'Get time zone' non usa 'timedatectl show'")
                if get_tz.get("register") != "current_timezone":
                    step.add_error("Task 'Get time zone' non registra 'current_timezone'")
            if not set_tz:
                step.add_error("Task 'Set time zone' non trovato in post_tasks")
            else:
                cmd = set_tz.get("ansible.builtin.command", "") or ""
                if "timedatectl set-timezone" not in cmd or "host_timezone" not in cmd:
                    step.add_error("Task 'Set time zone' non usa 'timedatectl set-timezone {{ host_timezone }}'")
                when = str(set_tz.get("when", ""))
                if "host_timezone" not in when or "current_timezone" not in when:
                    step.add_error("Condizione 'when' non confronta host_timezone con current_timezone.stdout")
                if set_tz.get("notify") != "Reboot host":
                    step.add_error("Task 'Set time zone' non ha 'notify: Reboot host'")

    with GradingStep("configure_time.yml: handler 'Reboot host' con ansible.builtin.reboot (passo 5.3)") as step:
        if not play:
            step.fail("configure_time.yml assente")
        else:
            handler = _find_task(play.get("handlers") or [], "Reboot host")
            if not handler:
                step.add_error("Handler 'Reboot host' non trovato")
            elif "ansible.builtin.reboot" not in handler:
                step.add_error("Handler 'Reboot host' non usa il modulo ansible.builtin.reboot")

    timesync_vars = _load_yaml(os.path.join(base, "group_vars", "all", "timesync.yml"))
    with GradingStep("group_vars/all/timesync.yml: variabili del ruolo timesync (passo 4.3)") as step:
        if not isinstance(timesync_vars, dict):
            step.fail("group_vars/all/timesync.yml assente o non valido")
        else:
            if timesync_vars.get("timesync_ntp_provider") != "chrony":
                step.add_error("timesync_ntp_provider atteso 'chrony'")
            servers = timesync_vars.get("timesync_ntp_servers") or []
            match = any(
                isinstance(s, dict) and s.get("hostname") == "classroom.example.com" and s.get("iburst")
                for s in servers
            )
            if not match:
                step.add_error("timesync_ntp_servers deve contenere hostname 'classroom.example.com' con iburst true")

    na_vars = _load_yaml(os.path.join(base, "group_vars", "na_datacenter", "timezone.yml"))
    with GradingStep("group_vars/na_datacenter/timezone.yml: host_timezone America/Chicago (passo 6)") as step:
        if not isinstance(na_vars, dict):
            step.fail("group_vars/na_datacenter/timezone.yml assente o non valido")
        elif na_vars.get("host_timezone") != "America/Chicago":
            step.add_error(f"host_timezone atteso 'America/Chicago', trovato '{na_vars.get('host_timezone')}'")

    eu_vars = _load_yaml(os.path.join(base, "group_vars", "europe_datacenter", "timezone.yml"))
    with GradingStep("group_vars/europe_datacenter/timezone.yml: host_timezone Europe/Helsinki (passo 6)") as step:
        if not isinstance(eu_vars, dict):
            step.fail("group_vars/europe_datacenter/timezone.yml assente o non valido")
        elif eu_vars.get("host_timezone") != "Europe/Helsinki":
            step.add_error(f"host_timezone atteso 'Europe/Helsinki', trovato '{eu_vars.get('host_timezone')}'")

    # Bonus dal vivo, SOLO lettura (timedatectl show, mai set-timezone): conferma se
    # il playbook e' gia' stato eseguito con successo (guida, passo 8). Non e'
    # bloccante per gli altri controlli se gli host non sono raggiungibili.
    with GradingStep("(bonus, sola lettura) servera e' in America/Chicago") as step:
        result = run("timedatectl show", host="servera")
        if result.returncode != 0:
            step.fail("servera non raggiungibile o timedatectl non disponibile")
        elif "Timezone=America/Chicago" not in result.stdout:
            step.add_error("Timezone su servera non e' America/Chicago (playbook non ancora eseguito?)")

    with GradingStep("(bonus, sola lettura) serverb e' in Europe/Helsinki") as step:
        result = run("timedatectl show", host="serverb")
        if result.returncode != 0:
            step.fail("serverb non raggiungibile o timedatectl non disponibile")
        elif "Timezone=Europe/Helsinki" not in result.stdout:
            step.add_error("Timezone su serverb non e' Europe/Helsinki (playbook non ancora eseguito?)")


if __name__ == "__main__":
    main()
