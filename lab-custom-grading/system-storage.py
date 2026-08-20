#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise AU294 "system-storage" (sku
au0026l, sezione 8.10 "Automating Storage Tasks"), sprovvista di
`lab grade` ufficiale. Specifica presa da
materials/labs/system-storage/solutions/storage.yml.sol: usa il ruolo
redhat.rhel_system_roles.storage per creare il volume group "apache-vg"
con due volumi logici, content-lv (512m, /var/www, xfs) e logs-lv (1g,
/var/log/httpd, xfs).

Il disco fisico da usare e' lasciato "CHANGE-ME" nella soluzione stessa: la
guida (passo 2.2, "the 5 GB physical device") fa identificare allo
studente il disco da 5GB con disk_list.yml, quindi varia da classroom a
classroom -> per regola aurea NON viene fissato un device name, si verifica
solo l'effetto (VG/LV/mount/fstab), indipendentemente da quale disco lo
fornisca.

Nessun test dal vivo eseguito per questo script: modificare LVM/mount su
servera durante l'analisi rischierebbe di lasciare lo stato di storage
condiviso in una condizione non facilmente reversibile (vedi CLAUDE.md
sez. 4) — verifica basata solo su solutions + testo guida.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

HOST = "servera"

# (nome LV, dimensione attesa in MiB, mount point, filesystem)
_EXPECTED_LVS = [
    ("content-lv", 512, "/var/www", "xfs"),
    ("logs-lv", 1024, "/var/log/httpd", "xfs"),
]


def lvs_json(host=HOST):
    result = run(
        "lvs --units m --nosuffix --noheadings "
        "-o lv_name,vg_name,lv_size --reportformat json",
        host=host, sudo=True,
    )
    if result.returncode != 0:
        return None
    import json
    try:
        return json.loads(result.stdout)["report"][0]["lv"]
    except (KeyError, IndexError, ValueError):
        return None


def main():
    print(f"🔧 Grading personalizzato per 'system-storage' (host: {HOST})")

    with GradingStep("Il volume group apache-vg esiste su servera") as step:
        result = run("vgs --noheadings -o vg_name", host=HOST, sudo=True)
        if result.returncode != 0 or "apache-vg" not in result.stdout:
            step.fail("Volume group 'apache-vg' non trovato")

    lvs = lvs_json() or []
    lv_by_name = {lv["lv_name"]: lv for lv in lvs}

    for lv_name, expected_mib, mount_point, fstype in _EXPECTED_LVS:
        with GradingStep(f"Il volume logico {lv_name} esiste in apache-vg con la dimensione attesa") as step:
            lv = lv_by_name.get(lv_name)
            if not lv or lv.get("vg_name") != "apache-vg":
                step.fail(f"Volume logico '{lv_name}' non trovato in apache-vg")
            else:
                try:
                    size_mib = float(lv["lv_size"])
                except (TypeError, ValueError):
                    size_mib = None
                # tolleranza 5%: il ruolo storage puo' arrotondare all'extent LVM
                if size_mib is None or abs(size_mib - expected_mib) > expected_mib * 0.05:
                    step.add_error(f"Dimensione attesa ~{expected_mib}MiB, trovata {lv.get('lv_size')}")

        with GradingStep(f"{lv_name} e' montato su {mount_point} come {fstype}, persistito in /etc/fstab") as step:
            mount_result = run(f"findmnt -n -o SOURCE,FSTYPE {mount_point}", host=HOST, sudo=True)
            if mount_result.returncode != 0:
                step.fail(f"Nessun filesystem montato su {mount_point}")
            else:
                fields = mount_result.stdout.split()
                if len(fields) < 2 or lv_name not in fields[0] or fields[1] != fstype:
                    step.add_error(f"Mount trovato ma non corrisponde: '{mount_result.stdout.strip()}'")

            fstab_result = run("cat /etc/fstab", host=HOST, sudo=True)
            if fstab_result.returncode != 0 or mount_point not in fstab_result.stdout:
                step.add_error(f"{mount_point} non presente in /etc/fstab (non persistente al reboot)")


if __name__ == "__main__":
    main()
