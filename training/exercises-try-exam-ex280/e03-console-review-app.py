"""
Try-exam EX280, 3 — database MySQL + app famous-quotes con troubleshooting
(tema: "CONFIGURE IDENTITY PROVIDER", punti 5-8).

setup() prepara da solo il risultato degli es. 1-2 (utenti dba/tester,
gruppo app-team, progetto console-review con RoleBinding e quota pods: 2),
cosi' l'esercizio si puo' fare anche da solo.

Il guasto "naturale" del tema: con la quota a 2 pod, database + 2 repliche
di famous-quotes non ci stanno (il ReplicaSet registra "exceeded quota").
Il tema annotato non dice come andava risolto, quindi qui si grada solo che
il Deployment chieda 2 repliche e che l'app funzioni (almeno un pod pronto,
route che risponde): sta allo studente decidere se alzare la quota.

Non e' gradabile CHI ha creato le risorse (dba / developer): managedFields
registra il client, non l'utente. Resta scritto nel compito.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ex280_common import (
    CHAPTER, SETUP_TIMEOUT, LOCALUSERS, GradingStep, oc, oc_get_json, track_lock,
    require_cluster_admin, reset_owned_project, delete_owned_project,
    set_owned_group, delete_owned_group, read_htpasswd, write_htpasswd,
    htpasswd_hash, deployment_container, ready_replicas, service_has_endpoints,
    http_status, run_cli,
)

SLUG = "e03"
PROJECT = "console-review"
GROUP = "app-team"
DB_IMAGE = "registry.redhat.io/rhel8/mysql-80:1"
APP_IMAGE = "quay.io/redhattraining/famous-quotes:2.1"
APP_ENV = {
    "QUOTES_HOSTNAME": "database",
    "QUOTES_USER": "famous",
    "QUOTES_DATABASE": "famous",
    "QUOTES_PASSWORD": "famous",
}

TITLE = "3) MySQL + famous-quotes in console-review, con troubleshooting"

TASK = f"""\
Il progetto {PROJECT} esiste gia' (quota: 2 pod; edit al gruppo
{GROUP} = developer, dba; view a tester). Password: dba e tester
redhat, developer developer.

  - Come utente dba, crea un database MySQL nel progetto {PROJECT}.
    Nome applicazione: database. Usa famous come username, password e
    nome del database. Immagine: {DB_IMAGE}
  - Come utente developer, crea deployment, service e route nel progetto
    {PROJECT}, tutti chiamati famous-quotes. Immagine {APP_IMAGE},
    due repliche, variabili d'ambiente:
{chr(10).join(f'        {k} = {v}' for k, v in APP_ENV.items())}
    Configurata correttamente, l'app si collega al database e mostra
    un elenco di citazioni famose.
  - Trova e correggi i problemi del deployment.
  - Apri il sito di famous-quotes nel browser e verifica che funzioni.
"""

SOLUTION = f"""\
oc login -u dba -p redhat
oc new-app --name database --image {DB_IMAGE} -n {PROJECT} \\
    -e MYSQL_USER=famous -e MYSQL_PASSWORD=famous -e MYSQL_DATABASE=famous

oc login -u developer -p developer
oc create deployment famous-quotes --image {APP_IMAGE} --replicas 2 -n {PROJECT}
oc set env deployment/famous-quotes -n {PROJECT} \\
    {' '.join(f'{k}={v}' for k, v in APP_ENV.items())}
oc expose deployment famous-quotes --port 8000 -n {PROJECT}
oc expose service famous-quotes -n {PROJECT}

Troubleshooting:
  oc get pods -n {PROJECT}
  oc get events -n {PROJECT} --sort-by=.lastTimestamp
  oc describe rs -n {PROJECT} -l app=famous-quotes   # "exceeded quota: pods"
  oc logs deployment/famous-quotes -n {PROJECT}      # errori di connessione al DB?
  oc get endpoints -n {PROJECT}                      # service senza endpoint = selector/porta sbagliati

