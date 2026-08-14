#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato updates-rollout, sprovvisto di
`lab grade` ufficiale (la classe UpdatesRollout nel pacchetto do180
implementa solo start()/finish(), non grade()).

L'esercizio non ha una cartella materials/solutions (e' un esercizio guidato
puramente imperativo: lo studente esegue una sequenza di comandi `oc set env`
/ `oc set image` su due deployment gia' distribuiti da start(), db.yaml e
web.yaml). Il riferimento allo stato finale atteso e' il file
DO180/materials/labs/updates-rollout/resources.txt, che elenca in ordine i
comandi che lo studente deve eseguire:

  oc set env deployment/mydb MYSQL_PASSWORD=redhat123
  oc set image deployment/mydb mysql-80=.../rhel9/mysql-80:1-228
  oc set image deployment/version versioned-hello=.../versioned-hello:v1.1

Questo script verifica quindi lo stato live dei due deployment nei due
progetti creati da start() (updates-rollout-db e updates-rollout-web,
vedi do180/updates-rollout.py: project_db/project_web = __LAB__ + "-db"/"-web"):

  - deployment/mydb (progetto -db): env MYSQL_PASSWORD aggiornata a
    "redhat123" e immagine del container mysql-80 aggiornata al tag 1-228
    (era 1-224 in db.yaml).
  - deployment/version (progetto -web): immagine del container
    versioned-hello aggiornata al tag v1.1 (era v1.0 in web.yaml), e il
    rollout e' andato a buon fine (tutte le 10 repliche pronte e aggiornate),
    a conferma che la readinessProbe configurata in web.yaml ha permesso un
    rolling update corretto.

Non vengono gradati i passaggi puramente di introspezione (query mysql,
lettura immagine del pod/replicaset, lettura della readinessProbe) perche'
non cambiano stato e non sono verificabili a posteriori.

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
DB_CONTAINER = "mysql-80"
EXPECTED_DB_IMAGE_TAG = "mysql-80:1-228"
EXPECTED_DB_ENV = {"MYSQL_PASSWORD": "redhat123"}

WEB_DEPLOYMENT = "version"
WEB_CONTAINER = "versioned-hello"
EXPECTED_WEB_IMAGE_TAG = "versioned-hello:v1.1"


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

    with GradingStep("L'immagine del database e' stata aggiornata al tag 1-228") as step:
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

    with GradingStep("L'immagine dell'applicazione web e' stata aggiornata al tag v1.1") as step:
        if web_container is None:
            step.fail()
        else:
            check_image_tag(web_container, EXPECTED_WEB_IMAGE_TAG, step)

    with GradingStep("Il rolling update del deployment version e' andato a buon fine") as step:
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
