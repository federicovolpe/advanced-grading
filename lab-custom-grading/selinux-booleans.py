#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "selinux-booleans" (sezione
PDF 6.6 "Tune the SELinux Policy by Adjusting Booleans", pag. 169-170),
sprovvista di `lab grade` ufficiale. Nessuna materials/solutions ne'
resources.txt: specifica presa dal testo della guida, su servera (+
verifica HTTP da workstation).

Stato finale atteso:
- /etc/httpd/conf.d/userdir.conf ha "UserDir public_html" attivo (non
  commentato) e "UserDir disabled" commentato.
- ~/public_html/index.html (utente student) esiste col contenuto atteso.
- /home/student ha permessi 711 (passo 4.4-4.5).
- httpd attivo.
- Il boolean httpd_enable_homedirs e' on in modo persistente (setsebool -P,
  passo 8).
- curl http://servera/~student/index.html da workstation restituisce il
  contenuto atteso (prova end-to-end, passo 9).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, service_is_active

HOST = "servera"
_EXPECTED_CONTENT = "This is student content on SERVERA."


def main():
    print(f"🔧 Grading personalizzato per 'selinux-booleans' (host: {HOST})")

    with GradingStep("userdir.conf ha UserDir public_html attivo") as step:
        result = run(
            "grep -E '^\\s*UserDir' /etc/httpd/conf.d/userdir.conf", host=HOST, sudo=True
        )
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        if "UserDir public_html" not in lines:
            step.add_error(f"'UserDir public_html' non attivo, trovato: {lines}")

    with GradingStep("~/public_html/index.html (student) esiste col contenuto atteso") as step:
        result = run("cat /home/student/public_html/index.html", host=HOST, sudo=True)
        if result.stdout.strip() != _EXPECTED_CONTENT:
            step.add_error(f"Atteso '{_EXPECTED_CONTENT}', trovato: '{result.stdout.strip()}'")

    with GradingStep("/home/student ha permessi 711") as step:
        result = run("stat -c %a /home/student", host=HOST, sudo=True)
        if result.stdout.strip() != "711":
            step.add_error(f"Atteso permessi '711', trovato: '{result.stdout.strip()}'")

    with GradingStep("httpd e' attivo") as step:
        if not service_is_active("httpd", host=HOST):
            step.fail("httpd non risulta attivo")

    with GradingStep("Il boolean httpd_enable_homedirs e' on in modo persistente") as step:
        result = run("semanage boolean -l | grep httpd_enable_homedirs", host=HOST, sudo=True)
        if "(on" not in result.stdout or ", on)" not in result.stdout:
            step.add_error(
                f"Atteso '(on , on)' per httpd_enable_homedirs, trovato: {result.stdout.strip()}"
            )

    with GradingStep("curl http://servera/~student/index.html restituisce il contenuto atteso") as step:
        result = run("curl -s http://servera/~student/index.html")
        if result.stdout.strip() != _EXPECTED_CONTENT:
            step.add_error(
                f"Risposta HTTP inattesa: {result.stdout.strip()[:200]}"
            )


if __name__ == "__main__":
    main()
