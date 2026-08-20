#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise AU294 "scale-files" (Cap. 6.2
"Including and Importing Files", pag. 342-348), sprovvista di `lab grade`
ufficiale (scale-files.py nel pacchetto au0024l non definisce grade()).

Specifica presa da materials/labs/scale-files/solutions/web-server-config.yml.sol
(identica al testo guidato, passi 4-7 e "Verify your work" del passo 9):

    - name: Configure web server
      hosts: servera.lab.example.com
      tasks:
        - name: Include the environment tasks file and set the variables
          ansible.builtin.include_tasks: tasks/environment.yml
          vars: {package: httpd, service: httpd}
        - name: Import the firewall tasks file and set the variables
          ansible.builtin.import_tasks: tasks/firewall.yml
          vars: {firewall_pkg: firewalld, firewall_svc: firewalld, rule: [http, https]}
        - name: Import the placeholder tasks file and set the variable
          ansible.builtin.import_tasks: tasks/placeholder.yml
          vars: {file: /var/www/html/index.html}
    - name: Import test play file and set the variable
      ansible.builtin.import_playbook: plays/test.yml
      vars: {url: 'http://servera.lab.example.com'}

Il punto centrale della lezione e' la differenza fra include_tasks (dinamico,
risolto a runtime) e import_tasks (statico, risolto al parse time): per
questo il tipo esatto di direttiva usato per ciascun task viene gradato,
non solo il file incluso/importato.

Oltre alla STRUTTURA del playbook, viene verificato anche l'EFFETTO reale
dell'esecuzione su servera.lab.example.com (il vero obiettivo dell'esercizio
e' eseguire il playbook, non solo scriverlo): pacchetto/servizio httpd,
regole firewalld http/https, e il file placeholder con il contenuto atteso.
Tutti controlli in sola lettura via SSH, nessuna modifica dallo script.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, package_installed, service_is_active, service_is_enabled, file_exists

import yaml

LAB_NAME = "scale-files"
HOST = "servera"
HOST_FQDN = "servera.lab.example.com"
WORKDIR_DEFAULT = os.path.expanduser(f"~/{LAB_NAME}")


def load_playbook(path):
    """Ritorna la lista di play del playbook (yaml.safe_load), o None se il
    file non esiste o non e' YAML valido/una lista."""
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except (OSError, yaml.YAMLError):
        return None
    return data if isinstance(data, list) else None


def find_task_by_target(tasks, module_key, target):
    """Ritorna il primo task che usa esattamente quella direttiva
    (es. 'ansible.builtin.import_tasks') puntando a quel file, o None."""
    for task in tasks or []:
        if isinstance(task, dict) and task.get(module_key) == target:
            return task
    return None


