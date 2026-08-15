#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "lvm-extend" (sezione PDF
11.4 "Extend a Logical Volume", pag. 283), sprovvista di `lab grade`
ufficiale. Nessuna materials/solutions ne' resources.txt: specifica presa
dal testo della guida, su servera.

Stato finale atteso:
- Il volume group "vg_servera" include /dev/sdb3 (passo 4.1).
- Il logical volume "lv_servera" e' esteso a 700 MiB (passo 4.2).
- Il filesystem xfs su /data riflette la nuova dimensione (passo 4.3,
  verificato tramite lo spazio totale disponibile riportato da df).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

HOST = "servera"
VG_NAME = "vg_servera"
LV_NAME = "lv_servera"


def main():
    print(f"🔧 Grading personalizzato per 'lvm-extend' (host: {HOST})")

    with GradingStep(f"Il volume group '{VG_NAME}' include /dev/sdb3") as step:
        result = run(f"vgs --noheadings -o pv_name {VG_NAME}", host=HOST, sudo=True)
        if result.returncode != 0:
            step.fail(f"Volume group '{VG_NAME}' non trovato")
        elif "/dev/sdb3" not in result.stdout:
            step.add_error(f"/dev/sdb3 non incluso nel VG, trovato: {result.stdout.strip()}")

    with GradingStep(f"Il logical volume '{LV_NAME}' e' esteso a 700 MiB") as step:
        result = run(
            f"lvs --noheadings --units m --nosuffix -o lv_size {VG_NAME}/{LV_NAME}",
            host=HOST, sudo=True,
        )
        if result.returncode != 0:
            step.fail(f"Logical volume '{LV_NAME}' non trovato")
        else:
            try:
                size_mb = float(result.stdout.strip())
            except ValueError:
                size_mb = 0
            if size_mb < 690:
                step.add_error(f"Atteso ~700 MiB, trovato: {result.stdout.strip()} MiB")

    with GradingStep("Il filesystem xfs su /data riflette lo spazio esteso (>500 MiB totali)") as step:
        result = run("df --output=size -m /data | tail -1", host=HOST, sudo=True)
        try:
            size_mb = int(result.stdout.strip())
        except ValueError:
            size_mb = 0
        if size_mb < 500:
            step.add_error(f"Dimensione filesystem inattesa: {result.stdout.strip()} MiB (atteso >500)")


if __name__ == "__main__":
    main()
