#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato deploy-newapp, sprovvisto di
`lab grade` ufficiale (la classe DeployNewapp nel pacchetto do180 implementa
solo start()/finish(), non grade()).

ATTENZIONE: questo script sostituisce integralmente una versione precedente
scritta per un'edizione pre-RHEL10 del corso, il cui esercizio era diverso
(un solo database MySQL dal template mysql-persistent, da lasciare in
esecuzione con PVC Bound fino a lab finish). Nell'edizione RHOCP 4.22/RHEL10
(manuale DO180-RHOCP4.22-en-1-20260730, sez. 4.2) l'esercizio e' cambiato:
lo studente crea DUE istanze database per confrontare i metodi "da template"
e "da immagine", poi ELIMINA quella da template prima di lab finish. Lo
script vecchio avrebbe dato FAIL sullo stato finale corretto (si aspettava
PVC/Secret ancora presenti a fine esercizio, che invece vanno cancellati).

Riassunto esercizio attuale (dal manuale):
  1. oc new-app --name mysql --template mysql-persistent -l team=red \
       -p MYSQL_USER=developer -p MYSQL_PASSWORD=developer
     -> crea Secret/Service/PVC/Deployment "mysql" con label team=red.
  2. oc new-app --name mariadb -l team=blue \
       --image registry.lab.example.com:8443/rhel10/mariadb-118:latest \
       -e MYSQL_USER=developer -e MYSQL_PASSWORD=developer \
       -e MYSQL_ROOT_PASSWORD=redhat
     -> crea ImageStream/Deployment/Service "mariadb" con label team=blue,
        credenziali passate come env var in chiaro (nessun Secret).
  3. Osservazioni comparative (readinessProbe, resource limits, secret) sui
     due pod: sono solo "observe" testuali nella guida, nessuna azione dello
     studente da verificare -> non gradate (regola "gradua solo cio' che si
     chiede di fare/creare").
  4. Passo finale prima di "Finish": `oc delete all -l team=red` seguito da
     `oc delete secret,pvc -l team=red`, quindi a fine esercizio NON deve
     rimanere nessuna risorsa con label team=red, mentre le risorse team=blue
     (mariadb) restano.

Il nome del progetto ("deploy-newapp") e i nomi "mysql"/"mariadb" sono
dettati esplicitamente dal comando di riferimento nel manuale (non lasciati
alla scelta dello studente), ma per robustezza cerchiamo comunque il
deployment mariadb anche per label/immagine oltre che per nome, nello stesso
stile di storage-configs.py: se lo studente ha seguito il comando cosi'
com'e' scritto lo troviamo comunque, e non avremmo un falso negativo per
una piccola variazione di nome.

Non verifichiamo i VALORI esatti delle credenziali (developer/developer/
redhat): il manuale li mostra come esempio del comando, ma nessun passo
successivo li usa per un confronto verificabile (a differenza di label,
probe, secret/no-secret, che SONO usati esplicitamente per il confronto
didattico) -> per la regola d'oro non inventiamo un controllo su valori che
il manuale non richiede di verificare.

Uso: deploy-newapp.py [nome-progetto]   (default: deploy-newapp)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "deploy-newapp"
MARIADB_IMAGE_HINT = "mariadb-118"
EXPECTED_PORT = 3306
MARIADB_ENV_VARS = ["MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_ROOT_PASSWORD"]
RED_LABEL_SELECTOR = "team=red"
BLUE_LABEL_SELECTOR = "team=blue"


def find_mariadb_deployment(project):
    """Cerca il Deployment creato da `oc new-app --image .../mariadb-118...`.
    Prova prima per label team=blue (imposta esplicitamente dal comando di
    riferimento), poi per immagine, cosi' un piccolo errore su un solo
    criterio non causa un falso negativo."""
    by_label = oc_get_json("deployment", "-n", project, "-l", BLUE_LABEL_SELECTOR)
    if by_label and by_label.get("items"):
        return by_label["items"][0]

    deployments = oc_get_json("deployment", "-n", project)
    if not deployments:
        return None
    for dep in deployments.get("items", []):
        for c in dep["spec"]["template"]["spec"].get("containers", []):
            if MARIADB_IMAGE_HINT in c.get("image", ""):
                return dep
    return None


def get_container(deployment):
    containers = deployment["spec"]["template"]["spec"].get("containers", [])
    return containers[0] if containers else None


def find_matching_service(project, pod_labels):
    """Cerca un Service il cui selector e' soddisfatto dalle label del pod
    template del deployment mariadb (stesso approccio di storage-configs.py:
    non assumiamo che il Service si chiami esattamente "mariadb")."""
    if not pod_labels:
        return None
    services = oc_get_json("service", "-n", project)
    if not services:
        return None
    for svc in services.get("items", []):
        selector = svc.get("spec", {}).get("selector") or {}
        if selector and all(pod_labels.get(k) == v for k, v in selector.items()):
            return svc
    return None


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    deployment = find_mariadb_deployment(project)
    container = get_container(deployment) if deployment else None

    with GradingStep(
        f"Un database e' stato distribuito da immagine ({MARIADB_IMAGE_HINT})"
    ) as step:
        if deployment is None:
            step.fail(
                f"Nessun Deployment nel progetto usa un'immagine "
                f"contenente '{MARIADB_IMAGE_HINT}' ne' ha la label "
                f"{BLUE_LABEL_SELECTOR}"
            )

    with GradingStep("Il pod del database (immagine) e' in esecuzione e pronto") as step:
        if deployment is None:
            step.fail()
        else:
            ready = deployment.get("status", {}).get("readyReplicas", 0)
            if not ready:
                step.add_error(
                    f"Nessuna replica pronta per il deployment "
                    f"'{deployment['metadata']['name']}'"
                )

    with GradingStep(
        f"Il deployment ha la label {BLUE_LABEL_SELECTOR} richiesta dal comando new-app"
    ) as step:
        if deployment is None:
            step.fail()
        elif deployment.get("metadata", {}).get("labels", {}).get("team") != "blue":
            step.add_error(
                f"Il deployment '{deployment['metadata']['name']}' non ha "
                f"la label {BLUE_LABEL_SELECTOR}"
            )

    with GradingStep(
        "Le credenziali del database (immagine) sono passate come env var, non da Secret"
    ) as step:
        if container is None:
            step.fail()
        else:
            for env_name in MARIADB_ENV_VARS:
                entry = next(
                    (e for e in container.get("env", []) if e.get("name") == env_name),
                    None,
                )
                if entry is None:
                    step.add_error(f"Variabile d'ambiente {env_name} non definita")
                elif "value" not in entry:
                    step.add_error(
                        f"{env_name} non e' un valore in chiaro (il metodo da "
                        "immagine, a differenza del template, non usa un Secret)"
                    )

    with GradingStep(f"Il servizio del database (immagine) espone la porta {EXPECTED_PORT}") as step:
        if deployment is None:
            step.fail()
        else:
            pod_labels = (
                deployment["spec"]["template"].get("metadata", {}).get("labels", {})
            )
            svc = find_matching_service(project, pod_labels)
            if svc is None:
                step.add_error(
                    "Nessun Service trovato con un selector che corrisponde "
                    "al pod template del deployment"
                )
            else:
                ports = [p.get("port") for p in svc.get("spec", {}).get("ports", [])]
                if EXPECTED_PORT not in ports:
                    step.add_error(
                        f"Il Service '{svc['metadata']['name']}' non espone "
                        f"la porta {EXPECTED_PORT} (porte trovate: {ports})"
                    )

    with GradingStep(
        f"Le risorse del database da template ({RED_LABEL_SELECTOR}) sono state eliminate"
    ) as step:
        # Ultimo passo della guida prima di "Finish": `oc delete all -l
        # team=red` + `oc delete secret,pvc -l team=red`. A differenza degli
        # altri check qui sopra, questo si aspetta l'ASSENZA delle risorse:
        # e' lo stato corretto solo dopo che lo studente ha completato anche
        # l'ultimo passo dell'esercizio, non un dettaglio dello starter.
        leftover = oc_get_json(
            "deployment,service,secret,pvc", "-l", RED_LABEL_SELECTOR, "-n", project
        )
        items = leftover.get("items", []) if leftover else []
        if items:
            kinds = ", ".join(
                f"{i['kind']}/{i['metadata']['name']}" for i in items
            )
            step.add_error(
                f"Risorse con label {RED_LABEL_SELECTOR} ancora presenti "
                f"(andavano eliminate con 'oc delete all -l {RED_LABEL_SELECTOR}' "
                f"e 'oc delete secret,pvc -l {RED_LABEL_SELECTOR}'): {kinds}"
            )


if __name__ == "__main__":
    main()
