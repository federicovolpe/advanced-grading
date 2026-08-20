#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise AU294 "develop-inventory" (sku
au0020l, sez. 2.2 "Building an Ansible Inventory"), sprovvista di `lab
grade` ufficiale. Specifica presa da materials/labs/develop-inventory/
solutions/inventory.sol (fonte primaria, CLAUDE.md step 1).

Verifica la struttura logica dell'inventario (gruppi/host, incluso "us"
come parent di raleigh+mountainview) invece di un diff testuale: lo
studente puo' esprimere gli stessi host con range ("server[a:d]...") o
elenco esplicito, entrambi validi secondo la guida.
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep

WORKDIR = os.path.expanduser(f"~/{sys.argv[1] if len(sys.argv) > 1 else 'develop-inventory'}")
INVENTORY_PATH = os.path.join(WORKDIR, "inventory")

# Sez. 2.2, tabella "Server Inventory Specifications" + gruppo "us:children".
_EXPECTED_GROUPS = {
    "webservers": {"servera.lab.example.com", "serverb.lab.example.com",
                   "serverc.lab.example.com", "serverd.lab.example.com"},
    "raleigh": {"servera.lab.example.com", "serverb.lab.example.com"},
    "mountainview": {"serverc.lab.example.com"},
    "london": {"serverd.lab.example.com"},
    "development": {"servera.lab.example.com"},
    "testing": {"serverb.lab.example.com"},
    "production": {"serverc.lab.example.com", "serverd.lab.example.com"},
    "us": {"servera.lab.example.com", "serverb.lab.example.com", "serverc.lab.example.com"},
}


def _resolve_hosts(data, group):
    """Risolve ricorsivamente l'insieme di host di un gruppo, seguendo
    'children' (necessario per "us:children" = raleigh + mountainview)."""
    node = data.get(group)
    if node is None:
        return None
    hosts = set(node.get("hosts", []))
    for child in node.get("children", []):
        child_hosts = _resolve_hosts(data, child)
        if child_hosts:
            hosts |= child_hosts
    return hosts


def _load_inventory():
    if not os.path.exists(INVENTORY_PATH):
        return None
    result = subprocess.run(
        ["ansible-inventory", "-i", INVENTORY_PATH, "--list"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def main():
    print(f"🔧 Grading personalizzato per 'develop-inventory' (dir: {WORKDIR})")

    with GradingStep(f"Il file inventory esiste in {WORKDIR}") as step:
        if not os.path.exists(INVENTORY_PATH):
            step.fail(f"'{INVENTORY_PATH}' non trovato")

    data = _load_inventory()
    with GradingStep("Il file inventory e' un inventario Ansible valido") as step:
        if data is None:
            step.fail("`ansible-inventory --list` non e' riuscito a interpretare il file")

    if data is None:
        return

    for group, expected_hosts in _EXPECTED_GROUPS.items():
        with GradingStep(f"Il gruppo '{group}' contiene gli host attesi") as step:
            actual_hosts = _resolve_hosts(data, group)
            if actual_hosts is None:
                step.fail(f"Gruppo '{group}' non definito nell'inventario")
            elif actual_hosts != expected_hosts:
                step.add_error(
                    f"Atteso {sorted(expected_hosts)}, trovato {sorted(actual_hosts)}"
                )


if __name__ == "__main__":
    main()
