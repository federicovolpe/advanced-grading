#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "installing-install" (sezione
PDF 16.2 "Install Red Hat Enterprise Linux Interactively", pag. 391-395),
sprovvista di `lab grade` ufficiale. Nessuna materials/solutions ne'
resources.txt: specifica presa dal testo della guida.

Questo esercizio installa RHEL 10 da zero, in modo interattivo via
console grafica (PXE boot + Anaconda), sulla macchina "serverc" — che non
esiste ancora prima dell'esercizio e diventa raggiungibile via SSH solo a
installazione completata. Il grading e' quindi di sola lettura contro
serverc una volta che risulta raggiungibile; se non lo e' ancora (VM non
installata), i controlli falliscono con timeout gestito da `_common.run`
senza bloccare (vedi `_common.py`).

Stato finale atteso (verificato dopo il primo reboot post-installazione,
passi 13-14):
- hostname = serverc.lab.example.com
- IP statico 172.25.250.12/24 su ens3, gateway 172.25.250.254
- DNS 172.25.250.220 in /etc/resolv.conf
- Partizionamento standard: sda2 xfs /boot, sda3 swap, sda4 xfs /
- L'utente root e' abilitato con password "redhat"
- L'utente student ha privilegi sudo
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, password_matches

HOST = "serverc"


def main():
    print(f"🔧 Grading personalizzato per 'installing-install' (host: {HOST})")

    reachable = True
    with GradingStep(f"{HOST} e' raggiungibile via SSH") as step:
        result = run("true", host=HOST)
        if result.returncode != 0:
            reachable = False
            step.fail(f"{HOST} non raggiungibile: l'installazione potrebbe non essere ancora completata")

    if not reachable:
        return

    with GradingStep("L'hostname e' serverc.lab.example.com") as step:
        result = run("hostname", host=HOST)
        if result.stdout.strip() != "serverc.lab.example.com":
            step.add_error(f"Atteso 'serverc.lab.example.com', trovato: '{result.stdout.strip()}'")

    with GradingStep("L'indirizzo IP statico 172.25.250.12/24 e' configurato su ens3") as step:
        result = run("ip -o -4 addr show ens3", host=HOST)
        if "172.25.250.12/24" not in result.stdout:
            step.add_error(f"IP atteso 172.25.250.12/24 non trovato: {result.stdout.strip()}")

    with GradingStep("Il gateway di default e' 172.25.250.254") as step:
        result = run("ip route show default", host=HOST)
        if "172.25.250.254" not in result.stdout:
            step.add_error(f"Gateway atteso 172.25.250.254 non trovato: {result.stdout.strip()}")

    with GradingStep("Il server DNS 172.25.250.220 e' configurato") as step:
        result = run("cat /etc/resolv.conf", host=HOST)
        if "172.25.250.220" not in result.stdout:
            step.add_error(f"DNS atteso 172.25.250.220 non trovato: {result.stdout.strip()}")

    with GradingStep("Il partizionamento standard e' quello atteso (boot xfs, swap, root xfs)") as step:
        result = run("lsblk -no FSTYPE,MOUNTPOINT /dev/sda2 /dev/sda3 /dev/sda4", host=HOST)
        lines = [l.split() for l in result.stdout.splitlines() if l.strip()]
        if len(lines) < 3:
            step.fail(f"Layout partizioni inatteso: {result.stdout.strip()}")
        else:
            boot, swap, root = lines[0], lines[1], lines[2]
            if boot[0] != "xfs" or (len(boot) > 1 and boot[1] != "/boot"):
                step.add_error(f"sda2 atteso 'xfs /boot', trovato: {boot}")
            if swap[0] != "swap":
                step.add_error(f"sda3 atteso 'swap', trovato: {swap}")
            if root[0] != "xfs" or (len(root) > 1 and root[1] != "/"):
                step.add_error(f"sda4 atteso 'xfs /', trovato: {root}")

    with GradingStep("L'utente root e' abilitato con password 'redhat'") as step:
        if not password_matches("root", "redhat", host=HOST):
            step.fail("La password di root non corrisponde a 'redhat' (o l'account non e' abilitato)")

    with GradingStep("L'utente student ha privilegi sudo") as step:
        result = run("id", host=HOST, sudo=True)
        if "uid=0(root)" not in result.stdout:
            step.add_error(f"'sudo id' non ha restituito uid=0(root): {result.stdout.strip()}")


if __name__ == "__main__":
    main()
