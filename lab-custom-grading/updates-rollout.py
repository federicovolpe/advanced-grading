#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato updates-rollout, sprovvisto di
`lab grade` ufficiale (la classe UpdatesRollout nel pacchetto do180
implementa solo start()/finish(), non grade()).

L'esercizio non ha una cartella materials/solutions (e' un esercizio guidato
puramente imperativo: lo studente esegue una sequenza di comandi `oc set env`
/ `oc set image` su due deployment gia' distribuiti da start(), db.yaml e
web.yaml). Il riferimento allo stato finale atteso e' il manuale ufficiale
(sezione 7.4, DO180-RHOCP4.22) insieme a
materials/labs/updates-rollout/resources.txt, che elencano in ordine i
comandi che lo studente deve eseguire:

  oc set env deployment/mydb MYSQL_PASSWORD=redhat123
  oc set image deployment/mydb mariadb-118=.../rhel10/mariadb-118:1784149182
  oc set image deployment/version versioned-hello=.../versioned-hello:v1.1
  oc rollout undo deployment/version

Nella versione RHOCP4.22/RHEL10 del corso il database e' passato da un
container MySQL ("mysql-80") a un container MariaDB RHEL10 ("mariadb-118",
immagine rhel10/mariadb-118, tag numerico timestamp anziche' "1-NNN"): la
versione precedente di questo script gradava ancora container "mysql-80" e
tag "1-228", che non esistono piu' in db.yaml (vedi
do180/exercises/updates_rollout.py: check_images_exist elenca
"rhel10/mariadb-118:1783945307"/"...:1784149182", e
materials/labs/updates-rollout/lab-start/db.yaml usa
name: mariadb-118 / image: .../rhel10/mariadb-118:1783945307).

