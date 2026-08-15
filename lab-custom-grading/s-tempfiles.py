#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "s-tempfiles" (sezione
PDF 4.4 "Manage Temporary Files", pag. 91-92), sprovvista di `lab grade`
ufficiale. Nessuna materials/solutions ne' resources.txt: specifica presa
dal testo della guida, eseguita su servera.

Stato finale atteso (passi 2-4):
- /etc/tmpfiles.d/tmp.conf contiene SOLO la riga
  "q /tmp 1777 root root 5d" (la guida chiede esplicitamente di rimuovere
  tutte le altre righe copiate da /usr/lib/tmpfiles.d/tmp.conf).
- /etc/tmpfiles.d/momentary.conf contiene la riga
  "d /run/momentary 0700 root root 30s".
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

HOST = "servera"
TMP_CONF = "/etc/tmpfiles.d/tmp.conf"
MOMENTARY_CONF = "/etc/tmpfiles.d/momentary.conf"
_TMP_RULE = "q /tmp 1777 root root 5d"
_MOMENTARY_RULE = "d /run/momentary 0700 root root 30s"


def _significant_lines(content):
    return [
        line.strip()
        for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def main():
    print(f"🔧 Grading personalizzato per 's-tempfiles' (host: {HOST})")

    with GradingStep(f"{TMP_CONF} contiene solo la regola richiesta (5 giorni)") as step:
        result = run(f"cat {TMP_CONF}", host=HOST, sudo=True)
        if result.returncode != 0:
            step.fail(f"{TMP_CONF} non trovato")
        else:
            lines = _significant_lines(result.stdout)
            if lines != [_TMP_RULE]:
                step.add_error(
                    f"Atteso solo '{_TMP_RULE}', trovato: {lines}"
                )

    with GradingStep(f"{MOMENTARY_CONF} contiene la regola richiesta (30 secondi)") as step:
        result = run(f"cat {MOMENTARY_CONF}", host=HOST, sudo=True)
        if result.returncode != 0:
            step.fail(f"{MOMENTARY_CONF} non trovato")
        else:
            lines = _significant_lines(result.stdout)
            if _MOMENTARY_RULE not in lines:
                step.add_error(
                    f"Regola attesa '{_MOMENTARY_RULE}' non trovata, contenuto: {lines}"
                )

    with GradingStep(f"{TMP_CONF} e' una configurazione valida (systemd-tmpfiles --clean)") as step:
        result = run(f"systemd-tmpfiles --clean {TMP_CONF}", host=HOST, sudo=True)
        if result.returncode != 0:
            step.add_error(
                f"'systemd-tmpfiles --clean {TMP_CONF}' e' uscito con codice "
                f"{result.returncode} (atteso 0): {result.stderr.strip()}"
            )

    with GradingStep(f"{MOMENTARY_CONF} e' una configurazione valida (systemd-tmpfiles --create)") as step:
        result = run(f"systemd-tmpfiles --create {MOMENTARY_CONF}", host=HOST, sudo=True)
        if result.returncode != 0:
            step.add_error(
                f"'systemd-tmpfiles --create {MOMENTARY_CONF}' e' uscito con codice "
                f"{result.returncode} (atteso 0): {result.stderr.strip()}"
            )


if __name__ == "__main__":
    main()
