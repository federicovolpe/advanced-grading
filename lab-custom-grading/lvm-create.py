#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "lvm-create" (sezione PDF
11.2 "Create Logical Volumes", pag. 275-276), sprovvista di `lab grade`
ufficiale. Nessuna materials/solutions ne' resources.txt: specifica presa
dal testo della guida, su servera.

Stato finale atteso:
- Volume group "vg_servera" esiste, basato su /dev/sdb1 e /dev/sdb2 (passi
  2-4).
- Logical volume "lv_servera" esiste dentro vg_servera (passo 5).
- lv_servera e' formattato xfs e montato su /data (passi 6-6.5).
- /data contiene file (copiati da /etc/*.conf al passo 7.1: prova che il
  filesystem e' davvero accessibile in scrittura/lettura).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

HOST = "servera"
VG_NAME = "vg_servera"
LV_NAME = "lv_servera"


def main():
    print(f"🔧 Grading personalizzato per 'lvm-create' (host: {HOST})")

    with GradingStep(f"Il volume group '{VG_NAME}' esiste su /dev/sdb1 e /dev/sdb2") as step:
        result = run(f"vgs --noheadings -o pv_name {VG_NAME}", host=HOST, sudo=True)
        if result.returncode != 0:
            step.fail(f"Volume group '{VG_NAME}' non trovato")
        else:
            pvs = result.stdout
            if "/dev/sdb1" not in pvs or "/dev/sdb2" not in pvs:
                step.add_error(f"Atteso /dev/sdb1 e /dev/sdb2 come PV, trovato: {pvs.strip()}")

    with GradingStep(f"Il logical volume '{LV_NAME}' esiste dentro '{VG_NAME}'") as step:
        result = run(f"lvs --noheadings -o lv_name {VG_NAME}", host=HOST, sudo=True)
        if LV_NAME not in result.stdout:
            step.fail(f"Logical volume '{LV_NAME}' non trovato in {VG_NAME}")

    with GradingStep(f"/data e' montato da /dev/{VG_NAME}/{LV_NAME} come xfs") as step:
        result = run("findmnt -no SOURCE,FSTYPE /data", host=HOST, sudo=True)
        if result.returncode != 0:
            step.fail("/data non risulta montato")
        elif LV_NAME not in result.stdout or "xfs" not in result.stdout:
            step.add_error(f"Atteso '{LV_NAME} ... xfs', trovato: {result.stdout.strip()}")

    with GradingStep("/data contiene i file copiati da /etc/*.conf") as step:
        result = run("ls /data | wc -l", host=HOST, sudo=True)
        try:
            count = int(result.stdout.strip())
        except ValueError:
            count = 0
        if count < 1:
            step.add_error("/data e' vuota")


if __name__ == "__main__":
    main()
