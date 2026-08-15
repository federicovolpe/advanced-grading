#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "image-bootable" (sezione
PDF 18.4 "Create Installable Images for Image Mode", pag. 464-465),
sprovvista di `lab grade` ufficiale. Nessuna materials/solutions ne'
resources.txt: specifica presa dal testo della guida, su workstation.

Stato finale atteso:
- L'immagine "webserver-bootc" e' pushata sul registry remoto (passo 6) —
  l'unico artefatto esplicitamente persistente richiesto dalla guida.
- Il container di test locale (passo 5.1, porta 8080->80) non viene mai
  fermato/rimosso nella guida: se e' ancora in esecuzione, deve rispondere
  con il messaggio atteso.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

REGISTRY = "registry.lab.example.com:5000"
IMAGE = "student/webserver-bootc"
_EXPECTED_CONTENT = "Hello image mode for RHEL!"


def main():
    print("🔧 Grading personalizzato per 'image-bootable' (host: workstation)")

    with GradingStep(f"L'immagine {IMAGE} e' presente sul registry remoto") as step:
        result = run(f"podman search --list-tags {REGISTRY}/{IMAGE}")
        if result.returncode != 0 or "webserver-bootc" not in result.stdout:
            step.fail(f"Immagine non trovata su {REGISTRY}/{IMAGE}: {result.stdout.strip()}")

    with GradingStep("Il container di test locale (porta 8080) serve il contenuto atteso") as step:
        result = run("curl -s localhost:8080")
        if result.stdout.strip() != _EXPECTED_CONTENT:
            step.add_error(
                f"Atteso '{_EXPECTED_CONTENT}' su localhost:8080, trovato: '{result.stdout.strip()}'"
            )


if __name__ == "__main__":
    main()