def main():
    project_dir = sys.argv[1] if len(sys.argv) > 1 else WORKDIR_DEFAULT
    if not os.path.isabs(project_dir):
        project_dir = os.path.expanduser(f"~/{project_dir}")
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (directory: {project_dir})")

    playbook_path = os.path.join(project_dir, "web-server-config.yml")
    plays = load_playbook(playbook_path)

    with GradingStep("web-server-config.yml esiste ed e' YAML valido con almeno 2 play") as step:
        if plays is None:
            step.fail(f"'{playbook_path}' non trovato o YAML non valido: esegui 'lab start {LAB_NAME}'")
        elif len(plays) < 2:
            step.fail(f"Attese almeno 2 play (configurazione + test), trovate {len(plays)}")

    play1 = plays[0] if plays and len(plays) >= 1 and isinstance(plays[0], dict) else None
    play2 = plays[1] if plays and len(plays) >= 2 and isinstance(plays[1], dict) else None
    tasks = play1.get("tasks") if play1 else None

    with GradingStep("Il primo play si chiama 'Configure web server' e targetizza servera.lab.example.com") as step:
        if not play1:
            step.fail("Primo play non trovato")
        else:
            if play1.get("name") != "Configure web server":
                step.add_error(f"Nome play atteso 'Configure web server', trovato {play1.get('name')!r}")
            if play1.get("hosts") != HOST_FQDN:
                step.add_error(f"Atteso hosts: {HOST_FQDN}, trovato {play1.get('hosts')!r}")

    with GradingStep("Task 1: ansible.builtin.include_tasks di tasks/environment.yml (package/service=httpd)") as step:
        task = find_task_by_target(tasks, "ansible.builtin.include_tasks", "tasks/environment.yml")
        if not task:
            # errore comune: usare import_tasks invece di include_tasks per questo file
            if find_task_by_target(tasks, "ansible.builtin.import_tasks", "tasks/environment.yml"):
                step.fail("tasks/environment.yml e' importato con import_tasks: deve essere include_tasks (e' l'oggetto della lezione)")
            else:
                step.fail("Nessun task 'ansible.builtin.include_tasks: tasks/environment.yml' trovato")
        else:
            v = task.get("vars") or {}
            if v.get("package") != "httpd":
                step.add_error(f"Var 'package' attesa 'httpd', trovata {v.get('package')!r}")
            if v.get("service") != "httpd":
                step.add_error(f"Var 'service' attesa 'httpd', trovata {v.get('service')!r}")

    with GradingStep("Task 2: ansible.builtin.import_tasks di tasks/firewall.yml (firewalld, regole http/https)") as step:
        task = find_task_by_target(tasks, "ansible.builtin.import_tasks", "tasks/firewall.yml")
        if not task:
            if find_task_by_target(tasks, "ansible.builtin.include_tasks", "tasks/firewall.yml"):
                step.fail("tasks/firewall.yml e' incluso con include_tasks: deve essere import_tasks")
            else:
                step.fail("Nessun task 'ansible.builtin.import_tasks: tasks/firewall.yml' trovato")
        else:
            v = task.get("vars") or {}
            if v.get("firewall_pkg") != "firewalld":
                step.add_error(f"Var 'firewall_pkg' attesa 'firewalld', trovata {v.get('firewall_pkg')!r}")
            if v.get("firewall_svc") != "firewalld":
                step.add_error(f"Var 'firewall_svc' attesa 'firewalld', trovata {v.get('firewall_svc')!r}")
            rule = v.get("rule")
            if not isinstance(rule, list) or set(rule) != {"http", "https"}:
                step.add_error(f"Var 'rule' attesa ['http', 'https'], trovata {rule!r}")

    with GradingStep("Task 3: ansible.builtin.import_tasks di tasks/placeholder.yml (file=/var/www/html/index.html)") as step:
        task = find_task_by_target(tasks, "ansible.builtin.import_tasks", "tasks/placeholder.yml")
        if not task:
            if find_task_by_target(tasks, "ansible.builtin.include_tasks", "tasks/placeholder.yml"):
                step.fail("tasks/placeholder.yml e' incluso con include_tasks: deve essere import_tasks")
            else:
                step.fail("Nessun task 'ansible.builtin.import_tasks: tasks/placeholder.yml' trovato")
        else:
            v = task.get("vars") or {}
            if v.get("file") != "/var/www/html/index.html":
                step.add_error(f"Var 'file' attesa '/var/www/html/index.html', trovata {v.get('file')!r}")

    with GradingStep("Secondo play: ansible.builtin.import_playbook di plays/test.yml (url del web server)") as step:
        if not play2:
            step.fail("Secondo play non trovato")
        elif play2.get("ansible.builtin.import_playbook") != "plays/test.yml":
            step.add_error(f"Atteso 'ansible.builtin.import_playbook: plays/test.yml', trovato {play2.get('ansible.builtin.import_playbook')!r}")
        else:
            v = play2.get("vars") or {}
            url = (v.get("url") or "").rstrip("/")
            if url != f"http://{HOST_FQDN}":
                step.add_error(f"Var 'url' attesa 'http://{HOST_FQDN}', trovata {v.get('url')!r}")

    # --- Effetto reale sull'host servera: l'obiettivo dell'esercizio e'
    # eseguire il playbook, non solo scriverlo. Controlli in sola lettura
    # via SSH (nessuna modifica dallo script).
    with GradingStep(f"Il pacchetto httpd e' installato e il servizio e' attivo/abilitato su {HOST_FQDN}") as step:
        if not package_installed("httpd", host=HOST):
            step.fail("Pacchetto 'httpd' non installato: esegui il playbook")
        else:
            if not service_is_active("httpd", host=HOST):
                step.add_error("Servizio httpd non attivo")
            if not service_is_enabled("httpd", host=HOST):
                step.add_error("Servizio httpd non abilitato al boot")

    with GradingStep(f"firewalld consente http e https su {HOST_FQDN}") as step:
        result = run("firewall-cmd --list-services", host=HOST, sudo=True)
        if result.returncode != 0:
            step.fail("Impossibile interrogare firewalld (firewall-cmd --list-services)")
        else:
            services = result.stdout.split()
            for svc in ("http", "https"):
                if svc not in services:
                    step.add_error(f"Servizio '{svc}' non abilitato in firewalld")

    with GradingStep(f"Il file placeholder /var/www/html/index.html e' stato creato con il contenuto atteso su {HOST_FQDN}") as step:
        if not file_exists("/var/www/html/index.html", host=HOST):
            step.fail("File non trovato: esegui il playbook")
        else:
            result = run("cat /var/www/html/index.html", host=HOST)
            expected = f"{HOST_FQDN} has been customized using Ansible."
            if expected not in result.stdout:
                step.add_error(f"Contenuto atteso '{expected}', trovato: {result.stdout.strip()!r}")


if __name__ == "__main__":
    main()
