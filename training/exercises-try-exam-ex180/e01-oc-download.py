"""
Try-exam EX180, 0+1 — connessione remota e download del client oc.

Punti 0 e 1 del tema: "ti connetti in remoto all'account X sulla macchina M"
e "scarica la cli di openshift per l'utente remoto X senza copiare il oc gia'
presente".

Scostamenti dal tema annotato (scelte nostre):
- la connessione ssh non e' verificabile da qui: la "macchina remota" e' la
  workstation e l'"utente remoto" e' quello con cui gira il training;
- la directory di destinazione (~/ex180-remote) e' nostra: il tema non dice
  dove installare il client.

"Senza copiare l'oc presente" si verifica per RISULTATO: l'archivio
scaricato deve restare nella directory, e il binario `oc` deve essere
IDENTICO (sha256) al file `oc` contenuto in quell'archivio. Vale sia per
`oc.tar` (download della console) sia per `openshift-client-linux.tar.gz`
(mirror), che contengono entrambi un file `oc`. Un `cp $(which oc)` non
lascia nessun archivio da cui derivare il binario, quindi non passa.
L'archivio pesa decine di MB e il monitor grada ogni 8s: gli sha256
(archivio e binario) sono messi in cache su disco, indicizzati per
percorso + dimensione + mtime, e ricalcolati solo se il file cambia.

Non verificato dal vivo su un cluster DO180 reale (nessun accesso durante
la scrittura): URL e permessi di lettura delle risorse di download della
console vanno confermati al primo uso.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ex180_common import (  # noqa: F401
    CHAPTER, SETUP_TIMEOUT, STATE_DIR, GradingStep, sha256_file, remove_path, run_cli,
)

SLUG = "e01"
TITLE = "0-1) Connessione remota e download del client oc"
PROJECT = None

TARGET_DIR = os.path.expanduser("~/ex180-remote")
TARGET_BIN = os.path.join(TARGET_DIR, "oc")
MIN_SIZE_BYTES = 10 * 1024 * 1024
CACHE_FILE = os.path.join(STATE_DIR, "e01-sha-cache.json")

TASK = f"""\
  0. Collegati in remoto all'account dell'esame sulla macchina indicata
     (nella simulazione lavora direttamente sul tuo account locale: la
     connessione ssh non viene verificata).

  1. Scarica la CLI di OpenShift ("oc", versione Linux) per questo
     utente e installala nella directory
         {TARGET_DIR}
     in modo che il binario sia {TARGET_BIN}
     ed esegua correttamente.

     Non copiare l'oc gia' presente sul sistema: devi scaricarla.
     Lascia nella stessa directory anche l'archivio che hai scaricato.
"""

SOLUTION = f"""\
# 0) ssh utente@macchina        (nella simulazione: nessun ssh)

