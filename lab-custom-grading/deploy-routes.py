#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato deploy-routes, sprovvisto di
`lab grade` ufficiale (la classe DeployRoutes nel pacchetto do180 implementa
solo start()/finish(), non grade()).

Niente materials/solutions ne' resources.txt per questo esercizio: la
specifica e' stata ricavata incrociando due fonti oggettive del modulo
ufficiale (do180/exercises/deploy_routes.py) e verificata dal vivo sul
cluster di questa classe:
- start() usa `self.project = "web-applications"` (diverso dal nome
  esercizio) e verifica che l'immagine
  registry.lab.example.com:8443/redhattraining/do180-httpd-app:v1 sia
  disponibile pubblicamente sul registry della classroom.
- il file di partenza materials/labs/deploy-routes/lab-start/index.php,
  incluso in quell'immagine, stampa letteralmente
  "Welcome to Red Hat Training, from $hostname" quando l'app risponde
  su HTTP: e' un segnale deterministico e indipendente dai nomi di
  risorsa scelti dallo studente per verificare che l'app giusta sia
  davvero raggiungibile via Route.

L'esercizio chiede di esporre l'app do180-httpd-app in DUE modi diversi
(nomi di app/service/route lasciati alla scelta dello studente, quindi
gradati per caratteristiche e non per nome fisso, come raccomandato in
CLAUDE.md):
1. una Route creata direttamente (es. `oc expose svc/...`);
2. una seconda app esposta tramite una risorsa Ingress (che OpenShift
   converte automaticamente in una Route, riconoscibile dalla
   ownerReference di kind "Ingress").

Per ciascuna delle due, il check verifica che esista almeno una Route del
tipo giusto e che risponda in HTTP con il contenuto atteso.

Uso: deploy-routes.py [nome-progetto]   (default: web-applications)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists, http_get

LAB_NAME = "deploy-routes"
PROJECT = "web-applications"
EXPECTED_TEXT = "Welcome to Red Hat Training, from"


def route_url(route):
    spec = route.get("spec", {})
    host = spec.get("host")
    if not host:
        return None
    scheme = "https" if spec.get("tls") else "http"
    path = spec.get("path") or "/"
    return f"{scheme}://{host}{path}"


def is_ingress_owned(route):
    owners = route.get("metadata", {}).get("ownerReferences", []) or []
    return any(o.get("kind") == "Ingress" for o in owners)


def route_serves_expected_app(route):
    url = route_url(route)
    if not url:
        return False
    ok, body = http_get(url, timeout=8)
    return ok and EXPECTED_TEXT in body


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else PROJECT
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    routes_data = oc_get_json("route", "-n", project)
    routes = routes_data.get("items", []) if routes_data else []
    direct_routes = [r for r in routes if not is_ingress_owned(r)]
    ingress_routes = [r for r in routes if is_ingress_owned(r)]

    with GradingStep("Un'app e' esposta con una Route creata direttamente (es. 'oc expose')") as step:
        if not direct_routes:
            step.add_error("Nessuna Route diretta (non generata da un Ingress) trovata nel progetto")
        elif not any(route_serves_expected_app(r) for r in direct_routes):
            step.add_error(
                "Nessuna delle Route dirette risponde con il contenuto atteso "
                f"({EXPECTED_TEXT!r}) dell'immagine do180-httpd-app"
            )

    ingress_data = oc_get_json("ingress", "-n", project)
    ingresses = ingress_data.get("items", []) if ingress_data else []

    with GradingStep("Un'altra app e' esposta tramite una risorsa Ingress") as step:
        if not ingresses:
            step.add_error("Nessuna risorsa Ingress trovata nel progetto")
        elif not ingress_routes:
            step.add_error("Esiste un Ingress ma OpenShift non ha ancora generato la Route corrispondente")
        elif not any(route_serves_expected_app(r) for r in ingress_routes):
            step.add_error(
                "Nessuna Route generata da un Ingress risponde con il contenuto atteso "
                f"({EXPECTED_TEXT!r}) dell'immagine do180-httpd-app"
            )


if __name__ == "__main__":
    main()
