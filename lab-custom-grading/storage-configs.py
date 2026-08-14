#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato storage-configs, sprovvisto di
`lab grade` ufficiale (la classe StorageConfigs nel pacchetto do180
implementa solo start()/finish(), non grade()).

A differenza di deploy-services/deploy-newapp, questo esercizio non lascia
ne' un resources.txt con i comandi di riferimento ne' un manifest YAML da
applicare in materials/labs/storage-configs (che contiene solo index.html
e redhatlogo.png, i due file "mancanti" nell'immagine redhattraining/
httpd-noimage:v1 usata da start()): l'obiettivo didattico e' creare una
ConfigMap e/o un Secret con questi due file e montarli nel deployment cosi'
che l'applicazione li serva correttamente, al posto della pagina/placeholder
di default dell'immagine "noimage".

Non essendoci nomi di oggetti (deployment/configmap/secret) dettati da un
manifest o da comandi di riferimento, questo script NON assume nomi
specifici: individua il deployment applicativo dall'immagine
"httpd-noimage", risale al Service e alla Route tramite i selector/label, e
verifica il risultato in modo "black box" (funzionale): la Route deve
servire byte-per-byte lo stesso index.html e lo stesso redhatlogo.png
copiati dallo start() in ~/DO180/labs/storage-configs. Questo e' l'unico
riscontro oggettivo disponibile senza fare assunzioni sui nomi scelti dallo
studente per ConfigMap/Secret. In aggiunta, verifica (in modo piu' permissivo,
senza pretendere nomi) che il deployment monti effettivamente un volume da
ConfigMap e uno da Secret, coerentemente con l'argomento dell'esercizio.

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
EXPECTED_IMAGE_SUBSTR = "httpd-noimage"
LAB_FILES_DIR = os.path.expanduser(f"~/DO180/labs/{LAB_NAME}")
INDEX_FILE = os.path.join(LAB_FILES_DIR, "index.html")
IMAGE_FILE = os.path.join(LAB_FILES_DIR, "redhatlogo.png")


def find_app_deployment(project):
    """Cerca, fra tutti i Deployment del progetto, quello che usa
    l'immagine httpd-noimage (nome scelto liberamente dallo studente)."""
    deployments = oc_get_json("deployment", "-n", project)
    if not deployments:
        return None, None
    for dep in deployments.get("items", []):
        for c in dep["spec"]["template"]["spec"].get("containers", []):
            if EXPECTED_IMAGE_SUBSTR in c.get("image", ""):
                return dep, c
    return None, None


def classify_volumes(deployment, container):
    """Ritorna (has_configmap_vol, has_secret_vol): True se il container
    monta (in volumeMounts) rispettivamente un volume 'configMap' e uno
    'secret' definiti nel pod template."""
    volumes = deployment["spec"]["template"]["spec"].get("volumes", []) or []
    mounted_names = {vm.get("name") for vm in container.get("volumeMounts", []) or []}
    has_cm = any(v.get("name") in mounted_names and "configMap" in v for v in volumes)
    has_secret = any(v.get("name") in mounted_names and "secret" in v for v in volumes)
    return has_cm, has_secret


def find_matching_service(project, match_labels):
    """Cerca un Service il cui selector e' soddisfatto dalle label dei pod
    del deployment (match_labels)."""
    if not match_labels:
        return None
    services = oc_get_json("service", "-n", project)
    if not services:
        return None
    for svc in services.get("items", []):
        selector = svc.get("spec", {}).get("selector") or {}
        if selector and all(match_labels.get(k) == v for k, v in selector.items()):
            return svc
    return None


def find_route_for_service(project, service_name):
    routes = oc_get_json("route", "-n", project)
    if not routes or not service_name:
        return None
    for route in routes.get("items", []):
        if route.get("spec", {}).get("to", {}).get("name") == service_name:
            return route
    return None


def route_url(route, path=""):
    spec = route.get("spec", {})
    host = spec.get("host")
    if not host:
        return None
    scheme = "https" if spec.get("tls") else "http"
    return f"{scheme}://{host}/{path.lstrip('/')}"


def fetch(url, timeout=10):
    """GET read-only. Ritorna (status, bytes) oppure (None, None) in caso
    di errore di rete/connessione."""
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

    deployment, container = find_app_deployment(project)

    with GradingStep(f"Un Deployment usa l'immagine {EXPECTED_IMAGE_SUBSTR}") as step:
        if deployment is None:
            step.fail(
                f"Nessun Deployment nel progetto usa un'immagine contenente "
                f"'{EXPECTED_IMAGE_SUBSTR}'"
            )

    with GradingStep("Il pod dell'applicazione e' in esecuzione e pronto") as step:
        if deployment is None:
            step.fail()
        else:
            ready = deployment.get("status", {}).get("readyReplicas", 0)
            if not ready:
                step.add_error(
                    f"Nessuna replica pronta per il deployment "
                    f"'{deployment['metadata']['name']}'"
                )

    with GradingStep(
        "Il deployment monta una ConfigMap e un Secret come volumi"
    ) as step:
        if deployment is None or container is None:
            step.fail()
        else:
            has_cm, has_secret = classify_volumes(deployment, container)
            if not has_cm:
                step.add_error(
                    "Nessun volume da ConfigMap risulta montato nel container "
                    "(atteso per fornire index.html)"
                )
            if not has_secret:
                step.add_error(
                    "Nessun volume da Secret risulta montato nel container "
                    "(atteso per fornire redhatlogo.png)"
                )

    service = None
    route = None
    if deployment is not None:
        match_labels = deployment.get("spec", {}).get("selector", {}).get(
            "matchLabels"
        ) or deployment["spec"]["template"]["metadata"].get("labels")
        service = find_matching_service(project, match_labels)
        if service is not None:
            route = find_route_for_service(
                project, service["metadata"]["name"]
            )

    with GradingStep("L'applicazione e' raggiungibile tramite una Route") as step:
        if deployment is None:
            step.fail()
        elif service is None:
            step.add_error(
                "Nessun Service seleziona i pod del deployment "
                f"'{deployment['metadata']['name']}'"
            )
        elif route is None:
            step.add_error(
                f"Nessuna Route punta al Service '{service['metadata']['name']}'"
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
                step.add_error(
                    f"GET {index_url} -> {status} (atteso 200)"
                )
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
