#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato storage-volumes (RHOCP 4.22 / RHEL10),
sprovvisto di `lab grade` ufficiale (la classe StorageVolumes nel pacchetto
do180 implementa solo start()/finish(), non grade()).

RISCRITTO rispetto alla versione precedente di questo script. Quella versione
era stata scritta senza accesso al testo della guida (nessuna materials/
solutions ne' resources.txt per questo esercizio) e quindi cercava le risorse
solo "per caratteristiche": immagine contenente "mysql-80", ConfigMap con
chiave "init-db.sql", una PVC qualunque montata nel pod. Il testo ATTUALE
della guida (Cap. 5.4 "Guided Exercise Provision Persistent Data Volumes",
DO180-RHOCP4.22-en-1-20260730) da' invece nomi ESATTI per ogni risorsa, quindi
si passa a verificarli per nome, come gia' fatto in storage-configs.py:

- Immagine registry.lab.example.com:8443/rhel10/mariadb-118 (NON piu'
  "rhel8/mysql-80" - conferma anche in do180/exercises/storage_volumes.py,
  start() chiama check_images_exist(["rhel10/mariadb-118",
  "redhattraining/do180-dbinit"])). E' un database MariaDB, non MySQL.
- Deployment "db-pod" (punto 3.3/7.3) con le env var (Tabella 15):
  MYSQL_USER=user1, MYSQL_PASSWORD=redhat123, MYSQL_DATABASE=items.
- Service "db-pod" (punto 3.8, Tabella 16): selector app=db-pod, porta e
  targetPort 3306.
- PVC "db-pod-pvc" (punto 4.4, Tabella 17): 1Gi, RWO, montata nel deployment
  su /var/lib/mysql.
- ConfigMap "init-db-cm" (punto 6.4), creata da
  ~/DO180/labs/storage-volumes/configmap/init-db.sql: contiene quindi la
  chiave dati "init-db.sql".

Il progetto e' "storage-volumes" (LAB nel modulo ufficiale, coerente con la
guida: "oc project storage-volumes").

Punto delicato - stato non permanente per design della guida stessa: ai punti
7 e 8 la guida chiede esplicitamente di CANCELLARE il deployment "db-pod" e
poi (punto 8.2) anche la PVC "db-pod-pvc", per verificare che i dati
sopravvivano alla ricreazione del deployment prima di cancellare tutto prima
di "lab finish". Questo e' l'opposto del caso "lascia il pod in esecuzione
fino a finish" gia' documentato in CLAUDE.md, ma lo stesso principio si
applica: il check su deployment/PVC e' valido "sul momento" (mentre lo
studente lavora ai punti 3-7, quando il monitor grafico interroga lab grade
ogni 30s) e torna legittimamente FAIL una volta completato anche il punto 8,
appena prima di "lab finish" - non e' un bug dello script, e' il risultato
atteso di seguire la guida fino in fondo. Gli "outcomes" dichiarati
dell'esercizio (deploy con storage persistente, identificare la PV e il
provisioner) sono raggiunti PRIMA di quella cancellazione finale, quindi e'
quello il momento che vogliamo intercettare.

Al punto 7.5 il volume che monta la PVC viene ricreato con un nome diverso
("db-pod-vol" invece di "db-pod-pvc" del punto 4.4): per questo il controllo
cerca il volume per claimName (db-pod-pvc) e mountPath (/var/lib/mysql),
non per nome del volume, cosi' regge in entrambe le fasi dell'esercizio.

La ConfigMap "init-db-cm" invece non viene mai cancellata dalla guida (solo
smontata implicitamente quando il deployment viene ricreato al punto 7.3, che
non la rimonta): il suo controllo verifica quindi solo che la risorsa e la
chiave esistano nel progetto, senza richiedere che sia attualmente montata
(il montaggio serve solo transitoriamente al punto 6 per eseguire una tantum
lo script di init via `mariadb ... < /var/db/config/init-db.sql`).

Uso: storage-volumes.py [nome-progetto]   (default: storage-volumes)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "storage-volumes"
DEPLOYMENT_NAME = "db-pod"
SERVICE_NAME = "db-pod"
PVC_NAME = "db-pod-pvc"
CONFIGMAP_NAME = "init-db-cm"
CONFIGMAP_KEY = "init-db.sql"
EXPECTED_IMAGE_SUBSTR = "rhel10/mariadb-118"
EXPECTED_PORT = 3306
EXPECTED_MOUNT_PATH = "/var/lib/mysql"
EXPECTED_ENV = {
    "MYSQL_USER": "user1",
    "MYSQL_PASSWORD": "redhat123",
    "MYSQL_DATABASE": "items",
}


def get_container(deployment):
    containers = (
        deployment.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
    )
    return containers[0] if containers else None


def env_dict(container):
    result = {}
    for e in container.get("env", []) or []:
        if "value" in e:
            result[e.get("name")] = e.get("value")
    return result


