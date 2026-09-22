"""
Cap. 5 — Manage Storage for Application Configuration and Data
Monta una ConfigMap contenente index.html in una sotto-directory del
docroot di Apache, cosi' che sia servita su un percorso specifico
(/messages) invece che sulla radice del sito.

Variante del tema uscito all'esame ("e' stata settata una ConfigMap che
punta a un file index.html, fai in modo che sia servita su /messages"):
stesso meccanismo dell'esercizio guidato ufficiale storage-configs (vedi
lab-custom-grading/storage-configs.py in questo repo) — ConfigMap montata
come volume dentro /var/www/html/ — ma qui il compito e' esplicitamente
farla comparire sotto una sotto-directory (/messages), non sulla radice.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, http_get, oc, oc_get_json, reset_project, run_cli

CHAPTER = "Cap. 5 — Manage Storage for Application Configuration and Data"
TITLE = "Servi una ConfigMap su un percorso specifico (/messages)"
PROJECT = "training-config-mountpath"
IMAGE = "registry.access.redhat.com/ubi9/httpd-24:latest"
CONFIGMAP_NAME = "site-messages"
EXPECTED_CONTENT = "Contenuto pubblicato dal training su /messages"
MOUNT_SUBPATH = "messages"
DOCROOT = "/var/www/html"

TASK = f"""\
Nel progetto "{PROJECT}" trovi gia' pronti: il Deployment "web" (immagine
httpd), il Service "web" (porta 8080) e una Route esposta sul Service, oltre
alla ConfigMap "{CONFIGMAP_NAME}" con una chiave "index.html". Monta quella
ConfigMap come volume nel Deployment "web" in modo che il suo contenuto sia
raggiungibile sul percorso /{MOUNT_SUBPATH} (cioe' su
{DOCROOT}/{MOUNT_SUBPATH}/index.html).

Comando suggerito (1):
  oc set volume deployment/web --add --type configmap \\
    --configmap-name={CONFIGMAP_NAME} --name=site-messages-vol \\
    --mount-path={DOCROOT}/{MOUNT_SUBPATH} -n {PROJECT}
"""


def setup():
    reset_project(PROJECT)
    oc("create", "deployment", "web", f"--image={IMAGE}", "-n", PROJECT, check=True)
    oc("expose", "deployment", "web", "--port=8080", "--target-port=8080", "-n", PROJECT, check=True)
    oc("expose", "service", "web", "-n", PROJECT, check=True)
    oc(
        "create", "configmap", CONFIGMAP_NAME,
        f"--from-literal=index.html={EXPECTED_CONTENT}",
        "-n", PROJECT, check=True,
    )


def _configmap_mount_path(deployment, configmap_name):
    """Ritorna il mountPath del volume del container alimentato da quella
    ConfigMap (per nome), o None — stessa logica di
    lab-custom-grading/storage-configs.py:configmap_volume_mount, qui
    inline perche' specifica di questo solo esercizio."""
    spec = deployment.get("spec", {}).get("template", {}).get("spec", {}) or {}
    volumes = spec.get("volumes", []) or []
    vol_name = next(
        (v.get("name") for v in volumes if (v.get("configMap") or {}).get("name") == configmap_name),
        None,
    )
    if vol_name is None:
        return None
    for c in spec.get("containers", []) or []:
        for vm in c.get("volumeMounts", []) or []:
            if vm.get("name") == vol_name:
                return vm.get("mountPath")
    return None


def grade():
    dep = oc_get_json("deployment", "web", "-n", PROJECT)

    with GradingStep(f"Il Deployment web monta la ConfigMap {CONFIGMAP_NAME} su .../{MOUNT_SUBPATH}") as step:
        if not dep:
            step.fail("Deployment 'web' non trovato")
        else:
            mount_path = _configmap_mount_path(dep, CONFIGMAP_NAME)
            if mount_path is None:
                step.add_error(f"Nessun volume alimentato dalla ConfigMap '{CONFIGMAP_NAME}'")
            elif not mount_path.rstrip("/").endswith(f"/{MOUNT_SUBPATH}"):
                step.add_error(f"mountPath attuale '{mount_path}', atteso che finisca con '/{MOUNT_SUBPATH}'")

    routes = oc_get_json("route", "-n", PROJECT)
    route = next(
        (r for r in (routes or {}).get("items", []) if r.get("spec", {}).get("to", {}).get("name") == "web"),
        None,
    )

    with GradingStep(f"Il sito serve il contenuto della ConfigMap su /{MOUNT_SUBPATH}") as step:
        host = (route or {}).get("spec", {}).get("host")
        if not host:
            step.fail("Route verso 'web' non trovata o senza host")
        else:
            url = f"http://{host}/{MOUNT_SUBPATH}/index.html"
            ok, body = http_get(url)
            if not ok:
                step.add_error(f"GET {url} fallita")
            elif body != EXPECTED_CONTENT:
                step.add_error(f"Contenuto servito diverso da quello atteso: {body!r}")


if __name__ == "__main__":
    run_cli(setup, grade)
