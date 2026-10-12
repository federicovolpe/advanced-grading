"""
Utilita' condivise dalla traccia "try-exam-ex280" (simulazione d'esame
EX280, Red Hat Certified OpenShift Administrator). Il file inizia con '_'
cosi' training_monitor.py non lo carica come esercizio.

A differenza delle altre tracce, qui lo stato da gradare e' in buona parte
CLUSTER-WIDE (identity provider, ClusterRoleBinding, label sui nodi): serve
un login come utente con cluster-admin (in questo classroom: admin), e ogni
cleanup() deve riportare il cluster allo stato di partenza del classroom —
e' un ambiente condiviso con le altre tracce (es. DO180 crea progetti come
developer: se self-provisioner restasse tolto, si romperebbe tutto).

Due accorgimenti per la concorrenza col monitor: training_monitor.py lancia
il cleanup() dell'esercizio che si lascia in un thread, IN PARALLELO al
setup() di quello successivo. Diversi esercizi condividono lo stesso
progetto (practice3, console-review: nomi del tema d'esame), quindi:
- setup()/cleanup() girano sotto track_lock() (flock), mai sovrapposti;
- progetti e gruppi creati da un setup() portano l'etichetta OWNER_LABEL con
  lo slug dell'esercizio, e un cleanup() cancella solo cio' che e' suo — non
  il progetto appena ricreato dal setup() dell'esercizio successivo.
"""
import contextlib
import fcntl
import glob
import json
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import (  # noqa: E402,F401
    GradingStep, oc, oc_get_json, project_exists, apply_yaml, wait_for,
    deployment_container, parse_quantity, run_cli,
)

CHAPTER = "Try exam EX280"

# Il primo setup() cancella/ricrea progetti e puo' aspettare che OAuth
# termini un rollout: piu' dei 180s di default del monitor.
SETUP_TIMEOUT = 300

OWNER_LABEL = "ex280-training/owner"
LOCK_FILE = os.path.expanduser("~/.local/share/training/.ex280.lock")
STATE_DIR = os.path.expanduser("~/.local/share/training/ex280-state")

# Identity provider HTPasswd del classroom (vedi do280/common/ocp/steps.py).
LOCALUSERS = "localusers"
CONFIG_NS = "openshift-config"

# Immagini presenti nel registry del classroom (le stesse usate da DO280).
IMG_HELLO = "registry.lab.example.com:8443/redhattraining/hello-world-nginx:v1.0"
IMG_HTTPD = "registry.lab.example.com:8443/ubi9/httpd-24:latest"


