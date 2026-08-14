#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato storage-statefulsets, sprovvisto di
`lab grade` ufficiale (la classe StorageStatefulsets nel pacchetto do180
implementa solo start()/finish(), non grade()).

start() copia nel progetto due manifest con placeholder CHANGE_ME
(vedi do180/materials/labs/storage-statefulsets/{service-db,statefulset-db}.yml):
lo studente deve completarli e applicarli con `oc apply`. Confrontando questi
file con la soluzione ufficiale (do180/materials/solutions/storage-statefulsets/)
tutte le differenze sono nei placeholder CHANGE_ME:

- service-db.yml: metadata.name=mysql-svc, spec.clusterIP=None (service
  headless, richiesto da un StatefulSet per la network identity stabile dei
  pod), spec.selector.app=database
- statefulset-db.yml: metadata.name=dbserver, spec.selector.matchLabels.app e
  spec.template.metadata.labels.app=database, spec.serviceName=mysql-svc
  (deve combaciare col Service headless), containers[0].name=dbserver,
  volumeMounts[0]={name: data, mountPath: /var/lib/mysql},
  volumeClaimTemplates[0]={name: data, storageClassName: lvms-vg1}
  (spec.replicas=2 e' gia' presente identico nel file di partenza, non e'
  un CHANGE_ME, ma viene comunque verificato come parte dello stato finale).

Questo script verifica le risorse live create a partire da questi manifest.

Uso: storage-statefulsets.py [nome-progetto]   (default: storage-statefulsets)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "storage-statefulsets"
SERVICE_NAME = "mysql-svc"
STATEFULSET_NAME = "dbserver"
CONTAINER_NAME = "dbserver"
APP_LABEL = "database"
VOLUME_NAME = "data"
MOUNT_PATH = "/var/lib/mysql"
STORAGE_CLASS = "lvms-vg1"
EXPECTED_REPLICAS = 2
EXPECTED_PORT = 3306


def get_container(statefulset, name=CONTAINER_NAME):
    containers = statefulset["spec"]["template"]["spec"]["containers"]
    for c in containers:
        if c.get("name") == name:
            return c
    return containers[0] if containers else None


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

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
            container = get_container(statefulset)
            if container is None:
                step.add_error("Nessun container trovato nel template del pod")

    with GradingStep(
        f"Il container {CONTAINER_NAME} monta il volume persistente su {MOUNT_PATH}"
    ) as step:
        if container is None:
            step.fail()
        else:
            mounts = container.get("volumeMounts", [])
            mount = next((m for m in mounts if m.get("name") == VOLUME_NAME), None)
            if mount is None:
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
