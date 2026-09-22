"""
Utilita' condivise dagli esercizi di training/ (curricula "liberi",
indipendenti dal tool ufficiale `lab`: vedi README.md, sezione "Training
libero"). Il meccanismo e' generico su due tracce indipendenti:

- training/exercises/       — curriculum DO180 (stato su un cluster OpenShift,
  un progetto `training-<slug>` per esercizio, helper oc_*/ensure_project/...).
- training/exercises-do188/ — curriculum DO188 (stato locale Podman: container/
  immagini/volumi/reti sulla workstation, nessun cluster richiesto, helper
  podman_*/podman()).

Riusa GradingStep/oc_get_json/project_exists/podman_* da
lab-custom-grading/_common.py (stesso repo, gia' generico) invece di
duplicarli, e aggiunge le utilita' di cui gli esercizi di training hanno
bisogno in piu': eseguire comandi che MODIFICANO lo stato (setup()/cleanup()),
non solo leggerlo.
"""

import json
import os
import subprocess
import sys
import time

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lab-custom-grading"),
)
from _common import (  # noqa: E402,F401
    GradingStep,
    oc_get_json,
    project_exists,
    podman_container,
    podman_image,
    podman_inspect,
    podman_network_exists,
    podman_volume_exists,
    podman_volume_mountpoint,
    container_is_running,
    container_networks,
    container_port_mappings,
    container_env,
    container_mounts,
    podman_exec,
    podman_logs,
    http_get,
)


def oc(*args, check=False, input_text=None):
    """Esegue `oc <args>`. Ritorna il subprocess.CompletedProcess (stdout/
    stderr come str). check=True solleva RuntimeError se il comando fallisce
    (usato in setup(), dove un fallimento e' un bug dello script, non un
    esito da gradare)."""
    result = subprocess.run(
        ["oc", *args], capture_output=True, text=True, input=input_text
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"oc {' '.join(args)} fallito: {result.stderr.strip()}")
    return result


def ensure_project(name):
    """Crea il progetto se non esiste ancora. Non lo svuota se esiste
    gia' — usala per gli esercizi dove ripartire da zero non e' necessario
    (l'ambiente iniziale e' comunque vuoto)."""
    if not project_exists(name):
        oc("new-project", name, check=True)
    _wait_default_serviceaccount(name)


def reset_project(name, timeout=90):
    """Cancella il progetto (se esiste) e lo ricrea vuoto: usata dalla
    maggior parte degli esercizi in setup() per garantire uno stato di
    partenza deterministico ogni volta che si (ri)entra nell'esercizio, non
    solo la prima volta (es. dopo aver premuto "Ricomincia esercizio", o per
    gli esercizi di troubleshooting dove il "rotto" iniziale deve tornare
    rotto anche se lo studente lo aveva gia' risolto)."""
    if project_exists(name):
        oc("delete", "project", name, "--wait=true", f"--timeout={timeout}s")
        deadline = time.time() + timeout
        while project_exists(name) and time.time() < deadline:
            time.sleep(2)
    oc("new-project", name, check=True)
    _wait_default_serviceaccount(name)


