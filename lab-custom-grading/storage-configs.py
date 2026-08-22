#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato storage-configs (RHOCP 4.22 / RHEL10),
sprovvisto di `lab grade` ufficiale (la classe StorageConfigs nel pacchetto
do180 implementa solo start()/finish(), non grade()).

RISCRITTO rispetto alla versione precedente di questo script. Quella versione
assumeva che l'esercizio non desse nomi di risorsa (deployment/service/route)
e che lo studente creasse sia una ConfigMap sia un Secret, cercando quindi il
deployment applicativo per immagine ("httpd-noimage") e i volumi per tipo.
Il testo ATTUALE della guida (Cap. 5.2 "Guided Exercise Externalize the
Configuration of Applications", DO180-RHOCP4.22-en-1-20260730) e' invece
completamente cambiato:

- L'immagine e' registry.lab.example.com:8443/ubi9/httpd-24:latest (uno UBI
  httpd generico, NON piu' "redhattraining/httpd-noimage:v1"). Nota: lo
  start() in do180/exercises/storage_configs.py chiama ancora
  images.check_images_exist(["redhattraining/httpd-noimage:v1"]) - e'
  evidentemente un residuo non allineato al refresh della guida (nessun altro
  riferimento a "httpd-noimage" compare nel testo attuale), quindi qui ci si
  affida al manuale (fonte piu' affidabile) per l'immagine effettiva.
- La guida impone nomi ESATTI per ogni risorsa, dati letteralmente nelle
  istruzioni step-by-step della console e nel comando CLI di riferimento:
    - Deployment "webconfig" (punto 2.4), 3 repliche pronte (punto 2.6:
      "wait for the blue circle to indicate that three pods are running";
      confermato al punto 5.4 con l'output "webconfig 3/3 3 3");
    - Service "webconfig-svc", selector app=webconfig, porta e targetPort
      8080 (tabella al punto 3, "Service field/Service value");
    - Route "webconfig-rt" verso webconfig-svc, targetPort 8080 (tabella al
      punto 3, "Route field/Route value");
    - ConfigMap "webfiles" (punto 4.2) con UNA SOLA chiave dati "index.html"
      (punto 4.3) e UNA chiave binaryData "redhatlogo.png" (punti 4.4-4.5) -
      **non esiste piu' un Secret**: la versione precedente di questo script
      cercava (in modo permissivo) sia un volume da ConfigMap sia uno da
      Secret, ma nella guida attuale tutto sta in un'unica ConfigMap con
      binaryData, esattamente il caso gia' segnalato come "gia' successo" nel
      prompt di audit.
    - Montaggio della ConfigMap come volume nel deployment webconfig, in
      /var/www/html/, tramite il comando CLI dato letteralmente al punto 5.3
      (`oc set volume deployment/webconfig --add --type configmap
      --configmap-name webfiles --name webfiles-vol --mount-path
      /var/www/html/`) - non esiste un'alternativa da console per questo
      passo, quindi anche il nome del volume ("webfiles-vol") e' di fatto
      dettato dalla guida; verifichiamo pero' la fonte del volume
      (configMap.name == "webfiles") piuttosto che il nome del volume stesso,
      per tollerare piccole varianti innocue senza perdere precisione sulla
      sostanza del compito.

Il progetto e' "storage-configs" (self.__LAB__ nel modulo ufficiale, coerente
con la guida: "oc project storage-configs").

Il riscontro end-to-end (punto 6 della guida: "Verify that the web
application shows the content from the configuration map") viene verificato
in sola lettura via HTTP sulla Route webconfig-rt, confrontando byte-per-byte
index.html e redhatlogo.png serviti con i file originali copiati da
`lab start` in ~/DO180/labs/storage-configs (stesso percorso citato nella
guida ai punti 4.3/4.5).

Uso: storage-configs.py [nome-progetto]   (default: storage-configs)
"""

import os
import ssl
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "storage-configs"
DEPLOYMENT_NAME = "webconfig"
SERVICE_NAME = "webconfig-svc"
ROUTE_NAME = "webconfig-rt"
CONFIGMAP_NAME = "webfiles"
EXPECTED_IMAGE_SUBSTR = "ubi9/httpd-24"
EXPECTED_REPLICAS = 3
EXPECTED_PORT = 8080
EXPECTED_MOUNT_PATH_PREFIX = "/var/www/html"
LAB_FILES_DIR = os.path.expanduser(f"~/DO180/labs/{LAB_NAME}")
INDEX_FILE = os.path.join(LAB_FILES_DIR, "index.html")
IMAGE_FILE = os.path.join(LAB_FILES_DIR, "redhatlogo.png")


def get_container(deployment):
    containers = (
        deployment.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
    )
    return containers[0] if containers else None


def configmap_volume_mount(deployment, container, configmap_name):
    """Ritorna il mountPath del volume del container che ha come sorgente la
    ConfigMap data (per nome), o None se nessun volume/mount corrisponde."""
    volumes = deployment["spec"]["template"]["spec"].get("volumes", []) or []
    vol_name = None
    for v in volumes:
        cm = v.get("configMap") or {}
        if cm.get("name") == configmap_name:
            vol_name = v.get("name")
            break
    if vol_name is None:
        return None
    for vm in container.get("volumeMounts", []) or []:
        if vm.get("name") == vol_name:
            return vm.get("mountPath")
    return None


def route_url(route, path=""):
    spec = route.get("spec", {})
    host = spec.get("host")
    if not host:
        return None
    scheme = "https" if spec.get("tls") else "http"
    return f"{scheme}://{host}/{path.lstrip('/')}"


def fetch(url, timeout=10):
    """GET read-only. Ritorna (status, bytes) oppure (None, None) in caso di
    errore di rete/connessione."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(url, timeout=timeout, context=ctx) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception:
        return None, None


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    deployment = oc_get_json("deployment", DEPLOYMENT_NAME, "-n", project)
    container = get_container(deployment) if deployment else None

    with GradingStep(
        f"Il deployment {DEPLOYMENT_NAME} usa l'immagine ubi9/httpd-24 corretta"
    ) as step:
        if deployment is None:
            step.fail(f"Deployment '{DEPLOYMENT_NAME}' non trovato nel progetto")
        elif container is None:
            step.add_error("Nessun container trovato nel deployment")
        elif EXPECTED_IMAGE_SUBSTR not in container.get("image", ""):
            step.add_error(
                f"Immagine attuale '{container.get('image')}', attesa che "
                f"contenga '{EXPECTED_IMAGE_SUBSTR}'"
            )

    with GradingStep(
        f"Il deployment {DEPLOYMENT_NAME} ha {EXPECTED_REPLICAS} repliche disponibili"
    ) as step:
        if deployment is None:
            step.fail()
        else:
            available = deployment.get("status", {}).get("availableReplicas", 0)
            if available != EXPECTED_REPLICAS:
                step.add_error(
                    f"availableReplicas attuale: {available}, atteso {EXPECTED_REPLICAS}"
                )

    service = oc_get_json("service", SERVICE_NAME, "-n", project)

    with GradingStep(
        f"Il service {SERVICE_NAME} espone la porta {EXPECTED_PORT} verso app={DEPLOYMENT_NAME}"
    ) as step:
        if service is None:
            step.fail(f"Service '{SERVICE_NAME}' non trovato nel progetto")
        else:
            selector = (service.get("spec", {}) or {}).get("selector") or {}
            if selector.get("app") != DEPLOYMENT_NAME:
                step.add_error(
                    f"Selector 'app' attuale: {selector.get('app')!r}, atteso {DEPLOYMENT_NAME!r}"
                )
            ports = service.get("spec", {}).get("ports", []) or []
            if not any(
                p.get("port") == EXPECTED_PORT and str(p.get("targetPort")) == str(EXPECTED_PORT)
                for p in ports
            ):
                step.add_error(
                    f"Nessuna porta {EXPECTED_PORT}->{EXPECTED_PORT} trovata (porte attuali: {ports})"
                )

    route = oc_get_json("route", ROUTE_NAME, "-n", project)

    with GradingStep(f"La Route {ROUTE_NAME} espone il service {SERVICE_NAME}") as step:
        if route is None:
            step.fail(f"Route '{ROUTE_NAME}' non trovata nel progetto")
        else:
            to_name = route.get("spec", {}).get("to", {}).get("name")
            if to_name != SERVICE_NAME:
                step.add_error(
                    f"La Route punta al service '{to_name}', atteso '{SERVICE_NAME}'"
                )

    configmap = oc_get_json("configmap", CONFIGMAP_NAME, "-n", project)

    with GradingStep(
        f"La ConfigMap {CONFIGMAP_NAME} contiene index.html e redhatlogo.png (binaryData)"
    ) as step:
        if configmap is None:
            step.fail(f"ConfigMap '{CONFIGMAP_NAME}' non trovata nel progetto")
        else:
            data = configmap.get("data") or {}
            binary_data = configmap.get("binaryData") or {}
            if "index.html" not in data:
                step.add_error("Chiave 'index.html' assente in data")
            if "redhatlogo.png" not in binary_data:
                step.add_error("Chiave 'redhatlogo.png' assente in binaryData")

    with GradingStep(
        f"Il deployment {DEPLOYMENT_NAME} monta la ConfigMap {CONFIGMAP_NAME} in {EXPECTED_MOUNT_PATH_PREFIX}"
    ) as step:
        if deployment is None or container is None:
            step.fail()
        else:
            mount_path = configmap_volume_mount(deployment, container, CONFIGMAP_NAME)
            if mount_path is None:
                step.add_error(
                    f"Nessun volume/volumeMount nel container risulta alimentato "
                    f"dalla ConfigMap '{CONFIGMAP_NAME}'"
                )
            elif not mount_path.rstrip("/").startswith(EXPECTED_MOUNT_PATH_PREFIX):
                step.add_error(
                    f"mountPath attuale '{mount_path}', atteso '{EXPECTED_MOUNT_PATH_PREFIX}'"
                )

    with GradingStep(
        "La Route serve il contenuto corretto (index.html e redhatlogo.png)"
    ) as step:
        if route is None:
            step.fail()
        elif not os.path.isfile(INDEX_FILE) or not os.path.isfile(IMAGE_FILE):
            step.add_error(
                f"File di riferimento non trovati in {LAB_FILES_DIR} "
                "(l'esercizio e' stato avviato con 'lab start storage-configs'?)"
            )
        else:
            with open(INDEX_FILE, "rb") as f:
                expected_index = f.read()
            with open(IMAGE_FILE, "rb") as f:
                expected_image = f.read()

            index_url = route_url(route, "index.html")
            status, body = fetch(index_url)
            if status != 200:
                step.add_error(f"GET {index_url} -> {status} (atteso 200)")
            elif body != expected_index:
                step.add_error(
                    f"Il contenuto servito da {index_url} non corrisponde "
                    "all'index.html originale dell'esercizio"
                )

            image_url = route_url(route, "redhatlogo.png")
            status, body = fetch(image_url)
            if status != 200:
                step.add_error(
                    f"GET {image_url} -> {status} (atteso 200): "
                    "l'immagine redhatlogo.png non e' servita correttamente"
                )
            elif body != expected_image:
                step.add_error(
                    f"Il contenuto servito da {image_url} non corrisponde "
                    "al redhatlogo.png originale dell'esercizio"
                )


if __name__ == "__main__":
    main()
