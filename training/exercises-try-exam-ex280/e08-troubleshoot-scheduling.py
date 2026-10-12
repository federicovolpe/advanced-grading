"""
Try-exam EX280, 8 — troubleshooting: pod che non vengono schedulati e
service senza endpoint (tema: "TROUBLESHOOTING").

Il tema annotato elenca tre guasti: taint sul nodo, node selector che non
corrisponde a nessun nodo, selector del service che non corrisponde ai
pod. Il taint e' stato lasciato fuori di proposito: questo classroom e' un
Single Node OpenShift, e un taint NoSchedule sull'unico nodo blocca la
schedulazione di QUALUNQUE nuovo pod senza toleration (anche quelli di
sistema, es. un rollout di oauth) — troppo rischioso su un cluster
condiviso. Restano gli altri due, entrambi verificati dal risultato:
accettati sia "etichetta il nodo" sia "togli il node selector".

La label usata ha un valore specifico dell'esercizio: cleanup() toglie la
label solo dai nodi che hanno ESATTAMENTE quel valore, mai altre label.
"""
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ex280_common import (
    CHAPTER, SETUP_TIMEOUT, IMG_HELLO, GradingStep, oc, oc_get_json, track_lock,
    require_cluster_admin, reset_owned_project, delete_owned_project,
    ready_replicas, service_has_endpoints, http_status, run_cli,
)

SLUG = "e08"
PROJECT = "practice-troubles"
APP = "hello"
NODE_LABEL_KEY = "workload"
NODE_LABEL_VALUE = "ex280-web"

TITLE = "8) Troubleshooting: scheduling e service"
TASK = f"""\
Nel progetto {PROJECT} l'applicazione {APP} non funziona: la sua
route non risponde.

  - Trova e correggi i problemi, senza ricreare deployment, service o
    route.
  - L'applicazione deve rispondere sulla route {APP}.
"""

SOLUTION = f"""\
oc project {PROJECT}
oc get pods                               # Pending
oc get events --sort-by=.lastTimestamp    # "didn't match Pod's node affinity/selector"
oc describe pod <pod>                     # Node-Selectors: {NODE_LABEL_KEY}={NODE_LABEL_VALUE}
oc get nodes --show-labels

# o si etichetta il nodo...
oc label node <nodo> {NODE_LABEL_KEY}={NODE_LABEL_VALUE}
# ...oppure si toglie il selector dal deployment:
#   oc patch deployment {APP} --type=json \\
#     -p '[{{"op":"remove","path":"/spec/template/spec/nodeSelector"}}]'

oc get endpoints {APP}                    # vuoto anche con il pod Running
oc describe service {APP}                 # Selector: app=helo
oc get pods --show-labels                 # app=hello
oc set selector service {APP} app={APP}

curl http://$(oc get route {APP} -o jsonpath='{{.spec.host}}')

Altro guasto possibile all'esame (non riprodotto qui): un taint sul nodo.
  oc describe node <nodo> | grep -i taint
  oc adm taint node <nodo> <chiave>-
"""


def _remove_node_label():
    oc("label", "node", "-l", f"{NODE_LABEL_KEY}={NODE_LABEL_VALUE}", f"{NODE_LABEL_KEY}-")


def setup():
    require_cluster_admin()
    with track_lock():
        _remove_node_label()
        reset_owned_project(PROJECT, SLUG)
        oc("create", "deployment", APP, f"--image={IMG_HELLO}", "-n", PROJECT, check=True)
        oc("patch", "deployment", APP, "-n", PROJECT, "--type=merge", "-p", json.dumps(
            {"spec": {"template": {"spec": {"nodeSelector": {NODE_LABEL_KEY: NODE_LABEL_VALUE}}}}}
        ), check=True)
        oc("expose", "deployment", APP, "--port=8080", "-n", PROJECT, check=True)
        oc("set", "selector", "service", APP, "app=helo", "-n", PROJECT, check=True)
        oc("expose", "service", APP, "-n", PROJECT, check=True)


def grade():
    ready, dep = ready_replicas(PROJECT, APP)
    with GradingStep(f"Il deployment {APP} ha almeno un pod pronto") as step:
        if not dep:
            step.fail(f"Deployment '{APP}' non trovato (non andava ricreato)")
        elif not ready:
            step.add_error("nessun pod pronto (oc get events)")

    with GradingStep(f"Il service {APP} ha endpoint") as step:
        if not oc_get_json("service", APP, "-n", PROJECT):
            step.fail(f"Service '{APP}' non trovato")
        elif not service_has_endpoints(PROJECT, APP):
            step.add_error("nessun endpoint: il selector non trova pod pronti")

    with GradingStep(f"La route {APP} risponde 200") as step:
        route = oc_get_json("route", APP, "-n", PROJECT)
        if not route:
            step.fail(f"Route '{APP}' non trovata")
        else:
            code = http_status(f"http://{route['spec'].get('host')}/")
            if code != "200":
                step.add_error(f"HTTP {code}")


def cleanup():
    with track_lock():
        delete_owned_project(PROJECT, SLUG)
        _remove_node_label()


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