def _wait_default_serviceaccount(namespace, timeout=30):
    """Attende che il ServiceAccount 'default' sia pronto: subito dopo
    'oc new-project', creare pod puo' fallire per un istante perche' il SA
    (e il relativo secret/token) non e' ancora stato provisionato."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if oc_get_json("serviceaccount", "default", "-n", namespace):
            return
        time.sleep(1)


def podman(*args, check=False, input_text=None):
    """Esegue `podman <args>` sulla workstation locale. Ritorna il
    subprocess.CompletedProcess (stdout/stderr come str). check=True solleva
    RuntimeError se il comando fallisce (usato in setup()/cleanup(), dove un
    fallimento e' un bug dello script, non un esito da gradare) — a meno che
    l'errore sia "non trovato", accettabile in cleanup() (risorsa gia'
    assente, es. da un run precedente interrotto)."""
    result = subprocess.run(
        ["podman", *args], capture_output=True, text=True, input=input_text
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"podman {' '.join(args)} fallito: {result.stderr.strip()}")
    return result


def podman_ps_by_label(label_key, label_value):
    """Ritorna i nomi dei container (anche fermi) con quella label esatta —
    usata per identificare i container creati da 'podman-compose' senza
    dipendere dal loro schema di naming esatto (varia fra versioni: es.
    '<project>_<service>_1' vs '<project>-<service>-1'), solo dalle label
    'com.docker.compose.*' che podman-compose imposta sempre."""
    result = subprocess.run(
        ["podman", "ps", "-a", "--filter", f"label={label_key}={label_value}", "--format", "{{.Names}}"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line]


def podman_reset(containers=(), volumes=(), networks=(), images=()):
    """Rimuove (forzatamente, ignorando gli errori) container/volumi/reti/
    immagini Podman locali per nome. Idempotente: va bene sia in setup()
    (stato di partenza deterministico ad ogni rientro nell'esercizio, es.
    dopo "Ricomincia esercizio") sia in cleanup() (uscita dall'esercizio),
    quindi non fallisce se una risorsa non esiste gia'. Ordine fisso
    (container prima di volumi/reti/immagini): un container in esecuzione
    blocca la rimozione della rete/volume/immagine a cui e' agganciato.
    'rm -f -v' (non solo -f): senza -v restano orfani i volumi ANONIMI creati
    automaticamente da alcune immagini (es. l'immagine ufficiale mysql ne crea
    uno oltre a quello nominato esplicitamente per /var/lib/mysql) — scoperto
    dal vivo testando c5-02-database.py, dove un giro di setup/cleanup
    lasciava un volume anonimo residuo mai piu' ripulito da nessuno."""
    for name in containers:
        podman("rm", "-f", "-v", name)
    for name in volumes:
        podman("volume", "rm", "-f", name)
    for name in networks:
        podman("network", "rm", "-f", name)
    for name in images:
        podman("rmi", "-f", name)


def apply_yaml(yaml_text, namespace=None, check=True):
    """Applica un manifest YAML/JSON passato come stringa (oc apply -f -)."""
    args = ["apply", "-f", "-"]
    if namespace:
        args += ["-n", namespace]
    return oc(*args, check=check, input_text=yaml_text)


def wait_for(predicate, timeout=60, interval=2):
    """Richiama predicate() ogni `interval` secondi finche' non ritorna un
    valore vero o scade `timeout`. Usata in setup() quando una risorsa deve
    raggiungere uno stato preciso prima di considerare l'ambiente pronto
    (es. una PVC diventi Bound). Ritorna l'ultimo valore di predicate()."""
    deadline = time.time() + timeout
    result = predicate()
    while not result and time.time() < deadline:
        time.sleep(interval)
        result = predicate()
    return result


def deployment_container(dep, index=0):
    """Ritorna il dict del container N-esimo (default il primo) di un
    Deployment decodificato da oc_get_json, o None. Usata invece di
    assumere un nome fisso: `oc create deployment X --image=Y` nomina il
    container dall'ultimo segmento di Y (es. 'ubi', 'httpd-24'), NON da X —
    comportamento verificato dal vivo su questo cluster, facile da sbagliare
    a mano."""
    if not dep:
        return None
    containers = (dep.get("spec", {}).get("template", {}).get("spec", {}) or {}).get(
        "containers", []
    )
    if len(containers) <= index:
        return None
    return containers[index]


def find_pvc_name_for_deployment(dep, mount_path=None):
    """Cerca nel Deployment il nome della PersistentVolumeClaim montata
    (opzionalmente solo quella montata su mount_path). Serve perche'
    `oc set volume --add --type=pvc` senza `--claim-name` genera un nome
    casuale (es. 'pvc-vzsxx') — gradare per nome fisso romperebbe ogni volta
    che lo studente non copia esattamente il comando suggerito. Ritorna
    None se nessuna PVC e' montata (o nessuna sul path richiesto)."""
    if not dep:
        return None
    pod_spec = dep.get("spec", {}).get("template", {}).get("spec", {}) or {}
    volumes = pod_spec.get("volumes", []) or []
    pvc_volume_names = {
        v["name"]: v["persistentVolumeClaim"]["claimName"]
        for v in volumes
        if "persistentVolumeClaim" in v
    }
    if not pvc_volume_names:
        return None
    if mount_path is None:
        return next(iter(pvc_volume_names.values()))
    for container in pod_spec.get("containers", []) or []:
        for vm in container.get("volumeMounts", []) or []:
            if vm.get("mountPath") == mount_path and vm.get("name") in pvc_volume_names:
                return pvc_volume_names[vm["name"]]
    return None


def find_running_pod(namespace, label_selector):
    """Ritorna il dict del primo pod Running e NON in fase di terminazione
    per quel selector, o None. Un pod con metadata.deletionTimestamp
    impostato riporta comunque status.phase == "Running" finche' i
    container non si sono davvero fermati (e' solo un artificio della CLI
    mostrarlo come "Terminating") — senza escluderlo esplicitamente, subito
    dopo un 'oc set volume'/'oc set env' (che ricrea il pod) si rischia di
    beccare per caso il pod VECCHIO, ancora in coda per la cancellazione,
    invece di quello nuovo con la modifica appena fatta."""
    pods = oc_get_json("pods", "-n", namespace, "-l", label_selector)
    for pod in (pods or {}).get("items", []):
        if pod.get("metadata", {}).get("deletionTimestamp"):
            continue
        if pod.get("status", {}).get("phase") == "Running":
            return pod
    return None


def parse_quantity(value):
    """Converte una Quantity Kubernetes (es. '500m', '128Mi', '2Gi', '1')
    in un float in unita' 'base' (core per CPU, byte per memoria/storage).
    Solo i suffissi usati negli esercizi di questo repo."""
    if value is None:
        return None
    value = str(value)
    suffixes = {
        "m": 1e-3,
        "Ki": 2**10, "Mi": 2**20, "Gi": 2**30, "Ti": 2**40,
        "k": 1e3, "M": 1e6, "G": 1e9, "T": 1e12,
    }
    for suf, mult in sorted(suffixes.items(), key=lambda kv: -len(kv[0])):
        if value.endswith(suf):
            try:
                return float(value[: -len(suf)]) * mult
            except ValueError:
                return None
    try:
        return float(value)
    except ValueError:
        return None


def run_cli(setup_fn, grade_fn, cleanup_fn=None):
    """Entry point standard di ogni modulo esercizio:
        python3 <esercizio>.py setup
        python3 <esercizio>.py grade
        python3 <esercizio>.py cleanup
    invocato dal monitor grafico (training_monitor.py) come subprocess, cosi'
    ogni run parte da un interprete pulito (stesso approccio del wrapper
    'lab' per lab-custom-grading). Il monitor invoca sempre 'cleanup' quando
    si lascia un esercizio (cambio esercizio, chiusura finestra, 'training
    cleanup'): e' il modulo stesso a sapere se questo significa cancellare un
    progetto OpenShift o rimuovere risorse Podman locali, non il monitor.

    cleanup_fn e' opzionale: se un modulo non lo passa esplicitamente (tutti
    gli esercizi DO180 scritti prima che 'cleanup' esistesse) si ricade sul
    vecchio comportamento — cancellare il progetto OpenShift in PROJECT nel
    namespace del chiamante, se definito — cosi' i moduli esistenti restano
    validi senza modifiche."""
    action = sys.argv[1] if len(sys.argv) > 1 else "grade"
    if action == "setup":
        setup_fn()
        print("Ambiente pronto.")
    elif action == "grade":
        grade_fn()
    elif action == "cleanup":
        if cleanup_fn:
            cleanup_fn()
        else:
            caller_globals = sys._getframe(1).f_globals
            project = caller_globals.get("PROJECT")
            oc_fn = caller_globals.get("oc") or oc
            if project and project_exists(project):
                oc_fn("delete", "project", project, "--wait=false")
        print("Pulizia completata.")
    else:
        print(f"Uso: {sys.argv[0]} [setup|grade|cleanup]", file=sys.stderr)
        sys.exit(1)
