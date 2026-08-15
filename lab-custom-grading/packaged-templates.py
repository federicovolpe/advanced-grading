#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato packaged-templates, sprovvisto di
`lab grade` ufficiale (la classe PackagedTemplates nel pacchetto do280
implementa solo start()/finish(), non grade() - vedi
do280/packaged-templates.py).

Lo start() applica gia' il template cluster-wide "mysql-persistent" nel
namespace "openshift" (rimosso dal finish()): NON e' compito dello studente
crearlo, e' solo materiale di partenza. Il compito dello studente (vedi
guida studente, sezione 2.2 "Use OpenShift Templates") e':

  1. Instanziare il template mysql-persistent nel progetto
     "packaged-templates" con `oc new-app --template=mysql-persistent
     -p MYSQL_USER=user1 -p MYSQL_PASSWORD=mypasswd` (MYSQL_DATABASE resta il
     default "sampledb"). Risultato: Secret/Service/PVC/Deployment "mysql".
  2. Creare il template custom "roster-template" nel proprio progetto da
     ~/DO280/labs/packaged-templates/custom-template/roster-template.yaml
     (`oc create -f ...`, senza -n: finisce nel progetto corrente, NON
     cluster-wide come mysql-persistent).
  3. Instanziarlo una prima volta con INIT_DB=true (stesse credenziali
     MYSQL_USER/MYSQL_PASSWORD del passo 1), poi aggiornarlo con
     roster-parameters.env (MYSQL_USER=user1, MYSQL_PASSWORD=mypasswd,
     IMAGE=.../do280-roster:v2), omettendo INIT_DB cosi' che torni al default
     "False" del template. Lo stato FINALE atteso sul cluster e' quindi
     quello dopo l'aggiornamento: immagine v2, INIT_DB=False.

Valori attesi presi da (in ordine): guida studente estratta in
packaged-templates.pdf.txt (comandi e parametri esatti degli step 3.2, 4.1-
4.5, 5.1-5.3) e materials/solutions/packaged-templates/roster-parameters.env
(MYSQL_USER, MYSQL_PASSWORD, IMAGE finali) e
materials/labs/packaged-templates/custom-template/roster-template.yaml (nomi
degli oggetti e default dei parametri del template custom, per confermare
che lo studente non l'abbia alterato).

Cosa NON viene gradato e perche':
- Il contenuto salvato dallo studente nel form dell'applicazione roster
  (step 4.9/5.5, "Enter your information..."): la guida non specifica uno
  schema di tabella/API verificabile in modo oggettivo senza assumere
  dettagli interni dell'immagine do280-roster non documentati qui.
- Il tag esatto dell'immagine mysql usata dal Deployment "mysql" (il
  parametro MYSQL_VERSION resta al default e l'immagine viene aggiornata da
  un trigger ImageChange legato all'ImageStream "mysql" in "openshift": il
  tag effettivo dipende dai tempi di import, non e' deterministico da file
  statici).
- Lo stato "Bound" della PVC "mysql": dipende dalla StorageClass/dal
  provisioner del cluster, non da un'azione dello studente.

Uso: packaged-templates.py [nome-progetto]   (default: packaged-templates)
"""

import base64
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "packaged-templates"

EXPECTED_MYSQL_USER = "user1"
EXPECTED_MYSQL_PASSWORD = "mypasswd"
EXPECTED_MYSQL_DATABASE = "sampledb"

EXPECTED_ROSTER_APPNAME = "do280-roster"
EXPECTED_ROSTER_IMAGE_SUBSTR = "do280-roster:v2"
EXPECTED_DATABASE_SERVICE_NAME = "mysql"
EXPECTED_INIT_DB = "False"


def decode_secret(secret):
    """Ritorna un dict {chiave: valore-decodificato} dai .data (base64) di
    un Secret. I .data del Secret restano tali anche se creato da
    stringData nel template: e' il server a codificarli."""
    data = secret.get("data") or {}
    decoded = {}
    for k, v in data.items():
        try:
            decoded[k] = base64.b64decode(v).decode("utf-8")
        except Exception:
            decoded[k] = None
    return decoded


def get_container(deployment, name=None):
    containers = deployment["spec"]["template"]["spec"].get("containers", [])
    if name is not None:
        for c in containers:
            if c.get("name") == name:
                return c
    return containers[0] if containers else None


