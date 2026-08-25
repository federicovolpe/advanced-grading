"""
Extra — Rete avanzata (vedi c8-04-network-networkpolicy.py). DO180 usa le
Route per l'accesso esterno (Cap. 4.7); l'Ingress Kubernetes e' un'API
alternativa che OpenShift supporta comunque, generando una Route "ombra"
per ogni Ingress — verificato dal vivo su questo cluster prima di scrivere
il check.
Esponi un Service con un Ingress Kubernetes.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, oc, oc_get_json, reset_project, run_cli

CHAPTER = "Extra — Rete avanzata"
TITLE = "Crea un Ingress"
PROJECT = "training-network-ingress"
IMAGE = "registry.access.redhat.com/ubi9/httpd-24:latest"
PORT = 8080
HOST = "myapp.example.com"

TASK = f"""\
Nel progetto "{PROJECT}" trovi il Deployment "app" e il Service "app"
(porta {PORT}), gia' pronti. Crea un Ingress chiamato "myapp-ingress"
che instrada le richieste per l'host "{HOST}" verso il Service "app"
sulla porta {PORT}.

Salva questo contenuto in ingress.yaml:

  apiVersion: networking.k8s.io/v1
  kind: Ingress
  metadata:
    name: myapp-ingress
  spec:
    rules:
      - host: {HOST}
        http:
          paths:
            - path: /
              pathType: Prefix
              backend:
                service:
                  name: app
                  port:
                    number: {PORT}

Poi applicalo (1 comando):
  oc apply -f ingress.yaml -n {PROJECT}
"""


def setup():
    reset_project(PROJECT)
    oc("create", "deployment", "app", f"--image={IMAGE}", "-n", PROJECT, check=True)
    oc("expose", "deployment", "app", f"--port={PORT}", f"--target-port={PORT}", "-n", PROJECT, check=True)


def grade():
    ingress = oc_get_json("ingress", "myapp-ingress", "-n", PROJECT)

    with GradingStep("L'Ingress myapp-ingress esiste") as step:
        if not ingress:
            step.fail("Ingress 'myapp-ingress' non trovato")

    with GradingStep(f"Instrada {HOST} verso il Service app:{PORT}") as step:
        if not ingress:
            step.fail("Ingress 'myapp-ingress' non trovato")
        else:
            rules = ingress.get("spec", {}).get("rules", []) or []
            match = None
            for rule in rules:
                if rule.get("host") != HOST:
                    continue
                for path in (rule.get("http") or {}).get("paths", []) or []:
                    backend = path.get("backend", {}).get("service", {})
                    if backend.get("name") == "app" and backend.get("port", {}).get("number") == PORT:
                        match = rule
            if not match:
                step.add_error(f"Nessuna regola per host={HOST!r} verso app:{PORT} (regole trovate: {rules})")

    with GradingStep("OpenShift ha ammesso l'Ingress (Route generata automaticamente)") as step:
        routes = oc_get_json("route", "-n", PROJECT)
        items = (routes or {}).get("items", []) or []
        admitted = any(
            r.get("spec", {}).get("host") == HOST
            and any(
                c.get("type") == "Admitted" and c.get("status") == "True"
                for ing in r.get("status", {}).get("ingress", [])
                for c in ing.get("conditions", [])
            )
            for r in items
        )
        if not admitted:
            step.add_error(f"Nessuna Route ammessa per l'host {HOST!r} (l'Ingress e' ancora in elaborazione?)")


if __name__ == "__main__":
    run_cli(setup, grade)
