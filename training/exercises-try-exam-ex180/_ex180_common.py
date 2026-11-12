"""
Utilita' condivise dalla traccia "try-exam ex180" (simulazione d'esame
DO180/EX180, facsimile annotato dall'utente). Il file inizia con '_' cosi'
training_monitor.py non lo carica come esercizio.

Differenze rispetto alle altre simulazioni:
- niente stato cluster-wide: basta il login come `developer` (self-provisioner)
  del classroom DO180, come per la traccia DO180 di training;
- il tema e' una sequenza di compiti che nell'esame si appoggiano l'uno
  sull'altro (configmap -> secret -> deployment -> PVC -> mount ...). Qui ogni
  esercizio ha il PROPRIO progetto (ex180-eNN) e il suo setup() crea gia' tutto
  cio' che l'esercizio precedente avrebbe prodotto: nessun esercizio dipende
  dal fatto che lo studente abbia risolto bene quello prima, e il cleanup() di
  uno (che il monitor lancia IN PARALLELO al setup() del successivo) non puo'
  rompere il setup del successivo: i progetti hanno nomi diversi, quindi non
  servono il flock e le label di proprieta' della traccia ex280;
- la "macchina M" del tema (file index.html, dump da caricare) e' la
  workstation locale: i file di partenza stanno sotto BASE_DIR. index.html e'
  scritto da piu' setup() (e03, e04) e non viene mai cancellato dai cleanup(),
  proprio per non creare corse fra cleanup e setup paralleli;
- nomi delle risorse, valori, percorsi e immagine sono scelte NOSTRE (il tema
  non ne da' nessuno): ogni esercizio lo dichiara nel docstring.
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import (  # noqa: E402,F401
    GradingStep, oc, oc_get_json, project_exists, reset_project, apply_yaml,
    wait_for, deployment_container, parse_quantity, find_pvc_name_for_deployment,
    find_running_pod, run_cli,
)

CHAPTER = "Try exam EX180"

# Il primo setup() puo' dover attendere la cancellazione di un progetto
# rimasto da un tentativo precedente (reset_project aspetta fino a 90s).
# NB: training_monitor.py legge SETUP_TIMEOUT dal namespace del FILE
# ESERCIZIO, quindi ogni esercizio deve importarlo esplicitamente.
SETUP_TIMEOUT = 240

# Immagine gia' usata dagli esercizi DO180 di training (raggiungibile dal
# classroom, ascolta sulla porta 8080 senza root). Scelta nostra: il tema non
# dice quale applicazione deployare.
IMG_HTTPD = "registry.access.redhat.com/ubi9/httpd-24:latest"
HTTP_PORT = 8080

# Storage class "specifica" del classroom (la stessa dell'esercizio c5-05,
# verificata dal vivo su RHOCP 4.18). Il tema non dice quale.
STORAGE_CLASS = "lvms-vg1"

# "Macchina M": file di partenza dell'esame.
BASE_DIR = os.path.expanduser("~/try-exam-ex180")
INDEX_HTML = os.path.join(BASE_DIR, "index.html")
INDEX_CONTENT = "<html><body><h1>Messaggio riservato - EX180</h1></body></html>\n"

STATE_DIR = os.path.expanduser("~/.local/share/training/ex180-state")

LOGIN_HINT = "oc login -u developer -p developer https://api.<dominio-del-classroom>:6443"


# --- File locali -----------------------------------------------------------

def write_index_html():
    """Crea ~/try-exam-ex180/index.html (il file 'presente sulla macchina M').
    Scrittura atomica (file temporaneo + rename): e03 ed e04 lo riscrivono
    nei loro setup(), e un grade concorrente non deve mai leggerlo a meta'."""
    os.makedirs(BASE_DIR, exist_ok=True)
    tmp = f"{INDEX_HTML}.tmp-{os.getpid()}"
    with open(tmp, "w") as fh:
        fh.write(INDEX_CONTENT)
    os.replace(tmp, INDEX_HTML)
    return INDEX_HTML


def read_index_html():
    """Contenuto ATTUALE del file: lo studente puo' averlo modificato, il
    secret va confrontato con quello che c'e' ora sul disco."""
    try:
        with open(INDEX_HTML) as fh:
            return fh.read()
    except OSError:
        return None


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def remove_path(path):
    """rm -f di un file (le directory si tolgono con shutil.rmtree)."""
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


# --- Progetto e login --------------------------------------------------------

def oc_logged_in():
    return oc("whoami").returncode == 0


def check_project(project):
    """Primo check di ogni esercizio con un progetto: distingue "oc non e'
    collegato al cluster" (tutti gli altri check fallirebbero con un
    fuorviante "non trovato") da "progetto assente"."""
    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            if not oc_logged_in():
                step.fail(f"oc non e' collegato a nessun cluster: {LOGIN_HINT}")
            else:
                step.fail(f"progetto '{project}' non trovato: ricomincia l'esercizio "
                          "(il setup lo crea)")


def delete_project(name):
    if project_exists(name):
        oc("delete", "project", name, "--wait=false")


def create_httpd_deployment(name, project, *extra):
    oc("create", "deployment", name, f"--image={IMG_HTTPD}", "-n", project, *extra, check=True)


# --- Lettura di Deployment e pod --------------------------------------------

