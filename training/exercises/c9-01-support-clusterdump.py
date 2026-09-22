"""
Cap. 9 — Support e Troubleshooting
Crea un dump delle risorse di un progetto, compresso in un archivio tar.gz
(tema uscito all'esame: "crea un file di dump di tutto il cluster
compresso con tar.gz").

Adattamento ai vincoli di questo classroom: un utente non-admin come
"developer" non ha i permessi per leggere risorse cluster-scoped (nodi,
tutti i namespace altrui, ecc.), quindi un dump letteralmente "di tutto il
cluster" non e' riproducibile con l'account con cui gira normalmente questo
training — vedi nota in CLAUDE.md sull'utente developer di un classroom
DO180. Qui il compito e' scoped al progetto dell'esercizio (dove lo
studente HA i permessi), stesso comando (`oc cluster-info dump`) e stesso
risultato finale richiesto (un .tar.gz), solo applicato a un solo
namespace invece che a tutti.

Nota: non ho accesso diretto al testo del manuale DO180 su questa macchina
per confermare capitolo/sezione esatti di questo argomento (vedi audit in
README.md) — l'esercizio e' scritto a partire dalla domanda d'esame e dal
comando CLI reale che la implementa, non da un testo di guida verificato.
"""
import os
import shutil
import sys
import tarfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, oc, reset_project, run_cli

CHAPTER = "Cap. 9 — Support e Troubleshooting"
TITLE = "Crea un dump compresso (tar.gz) delle risorse di un progetto"
PROJECT = "training-cluster-dump"

DUMP_DIR = os.path.expanduser("~/cluster-dump")
ARCHIVE_PATH = os.path.expanduser("~/cluster-dump.tar.gz")

TASK = f"""\
Nel progetto "{PROJECT}" (gia' pronto) crea un dump delle sue risorse con
`oc cluster-info dump`, poi comprimilo in un unico archivio tar.gz in
"{ARCHIVE_PATH}".

Comandi suggeriti (2):
  oc cluster-info dump --namespaces {PROJECT} --output-directory={DUMP_DIR}
  tar czf {ARCHIVE_PATH} -C "$HOME" {os.path.basename(DUMP_DIR)}
"""


def setup():
    reset_project(PROJECT)
    oc(
        "create", "configmap", "marker", "--from-literal=source=training",
        "-n", PROJECT, check=True,
    )
    shutil.rmtree(DUMP_DIR, ignore_errors=True)
    try:
        os.remove(ARCHIVE_PATH)
    except FileNotFoundError:
        pass


def grade():
    with GradingStep(f"L'archivio {ARCHIVE_PATH} esiste") as step:
        if not os.path.isfile(ARCHIVE_PATH):
            step.fail(f"'{ARCHIVE_PATH}' non trovato")

    with GradingStep("E' un vero tar.gz col dump del progetto (non un file vuoto/finto)") as step:
        if not os.path.isfile(ARCHIVE_PATH):
            step.fail("Archivio non trovato")
        else:
            try:
                with tarfile.open(ARCHIVE_PATH, "r:gz") as tar:
                    names = tar.getnames()
            except tarfile.TarError as exc:
                step.add_error(f"Non e' un tar.gz valido: {exc}")
            else:
                # 'oc cluster-info dump' crea sempre <output-dir>/<namespace>/*.json:
                # cerchiamo quella struttura per nome, non la directory di
                # primo livello (scelta libera dello studente).
                has_namespace_dump = any(
                    f"/{PROJECT}/" in name and name.endswith(".json")
                    for name in names
                )
                if not has_namespace_dump:
                    step.add_error(
                        f"Nessun file .json sotto una cartella '{PROJECT}/' nell'archivio "
                        f"(contenuto trovato: {names[:10]}{'...' if len(names) > 10 else ''})"
                    )


def cleanup():
    shutil.rmtree(DUMP_DIR, ignore_errors=True)
    try:
        os.remove(ARCHIVE_PATH)
    except FileNotFoundError:
        pass
    from _training_common import project_exists
    if project_exists(PROJECT):
        oc("delete", "project", PROJECT, "--wait=false")


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
