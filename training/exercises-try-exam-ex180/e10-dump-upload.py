"""
Try-exam EX180, 10 — dump del cluster, compresso con tar e caricato con una
utility fornita da Red Hat.

Scostamenti dal tema annotato (scelte nostre):
- il dump e' limitato al progetto ex180-e10 (`oc cluster-info dump
  --namespaces`), come nell'esercizio di training c9-01: l'utente developer
  non puo' leggere le risorse di tutto il cluster. Se si e' collegati come
  utente con piu' permessi va bene lo stesso: si controlla solo che nel dump
  ci sia il progetto. ATTENZIONE, non verificato dal vivo: `oc cluster-info
  dump` legge sempre anche la lista dei nodi, e per un utente senza quel
  permesso potrebbe fermarsi con "nodes is forbidden" anche con
  --namespaces; in quel caso va rifatto da un utente con piu' permessi
  (nel classroom: admin);
- L'UTILITY DI UPLOAD DELL'ESAME NON E' NOTA (il tema dice solo "una
  utility fornita da redhat": potrebbe essere `redhat-support-tool
  addattachment` o altro). Qui setup() installa un SEGNAPOSTO,
  ~/.local/bin/rh-upload, che "carica" un file su un caso copiandolo in
  ~/.local/share/training/ex180-state/portal/<numero-caso>/. Va sostituito
  con l'utility vera appena si sa qual era. Numero del caso (01234567),
  percorso dell'archivio (~/ex180-dump.tar.gz) e progetto sono nostri.

Grading per risultato: l'archivio deve essere un vero tar.gz con dentro i
file .json di una cartella che si chiama come il progetto (struttura che
`oc cluster-info dump --output-directory` crea sempre), e il file caricato
sul caso deve essere IDENTICO (sha256) all'archivio attuale: se si rifa'
l'archivio dopo il caricamento, va ricaricato.
"""
import os
import shutil
import stat
import sys
import tarfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ex180_common import (  # noqa: F401
    CHAPTER, SETUP_TIMEOUT, STATE_DIR, GradingStep, oc, reset_project, delete_project,
    check_project, create_httpd_deployment, sha256_file, remove_path, run_cli,
)

SLUG = "e10"
PROJECT = "ex180-e10"
TITLE = "10) Dump del cluster, tar e upload a Red Hat"
CASE = "01234567"
ARCHIVE = os.path.expanduser("~/ex180-dump.tar.gz")
DUMP_DIR = os.path.expanduser("~/ex180-dump")
UPLOAD_TOOL = os.path.expanduser("~/.local/bin/rh-upload")
PORTAL_DIR = os.path.join(STATE_DIR, "portal")
CASE_DIR = os.path.join(PORTAL_DIR, CASE)
MARKER = "EX180-TRAINING-PLACEHOLDER"

TASK = f"""\
Il supporto Red Hat ti chiede i dati del progetto {PROJECT} per il caso
numero {CASE}.

  1. Crea un dump del cluster che contenga le risorse del progetto
     {PROJECT}.
  2. Comprimi il dump con tar in un unico archivio:
         {ARCHIVE}
  3. Carica l'archivio sul caso {CASE} con l'utility fornita da Red Hat,
     che su questa macchina si chiama rh-upload.

(rh-upload e' un segnaposto della simulazione: l'utility usata all'esame
non e' nota. Per la sintassi consulta il suo aiuto, opzione --help)
"""

SOLUTION = f"""\
oc cluster-info dump --namespaces {PROJECT} --output-directory={DUMP_DIR}
#   (se risponde "nodes is forbidden": rifallo collegato come admin)
ls {DUMP_DIR}/{PROJECT}              # events.json, pods.json, ...

tar czf {ARCHIVE} -C ~ {os.path.basename(DUMP_DIR)}
tar tzf {ARCHIVE} | head

rh-upload --case {CASE} {ARCHIVE}
"""

