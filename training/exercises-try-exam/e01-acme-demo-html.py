"""
Try-exam 1 — container nginx che serve un index.html dell'host.
"Sempre aggiornato senza riavviare" impone un bind mount (non podman cp,
non un'immagine custom): il check principale e' quindi sui Mounts, il
confronto HTTP col file conferma che il mount e' quello giusto.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _exam_common import (
    BASE_DIR, IMG_NGINX, SETUP_TIMEOUT, GradingStep, podman_reset,
    container_mounts, http_get, ensure_images, write_file,
    check_container_basics, check_port, run_cli,
)

NAME = "acme-demo-html"
HOST_PORT = 8001
HOST_FILE = os.path.join(BASE_DIR, "acme-demo-html", "index.html")
NGINX_INDEX = "/usr/share/nginx/html/index.html"

TASK = f"""\
Fai partire un container con i seguenti parametri:
  - usa l'immagine {IMG_NGINX}
  - il nome del container deve essere {NAME}
  - il container deve essere staccato dalla command line
  - la porta 80 del container deve essere mappata sulla porta esterna {HOST_PORT}
  - il container deve servire i contenuti del file
    {HOST_FILE}
    quando si accede a localhost:{HOST_PORT}

Nota: il container deve servire sempre il file index.html aggiornato,
senza necessita' di riavviare il container.
"""

CHAPTER = "Try exam"
TITLE = "1) nginx che serve un file dell'host"
PROJECT = None


def setup():
    podman_reset(containers=[NAME])
    ensure_images(IMG_NGINX)
    write_file(HOST_FILE, "<h1>ACME demo html</h1>\n")


def _maps_to_nginx_index(mount):
    """True se il bind mount espone HOST_FILE come NGINX_INDEX: va bene sia
    montare il file stesso sia una qualunque directory che lo contiene."""
    if mount.get("Type") != "bind":
        return False
    src = os.path.realpath(mount.get("Source") or "")
    dest = mount.get("Destination") or ""
    host_file = os.path.realpath(HOST_FILE)
    if src == host_file:
        return dest == NGINX_INDEX
    if not host_file.startswith(src.rstrip("/") + "/"):
        return False
    return os.path.normpath(os.path.join(dest, os.path.relpath(host_file, src))) == NGINX_INDEX


def grade():
    check_container_basics(NAME, IMG_NGINX)
    check_port(NAME, HOST_PORT)

    with GradingStep(f"index.html dell'host montato (bind) come {NGINX_INDEX}") as step:
        mounts = container_mounts(NAME)
        if not any(_maps_to_nginx_index(m) for m in mounts):
            found = [f"{m.get('Source')} -> {m.get('Destination')} ({m.get('Type')})" for m in mounts]
            step.add_error(f"nessun bind mount adatto (una copia non si aggiorna); mount: {found or 'nessuno'}")

    with GradingStep(f"localhost:{HOST_PORT} serve il contenuto attuale di index.html") as step:
        ok, body = http_get(f"http://localhost:{HOST_PORT}/")
        try:
            expected = open(HOST_FILE).read()
        except OSError as exc:
            step.fail(f"impossibile leggere {HOST_FILE}: {exc}")
        else:
            if not ok:
                step.add_error(f"nessuna risposta valida da localhost:{HOST_PORT}")
            elif body.strip() != expected.strip():
                step.add_error("la pagina servita non coincide con il file sull'host")


def cleanup():
    podman_reset(containers=[NAME])


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
