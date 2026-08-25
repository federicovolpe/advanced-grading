"""
Extra — Rete avanzata (non e' un capitolo del manuale DO180: NetworkPolicy
e' trattato in DO280 "Network Security", aggiunto qui per coprire piu'
terreno rispetto al solo programma DO180).
Limita il traffico in ingresso a un'app con una NetworkPolicy.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, oc, oc_get_json, reset_project, run_cli

CHAPTER = "Extra — Rete avanzata"
TITLE = "Crea una NetworkPolicy"
PROJECT = "training-network-networkpolicy"
IMAGE = "registry.access.redhat.com/ubi9/httpd-24:latest"
PORT = 8080

TASK = f"""\
Nel progetto "{PROJECT}" trovi il Deployment "app" (label app=app,
ascolta sulla porta {PORT}). Crea una NetworkPolicy chiamata
"allow-app" che permetta il traffico in ingresso verso i pod con label
app=app sulla porta {PORT}, da qualunque namespace.

Salva questo contenuto in networkpolicy.yaml:

  apiVersion: networking.k8s.io/v1
  kind: NetworkPolicy
  metadata:
    name: allow-app
  spec:
    podSelector:
      matchLabels:
        app: app
    ingress:
      - from:
          - namespaceSelector: {{}}
        ports:
          - protocol: TCP
            port: {PORT}

Poi applicalo (1 comando):
  oc apply -f networkpolicy.yaml -n {PROJECT}
"""


def setup():
    reset_project(PROJECT)
    oc("create", "deployment", "app", f"--image={IMAGE}", "-n", PROJECT, check=True)


def grade():
    netpol = oc_get_json("networkpolicy", "allow-app", "-n", PROJECT)

    with GradingStep("La NetworkPolicy allow-app esiste") as step:
        if not netpol:
            step.fail("NetworkPolicy 'allow-app' non trovata")

    with GradingStep("Seleziona i pod con label app=app") as step:
        if not netpol:
            step.fail("NetworkPolicy 'allow-app' non trovata")
        else:
            selector = netpol.get("spec", {}).get("podSelector", {}).get("matchLabels", {})
            if selector.get("app") != "app":
                step.add_error(f"podSelector.matchLabels = {selector!r}, attesa app=app")

    with GradingStep(f"Permette ingresso sulla porta {PORT}") as step:
        if not netpol:
            step.fail("NetworkPolicy 'allow-app' non trovata")
        else:
            rules = netpol.get("spec", {}).get("ingress", []) or []
            found = any(
                p.get("port") == PORT
                for rule in rules
                for p in rule.get("ports", []) or []
            )
            if not found:
                step.add_error(f"Nessuna regola ingress apre la porta {PORT} (regole trovate: {rules})")


if __name__ == "__main__":
    run_cli(setup, grade)