# Segnaposto dell'utility di upload: stampa l'esito e lo sha256, "carica"
# copiando il file nella cartella del caso.
TOOL_SOURCE = f'''#!/usr/bin/env python3
# {MARKER}: installato da training/exercises-try-exam-ex180/e10-dump-upload.py,
# rimosso dal suo cleanup(). Simula l'upload di un file su un caso del
# supporto Red Hat: l'utility reale usata all'esame non e' nota.
import hashlib, os, shutil, sys

PORTAL = {PORTAL_DIR!r}
USAGE = """Uso: rh-upload --case NUMERO_CASO FILE

Carica FILE come allegato del caso di supporto NUMERO_CASO (8 cifre).
(Segnaposto della simulazione EX180: copia il file in
 {PORTAL_DIR}/NUMERO_CASO/)"""


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(USAGE)
        return 0 if argv else 2
    case, files, i = None, [], 0
    while i < len(argv):
        a = argv[i]
        if a in ("-c", "--case"):
            if i + 1 >= len(argv):
                print("rh-upload: manca il numero del caso dopo " + a, file=sys.stderr)
                return 2
            case, i = argv[i + 1], i + 2
            continue
        if a.startswith("--case="):
            case = a.split("=", 1)[1]
        elif a.startswith("-"):
            print("rh-upload: opzione sconosciuta: " + a, file=sys.stderr)
            print(USAGE, file=sys.stderr)
            return 2
        else:
            files.append(a)
        i += 1
    if not case or not case.isdigit() or len(case) != 8:
        print("rh-upload: serve --case con un numero di caso di 8 cifre", file=sys.stderr)
        return 2
    if len(files) != 1:
        print("rh-upload: indica esattamente un file da caricare", file=sys.stderr)
        return 2
    src = files[0]
    if not os.path.isfile(src):
        print("rh-upload: file non trovato: " + src, file=sys.stderr)
        return 1
    dest_dir = os.path.join(PORTAL, case)
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, os.path.basename(src))
    shutil.copyfile(src, dest)
    h = hashlib.sha256()
    with open(dest, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    print("Caricato " + os.path.basename(src) + " sul caso " + case
          + " (" + str(os.path.getsize(dest)) + " byte, sha256 " + h.hexdigest() + ")")
    return 0


sys.exit(main(sys.argv[1:]))
'''


def _is_ours(path):
    try:
        with open(path, errors="replace") as fh:
            return MARKER in fh.read(4096)
    except OSError:
        return False


def install_tool():
    if os.path.lexists(UPLOAD_TOOL) and not _is_ours(UPLOAD_TOOL):
        raise RuntimeError(f"{UPLOAD_TOOL} esiste gia' e non e' il segnaposto del training: "
                           "non lo sovrascrivo")
    os.makedirs(os.path.dirname(UPLOAD_TOOL), exist_ok=True)
    tmp = f"{UPLOAD_TOOL}.tmp-{os.getpid()}"
    with open(tmp, "w") as fh:
        fh.write(TOOL_SOURCE)
    os.chmod(tmp, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    os.replace(tmp, UPLOAD_TOOL)


def _remove_local_files():
    shutil.rmtree(DUMP_DIR, ignore_errors=True)
    shutil.rmtree(PORTAL_DIR, ignore_errors=True)
    remove_path(ARCHIVE)


def setup():
    _remove_local_files()
    install_tool()
    reset_project(PROJECT)
    oc("create", "configmap", "marker", "--from-literal=source=ex180", "-n", PROJECT, check=True)
    create_httpd_deployment("web", PROJECT)


def _dump_members(names):
    """File .json che stanno sotto una cartella col nome del progetto, a
    qualunque profondita' (la cartella di primo livello la sceglie lo
    studente: ex180-dump/, ./, nessuna...)."""
    out = []
    for n in names:
        parts = [p for p in n.split("/") if p not in ("", ".")]
        if n.endswith(".json") and PROJECT in parts[:-1]:
            out.append(n)
    return out


def grade():
    check_project(PROJECT)

    with GradingStep(f"L'archivio {ARCHIVE} esiste") as step:
        if not os.path.isfile(ARCHIVE):
            step.fail(f"'{ARCHIVE}' non trovato")

    with GradingStep(f"E' un vero tar.gz con il dump del progetto {PROJECT}") as step:
        if not os.path.isfile(ARCHIVE):
            step.fail("archivio non trovato")
        else:
            try:
                with tarfile.open(ARCHIVE, "r:gz") as tar:
                    names = tar.getnames()
            except (tarfile.TarError, OSError, EOFError) as exc:
                step.add_error(f"non e' un tar.gz valido: {exc}")
            else:
                if not _dump_members(names):
                    step.add_error(f"nessun file .json sotto una cartella '{PROJECT}/' "
                                   f"(contenuto: {names[:8]}{' ...' if len(names) > 8 else ''})")

    uploaded = []
    if os.path.isdir(CASE_DIR):
        uploaded = sorted(os.path.join(CASE_DIR, f) for f in os.listdir(CASE_DIR)
                          if os.path.isfile(os.path.join(CASE_DIR, f)))
    with GradingStep(f"Un file e' stato caricato sul caso {CASE}") as step:
        if not uploaded:
            other = sorted(os.listdir(PORTAL_DIR)) if os.path.isdir(PORTAL_DIR) else []
            step.fail("nessun file caricato sul caso"
                      + (f" (caricati sui casi: {', '.join(other)})" if other else ""))

    with GradingStep("Il file caricato e' identico all'archivio attuale") as step:
        if not uploaded or not os.path.isfile(ARCHIVE):
            step.fail("manca l'archivio o il caricamento (vedi check precedenti)")
        else:
            want = sha256_file(ARCHIVE)
            if not any(sha256_file(f) == want for f in uploaded):
                step.add_error("nessun file caricato coincide con l'archivio: l'hai rifatto "
                               "dopo averlo caricato? ricaricalo")


def cleanup():
    _remove_local_files()
    if _is_ours(UPLOAD_TOOL):
        remove_path(UPLOAD_TOOL)
    delete_project(PROJECT)


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
