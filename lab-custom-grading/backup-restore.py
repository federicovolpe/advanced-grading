#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato backup-restore (DO380, Cap. 2.6
"Back up and Restore with OADP"), sprovvisto di `lab grade` ufficiale
(la classe BackupRestore implementa solo start()/finish()).

Specifica ricavata dal diff labs/solutions (backup-db-manual.yaml,
restore-db-crash.yaml, schedule-db-backup.yaml) e dal testo della guida
studente (pag. 182-193): lo studente fa un backup crash-consistent del
progetto "database" e lo ripristina in un nuovo progetto "database-crash",
poi programma un backup settimanale application-consistent (con hook di
quiesce sul DB) e ne innesca uno manualmente, ripristinandolo in un
ulteriore progetto "database-backup". L'ultimo passo della guida (10.1 e
10.2) fa esplicitamente cancellare TUTTI i Backup/Restore/Schedule Velero
nel namespace openshift-adp (db-manual+db-crash gia' rimossi al passo 6.2,
poi i backup con label velero.io/schedule-name=db-backup e la Schedule
stessa al passo 10) prima di "Finish": cancellare un Backup Velero non
cancella pero' le risorse gia' ripristinate nel cluster (solo il record
Backup/Restore e i file su S3), quindi l'unica prova persistente e
verificabile a fine esercizio sono i due progetti "database-crash" e
"database-backup" con il deployment MariaDB ripristinato e pronto - e il
fatto che openshift-adp non contenga piu' alcun Backup/Restore/Schedule.
Non gradiamo le CR Velero (db-manual/db-crash/db-backup) proprio perche'
la guida le fa cancellare: la loro assenza a fine esercizio e' corretta,
non un fallimento.

Uso: backup-restore.py [nome-progetto]   (default: backup-restore, usato
solo per l'intestazione: le risorse vere sono in altri namespace)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "backup-restore"

RESTORED_PROJECTS = ["database-crash", "database-backup"]


def check_mariadb_restored(project, step):
    if not project_exists(project):
        step.fail(f"Progetto '{project}' non trovato")
        return

    deployment = oc_get_json("deployment", "mariadb", "-n", project)
    if deployment is None:
        step.add_error(f"Deployment 'mariadb' non trovato nel progetto {project}")
    else:
        status = deployment.get("status", {})
        if status.get("readyReplicas", 0) < 1:
            step.add_error(
                f"Il deployment 'mariadb' in {project} non ha repliche pronte"
            )

    pvc = oc_get_json("pvc", "mariadb", "-n", project)
    if pvc is None:
        step.add_error(f"PVC 'mariadb' non trovata nel progetto {project}")
    elif pvc.get("status", {}).get("phase") != "Bound":
        step.add_error(f"La PVC 'mariadb' in {project} non e' nello stato Bound")

    secret = oc_get_json("secret", "mariadb", "-n", project)
    if secret is None:
        step.add_error(f"Secret 'mariadb' non trovato nel progetto {project}")


def main():
    project_hint = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (riferimento: {project_hint})")

    for project in RESTORED_PROJECTS:
        with GradingStep(
            f"Il progetto {project} esiste con MariaDB ripristinato"
        ) as step:
            check_mariadb_restored(project, step)

    with GradingStep(
        "Le risorse Velero (Backup/Restore/Schedule) sono state rimosse da openshift-adp"
    ) as step:
        if not project_exists("openshift-adp"):
            step.add_error("Progetto 'openshift-adp' non trovato")
        else:
            for kind in ("backup", "restore", "schedule"):
                result = oc_get_json(kind, "-n", "openshift-adp")
                if result is not None and result.get("items"):
                    names = ", ".join(
                        i["metadata"]["name"] for i in result["items"]
                    )
                    step.add_error(
                        f"Trovate risorse '{kind}' non rimosse in openshift-adp: {names}"
                    )


if __name__ == "__main__":
    main()
