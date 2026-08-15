#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH124 "flatpak-configure" (sku
rh0004l, RH124 sezione 13.2 "Configure Flatpak for Application
Installation"), sprovvista di `lab grade` ufficiale. Nessuna
materials/solutions ne' resources.txt: specifica presa dal testo della
guida (RH124 13.2, passi 2-6). Gira interamente su workstation (non su
servera).

Stato finale atteso:
- Il remote di sistema 'rhel' e' disabilitato (passo 2) — questo e'
  l'unico effetto realmente persistente e distintivo dell'esercizio.
- Il remote utente 'myrepo', aggiunto al passo 4, viene eliminato di
  proposito al passo 6 insieme al runtime installato: lo stato finale
  coincide quindi con quello iniziale (nessun myrepo, nessun runtime
  freedesktop). Li controlliamo comunque perche' sono richiesti
  esplicitamente dalla guida, ma da soli non distinguono "mai fatto"
  da "fatto e ripulito correttamente".
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

_RUNTIME = "org.freedesktop.Platform"


def remote_names(show_disabled=False, user=False):
    cmd = "flatpak remotes --columns=name"
    if user:
        cmd += " --user"
    if show_disabled:
        cmd += " --show-disabled"
    result = run(cmd)
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def main():
    print("🔧 Grading personalizzato per 'flatpak-configure' (host: workstation)")

    with GradingStep("Il remote di sistema 'rhel' e' disabilitato") as step:
        enabled = remote_names(show_disabled=False)
        all_remotes = remote_names(show_disabled=True)
        if "rhel" not in all_remotes:
            step.fail("Il remote 'rhel' non risulta configurato affatto")
        elif "rhel" in enabled:
            step.fail("Il remote 'rhel' e' ancora abilitato (atteso disabilitato)")

    with GradingStep("Il remote utente 'myrepo' e' stato rimosso (pulizia finale)") as step:
        if "myrepo" in remote_names(user=True):
            step.fail("Il remote 'myrepo' esiste ancora: andava rimosso con flatpak remote-delete")

    with GradingStep(f"Il runtime {_RUNTIME} non e' installato (rimosso con myrepo)") as step:
        result = run("flatpak list --user --columns=application")
        if _RUNTIME in result.stdout:
            step.fail(f"{_RUNTIME} risulta ancora installato")


if __name__ == "__main__":
    main()
