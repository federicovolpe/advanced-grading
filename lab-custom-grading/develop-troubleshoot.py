#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise AU294 "develop-troubleshoot" (sku
au0020l, sez. 2.8 "Troubleshooting Playbooks and Managed Hosts"),
sprovvista di `lab grade` ufficiale. Specifica presa da materials/labs/
develop-troubleshoot/solutions/ (inventory.sol, samba.yml.sol) e dal testo
guida (passi 6-11): l'esercizio fa correggere un refuso nell'inventario
("serverb.lab.exammple.com" -> "serverb.lab.example.com" nel gruppo
nfs_servers) e un bug di indentazione YAML in samba.yml (che nello starter
impedisce persino il parsing del file), poi far girare samba.yml e
nfs.yml (gia' corretto di suo, ma irraggiungibile finche' l'inventario e'
sbagliato) e creare un nuovo playbook ping-serverb.yml.

Grada l'EFFETTO reale su servera/serverb, non il testo YAML: e' il modo
piu' affidabile di sapere che i playbook sono girati con successo dopo il
fix, esattamente come la guida stessa verifica via PLAY RECAP.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, package_installed, service_is_active, service_is_enabled

WORKDIR = os.path.expanduser(f"~/{sys.argv[1] if len(sys.argv) > 1 else 'develop-troubleshoot'}")


def _run_playbook(name):
    """Esegue un playbook DENTRO WORKDIR (cd), cosi' viene letto l'ansible.cfg
    locale (remote_user=devops) esattamente come farebbe lo studente dal
    terminale integrato di VS Code."""
    return run(f"cd {WORKDIR} && ansible-playbook -i inventory {name}")


def main():
    print(f"🔧 Grading personalizzato per 'develop-troubleshoot' (dir: {WORKDIR})")

    with GradingStep("Il refuso nell'inventario e' stato corretto (passo 10)") as step:
        inv_path = os.path.join(WORKDIR, "inventory")
        if not os.path.exists(inv_path):
            step.fail(f"'{inv_path}' non trovato")
        else:
            content = open(inv_path).read()
            if "exammple" in content:
                step.add_error("'serverb.lab.exammple.com' e' ancora presente nell'inventario")
            if "serverb.lab.example.com" not in content:
                step.add_error("'serverb.lab.example.com' non trovato nel gruppo nfs_servers")

    with GradingStep("ping-serverb.yml esiste ed e' stato eseguito con successo (passo 8)") as step:
        playbook = os.path.join(WORKDIR, "ping-serverb.yml")
        if not os.path.exists(playbook):
            step.fail("'ping-serverb.yml' non trovato")
        else:
            result = _run_playbook("ping-serverb.yml")
            if result.returncode != 0:
                step.add_error(f"L'esecuzione di ping-serverb.yml e' fallita: {result.stdout[-400:]}")

    # samba.yml corretto (passi 1-5): pacchetti, servizio, config, firewall su servera.
    for pkg in ("samba", "firewalld"):
        with GradingStep(f"{pkg} e' installato su servera") as step:
            if not package_installed(pkg, host="servera"):
                step.fail(f"Pacchetto '{pkg}' non installato su servera")

    with GradingStep("smb e' avviato e abilitato su servera") as step:
        if not service_is_active("smb", host="servera"):
            step.add_error("Servizio smb non attivo su servera")
        if not service_is_enabled("smb", host="servera"):
            step.add_error("Servizio smb non abilitato al boot su servera")

    with GradingStep("Il firewall di servera permette il servizio samba") as step:
        result = run("firewall-cmd --query-service=samba", host="servera", sudo=True)
        if result.returncode != 0:
            step.fail("Servizio 'samba' non permesso nel firewall di servera")

    with GradingStep("/etc/samba/smb.conf su servera e' stato distribuito dal template") as step:
        # Sez. 2.8, samba.j2 -> samba.conf.j2: verifica solo un marker stabile del
        # template (workgroup KAMANSI), non l'intero file (il commento in cima
        # include random_var, un dettaglio di debug non specificato univocamente).
        result = run("cat /etc/samba/smb.conf", host="servera", sudo=True)
        if result.returncode != 0 or "workgroup = KAMANSI" not in result.stdout:
            step.fail("/etc/samba/smb.conf mancante o non generato dal template atteso")

    # nfs.yml (gia' corretto di suo): l'unico modo per farlo girare con successo
    # e' aver corretto l'inventario, quindi la sua riuscita e' anche una riprova
    # indiretta del fix del passo 10.
    with GradingStep("nfs.yml e' stato eseguito con successo su serverb") as step:
        playbook = os.path.join(WORKDIR, "nfs.yml")
        if not os.path.exists(playbook):
            step.fail("'nfs.yml' non trovato")
        else:
            result = _run_playbook("nfs.yml")
            if result.returncode != 0:
                step.add_error(f"L'esecuzione di nfs.yml e' fallita: {result.stdout[-400:]}")

    with GradingStep("nfs-server e' avviato e abilitato su serverb") as step:
        if not service_is_active("nfs-server", host="serverb"):
            step.add_error("Servizio nfs-server non attivo su serverb")
        if not service_is_enabled("nfs-server", host="serverb"):
            step.add_error("Servizio nfs-server non abilitato al boot su serverb")

    with GradingStep("/exports e' esportata correttamente su serverb") as step:
        result = run("cat /etc/exports", host="serverb", sudo=True)
        if result.returncode != 0 or "/exports" not in result.stdout:
            step.fail("/etc/exports non contiene la riga di export attesa")


if __name__ == "__main__":
    main()
