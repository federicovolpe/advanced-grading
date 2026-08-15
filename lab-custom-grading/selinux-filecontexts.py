#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "selinux-filecontexts"
(sezione PDF 6.4 "Control SELinux File Contexts", pag. 164-166), sprovvista
di `lab grade` ufficiale. Nessuna materials/solutions ne' resources.txt:
specifica presa dal testo della guida, su servera (+ verifica HTTP da
workstation).

Stato finale atteso:
- /custom/index.html esiste con contenuto "This is SERVERA."
- httpd.conf usa /custom come DocumentRoot.
- httpd attivo.
- Il contesto SELinux di /custom e' httpd_sys_content_t (passi 5.2-5.3).
- curl http://servera/index.html da workstation restituisce "This is
  SERVERA." (prova end-to-end che il contesto SELinux e' corretto:
  altrimenti httpd risponderebbe 403, passo 6).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, service_is_active

HOST = "servera"


def main():
    print(f"🔧 Grading personalizzato per 'selinux-filecontexts' (host: {HOST})")

    with GradingStep("/custom/index.html esiste con il contenuto atteso") as step:
        result = run("cat /custom/index.html", host=HOST, sudo=True)
        if result.stdout.strip() != "This is SERVERA.":
            step.add_error(
                f"Atteso 'This is SERVERA.', trovato: '{result.stdout.strip()}'"
            )

    with GradingStep("httpd.conf usa /custom come DocumentRoot") as step:
        result = run(
            "grep -E '^DocumentRoot' /etc/httpd/conf/httpd.conf", host=HOST, sudo=True
        )
        if '"/custom"' not in result.stdout:
            step.add_error(f"DocumentRoot atteso '/custom', trovato: {result.stdout.strip()}")

    with GradingStep("httpd e' attivo") as step:
        if not service_is_active("httpd", host=HOST):
            step.fail("httpd non risulta attivo")

    with GradingStep("Il contesto SELinux di /custom e' httpd_sys_content_t") as step:
        result = run("ls -dZ /custom", host=HOST, sudo=True)
        if "httpd_sys_content_t" not in result.stdout:
            step.add_error(f"Contesto atteso 'httpd_sys_content_t', trovato: {result.stdout.strip()}")

    with GradingStep("curl http://servera/index.html restituisce il contenuto atteso (no 403 SELinux)") as step:
        result = run("curl -s http://servera/index.html")
        if result.stdout.strip() != "This is SERVERA.":
            step.add_error(
                f"Risposta HTTP inattesa (atteso 'This is SERVERA.'): {result.stdout.strip()[:200]}"
            )


if __name__ == "__main__":
    main()