Con la quota a 2 pod la seconda replica non parte. Una possibile
correzione (come admin: developer ha solo edit, non puo' toccare la quota):
  oc patch quota <nome> -n {PROJECT} -p '{{"spec":{{"hard":{{"pods":"3"}}}}}}'

Verifica:
  oc get route famous-quotes -n {PROJECT}
  curl http://<host della route>
"""


def _ensure_users():
    entries = read_htpasswd(LOCALUSERS)
    if entries is None:
        raise RuntimeError(f"secret {LOCALUSERS} non trovato")
    missing = [u for u in ("dba", "tester") if u not in entries]
    if missing:
        for user in missing:
            entries[user] = htpasswd_hash(user, "redhat")
        write_htpasswd(LOCALUSERS, entries)


def setup():
    require_cluster_admin()
    with track_lock():
        _ensure_users()
        set_owned_group(GROUP, SLUG, ["developer", "dba"])
        reset_owned_project(PROJECT, SLUG)
        oc("adm", "policy", "add-role-to-user", "view", "tester", "-n", PROJECT, check=True)
        oc("adm", "policy", "add-role-to-group", "edit", GROUP, "-n", PROJECT, check=True)
        oc("create", "quota", f"{PROJECT}-quota", "--hard=pods=2", "-n", PROJECT, check=True)


def _env(container):
    return {e.get("name"): e.get("value") for e in (container or {}).get("env") or []}


def grade():
    db = oc_get_json("deployment", "database", "-n", PROJECT)
    with GradingStep(f"Il deployment database usa {DB_IMAGE.split('/')[-1]}") as step:
        if not db:
            step.fail("Deployment 'database' non trovato")
        elif "mysql-80" not in ((deployment_container(db) or {}).get("image") or ""):
            step.add_error(f"immagine: {(deployment_container(db) or {}).get('image')}")

    with GradingStep("Il database e' in esecuzione e accetta famous/famous sul db famous") as step:
        ready, _ = ready_replicas(PROJECT, "database")
        if not ready:
            step.fail("Nessun pod del database pronto")
        else:
            # Sola lettura dentro il pod (vedi CLAUDE.md, sez. 4).
            result = oc("exec", "deployment/database", "-n", PROJECT, "--",
                        "mysql", "-ufamous", "-pfamous", "-h", "127.0.0.1", "famous",
                        "-e", "SELECT 1")
            if result.returncode != 0:
                step.add_error((result.stderr or "accesso fallito").strip().splitlines()[-1])

    with GradingStep("Il service database esiste e ha endpoint") as step:
        if not oc_get_json("service", "database", "-n", PROJECT):
            step.fail("Service 'database' non trovato (QUOTES_HOSTNAME=database non risolverebbe)")
        elif not service_has_endpoints(PROJECT, "database"):
            step.add_error("nessun endpoint: il selector non trova i pod del database")

    app = oc_get_json("deployment", "famous-quotes", "-n", PROJECT)
    container = deployment_container(app)
    with GradingStep("Il deployment famous-quotes usa famous-quotes:2.1 con 2 repliche") as step:
        if not app:
            step.fail("Deployment 'famous-quotes' non trovato")
        else:
            if not (container.get("image") or "").endswith("famous-quotes:2.1"):
                step.add_error(f"immagine: {container.get('image')}")
            if app.get("spec", {}).get("replicas") != 2:
                step.add_error(f"replicas = {app.get('spec', {}).get('replicas')}")

    with GradingStep("famous-quotes ha le variabili QUOTES_* richieste") as step:
        if not app:
            step.fail("Deployment 'famous-quotes' non trovato")
        else:
            env = _env(container)
            for key, value in APP_ENV.items():
                if env.get(key) != value:
                    step.add_error(f"{key} = {env.get(key)!r}, atteso {value!r}")

    with GradingStep("Almeno un pod di famous-quotes e' pronto") as step:
        ready, _ = ready_replicas(PROJECT, "famous-quotes")
        if not ready:
            step.add_error("nessun pod pronto (oc get events, oc logs)")

    with GradingStep("Il service famous-quotes esiste e ha endpoint") as step:
        if not oc_get_json("service", "famous-quotes", "-n", PROJECT):
            step.fail("Service 'famous-quotes' non trovato")
        elif not service_has_endpoints(PROJECT, "famous-quotes"):
            step.add_error("nessun endpoint: selector o pod non pronti")

    route = oc_get_json("route", "famous-quotes", "-n", PROJECT)
    with GradingStep("La route famous-quotes risponde 200") as step:
        if not route:
            step.fail("Route 'famous-quotes' non trovata")
        else:
            host = route["spec"].get("host")
            scheme = "https" if route["spec"].get("tls") else "http"
            code = http_status(f"{scheme}://{host}/")
            if code != "200":
                step.add_error(f"{scheme}://{host}/ -> HTTP {code}")


def cleanup():
    with track_lock():
        delete_owned_project(PROJECT, SLUG)
        delete_owned_group(GROUP, SLUG)


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
