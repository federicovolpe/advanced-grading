#!/usr/bin/env python3
"""
Grading "custom" per la lab guidata (Guided Exercise) openshift-lab,
sprovvista di `lab grade` ufficiale (la classe OpenShiftLab nel pacchetto
do188 implementa solo start()/finish(), non grade()). A differenza degli
altri esercizi di questo corso, qui si usa OpenShift (oc), non Podman
standalone.

La specifica viene dagli stessi watch_items che start() usa per il monitor
live (vedi do188/openshift-lab.py) e da materials/solutions/openshift-lab/
(deployment.yaml, service.yaml): lo studente deve creare un Deployment e un
Service "quotes-api" nel progetto "ocp-lab" (attributo self.project, diverso
dal nome esercizio __LAB__). Il progetto "ocp-lab" e' creato da start() e vi
viene gia' distribuita automaticamente (via materials/kubefiles/podman-ui/)
una UI "quotes-ui" con una Route senza host esplicito, che OpenShift espone
quindi sull'host di default "quotes-ui-ocp-lab.apps.ocp4.example.com" — da
qui il valore hardcoded self.quotes_path nel modulo ufficiale.

Uso: openshift-lab.py [nome-progetto]   (default: "ocp-lab")
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, http_get, oc_get_json, project_exists

LAB_NAME = "openshift-lab"
DEFAULT_PROJECT = "ocp-lab"
QUOTES_POD_SUBSTRING = "quotes-api"
QUOTES_SVC = "quotes-api"
QUOTES_SVC_PORT = 8080
QUOTES_UI_ROUTE_HOST = "quotes-ui-ocp-lab.apps.ocp4.example.com"


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROJECT
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto '{project}' esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")
            # non serve un return anticipato: senza progetto oc_get_json
            # ritorna None e ogni step successivo fallisce da solo

    with GradingStep(f"Un pod '{QUOTES_POD_SUBSTRING}' e' online nel progetto") as step:
        pods = oc_get_json("pods", "-n", project)
        items = (pods or {}).get("items", [])
        matching = [
            p for p in items
            if QUOTES_POD_SUBSTRING in p.get("metadata", {}).get("name", "")
        ]
        if not matching:
            step.fail(f"Nessun pod con nome contenente '{QUOTES_POD_SUBSTRING}' trovato")
        elif not any(p.get("status", {}).get("phase") == "Running" for p in matching):
            step.add_error(f"Il pod '{QUOTES_POD_SUBSTRING}' esiste ma non e' in stato Running")

    with GradingStep(f"Il service '{QUOTES_SVC}' esiste con la porta {QUOTES_SVC_PORT}") as step:
        svc = oc_get_json("service", QUOTES_SVC, "-n", project)
        if not svc:
            step.fail(f"Service '{QUOTES_SVC}' non trovato")
        else:
            ports = [p.get("port") for p in svc.get("spec", {}).get("ports", [])]
            if QUOTES_SVC_PORT not in ports:
                step.add_error(f"Il service non pubblica la porta {QUOTES_SVC_PORT} (trovate: {ports})")

    with GradingStep(f"Il service '{QUOTES_SVC}' instrada verso il pod '{QUOTES_POD_SUBSTRING}'") as step:
        # Usiamo gli Endpoints (come get_svc_targets nel modulo ufficiale):
        # e' l'evidenza che il selector del Service combacia con un pod
        # realmente pronto (Ready), non solo con le label sulla carta.
        endpoints = oc_get_json("endpoints", QUOTES_SVC, "-n", project)
        target_names = []
        for subset in (endpoints or {}).get("subsets", []):
            for addr in subset.get("addresses", []):
                target_names.append(addr.get("targetRef", {}).get("name", ""))
        if not any(QUOTES_POD_SUBSTRING in name for name in target_names):
            step.fail(
                f"Il service '{QUOTES_SVC}' non instrada verso alcun pod "
                f"'{QUOTES_POD_SUBSTRING}' pronto (endpoints: {target_names})"
            )

    with GradingStep(f"http://{QUOTES_UI_ROUTE_HOST}/ risponde") as step:
        ok, body = http_get(f"http://{QUOTES_UI_ROUTE_HOST}:80/")
        if not ok:
            step.fail(f"GET su http://{QUOTES_UI_ROUTE_HOST}/ non ha risposto correttamente")


if __name__ == "__main__":
    main()