def pvc_mount_path(deployment, container, claim_name):
    """Ritorna il mountPath del volume del container la cui sorgente e' la
    PVC data (per claimName, non per nome del volume: al punto 7.5 della
    guida il volume viene ricreato con un nome diverso dal punto 4.4 pur
    riferendo la stessa PVC)."""
    volumes = deployment["spec"]["template"]["spec"].get("volumes", []) or []
    vol_name = None
    for v in volumes:
        pvc = v.get("persistentVolumeClaim") or {}
        if pvc.get("claimName") == claim_name:
            vol_name = v.get("name")
            break
    if vol_name is None:
        return None
    for vm in container.get("volumeMounts", []) or []:
        if vm.get("name") == vol_name:
            return vm.get("mountPath")
    return None


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    deployment = oc_get_json("deployment", DEPLOYMENT_NAME, "-n", project)
    container = get_container(deployment) if deployment else None

    with GradingStep(
        f"Il deployment {DEPLOYMENT_NAME} usa l'immagine mariadb-118 corretta "
        "ed e' pronto"
    ) as step:
        if deployment is None:
            step.add_error(
                f"Deployment '{DEPLOYMENT_NAME}' non trovato nel progetto "
                "(atteso presente ai punti 3-7 della guida; assente per "
                "design dopo il punto 8, poco prima di 'lab finish')"
            )
        else:
            if container is None:
                step.add_error("Nessun container trovato nel deployment")
            elif EXPECTED_IMAGE_SUBSTR not in container.get("image", ""):
                step.add_error(
                    f"Immagine attuale '{container.get('image')}', attesa che "
                    f"contenga '{EXPECTED_IMAGE_SUBSTR}'"
                )
            ready = deployment.get("status", {}).get("readyReplicas", 0)
            if not ready:
                step.add_error(
                    f"Nessuna replica pronta per il deployment '{DEPLOYMENT_NAME}' "
                    "(il pod non e' Running/Ready)"
                )

    with GradingStep(
        f"Il deployment {DEPLOYMENT_NAME} ha le variabili d'ambiente MariaDB richieste"
    ) as step:
        if deployment is None or container is None:
            step.fail()
        else:
            actual = env_dict(container)
            for name, expected in EXPECTED_ENV.items():
                if actual.get(name) != expected:
                    step.add_error(
                        f"{name}={actual.get(name)!r}, atteso {expected!r}"
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

    pvc = oc_get_json("pvc", PVC_NAME, "-n", project)

    with GradingStep(
        f"La PVC {PVC_NAME} (1Gi, RWO, Bound) e' montata sul deployment in {EXPECTED_MOUNT_PATH}"
    ) as step:
        if pvc is None:
            step.add_error(
                f"PVC '{PVC_NAME}' non trovata nel progetto (attesa presente ai "
                "punti 4-7 della guida; cancellata per design al punto 8.2, "
                "poco prima di 'lab finish')"
            )
        else:
            phase = pvc.get("status", {}).get("phase")
            if phase != "Bound":
                step.add_error(f"PVC '{PVC_NAME}' non e' Bound (stato attuale: {phase})")
            access_modes = pvc.get("spec", {}).get("accessModes", []) or []
            if "ReadWriteOnce" not in access_modes:
                step.add_error(
                    f"accessModes attuali {access_modes}, atteso includere 'ReadWriteOnce'"
                )
            requested = (
                pvc.get("spec", {}).get("resources", {}).get("requests", {}).get("storage")
            )
            if requested != "1Gi":
                step.add_error(f"Storage richiesto attuale '{requested}', atteso '1Gi'")

        if deployment is None or container is None:
            step.add_error(
                "Deployment non trovato: impossibile verificare il montaggio della PVC"
            )
        else:
            mount_path = pvc_mount_path(deployment, container, PVC_NAME)
            if mount_path is None:
                step.add_error(
                    f"Nessun volume/volumeMount nel container risulta alimentato "
                    f"dalla PVC '{PVC_NAME}'"
                )
            elif mount_path != EXPECTED_MOUNT_PATH:
                step.add_error(
                    f"mountPath attuale '{mount_path}', atteso '{EXPECTED_MOUNT_PATH}'"
                )

    configmap = oc_get_json("configmap", CONFIGMAP_NAME, "-n", project)

    with GradingStep(
        f"La ConfigMap {CONFIGMAP_NAME} contiene lo script {CONFIGMAP_KEY}"
    ) as step:
        if configmap is None:
            step.fail(f"ConfigMap '{CONFIGMAP_NAME}' non trovata nel progetto")
        else:
            data = configmap.get("data") or {}
            if CONFIGMAP_KEY not in data:
                step.add_error(f"Chiave '{CONFIGMAP_KEY}' assente in data")


if __name__ == "__main__":
    main()