# 1) il link e' nella console web: icona "?" -> Command Line Tools ->
#    "Download oc for Linux for x86_64" (tasto destro, copia link).
#    Tipicamente:
#    https://downloads-openshift-console.apps.<dominio>/amd64/linux/oc.tar
mkdir -p {TARGET_DIR} && cd {TARGET_DIR}
curl -kLO <link copiato dalla console>
tar xf oc.tar                    # (o: tar xzf openshift-client-linux.tar.gz)
chmod +x oc
./oc version --client
"""


# --- cache degli sha256 ------------------------------------------------------

def _load_cache():
    try:
        with open(CACHE_FILE) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _save_cache(cache):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        tmp = f"{CACHE_FILE}.tmp-{os.getpid()}"
        with open(tmp, "w") as fh:
            json.dump(cache, fh)
        os.replace(tmp, CACHE_FILE)
    except OSError:
        pass  # la cache e' solo un'ottimizzazione


def _cached(cache, path, kind, compute):
    """sha (o None) per `path`, ricalcolato solo se dimensione/mtime cambiano."""
    st = os.stat(path)
    key = f"{kind}:{path}"
    stamp = [st.st_size, st.st_mtime_ns]
    entry = cache.get(key)
    if entry and entry.get("stamp") == stamp:
        return entry.get("sha")
    sha = compute(path)
    cache[key] = {"stamp": stamp, "sha": sha}
    return sha


def _archive_oc_sha(archive):
    """sha256 del file `oc` dentro l'archivio (tar, tar.gz, tar.xz...), o None
    se non e' un archivio tar o non contiene un file `oc`. Un solo
    passaggio: con i tar compressi ogni scansione decomprime tutto."""
    try:
        with tarfile.open(archive, "r:*") as tar:
            for m in tar:
                if os.path.basename(m.name) == "oc" and (m.isfile() or m.islnk()):
                    fh = tar.extractfile(m)
                    if fh is None:
                        continue
                    h = hashlib.sha256()
                    for chunk in iter(lambda: fh.read(1 << 20), b""):
                        h.update(chunk)
                    return h.hexdigest()
    except (tarfile.TarError, OSError, EOFError, KeyError):
        return None
    return None


def _archives(cache):
    """{percorso archivio: sha del suo `oc`} per i file della directory che
    sono archivi tar con dentro un file `oc` (il binario estratto escluso)."""
    if not os.path.isdir(TARGET_DIR):
        return {}
    out = {}
    for name in sorted(os.listdir(TARGET_DIR)):
        path = os.path.join(TARGET_DIR, name)
        if path == TARGET_BIN or os.path.islink(path) or not os.path.isfile(path):
            continue
        sha = _cached(cache, path, "archive", _archive_oc_sha)
        if sha:
            out[path] = sha
    return out


def setup():
    shutil.rmtree(TARGET_DIR, ignore_errors=True)
    remove_path(CACHE_FILE)


def grade():
    cache = _load_cache()

    with GradingStep(f"La directory {TARGET_DIR} esiste") as step:
        if not os.path.isdir(TARGET_DIR):
            step.fail(f"'{TARGET_DIR}' non trovata")

    archives = _archives(cache)
    with GradingStep("L'archivio scaricato (con dentro il file oc) e' nella directory") as step:
        if not archives:
            step.fail("nessun archivio tar con un file 'oc' dentro "
                      "(hai copiato il binario invece di scaricarlo? hai cancellato l'archivio?)")

    with GradingStep(f"{TARGET_BIN} e' un binario oc vero, eseguibile") as step:
        if not os.path.isfile(TARGET_BIN):
            step.fail(f"'{TARGET_BIN}' non trovato")
        else:
            if os.path.islink(TARGET_BIN):
                step.add_error("e' un collegamento simbolico, non il file estratto dall'archivio")
            size = os.path.getsize(TARGET_BIN)
            if size < MIN_SIZE_BYTES:
                step.add_error(f"dimensione {size} byte: un oc reale ne pesa almeno {MIN_SIZE_BYTES}")
            if not os.access(TARGET_BIN, os.X_OK):
                step.add_error("manca il permesso di esecuzione (chmod +x)")

    with GradingStep("oc version --client funziona") as step:
        if not (os.path.isfile(TARGET_BIN) and os.access(TARGET_BIN, os.X_OK)):
            step.fail("binario assente o non eseguibile")
        else:
            try:
                r = subprocess.run([TARGET_BIN, "version", "--client"],
                                   capture_output=True, text=True, timeout=15)
            except (subprocess.TimeoutExpired, OSError) as exc:
                step.add_error(f"esecuzione fallita: {exc}")
            else:
                if r.returncode != 0 or "Client Version" not in r.stdout:
                    step.add_error(f"rc={r.returncode}, stdout={r.stdout.strip()[:200]!r}")

    with GradingStep("Il binario viene dall'archivio scaricato (non e' una copia dell'oc di sistema)") as step:
        if not archives or not os.path.isfile(TARGET_BIN) or os.path.islink(TARGET_BIN):
            step.fail("mancano l'archivio o il binario (vedi check precedenti)")
        else:
            binary_sha = _cached(cache, TARGET_BIN, "binary", sha256_file)
            if binary_sha not in archives.values():
                step.add_error("il binario non coincide con il file oc contenuto nell'archivio "
                               f"({', '.join(os.path.basename(a) for a in archives)})")

    _save_cache(cache)


def cleanup():
    shutil.rmtree(TARGET_DIR, ignore_errors=True)
    remove_path(CACHE_FILE)


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
