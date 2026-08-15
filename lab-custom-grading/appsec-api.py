#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato appsec-api, sprovvisto di
`lab grade` ufficiale (la classe AppsecApi nel pacchetto do280 implementa
solo start()/finish(), non grade() - vedi do280/appsec-api.py).

Specifica derivata da due fonti concordanti:
- diff fra materials/labs/appsec-api e materials/solutions/appsec-api
  (reloader-deployment.yaml: aggiunta di spec.template.spec.serviceAccountName;
  config-app/configmap.yaml: cambio del campo description).
- testo della guida studente (DO280-RHOCP4.18, sez. 8.4 "Allow Application
  Access to Kubernetes APIs", pag. 360-364), che descrive passo-passo la
  procedura RBAC che i file YAML da soli non catturano (il ServiceAccount e
  il RoleBinding non sono forniti come manifest, vanno creati con `oc create
  sa` e `oc policy add-role-to-user`).

L'esercizio coinvolge DUE progetti creati da start()/dallo studente:
- "configmap-reloader" (pre-creato vuoto da start()): qui lo studente applica
  reloader-deployment.yaml, un controller Stakater Reloader che osserva le
  ConfigMap del progetto appsec-api e fa un rolling upgrade dei deployment
  quando cambiano (via annotazione configmap.reloader.stakater.com/reload
  gia' presente nel deployment.yaml di config-app, non modificata dallo
  studente).
- "appsec-api" (NON pre-creato da start(): il modulo ufficiale non chiama
  create_project_step su di esso, e il passo 4 della guida lo crea
  esplicitamente con `oc new-project appsec-api` come utente developer):
  qui lo studente applica i manifest di config-app/ e concede al
  ServiceAccount del reloader il ClusterRole "edit" tramite un RoleBinding
  locale (`oc policy add-role-to-user edit
  system:serviceaccount:configmap-reloader:<sa> --rolebinding-name
  reloader-edit -n appsec-api`).

Nota sul nome del ServiceAccount: la guida usa "configmap-reloader-sa" nei
comandi mostrati (step 3.1/3.2/5.1), ma il file
materials/solutions/appsec-api/reloader-deployment.yaml effettivamente
presente in questa cache usa invece "configmap-reloader" come
serviceAccountName - le due fonti "ufficiali" non concordano sul nome
esatto. Per questo lo script NON assume un nome fisso: legge il
serviceAccountName impostato dallo studente nel Deployment
"configmap-reloader" e verifica che quel ServiceAccount esista e abbia
davvero il RoleBinding atteso nel progetto appsec-api (ricerca per
caratteristiche - roleRef + subject - come in auth-rbac.py/storage-configs.py,
non per nome di RoleBinding, anch'esso non deterministico perche' generato
da `oc policy add-role-to-user`).

Uso: appsec-api.py [nome-progetto-appsec-api]
     (default progetto principale: appsec-api; il secondo progetto e'
     sempre "configmap-reloader", nome fisso non derivato dall'esercizio -
     vedi AppsecApi._reloader_project nel modulo ufficiale)
"""

import os
import ssl
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "appsec-api"
RELOADER_PROJECT = "configmap-reloader"

EXPECTED_RELOADER_IMAGE_SUBSTR = "do280-stakater-reloader"
EXPECTED_APP_IMAGE_SUBSTR = "do280-show-config-app"
EXPECTED_CONFIGMAP_NAME = "config-app"
EXPECTED_DESCRIPTION = "API that exposes its configuration"
EXPECTED_ROLE = "edit"
EXPECTED_RELOAD_ANNOTATION_KEY = "configmap.reloader.stakater.com/reload"


def get_container(deployment, name=None):
    containers = deployment["spec"]["template"]["spec"].get("containers", [])
    if name:
        for c in containers:
            if c.get("name") == name:
                return c
    return containers[0] if containers else None


def find_rolebinding_for_sa(rolebindings, role_name, sa_name, sa_namespace):
    """Cerca, fra i RoleBinding del progetto, quello il cui roleRef punta al
    ClusterRole indicato e che ha come subject il ServiceAccount indicato
    (cross-namespace, come generato da
    `oc policy add-role-to-user ... system:serviceaccount:<ns>:<sa>`). Non
    assume il nome del RoleBinding, che dipende da --rolebinding-name o dalla
    convenzione automatica del comando."""
    if not rolebindings:
        return None
    for rb in rolebindings.get("items", []):
        role_ref = rb.get("roleRef", {})
        if role_ref.get("kind") != "ClusterRole" or role_ref.get("name") != role_name:
            continue
        for subj in rb.get("subjects", []) or []:
            if (
                subj.get("kind") == "ServiceAccount"
                and subj.get("name") == sa_name
                and subj.get("namespace", sa_namespace) == sa_namespace
            ):
                return rb
    return None


def fetch(url, timeout=10):
    """GET read-only. Ritorna (status, bytes) oppure (None, None) in caso di
    errore di rete/connessione."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(url, timeout=timeout, context=ctx) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception:
        return None, None


def route_url(route, path=""):
    spec = route.get("spec", {})
    host = spec.get("host")
    if not host:
        return None
    scheme = "https" if spec.get("tls") else "http"
    return f"{scheme}://{host}/{path.lstrip('/')}"


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    reloader_project = RELOADER_PROJECT
    print(
        f"🔧 Grading personalizzato per '{LAB_NAME}' "
        f"(progetti: {project}, {reloader_project})"
    )

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato (creato con 'oc new-project')")

    with GradingStep(f"Il progetto {reloader_project} esiste") as step:
        if not project_exists(reloader_project):
            step.fail(f"Progetto '{reloader_project}' non trovato")

    # --- Reloader: deployment + ServiceAccount nel progetto configmap-reloader ---

    reloader_deployment = oc_get_json(
        "deployment", "configmap-reloader", "-n", reloader_project
    )
    reloader_container = None
    sa_name = None

    with GradingStep(
        f"Il Deployment 'configmap-reloader' esiste nel progetto {reloader_project}"
    ) as step:
        if reloader_deployment is None:
            step.fail("Deployment 'configmap-reloader' non trovato")
        else:
            reloader_container = get_container(reloader_deployment, "configmap-reloader")
            if reloader_container is None:
                step.add_error("Nessun container trovato nel deployment")
            elif EXPECTED_RELOADER_IMAGE_SUBSTR not in reloader_container.get("image", ""):
                step.add_error(
                    f"L'immagine del container non contiene "
                    f"'{EXPECTED_RELOADER_IMAGE_SUBSTR}' "
                    f"(trovata: {reloader_container.get('image')})"
                )
            sa_name = reloader_deployment["spec"]["template"]["spec"].get(
                "serviceAccountName"
            )

    with GradingStep(
        "Il deployment usa un ServiceAccount dedicato (non 'default')"
    ) as step:
        if reloader_deployment is None:
            step.fail()
        elif not sa_name or sa_name == "default":
            step.add_error(
                "spec.template.spec.serviceAccountName non e' impostato a un "
                "ServiceAccount dedicato (atteso: creato con 'oc create sa' e "
                "assegnato al deployment, es. 'configmap-reloader-sa')"
            )

    with GradingStep(
        f"Il ServiceAccount usato dal reloader esiste in {reloader_project}"
    ) as step:
        if not sa_name:
            step.fail()
        else:
            sa = oc_get_json("serviceaccount", sa_name, "-n", reloader_project)
            if sa is None:
                step.add_error(
                    f"ServiceAccount '{sa_name}' non trovato nel progetto "
                    f"'{reloader_project}'"
                )

    # --- RBAC cross-namespace: RoleBinding nel progetto appsec-api ---

    rolebindings = oc_get_json("rolebinding", "-n", project)

    with GradingStep(
        f"Il ServiceAccount del reloader ha il ClusterRole '{EXPECTED_ROLE}' "
        f"sul progetto {project}"
    ) as step:
        if not sa_name:
            step.fail(
                "Impossibile verificare: nessun ServiceAccount configurato "
                "nel deployment del reloader"
            )
        elif rolebindings is None:
            step.fail(f"Impossibile leggere i RoleBinding nel progetto '{project}'")
        elif (
            find_rolebinding_for_sa(
                rolebindings, EXPECTED_ROLE, sa_name, reloader_project
            )
            is None
        ):
            step.add_error(
                f"Nessun RoleBinding nel progetto '{project}' assegna il "
                f"ClusterRole '{EXPECTED_ROLE}' al ServiceAccount "
                f"'system:serviceaccount:{reloader_project}:{sa_name}' "
                "(atteso: 'oc policy add-role-to-user edit "
                f"system:serviceaccount:{reloader_project}:{sa_name} -n {project}')"
            )

    # --- config-app: ConfigMap, Deployment, Service, Route nel progetto appsec-api ---

    configmap = oc_get_json("configmap", EXPECTED_CONFIGMAP_NAME, "-n", project)

    with GradingStep(
        f"La ConfigMap '{EXPECTED_CONFIGMAP_NAME}' esiste con la description aggiornata"
    ) as step:
        if configmap is None:
            step.fail(f"ConfigMap '{EXPECTED_CONFIGMAP_NAME}' non trovata nel progetto")
        else:
            content = (configmap.get("data") or {}).get("config.yaml", "")
            if EXPECTED_DESCRIPTION not in content:
                step.add_error(
                    f"data['config.yaml'] non contiene la description "
                    f"aggiornata '{EXPECTED_DESCRIPTION}' (contenuto attuale: "
                    f"{content!r})"
                )

    app_deployment = oc_get_json("deployment", EXPECTED_CONFIGMAP_NAME, "-n", project)
    app_container = None

    with GradingStep(
        f"Il Deployment '{EXPECTED_CONFIGMAP_NAME}' e' configurato correttamente"
    ) as step:
        if app_deployment is None:
            step.fail(f"Deployment '{EXPECTED_CONFIGMAP_NAME}' non trovato nel progetto")
        else:
            app_container = get_container(app_deployment, EXPECTED_CONFIGMAP_NAME)
            if app_container is None:
                step.add_error("Nessun container trovato nel deployment")
            else:
                if EXPECTED_APP_IMAGE_SUBSTR not in app_container.get("image", ""):
                    step.add_error(
                        f"L'immagine del container non contiene "
                        f"'{EXPECTED_APP_IMAGE_SUBSTR}' "
                        f"(trovata: {app_container.get('image')})"
                    )
                mounted_names = {
                    vm.get("name") for vm in app_container.get("volumeMounts", []) or []
                }
                volumes = app_deployment["spec"]["template"]["spec"].get("volumes", []) or []
                has_cm_vol = any(
                    v.get("name") in mounted_names
                    and (v.get("configMap") or {}).get("name") == EXPECTED_CONFIGMAP_NAME
                    for v in volumes
                )
                if not has_cm_vol:
                    step.add_error(
                        f"Nessun volume monta la ConfigMap "
                        f"'{EXPECTED_CONFIGMAP_NAME}' nel container"
                    )
            annotations = app_deployment["metadata"].get("annotations") or {}
            if annotations.get(EXPECTED_RELOAD_ANNOTATION_KEY) != EXPECTED_CONFIGMAP_NAME:
                step.add_error(
                    f"Annotazione '{EXPECTED_RELOAD_ANNOTATION_KEY}' mancante o "
                    f"diversa da '{EXPECTED_CONFIGMAP_NAME}' (richiesta perche' "
                    "il controller Reloader la usa per individuare quale "
                    "deployment aggiornare)"
                )

    with GradingStep("Il pod dell'applicazione config-app e' pronto") as step:
        if app_deployment is None:
            step.fail()
        else:
            ready = app_deployment.get("status", {}).get("readyReplicas", 0)
            if not ready:
                step.add_error("Nessuna replica pronta per il deployment 'config-app'")

    service = oc_get_json("service", EXPECTED_CONFIGMAP_NAME, "-n", project)

    with GradingStep(f"Il Service '{EXPECTED_CONFIGMAP_NAME}' esiste") as step:
        if service is None:
            step.fail(f"Service '{EXPECTED_CONFIGMAP_NAME}' non trovato nel progetto")

    route = oc_get_json("route", EXPECTED_CONFIGMAP_NAME, "-n", project)

    with GradingStep(f"La Route '{EXPECTED_CONFIGMAP_NAME}' esiste") as step:
        if route is None:
            step.fail(f"Route '{EXPECTED_CONFIGMAP_NAME}' non trovata nel progetto")
        elif route.get("spec", {}).get("to", {}).get("name") != EXPECTED_CONFIGMAP_NAME:
            step.add_error(
                f"La Route non punta al Service '{EXPECTED_CONFIGMAP_NAME}'"
            )

    with GradingStep(
        "L'endpoint /config della Route restituisce la configurazione aggiornata"
    ) as step:
        if route is None:
            step.fail()
        else:
            url = route_url(route, "config")
            status, body = fetch(url)
            if status != 200:
                step.add_error(f"GET {url} -> {status} (atteso 200)")
            elif EXPECTED_DESCRIPTION.encode() not in (body or b""):
                step.add_error(
                    f"La risposta di {url} non contiene la description "
                    f"aggiornata '{EXPECTED_DESCRIPTION}' - verificare che il "
                    "controller Reloader abbia gia' fatto il rolling upgrade "
                    "dopo la modifica della ConfigMap"
                )


if __name__ == "__main__":
    main()
