#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato storage-classes, sprovvisto di
`lab grade` ufficiale (la classe StorageClasses nel pacchetto do180 in
do180/exercises/storage_classes.py implementa solo start()/finish(), non
grade()). start() non copia nessun file sorgente per questo esercizio (non
esiste una cartella materials/labs/storage-classes/); verifica solo la
presenza dell'immagine redhattraining/do180-roster:latest. Il file
nfs-pvc.yaml citato dalla guida al passo 7.1 si trova invece in
materials/solutions/storage-classes/ — un file di comodita' del corso,
identico al manifest mostrato nel testo, non qualcosa che start() consegna
allo studente.

Tutti i nomi di risorsa usati sotto sono dettati letteralmente dal testo
della guida (non lasciati alla scelta dello studente, a differenza di
storage-configs/storage-volumes): db-pod, db-pod-pvc, lvm-storage, nfs-pvc,
web-pod, app-pod, nfs-volume. Per questo lo script li usa come nomi fissi
(oc get <kind> <nome>) invece di cercare per caratteristiche.

Particolarita' di questo esercizio rispetto agli altri storage-*: al passo 6
la guida chiede esplicitamente di ELIMINARE il deployment/service/PVC del
database (db-pod, db-pod-pvc) dopo averli usati per la parte "block storage"
(passi 3-6), per poi proseguire con un PVC "nfs-storage" condiviso fra
web-pod e app-pod (passi 7-13), che e' invece lo stato che deve restare
presente fino a `lab finish`. Di conseguenza:
- lo stato FINALE atteso (quello verificato come requisito duro) e' che
  db-pod/db-pod-pvc siano stati eliminati, e che web-pod/app-pod/nfs-pvc
  siano configurati correttamente;
- la configurazione di db-pod/db-pod-pvc (storage class lvms-vg1, env var
  MySQL, mount path) viene comunque verificata "sul momento" se le risorse
  esistono ancora (lo studente e' ancora ai passi 3-5): e' l'unica finestra
  in cui e' possibile controllare che la parte "block storage" dell'esercizio
  sia stata fatta correttamente, dato che sparisce per sempre al passo 6.
  Se le risorse non esistono piu' questo check passa senza errori (non e'
  piu' verificabile, ed e' comunque lo stato finale corretto).

Il passo 2 (esplorare "oc get sc"/"oc describe sc lvms-vg1") e' pura
osservazione, non crea nulla: non e' gradato. Le storage class lvms-vg1/
nfs-storage sono infrastruttura preesistente del cluster, non qualcosa creato
dallo studente.

Uso: storage-classes.py [nome-progetto]   (default: storage-classes)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists, http_get

LAB_NAME = "storage-classes"

# --- Parte "block storage" (passi 3-6), transitoria: db-pod/db-pod-pvc
# vengono eliminati al passo 6 e non devono piu' esistere alla fine.
DB_POD = "db-pod"
DB_SERVICE = "db-pod"
DB_PVC = "db-pod-pvc"
DB_IMAGE_SUBSTR = "mariadb-118"
DB_ENV = {"MYSQL_USER": "user1", "MYSQL_PASSWORD": "redhat123", "MYSQL_DATABASE": "items"}
DB_VOLUME_NAME = "lvm-storage"
DB_MOUNT_PATH = "/var/lib/mysql"
DB_STORAGE_CLASS = "lvms-vg1"
DB_PVC_SIZE = "1Gi"

# --- Parte "shared storage" (passi 7-13), stato finale atteso.
NFS_PVC = "nfs-pvc"
NFS_STORAGE_CLASS = "nfs-storage"
NFS_PVC_SIZE = "1Gi"

WEB_POD = "web-pod"
WEB_IMAGE_SUBSTR = "ubi9/httpd-24"
WEB_MOUNT_PATH = "/var/www/html"
WEB_HOSTNAME = "web-pod.apps.lab.example.com"

APP_POD = "app-pod"
APP_IMAGE_SUBSTR = "do180-roster"
APP_PORT = 9090
APP_MOUNT_PATH = "/var/tmp"
APP_HOSTNAME = "app-pod.apps.lab.example.com"

SHARED_VOLUME_NAME = "nfs-volume"
SHARED_FILE = "People.html"


def get_container(deployment):
    containers = deployment["spec"]["template"]["spec"].get("containers", []) or []
    return containers[0] if containers else None


def find_volume(deployment, name):
    volumes = deployment["spec"]["template"]["spec"].get("volumes", []) or []
    return next((v for v in volumes if v.get("name") == name), None)


def find_mount(container, name):
    mounts = (container or {}).get("volumeMounts", []) or []
    return next((m for m in mounts if m.get("name") == name), None)


def container_ports(container):
    return [p.get("containerPort") for p in (container or {}).get("ports", []) or []]


