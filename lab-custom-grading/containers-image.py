#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "containers-image" (sezione
PDF 17.6 "Create and Manage Container Images", pag. 439-443), sprovvista
di `lab grade` ufficiale. Nessuna materials/solutions ne' resources.txt:
specifica presa dal testo della guida, su workstation.

L'esercizio rimuove entrambe le immagini locali alla fine (passo 11): lo
stato locale persistente e' quindi vuoto per design. L'unico artefatto
davvero persistente e verificabile a posteriori e' il push delle due
versioni dell'immagine "my_image" (tag 1.0 e 1.1) sul registry remoto
(passi 5 e 9), che resta li' indipendentemente dalla pulizia locale.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

REGISTRY = "registry.lab.example.com:5000"
IMAGE = "my_image"


def main():
    print("🔧 Grading personalizzato per 'containers-image' (host: workstation)")

    with GradingStep(f"L'immagine {IMAGE} con tag 1.0 e 1.1 e' presente sul registry remoto") as step:
        result = run(f"podman search --list-tags {REGISTRY}/{IMAGE}")
        if result.returncode != 0:
            step.fail(f"Impossibile interrogare il registry {REGISTRY}")
        else:
            tags = {line.split()[-1] for line in result.stdout.splitlines() if IMAGE in line}
            for expected_tag in ("1.0", "1.1"):
                if expected_tag not in tags:
                    step.add_error(f"Tag '{expected_tag}' non trovato sul registry (trovati: {sorted(tags)})")


if __name__ == "__main__":
    main()