def pod_spec(obj):
    """spec del pod: di un Deployment (spec.template.spec) o di un Pod (spec)."""
    spec = (obj or {}).get("spec") or {}
    if "template" in spec:
        return (spec.get("template") or {}).get("spec") or {}
    return spec


def _norm_path(path):
    return (path or "").rstrip("/") or "/"


def _volume_refs(volume, kind, name):
    """True se il volume (anche 'projected') punta alla risorsa `name` di tipo
    `kind` ('secret' | 'configMap' | 'persistentVolumeClaim')."""
    key = {"secret": "secretName", "configMap": "name", "persistentVolumeClaim": "claimName"}[kind]
    if (volume.get(kind) or {}).get(key) == name:
        return True
    if kind in ("secret", "configMap"):
        for src in (volume.get("projected") or {}).get("sources") or []:
            if (src.get(kind) or {}).get("name") == name:
                return True
    return False


def volume_mounts(obj, kind, name):
    """Lista di (nome container, mountPath, subPath) dei volumi di tipo
    `kind` che puntano alla risorsa `name`. Si cerca per contenuto: il nome
    del volume lo sceglie lo studente (o `oc set volume`)."""
    spec = pod_spec(obj)
    vol_names = {v.get("name") for v in spec.get("volumes") or [] if _volume_refs(v, kind, name)}
    out = []
    for c in spec.get("containers") or []:
        for vm in c.get("volumeMounts") or []:
            if vm.get("name") in vol_names:
                out.append((c.get("name"), vm.get("mountPath"), vm.get("subPath")))
    return out


def volume_mount_path(obj, kind, name):
    """mountPath (normalizzato, senza '/' finale) del primo montaggio della
    risorsa `name`, o None."""
    mounts = volume_mounts(obj, kind, name)
    return _norm_path(mounts[0][1]) if mounts else None


def mounted_at(obj, kind, name, path):
    """Nome del container che monta la risorsa `name` esattamente su `path`
    (tollera la '/' finale), o None."""
    for cname, mpath, _sub in volume_mounts(obj, kind, name):
        if _norm_path(mpath) == _norm_path(path):
            return cname
    return None


def configmap_used(obj, name):
    """La ConfigMap e' usata in uno dei modi ammessi: envFrom,
    env.valueFrom.configMapKeyRef oppure volume (anche projected)."""
    spec = pod_spec(obj)
    if any(_volume_refs(v, "configMap", name) for v in spec.get("volumes") or []):
        return True
    for c in spec.get("containers") or []:
        for ef in c.get("envFrom") or []:
            if (ef.get("configMapRef") or {}).get("name") == name:
                return True
        for e in c.get("env") or []:
            if ((e.get("valueFrom") or {}).get("configMapKeyRef") or {}).get("name") == name:
                return True
    return False


def available_replicas(dep):
    return ((dep or {}).get("status") or {}).get("availableReplicas") or 0


def _selector(dep):
    labels = (((dep or {}).get("spec") or {}).get("selector") or {}).get("matchLabels") or {}
    return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))


def _pod_ready(pod):
    if pod.get("metadata", {}).get("deletionTimestamp"):
        return False
    if pod.get("status", {}).get("phase") != "Running":
        return False
    return any(c.get("type") == "Ready" and c.get("status") == "True"
               for c in pod.get("status", {}).get("conditions") or [])


def ready_pods(dep, namespace, predicate=None):
    """Pod del Deployment Running, Ready, non in terminazione e (se dato)
    che soddisfano predicate(pod). Serve a gradare la versione NUOVA del
    deployment: dopo `oc set volume/probe/resources` il pod vecchio resta
    disponibile finche' il nuovo non e' pronto (RollingUpdate,
    maxUnavailable 0 con una replica), quindi status.availableReplicas da
    solo direbbe PASS anche se il pod nuovo non parte mai (es. PVC
    sbagliata, probe rotta)."""
    if not dep:
        return []
    sel = _selector(dep)
    args = ["pods", "-n", namespace] + (["-l", sel] if sel else [])
    pods = (oc_get_json(*args) or {}).get("items", [])
    return [p for p in pods if _pod_ready(p) and (predicate is None or predicate(p))]


def secret_value(secret, key):
    """Valore decodificato (str) della chiave di un Secret, o None."""
    import base64
    raw = ((secret or {}).get("data") or {}).get(key)
    if raw is None:
        return None
    try:
        return base64.b64decode(raw).decode(errors="replace")
    except (ValueError, TypeError):
        return None


def pod_exec(namespace, pod, container, *command, timeout=20):
    """`oc exec` in sola lettura. Ritorna (stdout, errore): errore e' None
    se il comando e' riuscito, altrimenti un messaggio leggibile (mai
    un'eccezione: il grade deve stampare un FAIL, non un traceback)."""
    import subprocess
    args = ["oc", "exec", pod, "-n", namespace]
    if container:
        args += ["-c", container]
    args += ["--", *command]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, f"oc exec non ha risposto entro {timeout}s"
    except OSError as exc:
        return None, f"oc exec non eseguibile: {exc}"
    if r.returncode != 0:
        return None, f"oc exec fallito (rc={r.returncode}): {(r.stderr or r.stdout).strip()[:200]}"
    return r.stdout, None
