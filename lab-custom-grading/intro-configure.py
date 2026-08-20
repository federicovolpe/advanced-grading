#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise AU294 "intro-configure" (sez. 1.6
"Configuring Ansible Settings", pag. 52-57), sprovvista di `lab grade`
ufficiale. Specifica presa da materials/labs/intro-configure/solutions/
(ansible-navigator.yml.sol, ansible.cfg.sol) del pacchetto au0018l,
confermata dal testo della guida (passi 2.2-3.4, che mostrano lo stesso
contenuto letterale).

Stato finale atteso in ~/intro-configure/ (dir locale su workstation creata
da `lab start`, lavorata dallo studente dentro il devcontainer VS Code):
- ansible-navigator.yml: execution-environment su podman/immagine EE del
  corso, pull policy "missing" con --tls-verify=false, e (passo 5.2)
  playbook-artifact.enable: false.
- ansible.cfg: [defaults] con inventory=./inventory, remote_user=devops,
  ask_pass=false; [privilege_escalation] con become=true su root via sudo,
  senza prompt password.
"""

import sys
import os
import configparser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep

try:
    import yaml
except ImportError:
    yaml = None

LAB_NAME = "intro-configure"

_EXPECTED_NAVIGATOR = {
    "ansible-navigator": {
        "execution-environment": {
            "container-engine": "podman",
            "enabled": True,
            "image": "utility.lab.example.com:5000/ansible-automation-platform-25/ee-supported-rhel8:latest",
            "pull": {
                "policy": "missing",
                "arguments": ["--tls-verify=false"],
            },
        },
        "playbook-artifact": {"enable": False},
    }
}


def get_workdir(default_name):
    """Directory locale dell'esercizio su workstation, di solito ~/<nome>."""
    override = sys.argv[1] if len(sys.argv) > 1 else None
    return os.path.expanduser(f"~/{override or default_name}")


def main():
    workdir = get_workdir(LAB_NAME)
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (dir: {workdir})")

    navigator_path = os.path.join(workdir, "ansible-navigator.yml")
    with GradingStep("ansible-navigator.yml configura l'execution environment richiesto") as step:
        if yaml is None:
            step.fail("PyYAML non disponibile per validare il file")
        elif not os.path.isfile(navigator_path):
            step.fail(f"File non trovato: {navigator_path}")
        else:
            try:
                with open(navigator_path) as f:
                    content = yaml.safe_load(f)
            except yaml.YAMLError as e:
                content = None
                step.add_error(f"YAML non valido: {e}")
            if content is not None and content != _EXPECTED_NAVIGATOR:
                step.add_error(
                    "Contenuto diverso da quello richiesto dalla guida (sez. 1.6, "
                    f"passi 2.2 e 5.2): atteso {_EXPECTED_NAVIGATOR}, trovato {content}"
                )

    cfg_path = os.path.join(workdir, "ansible.cfg")
    with GradingStep("ansible.cfg imposta defaults e privilege_escalation richiesti") as step:
        if not os.path.isfile(cfg_path):
            step.fail(f"File non trovato: {cfg_path}")
        else:
            parser = configparser.ConfigParser()
            try:
                parser.read(cfg_path)
            except configparser.Error as e:
                step.fail(f"ansible.cfg non parsabile: {e}")
            else:
                expected = {
                    "defaults": {
                        "inventory": "./inventory",
                        "remote_user": "devops",
                        "ask_pass": "false",
                    },
                    "privilege_escalation": {
                        "become": "true",
                        "become_method": "ansible.builtin.sudo",
                        "become_user": "root",
                        "become_ask_pass": "false",
                    },
                }
                for section, keys in expected.items():
                    if not parser.has_section(section):
                        step.add_error(f"Sezione [{section}] mancante")
                        continue
                    for key, value in keys.items():
                        actual = parser.get(section, key, fallback=None)
                        if actual is None:
                            step.add_error(f"[{section}] {key} mancante")
                        elif actual.strip().lower() != value:
                            step.add_error(
                                f"[{section}] {key} atteso '{value}', trovato '{actual}'"
                            )


if __name__ == "__main__":
    main()
