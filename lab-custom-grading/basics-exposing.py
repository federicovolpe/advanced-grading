#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise basics-exposing (corso DO188), priva
di `lab grade` ufficiale (la classe BasicsExposing implementa solo
start()/finish()).

CONFIDENZA DELLA FONTE: nessun `materials/solutions/basics-exposing/` ne'
`materials/labs/basics-exposing/`. Le fonti oggettive usate sono:
  - do188/basics-exposing.py: PODMAN_NETWORK = "cities"; start() richiede
    libere le porte 8080 e 8090 e copia i container source
    "podman-info-times" e "podman-info-cities"; finish() rimuove
    forzatamente i container "cities-app" e "times-app" e la rete "cities".
  - I Containerfile reali dei due container source (letti per intero):
      podman-info-times: EXPOSE 8080, ENTRYPOINT ["/app/times-app"]
      podman-info-cities: EXPOSE 8090, ENTRYPOINT ["/app/cities-app"]
    Questo conferma (non e' solo l'indizio) che times-app va pubblicato su
    8080 e cities-app su 8090.
  - Il codice Go dei due servizi (letto per intero) definisce le rotte
    HTTP reali:
      times-app:  GET /times/{city_code}  -> stringa data in formato
                  "2006-01-02T15:04:05.000Z" (es. per MAD/BKK/SAN/LON)
      cities-app: GET /cities/{city_code} -> JSON {name, population,
                  country, time}, dove cities-app chiama internamente
                  times-app all'URL preso dalla env var TIMES_APP_URL
                  (quindi richiede risoluzione DNS del nome "times-app",
                  possibile solo se entrambi i container sono sulla stessa
                  rete Podman custom "cities").

Non conosco il valore esatto assegnato a TIMES_APP_URL (nessuna solution/
resources.txt lo conferma), quindi non lo controllo direttamente: verifico
invece il comportamento end-to-end via una GET reale a cities-app, che a sua
volta contatta times-app solo se la configurazione (env var + rete) e'
corretta. E' un test piu' solido e meno fragile di un controllo su un env
var che non sono in grado di confermare con certezza.

Uso: basics-exposing.py   (nessun progetto OpenShift: e' un esercizio Podman)
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (
    GradingStep,
    container_is_running,
    container_networks,
    container_port_mappings,
    http_get,
    podman_network_exists,
)

LAB_NAME = "basics-exposing"
NETWORK = "cities"
TIMES_APP = "times-app"
CITIES_APP = "cities-app"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


def _published_on(name, host_port):
    ports = container_port_mappings(name)
    published = {p for hosts in ports.values() for p in hosts if p}
    return host_port in published


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    with GradingStep(f"La rete Podman '{NETWORK}' esiste") as step:
        if not podman_network_exists(NETWORK):
            step.fail(f"Rete '{NETWORK}' non trovata")

    with GradingStep(f"Il container '{TIMES_APP}' e' configurato correttamente") as step:
        if not container_is_running(TIMES_APP):
            step.fail(f"Container '{TIMES_APP}' non in esecuzione")
        else:
            if NETWORK not in container_networks(TIMES_APP):
                step.add_error(f"Il container non e' collegato alla rete '{NETWORK}'")
            if not _published_on(TIMES_APP, "8080"):
                step.add_error(
                    f"Nessuna porta pubblicata su 8080 host "
                    f"(mapping trovati: {container_port_mappings(TIMES_APP)})"
                )

    with GradingStep(f"Il container '{CITIES_APP}' e' configurato correttamente") as step:
        if not container_is_running(CITIES_APP):
            step.fail(f"Container '{CITIES_APP}' non in esecuzione")
        else:
            if NETWORK not in container_networks(CITIES_APP):
                step.add_error(f"Il container non e' collegato alla rete '{NETWORK}'")
            if not _published_on(CITIES_APP, "8090"):
                step.add_error(
                    f"Nessuna porta pubblicata su 8090 host "
                    f"(mapping trovati: {container_port_mappings(CITIES_APP)})"
                )

    with GradingStep("L'app times-app risponde correttamente su /times/MAD") as step:
        if not container_is_running(TIMES_APP):
            step.fail(f"Container '{TIMES_APP}' non in esecuzione")
        else:
            ok, body = http_get("http://localhost:8080/times/MAD")
            if not ok:
                step.fail("GET http://localhost:8080/times/MAD non ha risposto (HTTP)")
            elif not DATE_RE.match(body.strip()):
                step.add_error(
                    f"Risposta inattesa da /times/MAD: {body!r} "
                    "(atteso un timestamp tipo 2024-01-01T00:00:00.000Z)"
                )

    with GradingStep(
        "L'app cities-app risponde correttamente su /cities/MAD "
        "(verifica indiretta che raggiunga times-app via rete)"
    ) as step:
        if not container_is_running(CITIES_APP):
            step.fail(f"Container '{CITIES_APP}' non in esecuzione")
        else:
            ok, body = http_get("http://localhost:8090/cities/MAD")
            if not ok:
                step.fail("GET http://localhost:8090/cities/MAD non ha risposto (HTTP)")
            else:
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    step.fail(f"Risposta non e' JSON valido: {body!r}")
                else:
                    if data.get("name") != "Madrid":
                        step.add_error(f"Campo 'name' inatteso: {data.get('name')!r}")
                    if data.get("population") != 3223000:
                        step.add_error(f"Campo 'population' inatteso: {data.get('population')!r}")
                    if data.get("country") != "Spain":
                        step.add_error(f"Campo 'country' inatteso: {data.get('country')!r}")
                    if not data.get("time"):
                        step.add_error(
                            "Campo 'time' assente o nullo: cities-app non e' "
                            "riuscita a contattare times-app (rete/env non corretti?)"
                        )


if __name__ == "__main__":
    main()