Questo script verifica quindi lo stato live dei due deployment nei due
progetti creati da start() (updates-rollout-db e updates-rollout-web,
vedi do180/exercises/updates_rollout.py: project_db/project_web = LAB + "-db"/"-web"):

  - deployment/mydb (progetto -db): env MYSQL_PASSWORD aggiornata a
    "redhat123" e immagine del container mariadb-118 aggiornata al tag
    1784149182 (era 1783945307 in db.yaml).
  - deployment/version (progetto -web): il Punto 9 della guida ("Roll back
    the version deployment") e' l'ULTIMO passo prima di "Finish" e chiede
    esplicitamente `oc rollout undo deployment/version` (senza
    --to-revision, quindi torna alla revisione precedente), confermato al
    punto 9.3 dove il ReplicaSet iniziale risale a 10/10/10 e quello v1.1
    scende a 0/0/0. Lo stato finale corretto e' quindi immagine
    versioned-hello:v1.0 (non v1.1: quel tag e' solo lo stato INTERMEDIO,
    verificato ai punti 5-8 prima del rollback, non quello che deve
    risultare a fine esercizio). Un primo tentativo di questo script gradava
    v1.1 come stato finale: chi completava l'esercizio fino in fondo,
    rollback incluso, riceveva FAIL, mentre chi si fermava prima del
    rollback riceveva PASS — logica invertita, corretta qui.

Non vengono gradati i passaggi puramente di introspezione (query mariadb,
lettura immagine del pod/replicaset, lettura della readinessProbe, pausa/
ripresa del rollout) perche' non cambiano stato persistente e non sono
verificabili a posteriori: solo lo stato FINALE dei due deployment conta.

Uso: updates-rollout.py [nome-progetto-base]   (default: updates-rollout)
Il nome-progetto-base viene usato per derivare i due progetti "<base>-db" e
"<base>-web", come fa lo start() ufficiale.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "updates-rollout"

DB_DEPLOYMENT = "mydb"
DB_CONTAINER = "mariadb-118"
EXPECTED_DB_IMAGE_TAG = "mariadb-118:1784149182"
EXPECTED_DB_ENV = {"MYSQL_PASSWORD": "redhat123"}

WEB_DEPLOYMENT = "version"
WEB_CONTAINER = "versioned-hello"
# Stato FINALE atteso a fine esercizio: v1.0, non v1.1 — il Punto 9 della
# guida ("Roll back the version deployment") e' l'ultimo passo prima di
# "Finish" e riporta il deployment a v1.0 con 'oc rollout undo'. v1.1 e'
# solo lo stato intermedio verificato ai punti 5-8, prima del rollback.
EXPECTED_WEB_IMAGE_TAG = "versioned-hello:v1.0"


def get_container(deployment, name):
    containers = deployment["spec"]["template"]["spec"]["containers"]
    for c in containers:
        if c.get("name") == name:
            return c
    return containers[0] if containers else None


def check_env(container, expected, step):
    env_map = {e.get("name"): e.get("value") for e in container.get("env", []) or []}
    for key, expected_value in expected.items():
        actual = env_map.get(key)
        if actual != expected_value:
            step.add_error(f"{key} deve essere '{expected_value}' (trovato: {actual!r})")


def check_image_tag(container, expected_tag, step):
    image = container.get("image", "")
    if not image.endswith(expected_tag):
        step.add_error(
            f"Immagine non aggiornata: {image!r} (atteso un tag che termini con '{expected_tag}')"
        )


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    project_db = f"{base}-db"
    project_web = f"{base}-web"
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetti: {project_db}, {project_web})")

    with GradingStep(f"Il progetto {project_db} esiste") as step:
        if not project_exists(project_db):
            step.fail(f"Progetto '{project_db}' non trovato")

    with GradingStep(f"Il progetto {project_web} esiste") as step:
        if not project_exists(project_web):
            step.fail(f"Progetto '{project_web}' non trovato")

    db_deployment = oc_get_json("deployment", DB_DEPLOYMENT, "-n", project_db)
    db_container = None

    with GradingStep(f"Il deployment {DB_DEPLOYMENT} esiste") as step:
        if db_deployment is None:
            step.fail(f"Deployment '{DB_DEPLOYMENT}' non trovato nel progetto {project_db}")
        else:
            db_container = get_container(db_deployment, DB_CONTAINER)
            if db_container is None:
                step.fail("Nessun container trovato nel deployment")

    with GradingStep("La password del database e' stata aggiornata (MYSQL_PASSWORD)") as step:
        if db_container is None:
            step.fail()
        else:
            check_env(db_container, EXPECTED_DB_ENV, step)

    with GradingStep("L'immagine del database e' stata aggiornata al tag 1784149182") as step:
        if db_container is None:
            step.fail()
        else:
            check_image_tag(db_container, EXPECTED_DB_IMAGE_TAG, step)

    web_deployment = oc_get_json("deployment", WEB_DEPLOYMENT, "-n", project_web)
    web_container = None

    with GradingStep(f"Il deployment {WEB_DEPLOYMENT} esiste") as step:
        if web_deployment is None:
            step.fail(f"Deployment '{WEB_DEPLOYMENT}' non trovato nel progetto {project_web}")
        else:
            web_container = get_container(web_deployment, WEB_CONTAINER)
            if web_container is None:
                step.fail("Nessun container trovato nel deployment")

    with GradingStep("L'applicazione web e' stata riportata al tag v1.0 (rollback finale)") as step:
        if web_container is None:
            step.fail()
        else:
            check_image_tag(web_container, EXPECTED_WEB_IMAGE_TAG, step)

    with GradingStep("Il rollback del deployment version e' andato a buon fine") as step:
        if web_deployment is None:
            step.fail()
        else:
            spec_replicas = web_deployment["spec"].get("replicas", 0)
            status = web_deployment.get("status", {})
            updated = status.get("updatedReplicas", 0)
            ready = status.get("readyReplicas", 0)
            unavailable = status.get("unavailableReplicas", 0)
            if spec_replicas == 0:
                step.add_error("spec.replicas e' 0, impossibile verificare il rollout")
            if updated != spec_replicas:
                step.add_error(
                    f"updatedReplicas={updated}, attese {spec_replicas} "
                    "(il rollout dell'immagine non risulta completo)"
                )
            if ready != spec_replicas:
                step.add_error(
                    f"readyReplicas={ready}, attese {spec_replicas} "
                    "(non tutte le repliche sono pronte)"
                )
            if unavailable:
                step.add_error(f"unavailableReplicas={unavailable}, atteso 0")


if __name__ == "__main__":
    main()
