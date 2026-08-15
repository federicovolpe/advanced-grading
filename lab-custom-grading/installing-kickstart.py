#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "installing-kickstart"
(sezione PDF 16.4 "Automate Red Hat Enterprise Linux Installation with
Kickstart", pag. 407-408), sprovvista di `lab grade` ufficiale. Nessuna
materials/solutions ne' resources.txt: specifica presa dal testo della
guida.

Due parti verificabili:
1. Su servera: il file kickstart.cfg (passo 2.6) e' pubblicato via Apache
   in /var/www/html (passo 4.1) con le direttive chiave richieste.
2. Su serverc (raggiungibile solo a installazione Kickstart completata,
   come in installing-install): hostname transitorio "localhost", rete via
   DHCP, autopart LVM, e prova che lo script %post e' girato (voce
   "Kickstarted on" in /etc/issue).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

SERVERA = "servera"
SERVERC = "serverc"
_KEY_DIRECTIVES = [
    'url --url="http://content.example.com/rhel10.0/x86_64/dvd/"',
    "%packages",
    "@^minimal-environment",
    "@guest-agents",
    "vim-enhanced",
    "autopart",
    "rootpw --lock",
    'user --groups=wheel --name=student --password=student --plaintext --gecos="student"',
]


def main():
    print("🔧 Grading personalizzato per 'installing-kickstart'")

    with GradingStep(f"Il kickstart.cfg e' pubblicato su {SERVERA} via Apache") as step:
        result = run("cat /var/www/html/kickstart.cfg", host=SERVERA, sudo=True)
        if result.returncode != 0 or not result.stdout.strip():
            step.fail("/var/www/html/kickstart.cfg non trovato o vuoto su servera")
        else:
            content = result.stdout
            for directive in _KEY_DIRECTIVES:
                if directive not in content:
                    step.add_error(f"Direttiva mancante nel kickstart.cfg pubblicato: '{directive}'")

    with GradingStep("Il kickstart.cfg e' raggiungibile via HTTP da workstation") as step:
        result = run("curl -s http://servera.lab.example.com/kickstart.cfg")
        if "%packages" not in result.stdout:
            step.add_error("Il file non e' scaricabile via HTTP o ha contenuto inatteso")

    reachable = True
    with GradingStep(f"{SERVERC} e' raggiungibile via SSH (installazione Kickstart completata)") as step:
        result = run("true", host=SERVERC)
        if result.returncode != 0:
            reachable = False
            step.fail(f"{SERVERC} non raggiungibile: l'installazione potrebbe non essere ancora completata")

    if not reachable:
        return

    with GradingStep("L'hostname transitorio e' 'localhost' (nessun hostname statico dal Kickstart)") as step:
        result = run("hostnamectl --transient", host=SERVERC)
        if result.stdout.strip() != "localhost":
            step.add_error(f"Atteso 'localhost', trovato: '{result.stdout.strip()}'")

    with GradingStep("La rete su ens3 e' configurata via DHCP") as step:
        result = run("nmcli -g ipv4.method con show ens3", host=SERVERC)
        if result.stdout.strip() != "auto":
            step.add_error(f"Atteso ipv4.method 'auto', trovato: '{result.stdout.strip()}'")

    with GradingStep("Il partizionamento usa LVM (autopart)") as step:
        result = run("lsblk -no TYPE /dev/sda3", host=SERVERC, sudo=True)
        if "part" not in result.stdout:
            step.add_error(f"sda3 non e' una partizione come atteso: {result.stdout.strip()}")
        result = run("lvs --noheadings -o lv_name", host=SERVERC, sudo=True)
        if "root" not in result.stdout or "swap" not in result.stdout:
            step.add_error(f"LV 'root'/'swap' non trovati: {result.stdout.strip()}")

    with GradingStep("Lo script %post e' stato eseguito (voce in /etc/issue)") as step:
        result = run("grep -i Kickstarted /etc/issue", host=SERVERC, sudo=True)
        if result.returncode != 0:
            step.add_error("Nessuna voce 'Kickstarted on ...' trovata in /etc/issue")


if __name__ == "__main__":
    main()
