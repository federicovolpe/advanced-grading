#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato storage-statefulsets (RHOCP 4.22 /
RHEL10), sprovvisto di `lab grade` ufficiale (la classe StorageStatefulsets
nel pacchetto do180 implementa solo start()/finish(), non grade()).

RISCRITTO rispetto alla versione precedente di questo script. La sezione
YAML (Service headless + StatefulSet, punti 6-9 della guida) era gia'
corretta: nomi, label, mountPath e storageClassName combaciano esattamente
col confronto materials/labs vs materials/solutions (solo i placeholder
CHANGE_ME cambiano: metadata.name del service/statefulset, selector/labels
"app", serviceName, nome del container, volumeMounts, volumeClaimTemplates).
Mancava pero' del tutto la prima meta' dell'esercizio (punti 1-5, "Deploy a
web server with persistent storage" / "Scale... observe shared data" - due
dei cinque "Outcomes" elencati in cima alla guida), interamente imperativa
(oc create deployment + oc set volumes, nessun manifest YAML), quindi mai
gradata:

- Deployment "web-server", immagine
  registry.lab.example.com:8443/redhattraining/hello-world-nginx:latest
  (verificata anche da start() con images.check_images_exist).
- Volume "web-pv" (PVC) aggiunto con `oc set volumes --claim-mode rwo
  --claim-size 5Gi --mount-path /usr/share/nginx/html --claim-name
  web-pv-claim`: nomi/valori dati letteralmente nella tabella del punto 2,
  quindi verificabili senza indovinare nulla.
