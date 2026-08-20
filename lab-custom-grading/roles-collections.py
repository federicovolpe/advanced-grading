#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise AU294 "roles-collections" (sku
au0025l, sez. guida 7.8 "Obtaining Roles and Modules from Ansible Content
Collections"), sprovvista di `lab grade` ufficiale.

Fonte primaria: materials/labs/roles-collections/solutions/ (ansible.cfg.sol,
configure_time.yml.sol, group_vars/all/timesync.yml.sol) e il testo guida
(installa la collection redhat.rhel_system_roles da un tarball locale con
`ansible-galaxy collection install -p collections/`, poi usa il ruolo
timesync per configurare chrony su servera col server NTP
classroom.example.com).

Nota: lo stesso ruolo di sistema (timesync) e' riusato in modo piu' esteso
nell'esercizio "system-roles" (Cap. 8, pacchetto au0026l): qui non c'e'
sovrapposizione di file (dir esercizio/host diversi), la duplicazione
didattica e' intenzionale nel curriculum (introduzione vs approfondimento).

Verifica sia la struttura (collection installata localmente, ansible.cfg
punta a collections_path, group_vars col server NTP corretto) sia l'effetto
reale su servera (/etc/chrony.conf, chronyd attivo).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, service_is_active

LAB_NAME = "roles-collections"
HOST = "servera"
COLLECTION_NAME = "redhat.rhel_system_roles"
NTP_SERVER = "classroom.example.com"


def main():
    exercise_dir = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    workdir = os.path.expanduser(f"~/{exercise_dir}")
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (dir: {workdir}, host: {HOST})")

    with GradingStep(f"Collection {COLLECTION_NAME} installata localmente in collections/") as step:
        coll_dir = os.path.join(
            workdir, "collections", "ansible_collections", "redhat", "rhel_system_roles"
        )
        if not os.path.isdir(coll_dir):
            step.fail(f"'{coll_dir}' non trovata: collection non installata")

    with GradingStep("ansible.cfg punta collections_path a ./collections") as step:
        cfg_path = os.path.join(workdir, "ansible.cfg")
        if not os.path.isfile(cfg_path):
            step.fail(f"'{cfg_path}' non trovato")
        else:
            import configparser
            parser = configparser.ConfigParser()
            try:
                parser.read(cfg_path)
                collections_path = parser.get("defaults", "collections_path", fallback="")
            except configparser.Error:
                collections_path = ""
            if "collections" not in collections_path:
                step.add_error(
                    f"collections_path = {collections_path!r}, atteso un percorso che includa './collections'"
                )

    with GradingStep(f"group_vars/all imposta il server NTP {NTP_SERVER} per il ruolo timesync") as step:
        gv_dir = os.path.join(workdir, "group_vars", "all")
        found = False
        if os.path.isdir(gv_dir):
            import yaml
            for fname in os.listdir(gv_dir):
                fpath = os.path.join(gv_dir, fname)
                if not os.path.isfile(fpath):
                    continue
                try:
                    with open(fpath) as f:
                        data = yaml.safe_load(f) or {}
                except (OSError, yaml.YAMLError):
                    continue
                servers = data.get("timesync_ntp_servers") or []
                if any(isinstance(s, dict) and s.get("hostname") == NTP_SERVER for s in servers):
                    found = True
                    if data.get("timesync_ntp_provider") != "chrony":
                        step.add_error(
                            f"timesync_ntp_provider = {data.get('timesync_ntp_provider')!r}, atteso 'chrony'"
                        )
        if not found:
            step.fail(f"Nessun file in group_vars/all/ definisce timesync_ntp_servers con hostname {NTP_SERVER}")

    with GradingStep("Il playbook configure_time.yml include il ruolo timesync per il gruppo webservers") as step:
        playbook_path = os.path.join(workdir, "configure_time.yml")
        if not os.path.isfile(playbook_path):
            step.fail(f"'{playbook_path}' non trovato")
        else:
            import yaml
            try:
                with open(playbook_path) as f:
                    docs = yaml.safe_load(f) or []
                play = docs[0] if isinstance(docs, list) and docs else {}
            except (OSError, yaml.YAMLError):
                play = {}
            if play.get("hosts") != "webservers":
                step.add_error(f"hosts = {play.get('hosts')!r}, atteso 'webservers'")
            tasks = play.get("tasks") or []
            includes_role = any(
                isinstance(t, dict) and
                (t.get("ansible.builtin.include_role") or {}).get("name")
                == f"{COLLECTION_NAME}.timesync"
                for t in tasks
            )
            if not includes_role:
                step.add_error(
                    f"Nessun task 'ansible.builtin.include_role' con name: {COLLECTION_NAME}.timesync"
                )

    with GradingStep(f"chrony su {HOST} e' configurato con il server {NTP_SERVER} e chronyd e' attivo") as step:
        result = run("cat /etc/chrony.conf", host=HOST, sudo=True)
        if result.returncode != 0:
            step.fail(f"Impossibile leggere /etc/chrony.conf su {HOST}")
        elif NTP_SERVER not in result.stdout:
            step.add_error(f"'{NTP_SERVER}' non trovato in /etc/chrony.conf su {HOST}")
        if not service_is_active("chronyd", host=HOST):
            step.add_error(f"Servizio chronyd non attivo su {HOST}")


if __name__ == "__main__":
    main()
