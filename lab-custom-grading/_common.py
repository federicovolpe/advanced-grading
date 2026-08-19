"""
Utilita' condivise per gli script di grading "custom" (esercizi DO180 sprovvisti
di un `lab grade` ufficiale). Il formato di stampa (PASS/FAIL <titolo> seguito
da dettagli indentati di 8 spazi) e' compatibile con il parser di
~/.local/bin/lab_grade_monitor.py, cosi' i semafori funzionano anche qui.
"""

import json
import os
import subprocess


class GradingStep:
    """Riproduce grossolanamente labs.ui.GradingStep usato nei grading
    ufficiali Red Hat Training (vedi do180/reliability-review.py): un check
    e' FAIL se viene chiamato add_error()/fail() al suo interno, altrimenti
    e' PASS."""

    def __init__(self, title):
        self.title = title
        self.errors = []
        self.failed = False

    def add_error(self, message):
        self.errors.append(message)

    def fail(self, message=None):
        self.failed = True
        if message:
            self.errors.append(message)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        status = "FAIL" if (self.failed or self.errors) else "PASS"
        print(f"{status} {self.title}")
        for e in self.errors:
            print(f"        - {e}")
        return False


def oc_get_json(*args):
    """Esegue `oc get <args> -o json` e ritorna il dict, o None se la
    risorsa non esiste o il comando fallisce."""
    result = subprocess.run(
        ["oc", "get", *args, "-o", "json"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def project_exists(name):
    result = subprocess.run(["oc", "get", "project", name], capture_output=True)
    return result.returncode == 0


# --- Helper per DO432 (RHACM - multicluster management): il corso governa
# DUE cluster OpenShift distinti, hub e "managed" (managed-cluster). La
# sessione oc corrente dello studente puo' essere loggata sull'uno o
# sull'altro in un dato momento (la guida alterna `oc login` fra i due), per
# cui `oc_get_json`/`project_exists` (sopra) non bastano per un grading
# affidabile. Ogni modulo ufficiale, in start(), chiama
# use_ocp4_cluster_step()/use_ocp4_mng_cluster_step() (rht_labs_acm.rhacm),
# che scaricano da `utility` e mettono in cache due kubeconfig separati, gia'
# autenticati come cluster-admin, indipendenti dalla sessione oc corrente
# dello studente: usiamo direttamente quelli con --kubeconfig, cosi' il
# grading e' deterministico a prescindere da dove sia loggato lo studente.
HUB_KUBECONFIG = os.path.expanduser("~/.auth/ocp4-kubeconfig")
MANAGED_KUBECONFIG = os.path.expanduser("~/.auth/ocp4-mng-kubeconfig")


def oc_get_json_kc(kubeconfig, *args):
    """Come oc_get_json, ma contro un cluster specifico (kubeconfig
    esplicito, es. HUB_KUBECONFIG o MANAGED_KUBECONFIG) invece della sessione
    oc attiva. Usala direttamente solo quando il kubeconfig e' una variabile
    (es. un loop sui due cluster) — nel caso comune preferisci
    oc_get_json_hub/oc_get_json_managed sotto."""
    if not os.path.exists(kubeconfig):
        return None
    result = subprocess.run(
        ["oc", f"--kubeconfig={kubeconfig}", "get", *args, "-o", "json"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def oc_get_json_hub(*args):
    """Come oc_get_json, ma sempre contro l'hub cluster RHACM (vedi
    commento sopra)."""
    return oc_get_json_kc(HUB_KUBECONFIG, *args)


def oc_get_json_managed(*args):
    """Come oc_get_json_hub, ma contro il managed cluster."""
    return oc_get_json_kc(MANAGED_KUBECONFIG, *args)


def project_exists_hub(name):
    return oc_get_json_hub("project", name) is not None


def project_exists_managed(name):
    return oc_get_json_managed("project", name) is not None


def condition_true(obj, condition_type):
    """True se obj (risorsa RHOCP/RHACM decodificata da oc_get_json*) ha una
    condizione status.conditions con quel `type` e status "True". Usato per
    CR con lo schema conditions standard di Kubernetes (es. ManagedCluster:
    tipi "ManagedClusterJoined"/"ManagedClusterConditionAvailable")."""
    if not obj:
        return False
    for cond in (obj.get("status") or {}).get("conditions", []) or []:
        if cond.get("type") == condition_type:
            return cond.get("status") == "True"
    return False


# --- Helper per corsi RHCSA (RH124/RH134): niente OpenShift, i controlli
# girano su workstation o su un host remoto (servera/serverb) raggiungibile
# via SSH senza password, come nei grading ufficiali (labs.common.commands).


def run(command, host="workstation", sudo=False):
    """Esegue un comando su workstation (subprocess locale) o su un host
    remoto della classroom (via `ssh`, chiavi già configurate dal corso).
    Ritorna un subprocess.CompletedProcess (stdout/stderr come str).

    sudo=True usa la password standard della classroom ("student", la
    stessa indicata nelle guide ufficiali RH124/RH134), perché l'utente
    student non ha sudo passwordless su servera/serverb."""
    if sudo:
        command = f"echo student | sudo -S -p '' {command}"
    if host in ("workstation", "localhost", None):
        return subprocess.run(
            ["bash", "-c", command], capture_output=True, text=True
        )
    try:
        return subprocess.run(
            [
                "ssh",
                "-o", "BatchMode=yes",
                "-o", "ConnectTimeout=5",
                "-o", "StrictHostKeyChecking=no",
                host, command,
            ],
            capture_output=True, text=True, timeout=20,
        )
    except subprocess.TimeoutExpired:
        # Host non ancora raggiungibile (es. una VM non ancora installata
        # da questo stesso esercizio): non deve mai bloccare il grading.
        return subprocess.CompletedProcess([command], 255, "", "ssh timeout")


def command_ok(command, host="workstation", sudo=False):
    """True se il comando esce con codice 0."""
    return run(command, host=host, sudo=sudo).returncode == 0


def user_exists(username, host="workstation"):
    return command_ok(f"getent passwd {username}", host=host)


def group_exists(groupname, host="workstation"):
    return command_ok(f"getent group {groupname}", host=host)


def package_installed(package, host="workstation"):
    return command_ok(f"rpm -q {package}", host=host)


def service_is_active(service, host="workstation"):
    return command_ok(f"systemctl is-active --quiet {service}", host=host)


def service_is_enabled(service, host="workstation"):
    return command_ok(f"systemctl is-enabled --quiet {service}", host=host)


def file_exists(path, host="workstation", sudo=False):
    return command_ok(f"test -e {path}", host=host, sudo=sudo)


def password_matches(username, plaintext, host="workstation"):
    """Confronta la password di un utente locale con un valore atteso,
    senza mai stamparla: legge l'hash da /etc/shadow (serve sudo) e lo
    confronta ricalcolando l'hash con lo stesso salt via `crypt`."""
    import crypt

    result = run(f"getent shadow {username}", host=host, sudo=True)
    if result.returncode != 0:
        return False
    fields = result.stdout.strip().split(":")
    if len(fields) < 2:
        return False
    stored_hash = fields[1]
    if not stored_hash or stored_hash in ("!", "*", "!!", "!!*"):
        return False
    return crypt.crypt(plaintext, stored_hash) == stored_hash


# --- Helper per corsi Podman (DO188): niente RHCSA/OpenShift, i controlli
# girano su container/immagini/reti/volumi Podman locali sulla workstation.
# Tutte le funzioni accettano sudo=True per i pochi esercizi (es.
# custom-rootless) che confrontano container/immagini rootless vs rootful.


def _podman_cmd(args, sudo=False):
    return (["sudo"] if sudo else []) + ["podman", *args]


def podman_inspect(*args, sudo=False):
    """Esegue `podman inspect <args>` e ritorna la lista di dict decodificata,
    o None se la risorsa non esiste o il comando fallisce."""
    result = subprocess.run(
        _podman_cmd(["inspect", *args], sudo=sudo),
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def podman_container(name, sudo=False):
    """Ritorna il dict `podman inspect` di un container, o None se non esiste."""
    data = podman_inspect(name, sudo=sudo)
    return data[0] if data else None


def podman_image(name, sudo=False):
    """Ritorna il dict `podman inspect` di un'immagine, o None se non esiste."""
    data = podman_inspect(name, sudo=sudo)
    return data[0] if data else None


def container_is_running(name, sudo=False):
    c = podman_container(name, sudo=sudo)
    return bool(c and c.get("State", {}).get("Running"))


def container_networks(name, sudo=False):
    """Ritorna l'insieme dei nomi delle reti Podman collegate al container."""
    c = podman_container(name, sudo=sudo)
    if not c:
        return set()
    return set((c.get("NetworkSettings") or {}).get("Networks", {}).keys())


def container_port_mappings(name, sudo=False):
    """Ritorna {"<porta_container>/<proto>": ["<porta_host>", ...]} dalle
    PortBindings del container (solo porte effettivamente pubblicate)."""
    c = podman_container(name, sudo=sudo)
    if not c:
        return {}
    bindings = (c.get("HostConfig") or {}).get("PortBindings") or {}
    return {k: [b.get("HostPort") for b in v] for k, v in bindings.items() if v}


def container_env(name, sudo=False):
    """Ritorna un dict delle env var del container, da Config.Env."""
    c = podman_container(name, sudo=sudo)
    if not c:
        return {}
    result = {}
    for item in (c.get("Config") or {}).get("Env", []) or []:
        if "=" in item:
            k, v = item.split("=", 1)
            result[k] = v
    return result


def container_mounts(name, sudo=False):
    """Ritorna la lista dei mount del container (ciascuno un dict con
    almeno Source/Destination/Type, come da `podman inspect`.Mounts)."""
    c = podman_container(name, sudo=sudo)
    if not c:
        return []
    return c.get("Mounts") or []


def podman_network_exists(name, sudo=False):
    result = subprocess.run(_podman_cmd(["network", "exists", name], sudo=sudo), capture_output=True)
    return result.returncode == 0


def podman_volume_exists(name, sudo=False):
    result = subprocess.run(_podman_cmd(["volume", "exists", name], sudo=sudo), capture_output=True)
    return result.returncode == 0


def podman_volume_mountpoint(name, sudo=False):
    """Ritorna la Mountpoint del volume sul filesystem host, o None."""
    data = podman_inspect(name, sudo=sudo)
    if not data:
        return None
    return data[0].get("Mountpoint")


def podman_exec(name, *args, sudo=False):
    """Esegue `podman exec <name> <args>`. Ritorna un subprocess.CompletedProcess."""
    return subprocess.run(_podman_cmd(["exec", name, *args], sudo=sudo), capture_output=True, text=True)


def podman_logs(name, sudo=False):
    """Ritorna lo stdout+stderr di `podman logs <name>` (stringa unica), o "" se il
    container non esiste."""
    result = subprocess.run(_podman_cmd(["logs", name], sudo=sudo), capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    return result.stdout + result.stderr


def http_get(url, timeout=5):
    """Esegue una GET con curl (nessuna dipendenza extra tipo `requests`).
    Ritorna (ok, body): ok è True solo se la richiesta HTTP ha avuto successo
    (curl -f, quindi anche un 4xx/5xx del server conta come non-ok)."""
    result = subprocess.run(
        ["curl", "-fsS", "--max-time", str(timeout), url],
        capture_output=True, text=True,
    )
    return result.returncode == 0, result.stdout


def http_get_follow(url, timeout=5):
    """Come http_get, ma segue i redirect HTTP (curl -L): serve per gli
    esercizi (es. persisting-lab) dove un endpoint risponde con un redirect
    verso un altro container/porta e la specifica di grading ufficiale usa
    `requests.get()`, che segue i redirect di default."""
    result = subprocess.run(
        ["curl", "-fsSL", "--max-time", str(timeout), url],
        capture_output=True, text=True,
    )
    return result.returncode == 0, result.stdout


def http_get_insecure(url, timeout=5):
    """Come http_get, ma senza validare il certificato TLS (curl -k): serve
    per gli esercizi (es. custom-lab) che generano un certificato
    self-signed e vanno testati su https:// senza una CA valida."""
    result = subprocess.run(
        ["curl", "-fsSk", "--max-time", str(timeout), url],
        capture_output=True, text=True,
    )
    return result.returncode == 0, result.stdout


def selinux_label_ok(path, expected_type="container_file_t"):
    """Replica util.get_selinux_permissions usata dal grading ufficiale DO188
    (vedi common/watch_functions.py -> check_bindmount_access): esegue
    `ls -Z(d)` sul path host di un bind mount e verifica il context SELinux
    atteso (quello impostato da `:Z` sull'opzione -v/volumes di podman)."""
    import os
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return False
    option = "-Zd" if os.path.isdir(path) else "-Z"
    result = subprocess.run(["ls", option, path], capture_output=True, text=True)
    return expected_type in result.stdout


def skopeo_inspect(image_ref, tls_verify=True, timeout=15):
    """Esegue `skopeo inspect docker://<image_ref>` SENZA credenziali (utile
    per verificare che un'immagine in un registry sia davvero pubblica, come
    fa do188/images-lab.py per verificare il push dello studente). Ritorna
    (ok, dict-o-None): ok e' True solo se il comando ha successo senza fornire
    credenziali. tls_verify=False disabilita la verifica del certificato
    (serve solo se la CA della classroom non e' installata)."""
    args = ["skopeo", "inspect", f"docker://{image_ref}"]
    if not tls_verify:
        args.append("--tls-verify=false")
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        return False, None
    try:
        return True, json.loads(result.stdout)
    except json.JSONDecodeError:
        return True, None


def skopeo_inspect_auth(image_ref, username, password, tls_verify=True, timeout=15):
    """Come skopeo_inspect, ma CON credenziali: serve per i corsi RHOAI
    (es. AI0015L/workbench-custom) dove lo studente builda e pusha
    un'immagine custom sul registry della classroom
    (registry.lab.example.com:8443), che richiede autenticazione anche in
    lettura. Non usare per verificare immagini che devono essere pubbliche
    (in quel caso usa skopeo_inspect, senza credenziali)."""
    args = [
        "skopeo", "inspect", f"docker://{image_ref}",
        "--creds", f"{username}:{password}",
    ]
    if not tls_verify:
        args.append("--tls-verify=false")
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        return False, None
    try:
        return True, json.loads(result.stdout)
    except json.JSONDecodeError:
        return True, None


def oc_logs(name, namespace, tail=None):
    """Esegue `oc logs <name> -n <namespace>` e ritorna lo stdout (stringa), o
    "" se il comando fallisce (pod non trovato, non ancora pronto, ecc.)."""
    args = ["oc", "logs", name, "-n", namespace]
    if tail is not None:
        args += ["--tail", str(tail)]
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    return result.stdout


# --- Helper per corsi OpenShift "developer" (DO288): quasi tutto e' oc, ma
# alcuni esercizi usano anche Helm e Kustomize (letture/render, mai comandi
# che modificano il cluster dallo script di grading stesso).


def helm_get_json(*args, namespace=None):
    """Esegue `helm <args> -o json [-n <namespace>]` e ritorna il dict/list
    decodificato, o None se il comando fallisce (release non trovata, ecc.)."""
    cmd = ["helm", *args, "-o", "json"]
    if namespace:
        cmd += ["-n", namespace]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def oc_kustomize_docs(path):
    """Esegue `oc kustomize <path>` (render locale, non tocca il cluster) e
    ritorna la lista dei manifest YAML come dict. Lista vuota se il comando
    fallisce o la cartella non esiste."""
    import yaml

    result = subprocess.run(["oc", "kustomize", path], capture_output=True, text=True)
    if result.returncode != 0:
        return []
    try:
        return [doc for doc in yaml.safe_load_all(result.stdout) if doc]
    except yaml.YAMLError:
        return []


def http_get_json(url, timeout=5):
    """Come http_get, ma decodifica il body come JSON: utile per gli esercizi
    DO288 (deploy-cli, deploy-console, ecc.) le cui app di esempio esposte
    tramite Route rispondono con un payload REST. Ritorna (ok, dict/list o
    None): ok e' True solo se la richiesta HTTP ha successo E il body e' JSON
    valido."""
    ok, body = http_get(url, timeout=timeout)
    if not ok:
        return False, None
    try:
        return True, json.loads(body)
    except json.JSONDecodeError:
        return False, None


# --- Helper per corsi AI (AI267/AI0014L-AI0022L su OpenShift AI - RHOAI):
# a differenza di DO180, `start()` qui copia i materiali dell'esercizio (che
# lo studente completa riempiendo dei TODO) sulla workstation locale in
# ~/course/labs/<nome-esercizio>/ (vedi labs.utils.fs.copy_materials_step),
# NON dentro il cluster. Molti esercizi vanno quindi gradati leggendo questi
# file locali, oltre alle risorse OpenShift AI (Notebook, InferenceService,
# DataSciencePipeline, ecc. - tutte CRD, quindi oc_get_json funziona anche
# per queste senza bisogno di helper dedicati).

WORKDIR_DEFAULT = os.path.expanduser("~/course")


def get_workdir():
    """Ritorna la workdir dei materiali corso (default ~/course), leggendo
    l'eventuale override in ~/.grading/config.yaml (chiave 'workdir'), cosi'
    come fa labs.core.config.settings()."""
    config_path = os.path.expanduser("~/.grading/config.yaml")
    try:
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}
        workdir = config.get("workdir")
        if workdir:
            return os.path.expanduser(workdir)
    except (OSError, ImportError, yaml.YAMLError):
        pass
    return WORKDIR_DEFAULT


def lab_materials_dir(lab_name, kind="labs"):
    """Ritorna il path locale dei materiali di un esercizio copiati da
    `lab start` (kind='labs' per lo starter, 'solutions' per la soluzione
    ufficiale, usata solo per i test manuali, mai nel grading)."""
    return os.path.join(get_workdir(), kind, lab_name)


def read_text_file(path):
    """Ritorna il contenuto di un file come stringa, o None se non esiste
    o non e' leggibile."""
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return None


def parse_env_file(path):
    """Fa il parsing minimale di un file .env (KEY=VALUE per riga, ignora
    commenti/righe vuote, rimuove virgolette). Ritorna {} se il file non
    esiste. Non usa python-dotenv (non sempre disponibile) perche' il
    formato che ci serve gradare e' semplicissimo."""
    content = read_text_file(path)
    if content is None:
        return {}
    result = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def get_route_host(name, namespace):
    """Ritorna lo spec.host di una Route OpenShift, o None se non esiste.
    Preferire questa funzione a un dominio hardcoded quando si verifica che
    un file di configurazione dello studente (es. .env) punti all'endpoint
    giusto: il dominio della classroom (apps.<...>) puo' variare, il nome di
    Route/namespace no."""
    route = oc_get_json("route", name, "-n", namespace)
    if not route:
        return None
    return (route.get("spec") or {}).get("host")
