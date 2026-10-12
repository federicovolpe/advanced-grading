"""
Try-exam EX280, 5 — permessi a livello cluster
(tema: "CONFIGURE CLUSTER PERMISSION").

Si grada il RISULTATO con `oc auth can-i` impersonando gli utenti (serve
cluster-admin), non il modo: rimuovere il gruppo dalla ClusterRoleBinding
self-provisioners o cancellarla del tutto vanno bene entrambi. Non serve
che gli utenti esistano (l'es. 4 li crea, ma qui l'impersonazione basta).

"pippo non deve poter modificare il cluster" e' un requisito negativo: gli
appunti gli danno il ruolo view, ma il check verifica solo che non possa
modificare nulla a livello cluster.

ATTENZIONE: e' l'unico esercizio che cambia un default che le ALTRE tracce
usano (developer crea i propri progetti in DO180). cleanup() ripristina la
ClusterRoleBinding self-provisioners com'e' su un cluster appena installato
e toglie i ruoli dati agli utenti dell'esercizio. Se la finestra viene
chiusa male, `training cleanup try-exam-ex280` fa la stessa cosa.
"""
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ex280_common import (
    CHAPTER, SETUP_TIMEOUT, GradingStep, oc, oc_get_json, apply_yaml, track_lock,
    require_cluster_admin, can_i, run_cli,
)

SLUG = "e05"
USERS = ["wozniak", "jobs", "pippo", "pluto"]

TITLE = "5) Permessi cluster: self-provisioner e cluster-admin"
PROJECT = None

TASK = """\
  - Nessun utente, tranne quelli indicati sotto, deve poter creare
    progetti.
  - L'utente wozniak deve poter amministrare il cluster.
  - L'utente jobs deve poter creare progetti.
  - L'utente pippo non deve poter modificare il cluster.

La modifica deve sopravvivere a un riavvio dell'API server.
"""

SOLUTION = """\
oc login -u admin -p redhatocp

# nessuno crea progetti: togli il gruppo degli utenti autenticati
oc describe clusterrolebinding self-provisioners
oc annotate clusterrolebinding self-provisioners --overwrite \\
    rbac.authorization.kubernetes.io/autoupdate=false
oc adm policy remove-cluster-role-from-group self-provisioner \\
    system:authenticated:oauth
#   (equivalente da console: User Management -> RoleBindings ->
#    self-provisioners -> Delete)

oc adm policy add-cluster-role-to-user cluster-admin wozniak
oc adm policy add-cluster-role-to-user self-provisioner jobs
oc adm policy add-cluster-role-to-user view pippo     # sola lettura

Verifica (impersonando):
  oc auth can-i create projectrequests --as=developer --as-group=system:authenticated:oauth
  oc auth can-i create projectrequests --as=jobs --as-group=system:authenticated:oauth
  oc auth can-i '*' '*' --as=wozniak

Perche' l'annotazione: senza autoupdate=false l'API server ricrea il
binding di default al prossimo riavvio, e tutti tornano a creare progetti.
"""

DEFAULT_SELF_PROVISIONERS = """\
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: self-provisioners
  annotations:
    rbac.authorization.kubernetes.io/autoupdate: "true"
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: self-provisioner
subjects:
- apiGroup: rbac.authorization.k8s.io
  kind: Group
  name: system:authenticated:oauth
"""


def _reset():
    with track_lock():
        apply_yaml(DEFAULT_SELF_PROVISIONERS)
        crbs = (oc_get_json("clusterrolebinding") or {}).get("items", [])
        for crb in crbs:
            subjects = crb.get("subjects") or []
            ours = [s for s in subjects if s.get("kind") == "User" and s.get("name") in USERS]
            if not ours:
                continue
            name = crb["metadata"]["name"]
            if len(ours) == len(subjects):
                oc("delete", "clusterrolebinding", name, "--ignore-not-found")
            else:
                keep = [s for s in subjects if s not in ours]
                oc("patch", "clusterrolebinding", name, "--type=merge",
                   "-p", json.dumps({"subjects": keep}), check=True)


def setup():
    require_cluster_admin()
    _reset()


def grade():
    with GradingStep("Gli utenti autenticati non possono creare progetti (es. developer)") as step:
        for user in ("developer", "pippo", "pluto"):
            if can_i("create", "projectrequests.project.openshift.io", user):
                step.add_error(f"{user} puo' ancora creare progetti")

    with GradingStep("jobs puo' creare progetti") as step:
        if not can_i("create", "projectrequests.project.openshift.io", "jobs"):
            step.add_error("jobs non puo' creare progetti")

    with GradingStep("wozniak puo' amministrare il cluster") as step:
        if not can_i("*", "*", "wozniak"):
            step.add_error("wozniak non ha cluster-admin")

    with GradingStep("pippo non puo' modificare il cluster") as step:
        for verb, resource in (("create", "clusterrolebindings"), ("patch", "nodes"),
                               ("delete", "namespaces"), ("create", "projectrequests.project.openshift.io")):
            if can_i(verb, resource, "pippo"):
                step.add_error(f"pippo puo' {verb} {resource}")

    with GradingStep("La modifica sopravvive a un riavvio dell'API server") as step:
        crb = oc_get_json("clusterrolebinding", "self-provisioners")
        if not crb:
            # Un binding di default mancante viene ricreato dalla
            # riconciliazione RBAC all'avvio dell'API server.
            step.add_error("self-provisioners cancellata: al riavvio verrebbe ricreata "
                           "(annota autoupdate=false e togli il gruppo, invece)")
        else:
            ann = (crb["metadata"].get("annotations") or {}).get(
                "rbac.authorization.kubernetes.io/autoupdate")
            if ann != "false":
                step.add_error("self-provisioners senza autoupdate=false: verra' ripristinato")


def cleanup():
    _reset()


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