def get_env(container, name):
    for e in container.get("env", []) or []:
        if e.get("name") == name:
            return e
    return None


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    # --- Istanza del template mysql-persistent ---------------------------
    mysql_secret = oc_get_json("secret", "mysql", "-n", project)
    mysql_service = oc_get_json("service", "mysql", "-n", project)
    mysql_pvc = oc_get_json("pvc", "mysql", "-n", project)
    mysql_deployment = oc_get_json("deployment", "mysql", "-n", project)

    with GradingStep(
        "Il template mysql-persistent e' stato instanziato "
        "(Secret/Service/PVC/Deployment 'mysql')"
    ) as step:
        if mysql_secret is None:
            step.add_error("Secret 'mysql' non trovato")
        if mysql_service is None:
            step.add_error("Service 'mysql' non trovato")
        if mysql_pvc is None:
            step.add_error("PersistentVolumeClaim 'mysql' non trovata")
        if mysql_deployment is None:
            step.add_error("Deployment 'mysql' non trovato")

    with GradingStep(
        "Le credenziali MySQL nel Secret 'mysql' corrispondono a quelle "
        "richieste dalla guida (user1/mypasswd/sampledb)"
    ) as step:
        if mysql_secret is None:
            step.fail()
        else:
            values = decode_secret(mysql_secret)
            if values.get("database-user") != EXPECTED_MYSQL_USER:
                step.add_error(
                    "database-user atteso "
                    f"'{EXPECTED_MYSQL_USER}', trovato "
                    f"'{values.get('database-user')}' "
                    "(atteso da 'oc new-app --template=mysql-persistent "
                    "-p MYSQL_USER=user1 ...')"
                )
            if values.get("database-password") != EXPECTED_MYSQL_PASSWORD:
                step.add_error(
                    "database-password atteso "
                    f"'{EXPECTED_MYSQL_PASSWORD}', trovato un valore diverso "
                    "(atteso da '-p MYSQL_PASSWORD=mypasswd')"
                )
            if values.get("database-name") != EXPECTED_MYSQL_DATABASE:
                step.add_error(
                    "database-name atteso "
                    f"'{EXPECTED_MYSQL_DATABASE}' (default del template), "
                    f"trovato '{values.get('database-name')}'"
                )

    with GradingStep("Il pod mysql e' in esecuzione e pronto") as step:
        if mysql_deployment is None:
            step.fail()
        else:
            ready = mysql_deployment.get("status", {}).get("readyReplicas", 0)
            if not ready:
                step.add_error("Nessuna replica pronta per il Deployment 'mysql'")

    # --- Template custom roster-template -----------------------------
    # La guida crea il template con 'oc create -f roster-template.yaml' senza
    # -n: finisce nel progetto corrente (packaged-templates), NON cluster-wide
    # come mysql-persistent. Verifichiamo che esista li' e non sia stato
    # alterato nei parametri chiave.
    roster_template = oc_get_json("template", "roster-template", "-n", project)

    with GradingStep(
        f"Il template custom 'roster-template' e' registrato nel progetto "
        f"{project}"
    ) as step:
        if roster_template is None:
            step.fail(
                "Template 'roster-template' non trovato "
                f"(atteso: 'oc create -f "
                ".../custom-template/roster-template.yaml' nel progetto "
                f"{project})"
            )

    with GradingStep(
        "Il template roster-template non e' stato alterato nei parametri "
        "principali"
    ) as step:
        if roster_template is None:
            step.fail()
        else:
            params = {
                p["name"]: p.get("value")
                for p in roster_template.get("parameters", [])
            }
            expected_defaults = {
                "APPNAME": EXPECTED_ROSTER_APPNAME,
                "DATABASE_SERVICE_NAME": EXPECTED_DATABASE_SERVICE_NAME,
                "MYSQL_DATABASE": EXPECTED_MYSQL_DATABASE,
                "INIT_DB": EXPECTED_INIT_DB,
            }
            for name, expected in expected_defaults.items():
                if params.get(name) != expected:
                    step.add_error(
                        f"Parametro {name}: atteso default '{expected}', "
                        f"trovato '{params.get(name)}'"
                    )

    # --- Istanza (aggiornata) del template roster-template ---------------
    roster_deployment = oc_get_json(
        "deployment", EXPECTED_ROSTER_APPNAME, "-n", project
    )
    roster_service = oc_get_json("service", EXPECTED_ROSTER_APPNAME, "-n", project)
    roster_route = oc_get_json("route", EXPECTED_ROSTER_APPNAME, "-n", project)

    with GradingStep(
        f"Il Deployment '{EXPECTED_ROSTER_APPNAME}' esiste ed e' pronto"
    ) as step:
        if roster_deployment is None:
            step.fail(f"Deployment '{EXPECTED_ROSTER_APPNAME}' non trovato")
        else:
            ready = roster_deployment.get("status", {}).get("readyReplicas", 0)
            if not ready:
                step.add_error(
                    f"Nessuna replica pronta per il Deployment "
                    f"'{EXPECTED_ROSTER_APPNAME}'"
                )

    with GradingStep(
        "L'applicazione roster e' stata aggiornata alla versione v2 "
        "(roster-parameters.env) e non re-inizializza il database"
    ) as step:
        if roster_deployment is None:
            step.fail()
        else:
            container = get_container(
                roster_deployment, f"{EXPECTED_ROSTER_APPNAME}-image"
            )
            if container is None:
                step.fail("Container dell'applicazione non trovato nel deployment")
            else:
                image = container.get("image", "")
                if EXPECTED_ROSTER_IMAGE_SUBSTR not in image:
                    step.add_error(
                        f"Immagine attesa con '{EXPECTED_ROSTER_IMAGE_SUBSTR}' "
                        f"(da roster-parameters.env), trovata '{image}'"
                    )
                init_db_env = get_env(container, "INIT_DB")
                init_db_value = (
                    init_db_env.get("value") if init_db_env is not None else None
                )
                if init_db_value != EXPECTED_INIT_DB:
                    step.add_error(
                        f"INIT_DB atteso '{EXPECTED_INIT_DB}' (default del "
                        "template, dato che il secondo 'oc process' omette "
                        f"il parametro), trovato '{init_db_value}'"
                    )
                for env_name, secret_key in (
                    ("MYSQL_USER", "database-user"),
                    ("MYSQL_PASSWORD", "database-password"),
                    ("MYSQL_DATABASE", "database-name"),
                    ("DATABASE_SERVICE_NAME", "database-service"),
                ):
                    env = get_env(container, env_name)
                    ref = (env or {}).get("valueFrom", {}).get("secretKeyRef", {})
                    if ref.get("name") != EXPECTED_DATABASE_SERVICE_NAME:
                        step.add_error(
                            f"La variabile {env_name} dovrebbe leggere dal "
                            f"Secret '{EXPECTED_DATABASE_SERVICE_NAME}' "
                            f"(chiave {secret_key}), trovato riferimento a "
                            f"'{ref.get('name')}'"
                        )

    with GradingStep(
        f"Il Service '{EXPECTED_ROSTER_APPNAME}' espone la porta 9090"
    ) as step:
        if roster_service is None:
            step.fail(f"Service '{EXPECTED_ROSTER_APPNAME}' non trovato")
        else:
            ports = roster_service.get("spec", {}).get("ports", [])
            if not any(p.get("port") == 9090 for p in ports):
                step.add_error(
                    f"Nessuna porta 9090 esposta dal Service "
                    f"'{EXPECTED_ROSTER_APPNAME}' (trovate: {ports})"
                )

    with GradingStep(f"La Route '{EXPECTED_ROSTER_APPNAME}' esiste") as step:
        if roster_route is None:
            step.fail(f"Route '{EXPECTED_ROSTER_APPNAME}' non trovata")
        else:
            # Host deterministico: il template calcola
            # ${APPNAME}-${NAMESPACE}.apps.ocp4.example.com e NAMESPACE resta
            # al default "packaged-templates" in entrambi i process (mai
            # sovrascritto dalla guida), quindi e' verificabile solo se lo
            # studente ha usato il nome di progetto standard.
            expected_host = (
                f"{EXPECTED_ROSTER_APPNAME}-{LAB_NAME}.apps.ocp4.example.com"
            )
            host = roster_route.get("spec", {}).get("host")
            if project == LAB_NAME and host != expected_host:
                step.add_error(
                    f"Host atteso '{expected_host}', trovato '{host}'"
                )


if __name__ == "__main__":
    main()
