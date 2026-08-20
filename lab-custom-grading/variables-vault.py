#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise AU294 "variables-vault" (sku
au0021l, sez. guida 3.6 "Protecting Sensitive Data with Ansible Vault"),
sprovvista di `lab grade` ufficiale.

Fonte primaria: materials/labs/variables-vault/solutions/ (cert_pass.sol =
"redhat", production_pass.sol = "Pr0dUs3r", development_pass.sol =
"D3vUs3r", ansible.cfg.sol), confermata dal testo guida passo per passo
(passi 2-14): tre segreti vault distinti, uno anonimo (classroom-ca.pem) e
due con vault-id nominato (production-user/development-user per i file
vars/{prod,dev}-password.yml). Inventory: prod = servera/serverb,
dev = serverc/serverd.

Non decifriamo mai i file vault per leggerne il contenuto in chiaro (lo
scopo dell'esercizio e' proprio proteggerlo): verifichiamo solo l'header
$ANSIBLE_VAULT (presenza e vault-id corretto) e l'EFFETTO reale che
l'esecuzione delle playbook produce sui managed host (certificato copiato,
utenti creati con la password nota dalla guida).
"""

import os
import stat
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, user_exists, password_matches

LAB_NAME = "variables-vault"
_ALL_HOSTS = ["servera", "serverb", "serverc", "serverd"]
_PROD_HOSTS = ["servera", "serverb"]
_DEV_HOSTS = ["serverc", "serverd"]
_USER_PASSWORD = "redhat"


def _local_mode(path):
    try:
        return stat.S_IMODE(os.stat(path).st_mode)
    except OSError:
        return None


def main():
    exercise_dir = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    workdir = os.path.expanduser(f"~/{exercise_dir}")
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (dir: {workdir})")

    with GradingStep("classroom-ca.pem e' cifrato con Ansible Vault (nessun vault-id)") as step:
        path = os.path.join(workdir, "classroom-ca.pem")
        try:
            with open(path) as f:
                header = f.readline().strip()
        except OSError:
            step.fail(f"'{path}' non trovato")
            header = ""
        if header and not header.startswith("$ANSIBLE_VAULT"):
            step.fail(f"'{path}' non risulta cifrato (header: {header!r})")

    for fname, expected_id in (
        ("vars/prod-password.yml", "production-user"),
        ("vars/dev-password.yml", "development-user"),
    ):
        with GradingStep(f"{fname} e' cifrato con vault-id '{expected_id}'") as step:
            path = os.path.join(workdir, fname)
            try:
                with open(path) as f:
                    header = f.readline().strip()
            except OSError:
                step.fail(f"'{path}' non trovato")
                header = ""
            if header and not header.startswith("$ANSIBLE_VAULT"):
                step.fail(f"'{path}' non risulta cifrato (header: {header!r})")
            elif header and expected_id not in header:
                step.add_error(f"Header '{header}' non contiene il vault-id '{expected_id}'")

    for fname, expected_content in (
        (".cert_pass", "redhat"),
        (".production_pass", "Pr0dUs3r"),
        (".development_pass", "D3vUs3r"),
    ):
        with GradingStep(f"{fname} contiene la password in chiaro attesa, con permessi 0600") as step:
            path = os.path.join(workdir, fname)
            try:
                with open(path) as f:
                    content = f.read().strip()
            except OSError:
                step.fail(f"'{path}' non trovato")
                content = None
            if content is not None and content != expected_content:
                step.add_error(f"Contenuto = {content!r}, atteso {expected_content!r}")
            mode = _local_mode(path)
            if mode is not None and mode != 0o600:
                step.add_error(f"Permessi = 0{oct(mode)[2:]}, attesi 0600")

    with GradingStep("ansible.cfg imposta vault_identity_list con entrambi i vault-id") as step:
        cfg_path = os.path.join(workdir, "ansible.cfg")
        if not os.path.isfile(cfg_path):
            step.fail(f"'{cfg_path}' non trovato")
        else:
            import configparser
            parser = configparser.ConfigParser()
            try:
                parser.read(cfg_path)
                vault_list = parser.get("defaults", "vault_identity_list", fallback="")
            except configparser.Error:
                vault_list = ""
            for expected in ("production-user@.production_pass", "development-user@.development_pass"):
                if expected not in vault_list:
                    step.add_error(f"vault_identity_list = {vault_list!r}, manca {expected!r}")

    # NON gradiamo l'effetto di copy-certificate.yml (classroom-ca.pem in
    # /etc/pki/ca-trust/source/anchors/): verificato dal vivo che quel file
    # esiste gia', identico, su tutti gli host della classroom PRIMA di
    # qualunque intervento dello studente (dettaglio del base image, non un
    # effetto attribuibile all'esercizio) - darebbe sempre PASS.

    with GradingStep(f"prod_user1 esiste con la password richiesta sui host prod ({', '.join(_PROD_HOSTS)})") as step:
        for host in _PROD_HOSTS:
            if not user_exists("prod_user1", host=host):
                step.add_error(f"Utente 'prod_user1' non trovato su {host}")
            elif not password_matches("prod_user1", _USER_PASSWORD, host=host):
                step.add_error(f"Password di 'prod_user1' su {host} non corrisponde")

    with GradingStep(f"dev_user1 esiste con la password richiesta sui host dev ({', '.join(_DEV_HOSTS)})") as step:
        for host in _DEV_HOSTS:
            if not user_exists("dev_user1", host=host):
                step.add_error(f"Utente 'dev_user1' non trovato su {host}")
            elif not password_matches("dev_user1", _USER_PASSWORD, host=host):
                step.add_error(f"Password di 'dev_user1' su {host} non corrisponde")


if __name__ == "__main__":
    main()
