#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH134 "netsecurity-ports" (sezione
PDF 14.4 "SELinux Port Labeling", pag. 348-350), sprovvista di `lab grade`
ufficiale. Nessuna materials/solutions ne' resources.txt: specifica presa
dal testo della guida, su servera (+ verifica HTTP da workstation).

Stato finale atteso:
- La porta 82/tcp ha il contesto SELinux http_port_t (passo 3.2).
- httpd attivo (passo 3.3).
- La porta 82/tcp e' aperta in modo permanente sul firewall (passo 6.1).
- curl http://servera.lab.example.com:82 da workstation restituisce
  "Hello" (prova end-to-end, passo 7).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, run, service_is_active

HOST = "servera"
_EXPECTED_CONTENT = "Hello"


def _tcp_ports_for_type(semanage_output, port_type):
    """Estrae i numeri di porta TCP associati a un tipo SELinux dall'output
    di `semanage port -l` (formato: "TYPE   tcp   80, 81, 443, ...")."""
    ports = set()
    for line in semanage_output.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == port_type and parts[1] == "tcp":
            for token in " ".join(parts[2:]).replace(",", " ").split():
                if token.isdigit():
                    ports.add(token)
    return ports


def main():
    print(f"🔧 Grading personalizzato per 'netsecurity-ports' (host: {HOST})")

    with GradingStep("La porta 82/tcp ha il contesto SELinux http_port_t") as step:
        result = run("semanage port -l", host=HOST, sudo=True)
        ports = _tcp_ports_for_type(result.stdout, "http_port_t")
        if "82" not in ports:
            step.add_error(f"Porta 82 non trovata tra le porte http_port_t: {sorted(ports)}")

    with GradingStep("httpd e' attivo") as step:
        if not service_is_active("httpd", host=HOST):
            step.fail("httpd non risulta attivo")

    with GradingStep("La porta 82/tcp e' aperta in modo permanente sul firewall") as step:
        result = run("firewall-cmd --permanent --list-ports", host=HOST, sudo=True)
        if "82/tcp" not in result.stdout.split():
            step.add_error(f"'82/tcp' non presente tra le porte aperte: {result.stdout.strip()}")

    with GradingStep("curl http://servera.lab.example.com:82 restituisce il contenuto atteso") as step:
        result = run("curl -s http://servera.lab.example.com:82")
        if result.stdout.strip() != _EXPECTED_CONTENT:
            step.add_error(
                f"Risposta HTTP inattesa (atteso '{_EXPECTED_CONTENT}'): {result.stdout.strip()[:200]}"
            )


if __name__ == "__main__":
    main()
