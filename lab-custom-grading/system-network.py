#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise AU294 "system-network" (sku
au0026l, sezione 8.12 "Automating Network Configuration Tasks"),
sprovvista di `lab grade` ufficiale. Specifica presa da
materials/labs/system-network/solutions/vars.sol: il ruolo
redhat.rhel_system_roles.network deve configurare l'IP statico
192.168.0.12/24 sull'interfaccia identificata dal MAC address indicato
nella guida (passo 5.1, "identify the network interface with the
52:54:00:01:00:6e MAC address").

Il nome dell'interfaccia (nella soluzione e' un placeholder "MODIFY-ME",
nella guida un esempio "ens4") NON viene fissato: la guida stessa avverte
che "the interface name might differ in your classroom" (passo 5.4) —
verificato dal vivo in questa sessione: su questa macchina l'interfaccia
secondaria e' ens4, ma per regola aurea lo script cerca l'IP su QUALSIASI
interfaccia (esclusa lo), non un nome fisso.

Nessun test dal vivo eseguito: applicare il ruolo network durante l'analisi
rischierebbe di alterare la configurazione di rete di servera (anche se
l'interfaccia target e' quella secondaria, non quella usata per SSH) — per
questo esercizio la verifica si basa solo su solutions + testo guida (vedi
CLAUDE.md sez. 4).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run

HOST = "servera"
_EXPECTED_ADDR = "192.168.0.12/24"


def main():
    print(f"🔧 Grading personalizzato per 'system-network' (host: {HOST})")

    with GradingStep(f"Una interfaccia di rete su servera ha l'indirizzo {_EXPECTED_ADDR}") as step:
        result = run("ip -o -4 addr show", host=HOST)
        if result.returncode != 0:
            step.fail("Impossibile leggere gli indirizzi IPv4 su servera")
        else:
            found = any(
                _EXPECTED_ADDR in line and " lo " not in line
                for line in result.stdout.splitlines()
            )
            if not found:
                step.add_error(
                    f"Nessuna interfaccia (esclusa lo) con indirizzo {_EXPECTED_ADDR} trovata"
                )

    with GradingStep("La connessione NetworkManager e' persistente (state: up, non temporanea)") as step:
        result = run("nmcli -t -f NAME,STATE con show", host=HOST, sudo=True)
        if result.returncode != 0:
            step.fail("Impossibile interrogare nmcli su servera")
        elif not any(line.strip().endswith(":activated") for line in result.stdout.splitlines()):
            step.add_error("Nessuna connessione NetworkManager risulta 'activated'")


if __name__ == "__main__":
    main()
