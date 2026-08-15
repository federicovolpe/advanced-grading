#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH124 "net-configure" (sku
rh0026l, RH124 sezione 18.2 "Configure Networking from the Command Line"),
sprovvista di `lab grade` ufficiale. Nessuna materials/solutions ne'
resources.txt: specifica presa dal testo della guida (RH124 18.2, passi
6-10), su servera e serverb.

Stato finale atteso (indirizzi statici sulla rete secondaria ens4):
- servera: connessione 'static-addr', ipv4.method manual, 172.24.250.30/24.
- serverb: connessione 'static-addr', ipv4.method manual, 172.24.250.40/24,
  con la connessione temporanea 'Wired connection 1' eliminata (passo
  10.3, esplicito nella guida solo per serverb).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

CONN = "static-addr"
_EXPECTED = {
    "servera": "172.24.250.30/24",
    "serverb": "172.24.250.40/24",
}


def con_field(host, field):
    result = run(f"nmcli -t -f {field} con show {CONN}", host=host, sudo=True)
    if result.returncode != 0:
        return None
    line = result.stdout.strip()
    return line.split(":", 1)[1] if ":" in line else line


def main():
    print("🔧 Grading personalizzato per 'net-configure' (host: servera, serverb)")

    for host, expected_addr in _EXPECTED.items():
        with GradingStep(f"[{host}] La connessione '{CONN}' esiste con IP statico {expected_addr}") as step:
            method = con_field(host, "ipv4.method")
            addr = con_field(host, "ipv4.addresses")
            if method is None:
                step.fail(f"Connessione '{CONN}' non trovata su {host}")
                continue
            if method != "manual":
                step.add_error(f"ipv4.method atteso 'manual', trovato '{method}'")
            if addr != expected_addr:
                step.add_error(f"ipv4.addresses atteso '{expected_addr}', trovato '{addr}'")

    with GradingStep("[serverb] La connessione temporanea 'Wired connection 1' e' stata eliminata") as step:
        result = run("nmcli -t -f NAME con show", host="serverb", sudo=True)
        if "Wired connection 1" in result.stdout:
            step.fail("'Wired connection 1' esiste ancora su serverb: andava eliminata con nmcli con del")


if __name__ == "__main__":
    main()
