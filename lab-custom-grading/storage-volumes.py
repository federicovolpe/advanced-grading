#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato storage-volumes, sprovvisto di
`lab grade` ufficiale (la classe StorageVolumes nel pacchetto do180
implementa solo start()/finish(), non grade()).

A differenza di reliability-probes/reliability-requests, per storage-volumes
non esiste una cartella materials/solutions (verificato su tre copie del
pacchetto do180 installate su questa macchina) ne' un resources.txt con i
comandi di riferimento (come invece c'e' per deploy-services): l'unico
materiale di partenza e' materials/labs/storage-volumes/configmap/init-db.sql,
e start() richiede solo che l'immagine rhel8/mysql-80 sia disponibile.

Per questo lo script NON assume nomi esatti di Deployment/PVC/ConfigMap (non
confermati da nessun file del pacchetto), ma cerca le risorse per
caratteristiche oggettive, sullo stile di deploy-newapp.py:
  - un Deployment che usa l'immagine rhel8/mysql-80;
  - una ConfigMap che contiene la chiave "init-db.sql" (il nome del file
    shippato con l'esercizio), montata come volume nel pod;
  - un volume nel pod supportato da una PersistentVolumeClaim Bound (lo
    stesso pattern "PVC montata sul container" gia' gradato ufficialmente in
    storage-review.py per questo capitolo).

Il valore esatto del mountPath e i nomi di Deployment/PVC/ConfigMap non sono
gradati perche' non risultano da nessuna fonte disponibile su questa macchina
(nessuna soluzione, nessuna guida): si verifica solo che i due meccanismi di
volume richiesti dal titolo dell'esercizio (ConfigMap e PVC) siano
effettivamente collegati al pod del database.

Uso: storage-volumes.py [nome-progetto]   (default: storage-volumes)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "storage-volumes"
EXPECTED_IMAGE_SUBSTR = "mysql-80"
EXPECTED_CM_KEY = "init-db.sql"


def find_mysql_deployment(project):
    """Cerca, fra tutti i Deployment del progetto, quello che usa
    l'immagine rhel8/mysql-80 richiesta da start() (images.check_images_exist).
    Non assumiamo un nome fisso: lo studente puo' averlo chiamato come vuole."""
    deployments = oc_get_json("deployment", "-n", project)
    if not deployments:
        return None
    for dep in deployments.get("items", []):
        for c in dep["spec"]["template"]["spec"]["containers"]:
            if EXPECTED_IMAGE_SUBSTR in c.get("image", ""):
                return dep
    return None


def get_container(deployment):
    containers = deployment["spec"]["template"]["spec"]["containers"]
    for c in containers:
        if EXPECTED_IMAGE_SUBSTR in c.get("image", ""):
            return c
    return containers[0] if containers else None


def mounted_volume_names(container):
    return {vm.get("name") for vm in container.get("volumeMounts", []) or []}


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    deployment = find_mysql_deployment(project)
    container = None
    volumes = []
    mounted_names = set()

    with GradingStep("Il database MySQL (immagine rhel8/mysql-80) e' distribuito e pronto") as step:
        if deployment is None:
            step.fail(
                "Nessun Deployment che usa un'immagine rhel8/mysql-80 "
                "trovato nel progetto"
            )
        else:
            container = get_container(deployment)
            volumes = deployment["spec"]["template"]["spec"].get("volumes", [])
            mounted_names = mounted_volume_names(container) if container else set()
            ready = deployment.get("status", {}).get("readyReplicas", 0)
            if not ready:
                name = deployment["metadata"]["name"]
                step.add_error(
                    f"Nessuna replica pronta per il deployment '{name}' "
                    "(il pod non e' Running/Ready)"
                )

    with GradingStep(
        f"Lo script {EXPECTED_CM_KEY} e' stato caricato in una ConfigMap "
        "montata nel pod"
    ) as step:
        if deployment is None:
            step.fail()
        else:
            cm_volume = next(
                (v for v in volumes if "configMap" in v), None
            )
            if cm_volume is None:
                step.add_error(
                    "Il pod non monta nessun volume di tipo ConfigMap"
                )
            else:
                cm_name = cm_volume["configMap"].get("name")
                cm = oc_get_json("configmap", cm_name, "-n", project)
                if cm is None:
                    step.add_error(f"ConfigMap '{cm_name}' non trovata nel progetto")
                elif EXPECTED_CM_KEY not in (cm.get("data") or {}):
                    step.add_error(
                        f"La ConfigMap '{cm_name}' non contiene la chiave "
                        f"'{EXPECTED_CM_KEY}'"
                    )
                if cm_volume.get("name") not in mounted_names:
                    step.add_error(
                        "Il volume della ConfigMap non risulta montato "
                        "(volumeMounts) nel container del database"
                    )

    with GradingStep("Il database usa storage persistente (PVC Bound) montato nel pod") as step:
        if deployment is None:
            step.fail()
        else:
            pvc_volume = next(
                (v for v in volumes if "persistentVolumeClaim" in v), None
            )
            if pvc_volume is None:
                step.add_error(
                    "Il pod non monta nessuna PersistentVolumeClaim "
                    "(storage non persistente)"
                )
            else:
                claim = pvc_volume["persistentVolumeClaim"]["claimName"]
                pvc = oc_get_json("pvc", claim, "-n", project)
                if pvc is None:
                    step.add_error(f"PVC '{claim}' non trovata nel progetto")
                elif pvc.get("status", {}).get("phase") != "Bound":
                    step.add_error(
                        f"PVC '{claim}' non e' Bound "
                        f"(stato: {pvc.get('status', {}).get('phase')})"
                    )
                if pvc_volume.get("name") not in mounted_names:
                    step.add_error(
                        "Il volume della PVC non risulta montato "
                        "(volumeMounts) nel container del database"
                    )


if __name__ == "__main__":
    main()
