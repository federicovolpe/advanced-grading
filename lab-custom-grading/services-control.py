#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise RH124 "services-control" (sku
rh0024l, RH124 sezione 16.4 "Control System Services"), sprovvista di
`lab grade` ufficiale. Nessuna materials/solutions ne' resources.txt:
specifica presa dal testo della guida (RH124 16.4, passi 2-6), su servera.

I passi su sshd (restart, reload) sono transitori e non cambiano lo stato
persistente del servizio: non vengono gradati (non e' cio' che l'esercizio
chiede di modificare in modo duraturo). L'unico effetto persistente
richiesto e' su chronyd: va fermato (stop) e disabilitato all'avvio
(disable), e lo stato deve reggere anche dopo il reboot di verifica
richiesto dai passi 4 e 6 della guida.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, service_is_active, service_is_enabled

HOST = "servera"
SERVICE = "chronyd"


def main():
    print(f"🔧 Grading personalizzato per 'services-control' (host: {HOST})")

    with GradingStep(f"Il servizio {SERVICE} e' fermo (stop)") as step:
        if service_is_active(SERVICE, host=HOST):
            step.fail(f"{SERVICE} risulta ancora attivo")

    with GradingStep(f"Il servizio {SERVICE} e' disabilitato all'avvio (disable)") as step:
        if service_is_enabled(SERVICE, host=HOST):
            step.fail(f"{SERVICE} risulta ancora abilitato al boot")


if __name__ == "__main__":
    main()
