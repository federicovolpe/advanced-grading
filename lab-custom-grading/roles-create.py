#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise AU294 "roles-create" (sku au0025l,
sez. guida 7.4 "Creating Roles"), sprovvista di `lab grade` ufficiale.

Fonte primaria: materials/labs/roles-create/solutions/ (tasks/main.yml.sol,
handlers/main.yml.sol, meta/main.yml.sol, files/index.html.sol,
myvhost.yml.sol), confermata dal testo guida (crea un ruolo "myvhost" che
installa/configura Apache su servera, gruppo inventory "webservers").

Gradiamo sia la STRUTTURA locale del ruolo su workstation (roles/myvhost/...)
sia l'EFFETTO reale del ruolo eseguito su servera (pacchetto/servizio httpd,
regola firewalld, vhost.conf renderizzato dal template, index.html): la
guida stessa (passo finale) chiede di eseguire ansible-navigator run
myvhost.yml e verificare httpd/il contenuto pubblicato, quindi l'effetto e'
la specifica piu' affidabile. Non gradiamo la rimozione di
roles/myvhost/{defaults,vars,tests}/ (passo 2.2, "delete those directories"):
e' un dettaglio di pulizia dello scaffolding di ansible-galaxy, non
funzionale al risultato dell'esercizio.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, package_installed, service_is_active, service_is_enabled

LAB_NAME = "roles-create"
HOST = "servera"
ROLE_NAME = "myvhost"


def _read_remote(path, host, sudo=False):
    result = run(f"cat {path}", host=host, sudo=sudo)
    return result.stdout if result.returncode == 0 else None


def _remote_hostname_fqdn(host):
    result = run("hostname -f", host=host)
    return result.stdout.strip() if result.returncode == 0 else None


def main():
    exercise_dir = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    workdir = os.path.expanduser(f"~/{exercise_dir}")
    role_dir = os.path.join(workdir, "roles", ROLE_NAME)
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (dir: {workdir}, host: {HOST})")

    with GradingStep(f"Struttura del ruolo roles/{ROLE_NAME}/ presente sulla workstation") as step:
        for rel in ("tasks/main.yml", "handlers/main.yml", "meta/main.yml",
                    "files/index.html", "templates/vhost.conf.j2"):
            if not os.path.isfile(os.path.join(role_dir, rel)):
                step.add_error(f"Manca roles/{ROLE_NAME}/{rel}")

    with GradingStep("Il playbook myvhost.yml include il ruolo myvhost per il gruppo webservers") as step:
        playbook_path = os.path.join(workdir, "myvhost.yml")
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
                (t.get("ansible.builtin.include_role") or {}).get("name") == ROLE_NAME
                for t in tasks
            )
            if not includes_role:
                step.add_error(f"Nessun task 'ansible.builtin.include_role' con name: {ROLE_NAME}")

    fqdn = _remote_hostname_fqdn(HOST)

    with GradingStep(f"httpd installato, attivo e abilitato su {HOST} (effetto del ruolo)") as step:
        if not package_installed("httpd", host=HOST):
            step.fail(f"Pacchetto httpd non installato su {HOST}")
        else:
            if not service_is_active("httpd", host=HOST):
                step.add_error(f"Servizio httpd non attivo su {HOST}")
            if not service_is_enabled("httpd", host=HOST):
                step.add_error(f"Servizio httpd non abilitato al boot su {HOST}")

    with GradingStep(f"Servizio http abilitato permanentemente nel firewall di {HOST}") as step:
        result = run("firewall-cmd --permanent --query-service=http", host=HOST, sudo=True)
        if result.returncode != 0 or "yes" not in result.stdout.lower():
            step.fail(f"Servizio firewalld 'http' non permanente su {HOST}")

    with GradingStep(f"vhost.conf renderizzato correttamente in /etc/httpd/conf.d su {HOST}") as step:
        content = _read_remote("/etc/httpd/conf.d/vhost.conf", host=HOST, sudo=True)
        if content is None:
            step.fail(f"/etc/httpd/conf.d/vhost.conf non trovato su {HOST}")
        elif fqdn is None:
            step.fail(f"Impossibile determinare l'fqdn di {HOST} per confrontare il template")
        else:
            for expected in (
                f"ServerAdmin webmaster@{fqdn}",
                f"ServerName {fqdn}",
                f"DocumentRoot /var/www/vhosts/",
            ):
                if expected not in content:
                    step.add_error(f"Riga attesa '{expected}' non trovata in vhost.conf")

    with GradingStep(f"Contenuto index.html pubblicato correttamente su {HOST}") as step:
        local_index = os.path.join(role_dir, "files", "index.html")
        try:
            with open(local_index) as f:
                expected_content = f.read().strip()
        except OSError:
            step.fail(f"'{local_index}' non trovato: impossibile confrontare il contenuto")
            expected_content = None

        if expected_content is not None:
            result = run("hostname -s", host=HOST)
            hostname = result.stdout.strip() if result.returncode == 0 else None
            if not hostname:
                step.fail(f"Impossibile determinare l'hostname di {HOST}")
            else:
                remote_index = _read_remote(
                    f"/var/www/vhosts/{hostname}/index.html", host=HOST, sudo=True
                )
                if remote_index is None:
                    step.add_error(f"/var/www/vhosts/{hostname}/index.html non trovato su {HOST}")
                elif remote_index.strip() != expected_content:
                    step.add_error("Contenuto di index.html diverso da roles/myvhost/files/index.html")


if __name__ == "__main__":
    main()