- Deployment scalato a 2 repliche (punto 4) e contenuto di index.html
  condiviso fra i pod (punti 3 e 5: stesso PV, quindi stesso testo "Hello,
  World from <hostname del primo pod>" in tutte le repliche).

Il nome del container generato da `oc create deployment web-server` NON e'
documentato nella guida (non e' detto essere "web-server"): come in
deploy-workloads.py/storage-volumes.py, si usa containers[0] senza
assumerne il nome.

Non gradato, per la regola d'oro (nessun valore concreto verificabile):
- la storageClassName della PVC web-pv-claim: la guida dice solo "Use the
  default storage class" (nessun --claim-class nel comando), quindi lo
  storage class effettivo dipende dal default del cluster (nfs-storage in
  questa aula, ma non e' un valore che lo studente sceglie o digita).
  Verifichiamo solo che la PVC sia Bound con la dimensione/modalita' d'accesso
  richieste, non quale storage class l'abbia soddisfatta.
- le tabelle MySQL "items"/"inventory" nei due pod dbserver-0/1 (punti
  7.4-8.2): dimostrano la stessa cosa gia' verificata strutturalmente (una
  PVC dedicata e Bound per ogni pod dello StatefulSet, l'unico "Outcome"
  esplicito su questa parte) e richiederebbero oc exec + client mysql nel
  pod, con rischio di falsi negativi legati a timing/readiness durante il
  polling ogni 30s del monitor grafico, per un guadagno informativo marginale.

Uso: storage-statefulsets.py [nome-progetto]   (default: storage-statefulsets)
"""

import subprocess
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "storage-statefulsets"

# --- Parte 1: Deployment "web-server" + PVC "web-pv-claim" (punti 1-5) ---
WEB_DEPLOYMENT_NAME = "web-server"
WEB_APP_LABEL = "web-server"  # label di default impostata da `oc create deployment`
WEB_IMAGE_SUBSTR = "hello-world-nginx"
WEB_VOLUME_NAME = "web-pv"
WEB_CLAIM_NAME = "web-pv-claim"
WEB_MOUNT_PATH = "/usr/share/nginx/html"
WEB_CLAIM_SIZE = "5Gi"
WEB_REPLICAS = 2

# --- Parte 2: Service headless + StatefulSet "dbserver" (punti 6-9) ---
SERVICE_NAME = "mysql-svc"
STATEFULSET_NAME = "dbserver"
CONTAINER_NAME = "dbserver"
APP_LABEL = "database"
VOLUME_NAME = "data"
MOUNT_PATH = "/var/lib/mysql"
STORAGE_CLASS = "lvms-vg1"
EXPECTED_REPLICAS = 2
EXPECTED_PORT = 3306


def get_first_container(pod_spec):
    containers = pod_spec.get("containers", [])
    return containers[0] if containers else None


def get_named_container(statefulset, name):
    """Come get_first_container, ma cerca prima per nome (il nome del
    container dello StatefulSet e' un CHANGE_ME esplicito nel manifest, non
    generato automaticamente): ricade su containers[0] solo per poter
    continuare a verificare il resto (volumeMounts) anche se il nome e'
    sbagliato, segnalando comunque l'errore sul nome altrove."""
    containers = statefulset["spec"]["template"]["spec"].get("containers", [])
    for c in containers:
        if c.get("name") == name:
            return c
    return containers[0] if containers else None


def get_running_pod_names(project, app_label):
    data = oc_get_json("pods", "-l", f"app={app_label}", "-n", project)
    if not data:
        return []
    return [
        p["metadata"]["name"]
        for p in data.get("items", [])
        if p.get("status", {}).get("phase") == "Running"
    ]


def find_volume(deployment, name):
    volumes = deployment["spec"]["template"]["spec"].get("volumes", []) or []
    return next((v for v in volumes if v.get("name") == name), None)


def find_volume_mount(container, name):
    mounts = container.get("volumeMounts", []) or [] if container else []
    return next((m for m in mounts if m.get("name") == name), None)


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    # --- Parte 1: web-server + PVC ---

    web_deployment = oc_get_json("deployment", WEB_DEPLOYMENT_NAME, "-n", project)
    web_container = get_first_container(web_deployment["spec"]["template"]["spec"]) if web_deployment else None

    with GradingStep(
        f"Il Deployment {WEB_DEPLOYMENT_NAME} esiste con l'immagine hello-world-nginx"
    ) as step:
        if web_deployment is None:
            step.fail(f"Deployment '{WEB_DEPLOYMENT_NAME}' non trovato nel progetto")
        elif web_container is None:
            step.add_error("Nessun container trovato nel deployment")
        elif WEB_IMAGE_SUBSTR not in web_container.get("image", ""):
            step.add_error(
                f"Immagine attuale '{web_container.get('image')}', attesa che "
                f"contenga '{WEB_IMAGE_SUBSTR}'"
            )

    with GradingStep(
        f"Il Deployment {WEB_DEPLOYMENT_NAME} monta la PVC {WEB_CLAIM_NAME} su {WEB_MOUNT_PATH}"
    ) as step:
        if web_deployment is None:
            step.fail()
        else:
            volume = find_volume(web_deployment, WEB_VOLUME_NAME)
            if volume is None:
                step.add_error(f"Nessun volume chiamato '{WEB_VOLUME_NAME}' nel deployment")
            else:
                claim_name = (volume.get("persistentVolumeClaim") or {}).get("claimName")
                if claim_name != WEB_CLAIM_NAME:
                    step.add_error(
                        f"Il volume '{WEB_VOLUME_NAME}' punta alla claim '{claim_name}', "
                        f"attesa '{WEB_CLAIM_NAME}'"
                    )
                mount = find_volume_mount(web_container, WEB_VOLUME_NAME)
                if mount is None:
                    step.add_error(
                        f"Il volume '{WEB_VOLUME_NAME}' non risulta montato (volumeMounts) nel container"
                    )
                elif mount.get("mountPath") != WEB_MOUNT_PATH:
                    step.add_error(
                        f"mountPath attuale '{mount.get('mountPath')}', atteso '{WEB_MOUNT_PATH}'"
                    )

    web_pvc = oc_get_json("pvc", WEB_CLAIM_NAME, "-n", project)

    with GradingStep(f"La PVC {WEB_CLAIM_NAME} e' Bound con le dimensioni corrette") as step:
        if web_pvc is None:
            step.fail(f"PVC '{WEB_CLAIM_NAME}' non trovata nel progetto")
        else:
            if web_pvc.get("status", {}).get("phase") != "Bound":
                step.add_error(
                    f"Stato attuale: {web_pvc.get('status', {}).get('phase')}, atteso Bound"
                )
            pvc_spec = web_pvc.get("spec", {})
            if "ReadWriteOnce" not in pvc_spec.get("accessModes", []):
                step.add_error("accessModes deve includere ReadWriteOnce (claim-mode rwo)")
            requested = (pvc_spec.get("resources", {}).get("requests", {}) or {}).get("storage")
            if requested != WEB_CLAIM_SIZE:
                step.add_error(f"Dimensione richiesta '{requested}', attesa '{WEB_CLAIM_SIZE}'")

    with GradingStep(f"Il Deployment {WEB_DEPLOYMENT_NAME} e' scalato a {WEB_REPLICAS} repliche") as step:
        if web_deployment is None:
            step.fail()
        else:
            spec_replicas = web_deployment["spec"].get("replicas")
            ready = web_deployment.get("status", {}).get("readyReplicas", 0)
            if spec_replicas != WEB_REPLICAS:
                step.add_error(f"spec.replicas={spec_replicas}, atteso {WEB_REPLICAS}")
            if ready != WEB_REPLICAS:
                step.add_error(f"Solo {ready}/{WEB_REPLICAS} repliche pronte (status.readyReplicas)")

    web_pods = get_running_pod_names(project, WEB_APP_LABEL)

    with GradingStep(
        f"Il contenuto di {WEB_MOUNT_PATH}/index.html e' condiviso fra le repliche di {WEB_DEPLOYMENT_NAME}"
    ) as step:
        if not web_pods:
            step.fail(f"Nessun pod Running con label app={WEB_APP_LABEL} trovato")
        else:
            contents = {}
            for pod_name in web_pods:
                result = subprocess.run(
                    ["oc", "exec", f"pod/{pod_name}", "-n", project, "--",
                     "cat", f"{WEB_MOUNT_PATH}/index.html"],
                    capture_output=True, text=True, timeout=15,
                )
                if result.returncode != 0:
                    step.add_error(f"impossibile leggere index.html dal pod '{pod_name}'")
                else:
                    contents[pod_name] = result.stdout
            values = list(contents.values())
            if values and not all("Hello, World from" in v for v in values):
                step.add_error(
                    "index.html non contiene il testo 'Hello, World from ...' "
                    "inserito al punto 3.1 della guida"
                )
            if len(web_pods) > 1 and len(set(values)) > 1:
                step.add_error(
                    "I pod di web-server mostrano contenuti diversi: non stanno "
                    "condividendo lo stesso volume persistente"
                )

    # --- Parte 2: Service headless + StatefulSet ---

    service = oc_get_json("service", SERVICE_NAME, "-n", project)

    with GradingStep(f"Il Service {SERVICE_NAME} e' headless e seleziona i pod corretti") as step:
        if service is None:
            step.fail(f"Service '{SERVICE_NAME}' non trovato nel progetto")
        else:
            spec = service.get("spec", {})
            if spec.get("clusterIP") != "None":
                step.add_error(
                    "clusterIP deve essere 'None' (service headless, richiesto "
                    f"per un StatefulSet), trovato: {spec.get('clusterIP')}"
                )
            selector = spec.get("selector", {})
            if selector.get("app") != APP_LABEL:
                step.add_error(
                    f"Il selector deve essere app={APP_LABEL} "
                    f"(trovato: {selector.get('app')})"
                )
            port_numbers = [p.get("port") for p in spec.get("ports", [])]
            if EXPECTED_PORT not in port_numbers:
                step.add_error(
                    f"Il service non espone la porta {EXPECTED_PORT} "
                    f"(porte trovate: {port_numbers})"
                )

    statefulset = oc_get_json("statefulset", STATEFULSET_NAME, "-n", project)
    container = None

    with GradingStep(
        f"Lo StatefulSet {STATEFULSET_NAME} e' collegato al service headless "
        f"e ha {EXPECTED_REPLICAS} repliche pronte"
    ) as step:
        if statefulset is None:
            step.fail(f"StatefulSet '{STATEFULSET_NAME}' non trovato nel progetto")
        else:
            spec = statefulset["spec"]
            if spec.get("replicas") != EXPECTED_REPLICAS:
                step.add_error(f"replicas={spec.get('replicas')}, atteso {EXPECTED_REPLICAS}")
            if spec.get("serviceName") != SERVICE_NAME:
                step.add_error(
                    f"serviceName deve essere '{SERVICE_NAME}' (il Service headless), "
                    f"trovato: {spec.get('serviceName')}"
                )
            match_labels = spec.get("selector", {}).get("matchLabels", {})
            if match_labels.get("app") != APP_LABEL:
                step.add_error(
                    f"selector.matchLabels.app deve essere '{APP_LABEL}' "
                    f"(trovato: {match_labels.get('app')})"
                )
            template_labels = spec["template"]["metadata"].get("labels", {})
            if template_labels.get("app") != APP_LABEL:
                step.add_error(
                    f"template.metadata.labels.app deve essere '{APP_LABEL}' "
                    f"(trovato: {template_labels.get('app')})"
                )
            ready = statefulset.get("status", {}).get("readyReplicas", 0)
            if ready != EXPECTED_REPLICAS:
                step.add_error(
                    f"Solo {ready}/{EXPECTED_REPLICAS} repliche pronte (status.readyReplicas)"
                )
            container = get_named_container(statefulset, CONTAINER_NAME)
            if container is None:
                step.add_error("Nessun container trovato nel template del pod")
            elif container.get("name") != CONTAINER_NAME:
                step.add_error(
                    f"containers[0].name deve essere '{CONTAINER_NAME}' "
                    f"(trovato: {container.get('name')})"
                )

    with GradingStep(
        f"Il container {CONTAINER_NAME} monta il volume persistente su {MOUNT_PATH}"
    ) as step:
        if container is None:
            step.fail()
        else:
            mount = find_volume_mount(container, VOLUME_NAME)
            if mount is None:
                mounts = container.get("volumeMounts", [])
                step.add_error(
                    f"Nessun volumeMount chiamato '{VOLUME_NAME}' nel container "
                    f"(trovati: {[m.get('name') for m in mounts]})"
                )
            elif mount.get("mountPath") != MOUNT_PATH:
                step.add_error(
                    f"mountPath deve essere '{MOUNT_PATH}' (trovato: {mount.get('mountPath')})"
                )

    with GradingStep("Il volumeClaimTemplate richiede storage dalla storageClass corretta") as step:
        if statefulset is None:
            step.fail()
        else:
            templates = statefulset["spec"].get("volumeClaimTemplates", [])
            vct = next(
                (t for t in templates if t.get("metadata", {}).get("name") == VOLUME_NAME),
                None,
            )
            if vct is None:
                step.add_error(
                    f"Nessun volumeClaimTemplate chiamato '{VOLUME_NAME}' "
                    f"(trovati: {[t.get('metadata', {}).get('name') for t in templates]})"
                )
            else:
                vct_spec = vct.get("spec", {})
                if vct_spec.get("storageClassName") != STORAGE_CLASS:
                    step.add_error(
                        f"storageClassName deve essere '{STORAGE_CLASS}' "
                        f"(trovato: {vct_spec.get('storageClassName')})"
                    )
                if "ReadWriteOnce" not in vct_spec.get("accessModes", []):
                    step.add_error("accessModes deve includere ReadWriteOnce")

    with GradingStep(f"Le PVC generate dallo StatefulSet {STATEFULSET_NAME} sono Bound") as step:
        if statefulset is None:
            step.fail()
        else:
            for i in range(EXPECTED_REPLICAS):
                pvc_name = f"{VOLUME_NAME}-{STATEFULSET_NAME}-{i}"
                pvc = oc_get_json("pvc", pvc_name, "-n", project)
                if pvc is None:
                    step.add_error(f"PVC '{pvc_name}' non trovata nel progetto")
                elif pvc.get("status", {}).get("phase") != "Bound":
                    step.add_error(
                        f"PVC '{pvc_name}' non e' Bound "
                        f"(stato: {pvc.get('status', {}).get('phase')})"
                    )


if __name__ == "__main__":
    main()