@contextlib.contextmanager
def track_lock():
    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
    with open(LOCK_FILE, "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def require_cluster_admin():
    """In setup(): senza cluster-admin quasi nulla di questa traccia si puo'
    preparare ne' gradare (impersonazione, OAuth, nodi)."""
    result = oc("auth", "can-i", "*", "*", "--all-namespaces")
    if result.stdout.strip() != "yes":
        raise RuntimeError(
            "Serve un login come utente cluster-admin, es.:\n"
            "  oc login -u admin -p redhatocp https://api.lab.example.com:6443"
        )


def apps_domain():
    """Dominio wildcard delle route (es. apps.lab.example.com). Letto dal
    cluster perche' il tema d'esame usa apps.ocp4.example.com, che in
    questo classroom non esiste."""
    try:
        result = subprocess.run(
            ["oc", "get", "ingresses.config.openshift.io", "cluster",
             "-o", "jsonpath={.spec.domain}"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        pass
    return "apps.lab.example.com"


def can_i(verb, resource, user, groups=(), namespace=None):
    """`oc auth can-i` impersonando un utente (serve cluster-admin). Gli
    utenti che si autenticano via OAuth appartengono sempre a questi due
    gruppi virtuali: senza passarli l'impersonazione non vedrebbe i permessi
    concessi a system:authenticated:oauth (es. self-provisioner)."""
    args = ["auth", "can-i", verb, resource, f"--as={user}"]
    for g in groups or ("system:authenticated", "system:authenticated:oauth"):
        args.append(f"--as-group={g}")
    if namespace:
        args += ["-n", namespace]
    return oc(*args).stdout.strip() == "yes"


# --- Progetti e gruppi "di proprieta'" di un esercizio --------------------

def _delete_project_wait(name, timeout=120):
    if project_exists(name):
        oc("delete", "project", name, "--wait=false")
    deadline = time.time() + timeout
    while project_exists(name) and time.time() < deadline:
        time.sleep(2)


def reset_owned_project(name, owner):
    """Cancella il progetto (di chiunque sia) e lo ricrea vuoto, marcato
    come di proprieta' di 'owner'. Da chiamare sotto track_lock()."""
    _delete_project_wait(name)
    oc("new-project", name, "--skip-config-write", check=True)
    oc("label", "namespace", name, f"{OWNER_LABEL}={owner}", "--overwrite", check=True)
    wait_for(lambda: oc_get_json("serviceaccount", "default", "-n", name), timeout=30, interval=1)


def delete_owned_project(name, owner):
    ns = oc_get_json("namespace", name)
    if ns and (ns["metadata"].get("labels") or {}).get(OWNER_LABEL) == owner:
        oc("delete", "project", name, "--wait=false")


def ensure_absent_project(name):
    _delete_project_wait(name)


def set_owned_group(name, owner, users):
    oc("delete", "group", name, "--ignore-not-found")
    oc("adm", "groups", "new", name, *users, check=True)
    oc("label", "group", name, f"{OWNER_LABEL}={owner}", "--overwrite", check=True)


def delete_owned_group(name, owner):
    group = oc_get_json("group", name)
    if group and (group["metadata"].get("labels") or {}).get(OWNER_LABEL) == owner:
        oc("delete", "group", name, "--ignore-not-found")


# --- Secret HTPasswd -------------------------------------------------------

def read_htpasswd(secret, namespace=CONFIG_NS):
    """Ritorna {utente: hash} dal secret (chiave 'htpasswd'), o None se il
    secret o la chiave non esistono."""
    result = oc("extract", f"secret/{secret}", "-n", namespace, "--keys=htpasswd", "--to=-")
    if result.returncode != 0:
        return None
    entries = {}
    for line in result.stdout.splitlines():
        if ":" in line:
            user, _, pw_hash = line.strip().partition(":")
            entries[user] = pw_hash
    return entries


def htpasswd_ok(pw_hash, user, password):
    """Verifica la password con `htpasswd -v` (httpd-tools): gestisce tutti
    i formati che lo studente puo' aver generato (bcrypt -B, apr1, sha)."""
    with tempfile.NamedTemporaryFile("w", suffix=".htpasswd") as fh:
        fh.write(f"{user}:{pw_hash}\n")
        fh.flush()
        result = subprocess.run(["htpasswd", "-vb", fh.name, user, password],
                                capture_output=True, text=True)
    return result.returncode == 0


def write_htpasswd(secret, entries, namespace=CONFIG_NS):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "htpasswd")
        with open(path, "w") as fh:
            fh.writelines(f"{u}:{h}\n" for u, h in entries.items())
        oc("set", "data", f"secret/{secret}", "-n", namespace,
           f"--from-file=htpasswd={path}", check=True)


def htpasswd_hash(user, password):
    result = subprocess.run(["htpasswd", "-nbB", user, password],
                            capture_output=True, text=True, check=True)
    return result.stdout.strip().partition(":")[2]


def check_htpasswd_users(secret, users, password):
    """Un check per utente: presente nel secret, con quella password."""
    entries = read_htpasswd(secret)
    for user in users:
        with GradingStep(f"L'utente {user} e' nel secret {secret} con password {password}") as step:
            if entries is None:
                step.fail(f"Secret '{secret}' (chiave htpasswd) non trovato in {CONFIG_NS}")
            elif user not in entries:
                step.fail(f"Utente '{user}' assente (utenti: {sorted(entries)})")
            elif not htpasswd_ok(entries[user], user, password):
                step.add_error("la password non corrisponde")
    return entries


# --- OAuth -----------------------------------------------------------------

def oauth_identity_providers():
    oauth = oc_get_json("oauth", "cluster") or {}
    return (oauth.get("spec") or {}).get("identityProviders") or []


def check_authentication_operator_settled():
    """Dopo una modifica a OAuth o a un secret HTPasswd l'operatore
    authentication ridistribuisce i pod oauth-openshift: finche' e'
    Progressing il login dei nuovi utenti puo' non funzionare ancora."""
    with GradingStep("Il rollout di oauth-openshift e' completato") as step:
        co = oc_get_json("clusteroperator", "authentication")
        conds = {c["type"]: c["status"] for c in ((co or {}).get("status") or {}).get("conditions", [])}
        if conds.get("Available") != "True":
            step.add_error("clusteroperator authentication non Available")
        if conds.get("Progressing") != "False":
            step.add_error("clusteroperator authentication ancora Progressing (attendi il rollout)")


# --- Stato "gia' visto" per i compiti che un passo successivo modifica ----

def ever_seen(slug, key, currently_true):
    path = os.path.join(STATE_DIR, f"{slug}.{key}.seen")
    if currently_true:
        os.makedirs(STATE_DIR, exist_ok=True)
        open(path, "w").close()
        return True
    return os.path.exists(path)


def reset_seen(slug):
    for path in glob.glob(os.path.join(STATE_DIR, f"{slug}.*")):
        os.remove(path)


def save_state(slug, key, value):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(os.path.join(STATE_DIR, f"{slug}.{key}.json"), "w") as fh:
        json.dump(value, fh)


def load_state(slug, key, default=None):
    try:
        with open(os.path.join(STATE_DIR, f"{slug}.{key}.json")) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


# --- Check ricorrenti --------------------------------------------------------

def http_status(url, timeout=10):
    result = subprocess.run(
        ["curl", "-sk", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", str(timeout), url],
        capture_output=True, text=True,
    )
    return result.stdout.strip() or "000"


def check_project_exists(name):
    with GradingStep(f"Il progetto {name} esiste") as step:
        if not project_exists(name):
            step.fail(f"Progetto '{name}' non trovato")


def find_rolebinding(namespace, role, kind, name):
    """Cerca per contenuto, non per nome: `oc adm policy` e la console
    generano nomi diversi (es. 'view', 'edit-0', 'rolebinding-xyz')."""
    rbs = oc_get_json("rolebinding", "-n", namespace) or {}
    for rb in rbs.get("items", []):
        ref = rb.get("roleRef") or {}
        if ref.get("name") != role:
            continue
        for s in rb.get("subjects") or []:
            if s.get("kind") == kind and s.get("name") == name:
                return rb
    return None


def ready_replicas(namespace, deployment):
    dep = oc_get_json("deployment", deployment, "-n", namespace)
    return ((dep or {}).get("status") or {}).get("readyReplicas") or 0, dep


def service_has_endpoints(namespace, service):
    ep = oc_get_json("endpoints", service, "-n", namespace) or {}
    return any(s.get("addresses") for s in ep.get("subsets") or [])
