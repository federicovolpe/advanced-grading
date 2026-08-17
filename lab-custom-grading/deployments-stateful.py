#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise deployments-stateful (DO288), priva
di `lab grade` ufficiale (il modulo do288/deployments-stateful.py implementa
solo start()/finish()).

start() applica automaticamente un Deployment "mysql-db" iniziale (1 replica,
immagine rhel8/mysql-80, vedi
do288/materials/kubefiles/deployments-stateful/mysql-deployment.yaml). A
meta' esercizio la guida chiede di ELIMINARE questo Deployment e sostituirlo
con uno StatefulSet omonimo, con volumeClaimTemplates per la persistenza dei
dati e un volume configMap per lo script di init del database.

Specifica (fornita dall'utente, che ha letto guida ufficiale + sorgenti):
- Deployment "mysql-db": NON deve piu' esistere (eliminato al passo 6.3).
- StatefulSet "mysql-db": scalato a 3 repliche, con:
  - volumeClaimTemplates che include un template "mysql-db-pvc"
    (storageClassName nfs-storage, richiesta storage 1Gi, ReadWriteOnce).
  - un volume "init-db-volume" di tipo configMap (name: init-db-cm) montato
    su /tmp/init-db in almeno un container del pod template.
- ConfigMap "init-db-cm" (creata con `oc create cm init-db-cm --from-file
  init-db.sql`): deve avere una chiave "init-db.sql" il cui contenuto include
  "CREATE TABLE" (non verifichiamo il contenuto esatto, solo che sia lo
  script SQL atteso e non un file vuoto/placeholder).
- 3 pod mysql-db-0/1/2 devono avere ciascuno una PVC generata dal
  volumeClaimTemplate ("mysql-db-pvc-mysql-db-<N>") in stato Bound.

Uso: deployments-stateful.py [nome-progetto]   (default: deployments-stateful)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "deployments-stateful"
STATEFULSET = "mysql-db"
DEPLOYMENT = "mysql-db"
CONFIGMAP = "init-db-cm"
PVC_TEMPLATE_NAME = "mysql-db-pvc"
VOLUME_NAME = "init-db-volume"
VOLUME_MOUNT_PATH = "/tmp/init-db"
EXPECTED_REPLICAS = 3


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(f"Il Deployment '{DEPLOYMENT}' iniziale e' stato eliminato") as step:
        deployment = oc_get_json("deployment", DEPLOYMENT, "-n", project)
        if deployment:
            step.add_error(
                f"Il Deployment '{DEPLOYMENT}' esiste ancora: doveva essere eliminato "
                "prima di creare lo StatefulSet omonimo"
            )

    statefulset = oc_get_json("statefulset", STATEFULSET, "-n", project)
    with GradingStep(f"Lo StatefulSet '{STATEFULSET}' esiste ed e' scalato a {EXPECTED_REPLICAS} repliche") as step:
        if not statefulset:
            step.fail(f"StatefulSet '{STATEFULSET}' non trovato")
        else:
            spec = statefulset.get("spec") or {}
            replicas = spec.get("replicas")
            if replicas != EXPECTED_REPLICAS:
                step.add_error(
                    f"'.spec.replicas' e' {replicas!r}, atteso {EXPECTED_REPLICAS}"
                )

    with GradingStep(f"Il volumeClaimTemplate '{PVC_TEMPLATE_NAME}' e' configurato correttamente") as step:
        if not statefulset:
            step.fail(f"StatefulSet '{STATEFULSET}' non trovato")
        else:
            templates = (statefulset.get("spec") or {}).get("volumeClaimTemplates") or []
            match = next(
                (t for t in templates if (t.get("metadata") or {}).get("name") == PVC_TEMPLATE_NAME),
                None,
            )
            if not match:
                step.add_error(
                    f"Nessun volumeClaimTemplate chiamato '{PVC_TEMPLATE_NAME}' trovato"
                )
            else:
                tspec = match.get("spec") or {}
                if tspec.get("storageClassName") != "nfs-storage":
                    step.add_error(
                        f"storageClassName e' {tspec.get('storageClassName')!r}, atteso 'nfs-storage'"
                    )
                access_modes = tspec.get("accessModes") or []
                if "ReadWriteOnce" not in access_modes:
                    step.add_error(f"accessModes {access_modes!r} non include 'ReadWriteOnce'")
                storage = ((tspec.get("resources") or {}).get("requests") or {}).get("storage")
                if storage != "1Gi":
                    step.add_error(f"storage richiesta e' {storage!r}, attesa '1Gi'")

    with GradingStep(f"Il volume '{VOLUME_NAME}' (configMap '{CONFIGMAP}') e' montato su {VOLUME_MOUNT_PATH}") as step:
        if not statefulset:
            step.fail(f"StatefulSet '{STATEFULSET}' non trovato")
        else:
            pod_spec = ((statefulset.get("spec") or {}).get("template") or {}).get("spec") or {}
            volumes = pod_spec.get("volumes") or []
            volume = next((v for v in volumes if v.get("name") == VOLUME_NAME), None)
            if not volume:
                step.add_error(f"Nessun volume chiamato '{VOLUME_NAME}' trovato nel pod template")
            else:
                cm_name = (volume.get("configMap") or {}).get("name")
                if cm_name != CONFIGMAP:
                    step.add_error(
                        f"Il volume '{VOLUME_NAME}' punta al configMap {cm_name!r}, atteso '{CONFIGMAP}'"
                    )

            containers = pod_spec.get("containers") or []
            mounted = any(
                vm.get("name") == VOLUME_NAME and vm.get("mountPath") == VOLUME_MOUNT_PATH
                for c in containers
                for vm in (c.get("volumeMounts") or [])
            )
            if not mounted:
                step.add_error(
                    f"Nessun container monta il volume '{VOLUME_NAME}' su '{VOLUME_MOUNT_PATH}'"
                )

    with GradingStep(f"Il ConfigMap '{CONFIGMAP}' contiene lo script di init del database") as step:
        cm = oc_get_json("configmap", CONFIGMAP, "-n", project)
        if not cm:
            step.fail(f"ConfigMap '{CONFIGMAP}' non trovato")
        else:
            data = cm.get("data") or {}
            content = data.get("init-db.sql")
            if content is None:
                step.add_error("La chiave 'init-db.sql' non e' presente in .data")
            elif "CREATE TABLE" not in content:
                step.add_error("Il contenuto di 'init-db.sql' non contiene 'CREATE TABLE'")

    for i in range(EXPECTED_REPLICAS):
        pvc_name = f"{PVC_TEMPLATE_NAME}-{STATEFULSET}-{i}"
        with GradingStep(f"La PVC '{pvc_name}' e' Bound") as step:
            pvc = oc_get_json("pvc", pvc_name, "-n", project)
            if not pvc:
                step.fail(f"PVC '{pvc_name}' non trovata")
            else:
                phase = (pvc.get("status") or {}).get("phase")
                if phase != "Bound":
                    step.add_error(f"Stato della PVC e' {phase!r}, atteso 'Bound'")


if __name__ == "__main__":
    main()
