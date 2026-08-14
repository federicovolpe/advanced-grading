#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato deploy-newapp, sprovvisto di
`lab grade` ufficiale (la classe DeployNewapp nel pacchetto do180 implementa
solo start()/finish(), non grade()).

start() pubblica nel namespace condiviso "openshift" il template
"mysql-persistent" (vedi do180/materials/labs/deploy-newapp/
mysql-persistent-template.yaml): lo studente deve istanziarlo nel proprio
progetto per ottenere un database MySQL. A differenza della variante
"mysql-ephemeral", l'obiettivo didattico del template "persistent" e' che i
dati risiedano su storage persistente (PVC Bound) e che le credenziali siano
gestite tramite un Secret, non passate in chiaro.

Uso: deploy-newapp.py [nome-progetto]   (default: deploy-newapp)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "deploy-newapp"
EXPECTED_PORT = 3306
EXPECTED_ENV_VARS = ["MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_ROOT_PASSWORD", "MYSQL_DATABASE"]


def find_mysql_deployment(project):
    """Cerca, fra tutti i Deployment del progetto, quello generato dal
    template mysql-persistent. Lo riconosciamo dalle variabili d'ambiente
    tipiche del template e non dal nome, perche' il nome dipende dal
    parametro DATABASE_SERVICE_NAME scelto dallo studente."""
    deployments = oc_get_json("deployment", "-n", project)
    if not deployments:
        return None
    for dep in deployments.get("items", []):
        for c in dep["spec"]["template"]["spec"]["containers"]:
            env_names = {e.get("name") for e in c.get("env", [])}
            if "MYSQL_DATABASE" in env_names and "MYSQL_USER" in env_names:
                return dep
    return None


def get_container(deployment):
    containers = deployment["spec"]["template"]["spec"]["containers"]
    return containers[0] if containers else None


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    deployment = find_mysql_deployment(project)
    name = deployment["metadata"]["name"] if deployment else None
    container = get_container(deployment) if deployment else None

    with GradingStep("Il database MySQL e' stato distribuito nel progetto") as step:
        if deployment is None:
            step.fail(
                "Nessun Deployment MySQL (dal template mysql-persistent) "
                "trovato nel progetto"
            )

    with GradingStep("Il pod MySQL e' in esecuzione e pronto") as step:
        if deployment is None:
            step.fail()
        else:
            ready = deployment.get("status", {}).get("readyReplicas", 0)
            if not ready:
                step.add_error(
                    f"Nessuna replica pronta per il deployment '{name}' "
                    "(il pod non e' Running/Ready)"
                )

    with GradingStep("Le credenziali del database provengono da un Secret") as step:
        if container is None:
            step.fail()
        else:
            for env_name in EXPECTED_ENV_VARS:
                entry = next(
                    (e for e in container.get("env", []) if e.get("name") == env_name),
                    None,
                )
                if entry is None:
                    step.add_error(f"Variabile d'ambiente {env_name} non definita")
                elif "secretKeyRef" not in entry.get("valueFrom", {}):
                    step.add_error(
                        f"{env_name} non proviene da un Secret "
                        "(possibile credenziale in chiaro)"
                    )

    with GradingStep("Il database usa storage persistente (PVC Bound)") as step:
        if deployment is None:
            step.fail()
        else:
            volumes = deployment["spec"]["template"]["spec"].get("volumes", [])
            pvc_claim = next(
                (
                    v["persistentVolumeClaim"]["claimName"]
                    for v in volumes
                    if "persistentVolumeClaim" in v
                ),
                None,
            )
            if pvc_claim is None:
                step.add_error(
                    "Il pod non monta nessuna PersistentVolumeClaim "
                    "(storage non persistente)"
                )
            else:
                pvc = oc_get_json("pvc", pvc_claim, "-n", project)
                if pvc is None:
                    step.add_error(f"PVC '{pvc_claim}' non trovata nel progetto")
                elif pvc.get("status", {}).get("phase") != "Bound":
                    step.add_error(
                        f"PVC '{pvc_claim}' non e' Bound "
                        f"(stato: {pvc.get('status', {}).get('phase')})"
                    )

    with GradingStep(f"Il servizio espone la porta {EXPECTED_PORT}") as step:
        if name is None:
            step.fail()
        else:
            svc = oc_get_json("service", name, "-n", project)
            if svc is None:
                step.add_error(f"Nessun Service '{name}' trovato nel progetto")
            else:
                ports = [p.get("port") for p in svc.get("spec", {}).get("ports", [])]
                if EXPECTED_PORT not in ports:
                    step.add_error(
                        f"Il Service '{name}' non espone la porta {EXPECTED_PORT} "
                        f"(porte trovate: {ports})"
                    )


if __name__ == "__main__":
    main()
