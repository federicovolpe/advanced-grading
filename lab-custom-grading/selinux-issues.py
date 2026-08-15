#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "selinux-issues" (sezione
PDF 6.8 "Investigate and Resolve SELinux Issues", pag. 176-178), sprovvista
di `lab grade` ufficiale. Nessuna materials/solutions ne' resources.txt:
specifica presa dal testo della guida, su servera (+ verifica HTTP da
workstation).

L'esercizio parte da httpd gia' configurato a servire /custom (con
contesto SELinux errato, causa dell'AVC denial): lo studente deve solo
correggere il contesto (passi 6.1-6.2). Stato finale atteso:
- Il contesto SELinux di /custom e' httpd_sys_content_t.
- curl http://servera/index.html da workstation restituisce "This is
  SERVERA." (prova end-to-end, passo 7).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

HOST = "servera"
_EXPECTED_CONTENT = "This is SERVERA."


def main():
    print(f"🔧 Grading personalizzato per 'selinux-issues' (host: {HOST})")

    with GradingStep("Il contesto SELinux di /custom e' httpd_sys_content_t") as step:
        result = run("ls -dZ /custom", host=HOST, sudo=True)
        if "httpd_sys_content_t" not in result.stdout:
            step.add_error(f"Contesto atteso 'httpd_sys_content_t', trovato: {result.stdout.strip()}")

    with GradingStep("curl http://servera/index.html restituisce il contenuto atteso (AVC risolto)") as step:
        result = run("curl -s http://servera/index.html")
        if result.stdout.strip() != _EXPECTED_CONTENT:
            step.add_error(
                f"Risposta HTTP inattesa (atteso '{_EXPECTED_CONTENT}'): {result.stdout.strip()[:200]}"
            )


if __name__ == "__main__":
    main()
