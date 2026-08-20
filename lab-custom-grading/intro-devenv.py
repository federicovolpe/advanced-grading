#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise AU294 "intro-devenv" (sez. 1.4
"Configuring Your Ansible Development Environment", pag. 34-40), sprovvista
di `lab grade` ufficiale. Nessuna materials/solutions per questo esercizio:
i file di partenza (au0018l/materials/git_repos/intro-devenv/) sono quelli
pushati su Gitea da `lab start` (ansible.cfg, ansible-navigator.yml,
hello-world.yml, inventory), il repository Git clonato dallo studente.

Stato persistente e oggettivamente verificabile, sul repo clonato in
~/git-repos/intro-devenv/:

- passo 4.4-4.5: il file .devcontainer/podman/devcontainer.json (generato
  dal wizard "Devcontainer" dell'estensione Ansible) viene modificato
  cambiando la chiave "image" e aggiungendo l'argomento --tls-verify=false
  a runArgs (contenuto letterale mostrato in guida, pag. 36-37).
- passo 5.2: il playbook hello-world.yml viene modificato cambiando il
  parametro msg da "Hello" a "Hello World" (contenuto esatto mostrato nella
  guida).
- passo 6: le modifiche vengono committate e pushate al repository Gitea
  remoto (http://utility.lab.example.com:3000/student/intro-devenv.git).

Il resto dell'esercizio (impostazioni Ansible extension / Dev Containers in
VS Code, passi 2-3) NON viene gradato deliberatamente: verificato che
`start()` (au294_common/playbooks/reset-vscode-config.yml) scrive gia' PRIMA
che lo studente tocchi nulla, nelle User Settings globali
(~/.config/Code/User/settings.json), esattamente le chiavi che la guida
chiede di impostare via UI (ansible.executionEnvironment.enabled/
containerEngine/pull.arguments, dev.containers.dockerPath/dockerComposePath):
lo stato finale di queste chiavi e' quindi identico indipendentemente da
cosa fa lo studente, non e' un discriminante valido. L'unica eccezione
sarebbe ansible.validation.lint.enabled (passo 2.2, scope Workspace): dal
package.json dell'estensione (redhat.ansible) il default e' gia' True, quindi
anche questo checkbox risulta gia' spuntato di default e un eventuale
override in .vscode/settings.json del workspace clonato non e' un segnale
affidabile (potrebbe non essere scritto anche se lo studente esegue
correttamente i passi in UI). Per lo stesso motivo non gradiamo il valore di
Execution Environment: Image nello scope Workspace (passo 2.5): non possiamo
verificare con certezza il comportamento di serializzazione di VS Code in
questo scenario senza guidare interattivamente l'IDE.
"""

import sys
import os
import json
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep

try:
    import yaml
except ImportError:
    yaml = None

LAB_NAME = "intro-devenv"
_EXPECTED_PLAYBOOK = [
    {
        "name": "Hello World",
        "hosts": "servera",
        "tasks": [
            {
                "name": "Print Hello World",
                "ansible.builtin.debug": {"msg": "Hello World"},
            }
        ],
    }
]
_EXPECTED_EE_IMAGE = (
    "utility.lab.example.com:5000/ansible-automation-platform-25/"
    "ansible-dev-tools-rhel8:latest"
)


def get_repo_dir(default_name):
    override = sys.argv[1] if len(sys.argv) > 1 else None
    return os.path.expanduser(f"~/git-repos/{override or default_name}")


def git(repo_dir, *args):
    return subprocess.run(
        ["git", "-C", repo_dir, *args], capture_output=True, text=True
    )


def main():
    repo_dir = get_repo_dir(LAB_NAME)
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (repo: {repo_dir})")

    devcontainer_path = os.path.join(
        repo_dir, ".devcontainer", "podman", "devcontainer.json"
    )
    with GradingStep(
        "Il devcontainer usa l'immagine ansible-dev-tools-rhel8:latest con --tls-verify=false"
    ) as step:
        if not os.path.isfile(devcontainer_path):
            step.fail(f"File non trovato: {devcontainer_path}")
        else:
            try:
                with open(devcontainer_path) as f:
                    devcontainer = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                devcontainer = None
                step.fail(f"devcontainer.json non e' JSON valido: {e}")
            if devcontainer is not None:
                image = devcontainer.get("image")
                if image != _EXPECTED_EE_IMAGE:
                    step.add_error(
                        f"Chiave 'image' attesa '{_EXPECTED_EE_IMAGE}', trovata '{image}'"
                    )
                run_args = devcontainer.get("runArgs") or []
                if "--tls-verify=false" not in run_args:
                    step.add_error(
                        "runArgs non contiene l'argomento '--tls-verify=false'"
                    )

    playbook_path = os.path.join(repo_dir, "hello-world.yml")
    with GradingStep("hello-world.yml stampa 'Hello World' su servera") as step:
        if yaml is None:
            step.fail("PyYAML non disponibile per validare il file")
        elif not os.path.isfile(playbook_path):
            step.fail(f"File non trovato: {playbook_path}")
        else:
            try:
                with open(playbook_path) as f:
                    content = yaml.safe_load(f)
            except yaml.YAMLError as e:
                content = None
                step.add_error(f"YAML non valido: {e}")
            if content is not None and content != _EXPECTED_PLAYBOOK:
                step.add_error(
                    "Contenuto diverso da quello richiesto dalla guida (sez. 1.4, "
                    f"passo 5.2): atteso {_EXPECTED_PLAYBOOK}, trovato {content}"
                )

    with GradingStep("hello-world.yml e' stato committato (nessuna modifica pendente)") as step:
        if not os.path.isdir(os.path.join(repo_dir, ".git")):
            step.fail(f"'{repo_dir}' non e' un repository Git clonato")
        else:
            # Limitato al solo hello-world.yml (non all'intero working tree):
            # la guida (passo 6.2) chiede di stage/commit solo di questo file,
            # la directory .devcontainer/ generata dal wizard resta untracked
            # di proposito e non deve far fallire il check.
            result = git(repo_dir, "status", "--porcelain", "--", "hello-world.yml")
            if result.returncode != 0:
                step.fail("Impossibile leggere lo stato del repository")
            elif result.stdout.strip():
                step.add_error(
                    "hello-world.yml ha modifiche non committate: "
                    + result.stdout.strip()
                )

    with GradingStep("Le modifiche sono state pushate al repository Gitea remoto") as step:
        if not os.path.isdir(os.path.join(repo_dir, ".git")):
            step.fail(f"'{repo_dir}' non e' un repository Git clonato")
        else:
            local_head = git(repo_dir, "rev-parse", "HEAD")
            remote_head = git(repo_dir, "ls-remote", "origin", "HEAD")
            if local_head.returncode != 0:
                step.fail("Impossibile leggere l'HEAD locale")
            elif remote_head.returncode != 0:
                step.fail("Impossibile contattare il repository remoto (origin)")
            else:
                local_sha = local_head.stdout.strip()
                remote_sha = remote_head.stdout.split()[0] if remote_head.stdout.split() else ""
                if local_sha != remote_sha:
                    step.add_error(
                        "HEAD locale non corrisponde al remoto: il push non e' "
                        "stato completato (o ci sono commit locali non pushati)"
                    )


if __name__ == "__main__":
    main()
