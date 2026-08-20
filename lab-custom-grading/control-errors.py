#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise AU294 "control-errors" (Cap. 4.6
"Handling Task Failure"), sprovvista di `lab grade` ufficiale.

Specifica presa da materials/labs/control-errors/solutions/*.sol (identici
al testo guida, Cap. 4.6): quattro playbook indipendenti nella cartella
dell'esercizio. Inventory (materials/labs/control-errors/inventory):
gruppo prod = servera.lab.example.com/serverb.lab.example.com,
gruppo dev = serverc.lab.example.com/serverd.lab.example.com.

Playbook attesi:
- ignore_errors.yml: hosts dev, vars required_package=vim-X11/
  optional_package=vlc; installa optional_package con ignore_errors: true.
- force_handlers.yml: hosts dev, force_handlers: true; copia motd.txt con
  notify "Log MOTD update"; l'handler scrive su /var/log/motd_changes.log.
- testing_conditions.yml: hosts dev, vars install_package=httpd (valore
  finale dopo il punto 12 della guida, confermato dal file .sol); task dnf
  con failed_when: install_package != "httpd".
- block.yml: hosts prod, block/rescue/always per creare l'utente
  preferred_usr con UID 0 (fallisce, root ce l'ha gia'), rescue lo ricrea
  senza UID fisso, always mostra `id`.

Il vlc non e' mai verificato come "installato" dal vivo: nel repository
della classroom quel pacchetto non esiste (richiede EPEL), quindi il task
fallisce sempre per progetto della guida - non e' un effetto da controllare.

Controlli live (sola lettura, mai comandi che modificano host): pacchetti
gia' installati, contenuto di /etc/motd e /var/log/motd_changes.log,
esistenza dell'utente prod_user1 - tutti osservabili solo SE lo studente ha
gia' eseguito il playbook corrispondente, quindi possono legittimamente
fallire finche' non lo fa (vedi CLAUDE.md, nota sullo stato "temporaneo ma
gradabile sul momento").
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, package_installed, user_exists

LAB_NAME = "control-errors"
HOST_DEV_C = "serverc"
HOST_DEV_D = "serverd"
HOST_PROD_A = "servera"
HOST_PROD_B = "serverb"

REQUIRED_PACKAGE = "vim-X11"
INSTALL_PACKAGE_FINAL = "httpd"
PREFERRED_USER = "prod_user1"


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
    notify = task.get("notify")
    if notify is None:
        return []
    return notify if isinstance(notify, list) else [notify]


def read_remote_file(path, host):
    """Legge un file remoto in sola lettura (cat), None se non esiste/errore."""
    result = run(f"cat {path}", host=host)
    if result.returncode != 0:
        return None
    return result.stdout


def main():
    dirname = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    workdir = os.path.expanduser(f"~/{dirname}")
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (cartella: {workdir})")

    # ================= ignore_errors.yml =================
    ie_path = os.path.join(workdir, "ignore_errors.yml")
    ie_playbook = load_playbook(ie_path)
    ie_play = get_first_play(ie_playbook) if ie_playbook else None
    ie_tasks = (ie_play or {}).get("tasks") or []

    with GradingStep("ignore_errors.yml: play su dev con vars required/optional_package") as step:
        if ie_play is None:
            step.fail(f"'{ie_path}' non trovato o non e' YAML valido")
        else:
            if ie_play.get("hosts") != "dev":
                step.add_error(f"hosts atteso 'dev', trovato '{ie_play.get('hosts')}'")
            if ie_play.get("become") is not True:
                step.add_error("become: true mancante sul play")
            pvars = ie_play.get("vars") or {}
            if pvars.get("required_package") != "vim-X11":
                step.add_error(f"required_package atteso 'vim-X11', trovato '{pvars.get('required_package')}'")
            if pvars.get("optional_package") != "vlc":
                step.add_error(f"optional_package atteso 'vlc', trovato '{pvars.get('optional_package')}'")

    with GradingStep("ignore_errors.yml: il task del pacchetto opzionale usa ignore_errors: true") as step:
        dnf_tasks = find_tasks(ie_tasks, "ansible.builtin.dnf")
        found = False
        for t in dnf_tasks:
            params = t["ansible.builtin.dnf"] or {}
            if references(params.get("name"), "optional_package") and t.get("ignore_errors") is True:
                found = True
                break
        if not found:
            step.fail("Nessun task dnf su optional_package con ignore_errors: true")

    with GradingStep("ignore_errors.yml: il task del pacchetto richiesto NON ignora gli errori") as step:
        dnf_tasks = find_tasks(ie_tasks, "ansible.builtin.dnf")
        found = False
        for t in dnf_tasks:
            params = t["ansible.builtin.dnf"] or {}
            if references(params.get("name"), "required_package"):
                found = True
                if t.get("ignore_errors") is True:
                    step.add_error(
                        "Il task su required_package non deve avere ignore_errors: true "
                        "(altrimenti l'esercizio non dimostra la differenza di comportamento)"
                    )
        if not found:
            step.fail("Nessun task dnf su required_package")

    with GradingStep("ignore_errors.yml: un task debug finale stampa il messaggio di successo") as step:
        if not find_tasks(ie_tasks, "ansible.builtin.debug"):
            step.fail("Nessun task ansible.builtin.debug finale")

    with GradingStep("(live, sola lettura) vim-X11 installato su serverc/serverd") as step:
        for host in (HOST_DEV_C, HOST_DEV_D):
            if not package_installed(REQUIRED_PACKAGE, host=host):
                step.add_error(f"Pacchetto '{REQUIRED_PACKAGE}' non risulta installato su {host}")

    # ================= force_handlers.yml =================
    fh_path = os.path.join(workdir, "force_handlers.yml")
    fh_playbook = load_playbook(fh_path)
    fh_play = get_first_play(fh_playbook) if fh_playbook else None
    fh_tasks = (fh_play or {}).get("tasks") or []
    fh_handlers = (fh_play or {}).get("handlers") or []

    with GradingStep("force_handlers.yml: play su dev con force_handlers: true") as step:
        if fh_play is None:
            step.fail(f"'{fh_path}' non trovato o non e' YAML valido")
        else:
            if fh_play.get("hosts") != "dev":
                step.add_error(f"hosts atteso 'dev', trovato '{fh_play.get('hosts')}'")
            if fh_play.get("become") is not True:
                step.add_error("become: true mancante sul play")
            if fh_play.get("force_handlers") is not True:
                step.add_error("force_handlers: true mancante sul play")

    with GradingStep("force_handlers.yml: il task MOTD copia files/motd.txt e notifica l'handler") as step:
        copy_tasks = find_tasks(fh_tasks, "ansible.builtin.copy")
        found = False
        for t in copy_tasks:
            params = t["ansible.builtin.copy"] or {}
            if (
                references(params.get("src"), "motd.txt")
                and params.get("dest") == "/etc/motd"
                and "Log MOTD update" in notify_list(t)
            ):
                found = True
                break
        if not found:
            step.fail("Nessun task copy (files/motd.txt -> /etc/motd) con notify: Log MOTD update")

    with GradingStep("force_handlers.yml: un task installa il pacchetto opzionale vlc (senza ignore_errors)") as step:
        dnf_tasks = find_tasks(fh_tasks, "ansible.builtin.dnf")
        found = any(references((t["ansible.builtin.dnf"] or {}).get("name"), "vlc") for t in dnf_tasks)
        if not found:
            step.fail("Nessun task dnf che installi vlc")

    with GradingStep("force_handlers.yml: l'handler 'Log MOTD update' scrive su motd_changes.log") as step:
        by_name = {h.get("name"): h for h in fh_handlers if isinstance(h, dict)}
        h = by_name.get("Log MOTD update")
        if h is None:
            step.fail("Handler 'Log MOTD update' non trovato")
        else:
            params = h.get("ansible.builtin.lineinfile") or {}
            if params.get("path") != "/var/log/motd_changes.log":
                step.add_error(f"path atteso '/var/log/motd_changes.log', trovato '{params.get('path')}'")
            if not references(params.get("line"), "date_time"):
                step.add_error("La riga di log non usa i facts ansible_facts['date_time']")
            if params.get("create") is not True:
                step.add_error("create: true mancante nell'handler")

    with GradingStep("(live, sola lettura) /etc/motd e' stato aggiornato su serverc/serverd") as step:
        for host in (HOST_DEV_C, HOST_DEV_D):
            content = read_remote_file("/etc/motd", host)
            if content is None or "Managed by Ansible" not in content:
                step.add_error(f"/etc/motd su {host} non contiene il banner atteso")

    with GradingStep("(live, sola lettura) /var/log/motd_changes.log registra l'aggiornamento") as step:
        for host in (HOST_DEV_C, HOST_DEV_D):
            content = read_remote_file("/var/log/motd_changes.log", host)
            if content is None or "MOTD updated on" not in content:
                step.add_error(f"/var/log/motd_changes.log su {host} assente o senza la riga attesa")

    # ================= testing_conditions.yml =================
    tc_path = os.path.join(workdir, "testing_conditions.yml")
    tc_playbook = load_playbook(tc_path)
    tc_play = get_first_play(tc_playbook) if tc_playbook else None
    tc_tasks = (tc_play or {}).get("tasks") or []

    with GradingStep("testing_conditions.yml: play su dev con install_package: httpd") as step:
        if tc_play is None:
            step.fail(f"'{tc_path}' non trovato o non e' YAML valido")
        else:
            if tc_play.get("hosts") != "dev":
                step.add_error(f"hosts atteso 'dev', trovato '{tc_play.get('hosts')}'")
            if tc_play.get("become") is not True:
                step.add_error("become: true mancante sul play")
            pvars = tc_play.get("vars") or {}
            # Valore finale atteso a fine esercizio (punto 12 della guida):
            # lo studente lo cambia da vsftpd a httpd apposta per far
            # riuscire il task successivo.
            if pvars.get("install_package") != INSTALL_PACKAGE_FINAL:
                step.add_error(
                    f"install_package atteso '{INSTALL_PACKAGE_FINAL}' (valore finale richiesto "
                    f"dal punto 12 della guida), trovato '{pvars.get('install_package')}'"
                )

    with GradingStep("testing_conditions.yml: il task 'date' usa changed_when: false") as step:
        cmd_tasks = find_tasks(tc_tasks, "ansible.builtin.command")
        found = False
        for t in cmd_tasks:
            params = t["ansible.builtin.command"] or {}
            if references(params.get("cmd"), "date") and t.get("register") and t.get("changed_when") is False:
                found = True
                break
        if not found:
            step.fail("Nessun task command 'date' con register e changed_when: false")

    with GradingStep("testing_conditions.yml: il task dnf ha failed_when: install_package != \"httpd\"") as step:
        dnf_tasks = find_tasks(tc_tasks, "ansible.builtin.dnf")
        found = False
        for t in dnf_tasks:
            params = t["ansible.builtin.dnf"] or {}
            if references(params.get("name"), "install_package") and references(
                t.get("failed_when"), "install_package", "httpd"
            ):
                found = True
                break
        if not found:
            step.fail("Nessun task dnf su install_package con failed_when che confronta con \"httpd\"")

    with GradingStep("(live, sola lettura) httpd installato su serverc/serverd") as step:
        for host in (HOST_DEV_C, HOST_DEV_D):
            if not package_installed("httpd", host=host):
                step.add_error(f"Pacchetto 'httpd' non risulta installato su {host}")

    # ================= block.yml =================
    b_path = os.path.join(workdir, "block.yml")
    b_playbook = load_playbook(b_path)
    b_play = get_first_play(b_playbook) if b_playbook else None
    b_tasks = (b_play or {}).get("tasks") or []

    with GradingStep("block.yml: play su prod con preferred_usr/preferred_uid") as step:
        if b_play is None:
            step.fail(f"'{b_path}' non trovato o non e' YAML valido")
        else:
            if b_play.get("hosts") != "prod":
                step.add_error(f"hosts atteso 'prod', trovato '{b_play.get('hosts')}'")
            if b_play.get("become") is not True:
                step.add_error("become: true mancante sul play")
            pvars = b_play.get("vars") or {}
            if pvars.get("preferred_usr") != "prod_user1":
                step.add_error(f"preferred_usr atteso 'prod_user1', trovato '{pvars.get('preferred_usr')}'")
            if pvars.get("preferred_uid") != 0:
                step.add_error(f"preferred_uid atteso 0, trovato '{pvars.get('preferred_uid')}'")

    block_task = None
    for t in b_tasks:
        if isinstance(t, dict) and "block" in t:
            block_task = t
            break

    with GradingStep("block.yml: il blocco crea l'utente con l'UID preferito") as step:
        if block_task is None:
            step.fail("Nessun task con la chiave 'block' trovato")
        else:
            user_tasks = find_tasks(block_task["block"], "ansible.builtin.user")
            found = any(
                references((t["ansible.builtin.user"] or {}).get("name"), "preferred_usr")
                and references((t["ansible.builtin.user"] or {}).get("uid"), "preferred_uid")
                for t in user_tasks
            )
            if not found:
                step.add_error(
                    "Nessun task ansible.builtin.user nel block con name preferred_usr e uid preferred_uid"
                )

    with GradingStep("block.yml: il rescue logga l'errore e ricrea l'utente senza UID fisso") as step:
        if block_task is None:
            step.fail()
        else:
            rescue_tasks = block_task.get("rescue") or []
            has_debug = bool(find_tasks(rescue_tasks, "ansible.builtin.debug"))
            user_tasks = find_tasks(rescue_tasks, "ansible.builtin.user")
            has_user_no_uid = any(
                references((t["ansible.builtin.user"] or {}).get("name"), "preferred_usr")
                and "uid" not in (t["ansible.builtin.user"] or {})
                for t in user_tasks
            )
            if not has_debug:
                step.add_error("Nessun task debug nel rescue")
            if not has_user_no_uid:
                step.add_error("Nessun task user nel rescue che crei l'utente SENZA specificare uid")

    with GradingStep("block.yml: l'always mostra le informazioni utente con `id` (changed_when: false)") as step:
        if block_task is None:
            step.fail()
        else:
            always_tasks = block_task.get("always") or []
            cmd_tasks = find_tasks(always_tasks, "ansible.builtin.command")
            has_id_cmd = any(
                references((t["ansible.builtin.command"] or {}).get("cmd"), "id")
                and t.get("register")
                and t.get("changed_when") is False
                for t in cmd_tasks
            )
            has_debug = bool(find_tasks(always_tasks, "ansible.builtin.debug"))
            if not has_id_cmd:
                step.add_error("Nessun task command `id ...` con register e changed_when: false nell'always")
            if not has_debug:
                step.add_error("Nessun task debug che mostri il risultato nell'always")

    with GradingStep("(live, sola lettura) l'utente prod_user1 esiste su servera/serverb") as step:
        for host in (HOST_PROD_A, HOST_PROD_B):
            if not user_exists(PREFERRED_USER, host=host):
                step.add_error(f"Utente '{PREFERRED_USER}' non trovato su {host}")


if __name__ == "__main__":
    main()
