"""
Try-exam 2 — podman cp di una directory e di una configurazione nginx,
poi `nginx -s reload`. La "cartella /html del container" del tema e' la
document root dell'immagine nginx ufficiale (/usr/share/nginx/html).

Il reload non lascia traccia in `podman inspect`: lo si verifica dagli
effetti. Il default.conf fornito aggiunge un header X-Acme-Config che la
configurazione di serie non ha, quindi vederlo nella risposta prova che
nginx sta usando il file copiato (reload, o anche un restart: entrambi
leciti come risultato finale).
"""
import sys, os
import subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _exam_common import (
    BASE_DIR, IMG_NGINX, SETUP_TIMEOUT, GradingStep, podman_reset,
    container_mounts, podman_exec, ensure_images, write_file,
    check_container_basics, check_port, run_cli,
)

NAME = "acme-demo-nginx"
HOST_PORT = 8002
WORK_DIR = os.path.join(BASE_DIR, "acme-demo-nginx")
HOST_HTML = os.path.join(WORK_DIR, "html")
HOST_CONF = os.path.join(WORK_DIR, "nginx", "default.conf")
DOC_ROOT = "/usr/share/nginx/html"
CONF_PATH = "/etc/nginx/conf.d/default.conf"
MARKER_HEADER = "X-Acme-Config"

HTML_FILES = {
    "index.html": "<h1>ACME demo nginx</h1>\n<a href=\"about.html\">About</a>\n",
    "about.html": "<h1>About ACME</h1>\n",
    "css/style.css": "body { font-family: sans-serif; }\n",
}

DEFAULT_CONF = f"""\
server {{
    listen       80;
    listen       [::]:80;
    server_name  localhost;

    add_header {MARKER_HEADER} "acme" always;

    location / {{
        root   {DOC_ROOT};
        index  index.html;
    }}
}}
"""

TASK = f"""\
Fai partire un container con:
  - l'immagine dell'esercizio precedente ({IMG_NGINX})
  - il nome del container deve essere {NAME}
  - il container deve essere staccato dalla command line
  - la porta 80 del container deve essere mappata sulla porta esterna {HOST_PORT}

Poi:
  - copia la directory {HOST_HTML} e tutti i suoi
    contenuti dentro la cartella {DOC_ROOT} del container
  - copia il file {HOST_CONF}
    nel file {CONF_PATH} del container
  - esegui il comando "nginx -s reload" dentro il container
"""

CHAPTER = "Try exam"
TITLE = "2) podman cp e reload di nginx"
PROJECT = None


def setup():
    podman_reset(containers=[NAME])
    ensure_images(IMG_NGINX)
    for rel, content in HTML_FILES.items():
        write_file(os.path.join(HOST_HTML, rel), content)
    write_file(HOST_CONF, DEFAULT_CONF)


def _container_file(path):
    result = podman_exec(NAME, "cat", path)
    return result.stdout if result.returncode == 0 else None


def grade():
    c = check_container_basics(NAME, IMG_NGINX)
    check_port(NAME, HOST_PORT)

    with GradingStep(f"I file sono copiati (non montati) in {DOC_ROOT}") as step:
        if not c:
            step.fail("Container non trovato")
        else:
            if any(m.get("Destination", "").startswith(DOC_ROOT) for m in container_mounts(NAME)):
                step.add_error(f"{DOC_ROOT} e' un mount: l'esercizio chiede di copiare i file")
            for root, _dirs, files in os.walk(HOST_HTML):
                for fname in files:
                    host_path = os.path.join(root, fname)
                    rel = os.path.relpath(host_path, HOST_HTML)
                    inside = _container_file(f"{DOC_ROOT}/{rel}")
                    if inside is None:
                        step.add_error(f"{DOC_ROOT}/{rel} non presente nel container")
                    elif inside != open(host_path).read():
                        step.add_error(f"{DOC_ROOT}/{rel} diverso dal file sull'host")

    with GradingStep(f"default.conf copiato in {CONF_PATH}") as step:
        inside = _container_file(CONF_PATH) if c else None
        if inside is None:
            step.fail(f"impossibile leggere {CONF_PATH} nel container")
        elif inside != open(HOST_CONF).read():
            step.add_error(f"{CONF_PATH} non coincide con {HOST_CONF}")

    with GradingStep("nginx sta usando la nuova configurazione (reload eseguito)") as step:
        result = subprocess.run(
            ["curl", "-sS", "-D", "-", "-o", "/dev/null", "--max-time", "5",
             f"http://localhost:{HOST_PORT}/"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            step.fail(f"nessuna risposta da localhost:{HOST_PORT}")
        elif MARKER_HEADER.lower() not in result.stdout.lower():
            step.add_error("la risposta non ha l'header previsto dal nuovo default.conf: nginx non e' stato ricaricato")


def cleanup():
    podman_reset(containers=[NAME])


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
