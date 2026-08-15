#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH124 "net-edit" (sku rh0026l,
RH124 sezione 18.4 "Edit Network Configuration Files"), sprovvista di
`lab grade` ufficiale. Nessuna materials/solutions ne' resources.txt:
specifica presa dal testo della guida (RH124 18.4, passi 3-7), su servera
e serverb.

A differenza di net-configure (che crea una nuova connessione 'static-addr'),
qui si modifica il profilo esistente 'Wired connection 1': ipv4.method
manual con indirizzo primario via nmcli con mod, poi un secondo indirizzo
(address2) aggiunto modificando a mano il file .nmconnection, seguito da
`nmcli con reload` + `nmcli con up`.

Stato finale atteso sull'interfaccia ens4:
- servera: 172.24.250.30/24 (primario) + 10.0.1.1/24 (secondario).
- serverb: 172.24.250.40/24 (primario) + 10.0.1.2/24 (secondario).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

CONN = "Wired connection 1"
_EXPECTED = {
    "servera": ("172.24.250.30/24", "10.0.1.1/24"),
    "serverb": ("172.24.250.40/24", "10.0.1.2/24"),
}


def con_field(host, field):
    result = run(f"nmcli -f {field} con show '{CONN}'", host=host, sudo=True)
    if result.returncode != 0:
        return None
    return result.stdout


def main():
    print("🔧 Grading personalizzato per 'net-edit' (host: servera, serverb)")

    for host, (primary, secondary) in _EXPECTED.items():
        with GradingStep(
            f"[{host}] '{CONN}' e' statica con indirizzo primario {primary} e secondario {secondary}"
        ) as step:
            method_out = con_field(host, "ipv4.method")
            if method_out is None:
                step.fail(f"Connessione '{CONN}' non trovata su {host}")
                continue
            if "manual" not in method_out:
                step.add_error(f"ipv4.method atteso 'manual': {method_out.strip()}")

            addr_out = con_field(host, "ipv4.addresses") or ""
            if primary not in addr_out:
                step.add_error(f"Indirizzo primario {primary} non trovato: {addr_out.strip()}")
            if secondary not in addr_out:
                step.add_error(f"Indirizzo secondario {secondary} non trovato: {addr_out.strip()}")


if __name__ == "__main__":
    main()
