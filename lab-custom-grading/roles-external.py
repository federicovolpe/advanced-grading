#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise AU294 "roles-external" (sku au0025l,
sez. guida 7.6 "Deploying Roles from External Content Sources"), sprovvista
di `lab grade` ufficiale.

Fonte primaria: materials/labs/roles-external/solutions/ (roles/
requirements.yml.sol, use-bash_env-role.yml.sol) e il repo Git di partenza
"bash_env.tar" (role Ansible "student.bash_env" ospitato su
serverd.lab.example.com:infra/bash_env), confermata dal testo guida.

Lo studente installa il ruolo "student.bash_env" da un repository Git esterno
(requirements.yml + ansible-galaxy role install) e lo applica a servera
(gruppo "webservers") con un playbook che: rimuove l'utente student2 (se
presente), include il ruolo (scrive .bashrc/.bash_profile/.vimrc in
/etc/skel/, letto da vars/main.yml del ruolo stesso — "Don't change!"), poi
ricrea student2 (che eredita /etc/skel al momento della creazione). L'effetto
verificabile e' quindi il PS1 personalizzato ereditato da student2 (definito
dal var 'default_prompt' passato dal playbook), non un valore a scelta dello
studente: la guida lo fornisce esplicitamente.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, user_exists

LAB_NAME = "roles-external"
HOST = "servera"
ROLE_NAME = "student.bash_env"
ROLE_SRC = "git@serverd.lab.example.com:infra/bash_env"
_EXPECTED_PROMPT_LITERAL = r"[\u on \h in \W dir]\$"


def _read_remote(path, host, sudo=False):
    result = run(f"cat {path}", host=host, sudo=sudo)
    return result.stdout if result.returncode == 0 else None


def main():
    exercise_dir = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    workdir = os.path.expanduser(f"~/{exercise_dir}")
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (dir: {workdir}, host: {HOST})")

    with GradingStep(f"roles/requirements.yml richiede {ROLE_NAME} dal repo Git corretto") as step:
        req_path = os.path.join(workdir, "roles", "requirements.yml")
        if not os.path.isfile(req_path):
            step.fail(f"'{req_path}' non trovato")
        else:
            import yaml
            try:
                with open(req_path) as f:
                    entries = yaml.safe_load(f) or []
            except (OSError, yaml.YAMLError):
                entries = []
            entry = next(
                (e for e in entries if isinstance(e, dict) and e.get("name") == ROLE_NAME),
                None,
            )
            if entry is None:
                step.add_error(f"Nessuna voce con name: {ROLE_NAME}")
            else:
                if entry.get("src") != ROLE_SRC:
                    step.add_error(f"src = {entry.get('src')!r}, atteso {ROLE_SRC!r}")
                if entry.get("scm") != "git":
                    step.add_error(f"scm = {entry.get('scm')!r}, atteso 'git'")

    with GradingStep(f"Ruolo {ROLE_NAME} installato localmente in roles/") as step:
        role_local_dir = os.path.join(workdir, "roles", ROLE_NAME)
        if not os.path.isfile(os.path.join(role_local_dir, "tasks", "main.yml")):
            step.fail(f"'{role_local_dir}/tasks/main.yml' non trovato: ruolo non installato")

    with GradingStep("Il playbook use-bash_env-role.yml include il ruolo per il gruppo webservers") as step:
        playbook_path = os.path.join(workdir, "use-bash_env-role.yml")
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

    with GradingStep(f"L'utente student2 esiste su {HOST} (post_tasks del playbook)") as step:
        if not user_exists("student2", host=HOST):
            step.fail(f"Utente 'student2' non trovato su {HOST}")

    with GradingStep(f"~student2/.bashrc su {HOST} ha il PS1 personalizzato dal ruolo") as step:
        content = _read_remote("~student2/.bashrc", host=HOST, sudo=True)
        if content is None:
            step.fail(f"Impossibile leggere ~student2/.bashrc su {HOST}")
        elif _EXPECTED_PROMPT_LITERAL not in content:
            step.add_error(
                f"Prompt atteso '{_EXPECTED_PROMPT_LITERAL}' non trovato in ~student2/.bashrc"
            )


if __name__ == "__main__":
    main()
