#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato pods-images, sprovvisto di
`lab grade` ufficiale (la classe PodsImages nel pacchetto do180 implementa
solo start()/finish(), non grade() - vedi do180/exercises/pods_images.py).

Basato sul testo della guida ufficiale (DO180-RHOCP4.22, Capitolo 3, "3.4.
Guided Exercise: Find and Inspect Container Images"). Rispetto alle versioni
precedenti del corso e' cambiato l'host del registry della classroom
(ora registry.lab.example.com:8443, non piu' registry.ocp4.example.com:8443)
e sono comparse le immagini RHEL10 (rhel10/mariadb-118 al posto di
rhel9/mysql-80), coerentemente con l'update RHOCP 4.22/RHEL10.

Stato finale atteso nel progetto pods-images, prima di "lab finish" (i tre
pod restano volutamente in esecuzione fino al Finish, la guida non li fa
eliminare):

  - docker-nginx: creato al punto 3 con l'immagine
    redhattraining/docker-nginx:1.23 (che richiede l'utente root, quindi va
    in CrashLoopBackOff su un cluster non privilegiato) e va ELIMINATO al
    punto 3.8 dopo la diagnosi - quindi il check giusto e' che NON esista
    piu', non che sia Running.
  - bitnami-mysql: creato al punto 4.5 con
    redhattraining/bitnami-mysql:8.0.31 e MYSQL_ROOT_PASSWORD=redhat123,
    deve restare Running.
  - rhel10-mariadb: il primo tentativo (punto 6) senza env va in
    CrashLoopBackOff ed e' esplicitamente eliminato al punto 7.1; il pod
    finale (punto 7.2) usa rhel10/mariadb-118:1-2 con MYSQL_USER=redhat,
    MYSQL_PASSWORD=redhat123, MYSQL_DATABASE=worldx e deve restare Running.
  - mariadbclient: creato al punto 9.2 con la stessa immagine
    rhel10/mariadb-118:1-2 e MYSQL_ROOT_PASSWORD=redhat123, usato solo per
    verificare (mariadb-show, punto 9.3) che il database worldx su
    rhel10-mariadb sia raggiungibile.

Non gradiamo: i nomi dei pod di debug (oc debug pod/docker-nginx crea un
pod "docker-nginx-debug-<random>" con suffisso casuale, non deterministico -
regola d'oro, non lo inventiamo), ne' i valori esplorativi di sola lettura
(tag disponibili via skopeo, UID del container, output di oc image info):
sono verifiche che lo studente fa a schermo, non producono stato persistente
diverso da quanto gia' coperto dai pod sopra.

Uso: pods-images.py [nome-progetto]   (default: pods-images)
"""

import subprocess
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "pods-images"

BITNAMI_MYSQL_IMAGE = "registry.lab.example.com:8443/redhattraining/bitnami-mysql:8.0.31"
MARIADB_IMAGE = "registry.lab.example.com:8443/rhel10/mariadb-118:1-2"

BITNAMI_MYSQL_ENV = {"MYSQL_ROOT_PASSWORD": "redhat123"}
RHEL10_MARIADB_ENV = {
    "MYSQL_USER": "redhat",
    "MYSQL_PASSWORD": "redhat123",
    "MYSQL_DATABASE": "worldx",
}
MARIADBCLIENT_ENV = {"MYSQL_ROOT_PASSWORD": "redhat123"}


def get_container(pod, name):
    """Il pod e' creato con `oc run <name> --image ...`, quindi contiene un
    solo container; per robustezza cerchiamo comunque per nome prima di
    ripiegare sul primo."""
    containers = (pod.get("spec") or {}).get("containers", [])
    for c in containers:
        if c.get("name") == name:
            return c
    return containers[0] if containers else None


def container_env(container):
    return {e.get("name"): e.get("value") for e in (container.get("env") or [])}


def check_pod(project, name, expected_image, expected_env, step):
    """Verifica esistenza/stato Running/immagine/env di un pod creato con
    `oc run`. Ritorna il pod (o None) per eventuali controlli successivi."""
    pod = oc_get_json("pod", name, "-n", project)
    if pod is None:
        step.fail(f"Pod '{name}' non trovato nel progetto")
        return None

    phase = (pod.get("status") or {}).get("phase")
    if phase != "Running":
        step.add_error(f"Il pod '{name}' e' in stato '{phase}', atteso 'Running'")

    container = get_container(pod, name)
    if container is None:
        step.add_error(f"Nessun container trovato nel pod '{name}'")
        return pod

    if container.get("image") != expected_image:
        step.add_error(
            f"Immagine inattesa per '{name}': {container.get('image')} "
            f"(attesa: {expected_image})"
        )

    env = container_env(container)
    for key, expected in expected_env.items():
        actual = env.get(key)
        if actual != expected:
            step.add_error(
                f"Variabile '{key}' del pod '{name}' deve essere '{expected}' "
                f"(trovata: {actual!r})"
            )

    return pod


def check_worldx_reachable(project, mariadb_ip):
    """Replica il punto 9.3 della guida: dal pod mariadbclient interroga
    (sola lettura, nessuna modifica al cluster) il database worldx esposto
    dal pod rhel10-mariadb con le credenziali 'redhat'/'redhat123'. Ritorna
    True se 'worldx' compare nell'elenco dei database."""
    result = subprocess.run(
        [
            "oc", "exec", "mariadbclient", "-n", project, "--",
            "mariadb-show", "-uredhat", "-predhat123", "-h", mariadb_ip,
        ],
        capture_output=True, text=True, timeout=30,
    )
    return result.returncode == 0 and "worldx" in result.stdout


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep("Il pod docker-nginx e' stato eliminato dopo la diagnosi (punto 3.8)") as step:
        if oc_get_json("pod", "docker-nginx", "-n", project) is not None:
            step.add_error(
                "Il pod 'docker-nginx' esiste ancora: la guida chiede di eliminarlo "
                "con 'oc delete pod docker-nginx' dopo averne diagnosticato il "
                "CrashLoopBackOff (immagine che richiede l'utente root)"
            )

    with GradingStep("Il pod bitnami-mysql e' in esecuzione con l'immagine e le credenziali corrette") as step:
        check_pod(project, "bitnami-mysql", BITNAMI_MYSQL_IMAGE, BITNAMI_MYSQL_ENV, step)

    rhel10_mariadb_pod = None
    with GradingStep("Il pod rhel10-mariadb e' in esecuzione con l'immagine e le variabili corrette") as step:
        rhel10_mariadb_pod = check_pod(project, "rhel10-mariadb", MARIADB_IMAGE, RHEL10_MARIADB_ENV, step)

    with GradingStep("Il pod mariadbclient e' in esecuzione con l'immagine e le credenziali corrette") as step:
        check_pod(project, "mariadbclient", MARIADB_IMAGE, MARIADBCLIENT_ENV, step)

    with GradingStep("Il database worldx su rhel10-mariadb e' raggiungibile dal pod mariadbclient") as step:
        mariadb_ip = (rhel10_mariadb_pod or {}).get("status", {}).get("podIP")
        if not mariadb_ip:
            step.fail("IP del pod rhel10-mariadb non disponibile (pod assente o non ancora schedulato)")
        elif not check_worldx_reachable(project, mariadb_ip):
            step.add_error(
                "mariadb-show da mariadbclient verso rhel10-mariadb non ha restituito "
                "'worldx': verifica che entrambi i pod siano Running e le credenziali "
                "(redhat/redhat123) siano corrette"
            )


if __name__ == "__main__":
    main()