def check_pvc_shape(step, pvc, storage_class, size):
    """Verifica accessModes/size/storageClassName/fase Bound di una PVC."""
    spec = pvc.get("spec", {})
    if spec.get("storageClassName") != storage_class:
        step.add_error(
            f"storageClassName atteso '{storage_class}', trovato "
            f"'{spec.get('storageClassName')}'"
        )
    if "ReadWriteOnce" not in (spec.get("accessModes") or []):
        step.add_error("accessModes deve includere ReadWriteOnce")
    requested = spec.get("resources", {}).get("requests", {}).get("storage")
    if requested != size:
        step.add_error(f"storage richiesto atteso '{size}', trovato '{requested}'")
    phase = pvc.get("status", {}).get("phase")
    if phase != "Bound":
        step.add_error(f"PVC non e' Bound (stato: {phase})")


def check_volume_mount(step, deployment, container, volume_name, claim_name, mount_path):
    """Verifica che il deployment monti la PVC indicata con nome/mountPath attesi."""
    volume = find_volume(deployment, volume_name)
    if volume is None:
        step.add_error(f"Nessun volume chiamato '{volume_name}' nel pod template")
        return
    claim = volume.get("persistentVolumeClaim", {}).get("claimName")
    if claim != claim_name:
        step.add_error(
            f"Il volume '{volume_name}' deve referenziare la PVC '{claim_name}' "
            f"(trovato: '{claim}')"
        )
    mount = find_mount(container, volume_name)
    if mount is None:
        step.add_error(f"Il volume '{volume_name}' non risulta montato (volumeMounts) nel container")
    elif mount.get("mountPath") != mount_path:
        step.add_error(
            f"mountPath atteso '{mount_path}' per il volume '{volume_name}' "
            f"(trovato: '{mount.get('mountPath')}')"
        )


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    # --- Passi 3-6: db-pod (block storage), transitorio ---
    db_deployment = oc_get_json("deployment", DB_POD, "-n", project)
    db_pvc = oc_get_json("pvc", DB_PVC, "-n", project)
    db_service = oc_get_json("service", DB_SERVICE, "-n", project)

    with GradingStep(
        f"Se ancora presente, il database '{DB_POD}' usa l'immagine mariadb-118, "
        f"le env var corrette e monta la PVC '{DB_PVC}' (storage class {DB_STORAGE_CLASS})"
    ) as step:
        if db_deployment is None:
            pass  # gia' eliminato (passo 6): nulla da verificare, e' lo stato finale corretto
        else:
            container = get_container(db_deployment)
            if container is None:
                step.add_error(f"Nessun container trovato nel deployment '{DB_POD}'")
            else:
                image = container.get("image", "")
                if DB_IMAGE_SUBSTR not in image:
                    step.add_error(
                        f"L'immagine deve contenere '{DB_IMAGE_SUBSTR}' (trovata: '{image}')"
                    )
                env = {e.get("name"): e.get("value") for e in container.get("env", []) or []}
                for key, expected in DB_ENV.items():
                    if env.get(key) != expected:
                        step.add_error(
                            f"Env var {key} attesa '{expected}', trovata '{env.get(key)}'"
                        )
                check_volume_mount(
                    step, db_deployment, container, DB_VOLUME_NAME, DB_PVC, DB_MOUNT_PATH
                )
            if db_pvc is None:
                step.add_error(f"PVC '{DB_PVC}' non trovata (attesa mentre '{DB_POD}' e' presente)")
            else:
                check_pvc_shape(step, db_pvc, DB_STORAGE_CLASS, DB_PVC_SIZE)

    with GradingStep(
        f"Pulizia finale: '{DB_POD}' (deployment/service) e '{DB_PVC}' sono stati eliminati"
    ) as step:
        if db_deployment is not None:
            step.add_error(f"Deployment '{DB_POD}' ancora presente: andava eliminato al passo 6.1")
        if db_service is not None:
            step.add_error(f"Service '{DB_SERVICE}' ancora presente: andava eliminato al passo 6.1")
        if db_pvc is not None:
            step.add_error(f"PVC '{DB_PVC}' ancora presente: andava eliminata al passo 6.3")

    # --- Passo 7: nfs-pvc (storage condiviso) ---
    nfs_pvc = oc_get_json("pvc", NFS_PVC, "-n", project)

    with GradingStep(
        f"La PVC '{NFS_PVC}' esiste, usa la storage class {NFS_STORAGE_CLASS} ed e' Bound"
    ) as step:
        if nfs_pvc is None:
            step.fail(f"PVC '{NFS_PVC}' non trovata nel progetto")
        else:
            check_pvc_shape(step, nfs_pvc, NFS_STORAGE_CLASS, NFS_PVC_SIZE)

    # --- Passi 8-9: web-pod ---
    web_deployment = oc_get_json("deployment", WEB_POD, "-n", project)
    web_container = get_container(web_deployment) if web_deployment else None

    with GradingStep(
        f"Il deployment '{WEB_POD}' usa l'immagine {WEB_IMAGE_SUBSTR} ed e' pronto"
    ) as step:
        if web_deployment is None:
            step.fail(f"Deployment '{WEB_POD}' non trovato nel progetto")
        else:
            image = (web_container or {}).get("image", "")
            if WEB_IMAGE_SUBSTR not in image:
                step.add_error(
                    f"L'immagine deve contenere '{WEB_IMAGE_SUBSTR}' (trovata: '{image}')"
                )
            ready = web_deployment.get("status", {}).get("readyReplicas", 0)
            if not ready:
                step.add_error(f"Nessuna replica pronta per '{WEB_POD}'")

    web_route = oc_get_json("route", WEB_POD, "-n", project)

    with GradingStep(
        f"Esiste una Route per '{WEB_POD}' con hostname {WEB_HOSTNAME}"
    ) as step:
        if web_route is None:
            step.fail(f"Route '{WEB_POD}' non trovata nel progetto")
        else:
            host = web_route.get("spec", {}).get("host")
            if host != WEB_HOSTNAME:
                step.add_error(f"hostname atteso '{WEB_HOSTNAME}', trovato '{host}'")

    with GradingStep(
        f"Il deployment '{WEB_POD}' monta la PVC '{NFS_PVC}' su {WEB_MOUNT_PATH}"
    ) as step:
        if web_deployment is None or web_container is None:
            step.fail()
        else:
            check_volume_mount(
                step, web_deployment, web_container, SHARED_VOLUME_NAME, NFS_PVC, WEB_MOUNT_PATH
            )

    # --- Passi 10-11: app-pod ---
    app_deployment = oc_get_json("deployment", APP_POD, "-n", project)
    app_container = get_container(app_deployment) if app_deployment else None

    with GradingStep(
        f"Il deployment '{APP_POD}' usa l'immagine {APP_IMAGE_SUBSTR} (porta {APP_PORT}) ed e' pronto"
    ) as step:
        if app_deployment is None:
            step.fail(f"Deployment '{APP_POD}' non trovato nel progetto")
        else:
            image = (app_container or {}).get("image", "")
            if APP_IMAGE_SUBSTR not in image:
                step.add_error(
                    f"L'immagine deve contenere '{APP_IMAGE_SUBSTR}' (trovata: '{image}')"
                )
            if APP_PORT not in container_ports(app_container):
                step.add_error(
                    f"containerPort {APP_PORT} non trovato (porte: {container_ports(app_container)})"
                )
            ready = app_deployment.get("status", {}).get("readyReplicas", 0)
            if not ready:
                step.add_error(f"Nessuna replica pronta per '{APP_POD}'")

    app_route = oc_get_json("route", APP_POD, "-n", project)

    with GradingStep(
        f"Esiste una Route per '{APP_POD}' con hostname {APP_HOSTNAME}"
    ) as step:
        if app_route is None:
            step.fail(f"Route '{APP_POD}' non trovata nel progetto")
        else:
            host = app_route.get("spec", {}).get("host")
            if host != APP_HOSTNAME:
                step.add_error(f"hostname atteso '{APP_HOSTNAME}', trovato '{host}'")

    with GradingStep(
        f"Il deployment '{APP_POD}' monta la stessa PVC '{NFS_PVC}' su {APP_MOUNT_PATH}"
    ) as step:
        if app_deployment is None or app_container is None:
            step.fail()
        else:
            check_volume_mount(
                step, app_deployment, app_container, SHARED_VOLUME_NAME, NFS_PVC, APP_MOUNT_PATH
            )

    # --- Passi 12-13: verifica funzionale del volume condiviso ---
    # People.html viene scritto da app-pod su /var/tmp (stesso PVC montato su
    # web-pod in /var/www/html): un GET su web-pod/People.html e' l'unica
    # prova oggettiva, indipendente dal contenuto (che dipende da cosa lo
    # studente ha digitato nel form), che il passo 12 e' stato completato.
    with GradingStep(
        f"'{SHARED_FILE}' creato da {APP_POD} e' visibile tramite {WEB_POD} (volume condiviso)"
    ) as step:
        if web_route is None:
            step.fail("Nessuna Route disponibile per verificare il file condiviso")
        else:
            host = web_route.get("spec", {}).get("host")
            if not host:
                step.fail("La Route non ha ancora un host assegnato")
            else:
                url = f"http://{host}/{SHARED_FILE}"
                ok, _ = http_get(url, timeout=10)
                if not ok:
                    step.add_error(
                        f"GET {url} non risponde con successo: usare il form di "
                        f"{APP_POD} e cliccare 'push' (passo 12) per creare il file"
                    )


if __name__ == "__main__":
    main()
