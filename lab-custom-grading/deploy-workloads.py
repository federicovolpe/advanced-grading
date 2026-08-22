#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato deploy-workloads, sprovvisto di
`lab grade` ufficiale (la classe DeployWorkloads nel pacchetto do180
implementa solo start()/finish(), non grade()).

Nessuna cartella materials/labs o materials/solutions per questo esercizio
(e' puramente imperativo, niente manifest YAML da applicare): lo studente
crea un deployment "my-db" con l'immagine rhel10/mariadb-118 (che parte in
crash loop perche' mancano le variabili d'ambiente MySQL), lo ripara
impostando MYSQL_USER/MYSQL_PASSWORD/MYSQL_DATABASE con `oc set env`, e crea
un job "date-loop" (immagine ubi9/ubi) che stampa la data ripetutamente
(vedi manuale, cap. 4.4, sezione "Guided Exercise" fino a "Finish").

Non gradati (per la regola d'oro: nessun valore atteso oggettivo, o passo
solo dimostrativo senza stato persistente da verificare):
- il pod ephemeral "db-test" (creato con `oc run --restart=Never` per una
  singola query "select 1;"): e' un test una tantum, non fa parte degli
  "Outcomes" elencati (creare deployment, aggiornare env, creare/eseguire
  job, leggerne i log/lo stato di terminazione), e il nome/l'esistenza del
  pod al termine dell'esercizio dipendono da quando lo studente lo elimina;
- i passi 3 e 5 della guida (cancellare il pod di my-db/date-loop e
  osservare se viene ricreato): sono verifiche interattive sul
  comportamento del controller, non lasciano una differenza di stato
  osservabile in retrospettiva rispetto a "non li ho mai eseguiti" (un
  deployment Ready e un job completato appaiono identici prima e dopo);
  l'unico stato oggettivo e duraturo da gradare e' che il deployment sia
  pronto e il job sia arrivato a completamento.

Uso: deploy-workloads.py [nome-progetto]   (default: deploy-workloads)
"""

import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "deploy-workloads"
DEPLOYMENT_NAME = "my-db"
EXPECTED_DB_IMAGE_SUBSTR = "mariadb-118"
EXPECTED_ENV = {
    "MYSQL_USER": "developer",
    "MYSQL_PASSWORD": "developer",
    "MYSQL_DATABASE": "sampledb",
}
JOB_NAME = "date-loop"
EXPECTED_JOB_IMAGE_SUBSTR = "ubi9/ubi"


def get_container(pod_spec, name):
    """Cerca il container per nome; se non lo trova (il nome del container
    generato da `oc create deployment` non e' documentato nel manuale, a
    differenza del job dove la guida mostra esplicitamente "name: date-loop"
    nello YAML) usa il primo container, come gia' fatto in deploy-services.py
    per lo stesso motivo."""
    containers = pod_spec.get("containers", [])
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


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    deployment = oc_get_json("deployment", DEPLOYMENT_NAME, "-n", project)
    db_container = None

    with GradingStep(f"Il deployment {DEPLOYMENT_NAME} esiste con l'immagine MariaDB corretta") as step:
        if deployment is None:
            step.fail(f"Deployment '{DEPLOYMENT_NAME}' non trovato nel progetto")
        else:
            db_container = get_container(deployment["spec"]["template"]["spec"], DEPLOYMENT_NAME)
            if db_container is None:
                step.add_error("Nessun container trovato nel deployment")
            elif EXPECTED_DB_IMAGE_SUBSTR not in db_container.get("image", ""):
                step.add_error(
                    f"Immagine inattesa: {db_container.get('image')} "
                    f"(deve contenere '{EXPECTED_DB_IMAGE_SUBSTR}')"
                )

    with GradingStep("Le variabili d'ambiente MySQL sono impostate correttamente") as step:
        if db_container is None:
            step.fail()
        else:
            check_env(db_container, step)

    with GradingStep(f"Il deployment {DEPLOYMENT_NAME} ha almeno una replica pronta") as step:
        if deployment is None:
            step.fail()
        else:
            ready = deployment.get("status", {}).get("readyReplicas", 0)
            if not ready:
                step.add_error(
                    "status.readyReplicas e' 0: il server MariaDB non parte "
                    "correttamente (verificare le variabili d'ambiente MySQL)"
                )

    job = oc_get_json("job", JOB_NAME, "-n", project)
    job_container = None

    with GradingStep(f"Il job {JOB_NAME} esiste con l'immagine corretta") as step:
        if job is None:
            step.fail(f"Job '{JOB_NAME}' non trovato nel progetto")
        else:
            job_container = get_container(job["spec"]["template"]["spec"], JOB_NAME)
            if job_container is None:
                step.add_error("Nessun container trovato nel job")
            elif EXPECTED_JOB_IMAGE_SUBSTR not in job_container.get("image", ""):
                step.add_error(
                    f"Immagine inattesa: {job_container.get('image')} "
                    f"(deve contenere '{EXPECTED_JOB_IMAGE_SUBSTR}')"
                )

    with GradingStep(f"Il job {JOB_NAME} esegue uno script che stampa la data ripetutamente") as step:
        if job_container is None:
            step.fail()
        else:
            command = job_container.get("command") or []
            args = job_container.get("args") or []
            full = " ".join(command + args)
            # Non pretendiamo il numero esatto di iterazioni (incidentale):
            # basta che lo script richiami il comando `date` come da manuale.
            if not re.search(r"\bdate\b", full):
                step.add_error(
                    f"Il comando del container non richiama 'date': {command + args!r}"
                )

    with GradingStep(f"Il job {JOB_NAME} e' stato completato con successo") as step:
        if job is None:
            step.fail()
        elif not job.get("status", {}).get("succeeded"):
            step.add_error("Il job non risulta completato con successo (status.succeeded)")


if __name__ == "__main__":
    main()
