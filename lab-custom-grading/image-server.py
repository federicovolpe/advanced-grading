#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "image-server" (sezione PDF
18.6 "Install Red Hat Enterprise Linux by Using Image Mode", pag.
472-474), sprovvista di `lab grade` ufficiale. Nessuna materials/solutions
ne' resources.txt: specifica presa dal testo della guida.

Due parti verificabili, come in installing-kickstart:
1. Su servera: ks.cfg pubblicato via Apache con la direttiva
   ostreecontainer e senza sezione %packages (passi 1.2-2.1).
2. Su serverc (raggiungibile solo a installazione completata): /var
   mutabile (testfile, motd), / e /usr immutabili (bootc image mode),
   bootc status mostra l'immagine corretta, e il webserver bootc risponde
   da workstation (passo 7).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

SERVERA = "servera"
SERVERC = "serverc"
_BOOTC_IMAGE = "registry.lab.example.com:5000/student/webserver-bootc"


def main():
    print("🔧 Grading personalizzato per 'image-server'")

    with GradingStep(f"ks.cfg e' pubblicato su {SERVERA} con la direttiva ostreecontainer") as step:
        result = run("cat /var/www/html/ks.cfg", host=SERVERA, sudo=True)
        if result.returncode != 0 or not result.stdout.strip():
            step.fail("/var/www/html/ks.cfg non trovato o vuoto su servera")
        else:
            content = result.stdout
            if f"ostreecontainer --url={_BOOTC_IMAGE}" not in content:
                step.add_error("Direttiva 'ostreecontainer --url=...' mancante o errata")
            if "%packages" in content:
                step.add_error("La sezione %packages doveva essere rimossa (image mode non la usa)")

    reachable = True
    with GradingStep(f"{SERVERC} e' raggiungibile via SSH (installazione image mode completata)") as step:
        result = run("true", host=SERVERC)
        if result.returncode != 0:
            reachable = False
            step.fail(f"{SERVERC} non raggiungibile: l'installazione potrebbe non essere ancora completata")

    if not reachable:
        return

    with GradingStep("bootc status mostra l'immagine bootc corretta come booted") as step:
        result = run("bootc status", host=SERVERC, sudo=True)
        if _BOOTC_IMAGE not in result.stdout:
            step.add_error(f"Immagine attesa '{_BOOTC_IMAGE}' non trovata: {result.stdout.strip()}")

    with GradingStep("/var e' mutabile (testfile e motd persistenti)") as step:
        result = run("cat /var/tmp/testfile", host=SERVERC)
        if result.stdout.strip() != "testing":
            step.add_error(f"Atteso 'testing' in /var/tmp/testfile, trovato: '{result.stdout.strip()}'")
        result = run("cat /etc/motd", host=SERVERC, sudo=True)
        if "This is image mode." not in result.stdout:
            step.add_error("'This is image mode.' non trovato in /etc/motd")

    with GradingStep("Il filesystem radice e' immutabile (read-only, tipico di bootc)") as step:
        # Solo lettura (findmnt), non si tenta una scrittura reale su / per
        # evitare di lasciare file residui in caso l'esercizio non sia
        # ancora completato (root ancora scrivibile).
        result = run("findmnt -no OPTIONS /", host=SERVERC, sudo=True)
        options = result.stdout.strip().split(",")
        if not options or options[0] != "ro":
            step.add_error(
                f"Atteso 'ro' come prima opzione di mount su /, trovato: {result.stdout.strip()}"
            )

    with GradingStep("Il webserver bootc risponde correttamente da workstation") as step:
        result = run("curl -s http://serverc.lab.example.com")
        if result.stdout.strip() != "Hello image mode for RHEL!":
            step.add_error(f"Risposta HTTP inattesa: {result.stdout.strip()[:200]}")


if __name__ == "__main__":
    main()
