#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato deploy-services, sprovvisto di
`lab grade` ufficiale (la classe DeployServices nel pacchetto do180
implementa solo start()/finish(), non grade()).

Aggiornato alla versione RHOCP 4.22 / RHEL10 del corso (manuale
"4.6. Guided Exercise Kubernetes Pod and Service Networks"): rispetto alla
versione precedente di questo script sono cambiati:
  - l'immagine del database: rhel10/mariadb-118 (non piu' rhel8/mysql-80).
    Confermata anche da start() -> images.check_images_exist(["rhel10/
    mariadb-118", "redhattraining/do180-dbinit"]).
  - lo studente crea un Deployment "db-pod" (con `oc create deployment`,
    NON un pod nudo con `oc run`): il pod effettivo ha un nome generato con
    hash-suffix (es. db-pod-6f6bb8c847-zdfjb), quindi non si puo' cercare
    un pod chiamato letteralmente "db-pod" per nome esatto (bug della
    versione precedente) - va cercato per label, usando il selector del
    Deployment stesso (di default app=db-pod, impostato da `oc create
    deployment`).
  - il Job di inizializzazione si chiama "mariadb-init" (non "mysql-init")
    e usa l'immagine redhattraining/do180-dbinit:v2 (basata su
    mariadb-118, non mysql-80). PERO' il manuale chiede esplicitamente allo
    studente di CANCELLARE questo Job una volta completato (punto 8.4:
    "Delete the mariadb-init job") prima di "lab finish": al termine
    dell'esercizio il Job non esiste piu', quindi gradarne la sola
    esistenza darebbe un falso FAIL a chi ha seguito correttamente la
    guida fino in fondo. Invece di gradare il Job, verifichiamo il suo
    EFFETTO persistente: il contenuto della tabella Item nel database (le
    due righe inserite dallo script SQL incluso nell'immagine
    do180-dbinit), interrogato in sola lettura con `oc exec` dentro il pod
    db-pod - stato che sopravvive alla cancellazione del Job.
  - il secondo progetto "deploy-services-2" (punto 7) e i pod temporanei
    "shell"/"query-db" (punti 6, 9, 10) sono creati con `--rm` o cancellati
    esplicitamente subito dopo l'uso: servono solo a testare interattivamente
    la risoluzione DNS/gli endpoint del service, non lasciano alcuno stato
    persistente da gradare.

Uso: deploy-services.py [nome-progetto]   (default: deploy-services)
"""

import subprocess
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "deploy-services"
DEPLOYMENT_NAME = "db-pod"
SERVICE_NAME = "db-pod"
EXPECTED_IMAGE_SUBSTR = "rhel10/mariadb-118"
EXPECTED_ENV = {
    "MYSQL_USER": "user1",
    "MYSQL_PASSWORD": "mypa55w0rd",
    "MYSQL_DATABASE": "items",
}
EXPECTED_PORT = 3306
# Le righe inserite dallo script SQL incluso nell'immagine do180-dbinit:v2
# (vedi il testo del manuale, punto 8.1): (id, description, done).
EXPECTED_ITEMS = {
    ("1", "Pick up newspaper", "0"),
    ("2", "Buy groceries", "1"),
}


def get_container(deployment, name=DEPLOYMENT_NAME):
    containers = deployment["spec"]["template"]["spec"]["containers"]
    for c in containers:
        if c.get("name") == name:
            return c
    return containers[0] if containers else None


def check_env(container, step):
    env_map = {e.get("name"): e.get("value") for e in container.get("env", []) or []}
    for key, expected in EXPECTED_ENV.items():
        actual = env_map.get(key)
        if actual != expected:
            step.add_error(f"{key} deve essere '{expected}' (trovato: {actual!r})")


def find_pod_by_labels(project, match_labels):
    """Cerca, fra tutti i pod del progetto, il primo le cui label
    includono match_labels: il pod creato dal Deployment ha un nome con
    hash-suffix generato automaticamente, quindi non e' cercabile per nome
    esatto (vedi commento in testa al file)."""
    if not match_labels:
        return None
    pods = oc_get_json("pod", "-n", project)
    if not pods:
        return None
    for pod in pods.get("items", []):
        labels = pod.get("metadata", {}).get("labels", {}) or {}
        if all(labels.get(k) == v for k, v in match_labels.items()):
            return pod
    return None


def query_items(project, pod_name):
    """Esegue una SELECT in sola lettura sulla tabella Item dentro il pod
    db-pod (nessuna modifica allo stato del cluster). Ritorna l'insieme di
    tuple (id, description, done), o None se la query fallisce."""
    result = subprocess.run(
        [
            "oc", "exec", f"pod/{pod_name}", "-n", project, "--",
            "mariadb", f"-u{EXPECTED_ENV['MYSQL_USER']}",
            f"-p{EXPECTED_ENV['MYSQL_PASSWORD']}", EXPECTED_ENV["MYSQL_DATABASE"],
            "-N", "-B", "-e", "SELECT id, description, done FROM Item ORDER BY id;",
        ],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        return None
    rows = set()
    for line in result.stdout.splitlines():
        fields = tuple(line.split("\t"))
        if len(fields) == 3:
            rows.add(fields)
    return rows


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    deployment = oc_get_json("deployment", DEPLOYMENT_NAME, "-n", project)
    container = None
    match_labels = None

    with GradingStep(f"Il deployment {DEPLOYMENT_NAME} esiste ed e' disponibile") as step:
        if deployment is None:
            step.fail(f"Deployment '{DEPLOYMENT_NAME}' non trovato nel progetto")
        else:
            available = deployment.get("status", {}).get("availableReplicas", 0)
            if not available:
                step.add_error("Nessuna replica disponibile (status.availableReplicas)")
            container = get_container(deployment)
            if container is None:
                step.add_error("Nessun container trovato nel deployment")
            match_labels = deployment.get("spec", {}).get("selector", {}).get("matchLabels")

    with GradingStep(f"Il deployment {DEPLOYMENT_NAME} usa l'immagine mariadb-118 corretta") as step:
        if container is None:
            step.fail()
        elif EXPECTED_IMAGE_SUBSTR not in container.get("image", ""):
            step.add_error(
                f"Immagine inattesa: {container.get('image')} "
                f"(deve contenere '{EXPECTED_IMAGE_SUBSTR}')"
            )

    with GradingStep("Le variabili d'ambiente del database sono configurate correttamente") as step:
        if container is None:
            step.fail()
        else:
            check_env(container, step)

    pod = None
    with GradingStep(f"Un pod del deployment {DEPLOYMENT_NAME} e' in esecuzione") as step:
        if match_labels is None:
            step.fail("Impossibile determinare il selector del deployment")
        else:
            pod = find_pod_by_labels(project, match_labels)
            if pod is None:
                step.add_error(
                    f"Nessun pod con label {match_labels} trovato nel progetto"
                )
            elif pod.get("status", {}).get("phase") != "Running":
                step.add_error(
                    f"Il pod e' in stato '{pod.get('status', {}).get('phase')}', atteso 'Running'"
                )

    service = oc_get_json("service", SERVICE_NAME, "-n", project)

    with GradingStep(f"Il service {SERVICE_NAME} espone correttamente la porta {EXPECTED_PORT}") as step:
        if service is None:
            step.fail(f"Service '{SERVICE_NAME}' non trovato nel progetto")
        else:
            ports = service.get("spec", {}).get("ports", [])
            if not ports:
                step.add_error("Il service non definisce alcuna porta")
            else:
                port = ports[0]
                if port.get("port") != EXPECTED_PORT:
                    step.add_error(f"Porta {port.get('port')}, attesa {EXPECTED_PORT}")
                if str(port.get("targetPort")) != str(EXPECTED_PORT):
                    step.add_error(
                        f"targetPort {port.get('targetPort')}, atteso {EXPECTED_PORT}"
                    )
                if port.get("protocol", "TCP") != "TCP":
                    step.add_error(f"Protocollo {port.get('protocol')}, atteso TCP")
            selector = (service.get("spec", {}) or {}).get("selector") or {}
            if match_labels and not all(selector.get(k) == v for k, v in match_labels.items()):
                step.add_error(
                    f"Il selector del service {selector} non corrisponde alle label del deployment {match_labels}"
                )

    with GradingStep("Il database e' stato inizializzato con i dati corretti (tabella Item)") as step:
        if pod is None or pod.get("status", {}).get("phase") != "Running":
            step.fail("Nessun pod Running su cui interrogare il database")
        else:
            pod_name = pod["metadata"]["name"]
            rows = query_items(project, pod_name)
            if rows is None:
                step.add_error(
                    "Impossibile eseguire la query nel pod (mariadb non raggiungibile, "
                    "credenziali errate, o tabella Item non ancora creata dal job "
                    "mariadb-init)"
                )
            elif not EXPECTED_ITEMS.issubset(rows):
                missing = EXPECTED_ITEMS - rows
                step.add_error(
                    f"Righe mancanti/errate nella tabella Item: {sorted(missing)} "
                    f"(trovate: {sorted(rows)})"
                )


if __name__ == "__main__":
    main()
