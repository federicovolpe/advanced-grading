"""
Try-exam 4 — completare un Containerfile (ARG -> ENV, COPY) e costruire
l'immagine con --build-arg. Il tema dice "/docker-entrypointinitdb.d": la
directory reale letta dall'entrypoint mariadb e' /docker-entrypoint-initdb.d.

Il grosso dei check e' sull'immagine risultante (Env, layer, file
contenuti), non sul testo del Containerfile: e' l'esito oggettivo. Dal
testo si verifica solo cio' che l'immagine non puo' dire, cioe' che i
valori arrivano dagli ARG e non sono scritti a mano nelle ENV.
"""
import sys, os
import re
import subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _exam_common import (
    BASE_DIR, UPSTREAM_MARIADB, SETUP_TIMEOUT, GradingStep, podman,
    podman_image, ensure_upstream, write_file, run_cli,
)

WORK_DIR = os.path.join(BASE_DIR, "acme-db")
CONTAINERFILE = os.path.join(WORK_DIR, "Containerfile.acme-db")
SQL_FILE = os.path.join(WORK_DIR, "acmeData.sql")
IMAGE = "acme-db:latest"
INIT_DIR = "/docker-entrypoint-initdb.d"
ARGS = {"DB_ROOT_PASSWORD": "acme", "DB_ACME_DATABASE": "acme"}
ENV_FROM_ARG = {"MARIADB_ROOT_PASSWORD": "DB_ROOT_PASSWORD", "MARIADB_DATABASE": "DB_ACME_DATABASE"}

STARTER = """\
# Containerfile per il database ACME
"""

SQL = """\
CREATE TABLE IF NOT EXISTS customers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL
);
INSERT INTO customers (name) VALUES ('Wile E. Coyote'), ('Road Runner');
"""

TASK = f"""\
Aggiorna il file {CONTAINERFILE}
e aggiungi quanto necessario perche':
  - l'immagine base sia mariadb:latest
  - accetti i seguenti parametri (build argument):
      - DB_ROOT_PASSWORD
      - DB_ACME_DATABASE
  - imposti le seguenti variabili d'ambiente:
      - MARIADB_ROOT_PASSWORD -> ha il valore del parametro DB_ROOT_PASSWORD
      - MARIADB_DATABASE      -> ha il valore del parametro DB_ACME_DATABASE
  - copi il file acmeData.sql nella directory {INIT_DIR} del container

Poi crea un'immagine taggata {IMAGE} usando il file Containerfile.acme-db,
passando gli argomenti DB_ROOT_PASSWORD con valore acme e
DB_ACME_DATABASE con valore acme.
"""

CHAPTER = "Try exam"
TITLE = "4) Containerfile con ARG/ENV e build"
PROJECT = None


def setup():
    podman("rmi", "-f", IMAGE)
    ensure_upstream(UPSTREAM_MARIADB)
    write_file(CONTAINERFILE, STARTER)
    write_file(SQL_FILE, SQL)


def _image_env(img):
    env = {}
    for item in ((img or {}).get("Config") or {}).get("Env") or []:
        k, _, v = item.partition("=")
        env[k] = v
    return env


def grade():
    try:
        text = open(CONTAINERFILE).read()
    except OSError as exc:
        text = ""
        print(f"FAIL Il file {CONTAINERFILE} e' leggibile\n        - {exc}")
    instructions = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]

    with GradingStep("Il Containerfile parte da mariadb:latest") as step:
        froms = [l.split()[1] for l in instructions if l.upper().startswith("FROM ") and len(l.split()) > 1]
        if not froms:
            step.add_error("nessuna istruzione FROM")
        elif froms[0] not in ("mariadb:latest", UPSTREAM_MARIADB, "docker.io/mariadb:latest"):
            step.add_error(f"FROM {froms[0]}")

    with GradingStep("Il Containerfile dichiara gli ARG DB_ROOT_PASSWORD e DB_ACME_DATABASE") as step:
        for arg in ARGS:
            if not any(re.match(rf"ARG\s+{arg}(\s|=|$)", l, re.I) for l in instructions):
                step.add_error(f"manca ARG {arg}")

    with GradingStep("Le ENV MARIADB_* prendono il valore dagli ARG") as step:
        for env, arg in ENV_FROM_ARG.items():
            if not re.search(rf"\b{env}\s*[= ]\s*\"?\$\{{?{arg}\b", text):
                step.add_error(f"{env} non e' impostata da ${arg}")

    img = podman_image(IMAGE)
    with GradingStep(f"L'immagine {IMAGE} esiste") as step:
        if not img:
            step.fail(f"Immagine '{IMAGE}' non trovata (podman build -t {IMAGE} ...)")

    with GradingStep("L'immagine e' costruita sopra mariadb:latest") as step:
        base = podman_image(UPSTREAM_MARIADB)
        base_layers = ((base or {}).get("RootFS") or {}).get("Layers") or []
        layers = ((img or {}).get("RootFS") or {}).get("Layers") or []
        if not img:
            step.fail("Immagine non trovata")
        elif not base_layers or layers[:len(base_layers)] != base_layers:
            step.add_error("i layer dell'immagine non partono da quelli di mariadb:latest")

    with GradingStep("Nell'immagine MARIADB_ROOT_PASSWORD=acme e MARIADB_DATABASE=acme") as step:
        env = _image_env(img)
        if not img:
            step.fail("Immagine non trovata")
        for env_name, arg in ENV_FROM_ARG.items():
            if img and env.get(env_name) != ARGS[arg]:
                step.add_error(f"{env_name}={env.get(env_name)!r} (build-arg {arg}={ARGS[arg]} passato?)")

    with GradingStep(f"acmeData.sql e' presente in {INIT_DIR}") as step:
        if not img:
            step.fail("Immagine non trovata")
        else:
            result = subprocess.run(
                ["podman", "run", "--rm", "--entrypoint", "cat", IMAGE, f"{INIT_DIR}/acmeData.sql"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                step.add_error(f"{INIT_DIR}/acmeData.sql non trovato nell'immagine")
            elif result.stdout != open(SQL_FILE).read():
                step.add_error("il file nell'immagine non coincide con acmeData.sql")


def cleanup():
    podman("rmi", "-f", IMAGE)


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
