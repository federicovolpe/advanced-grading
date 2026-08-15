#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato declarative-manifests (DO280),
sprovvisto di `lab grade` ufficiale (la classe DeclarativeManifests
implementa solo start()/finish(), non grade() - vedi
do280/declarative-manifests.py).

Fonti usate, in ordine: i manifest versionati in
materials/solutions/declarative-manifests/{database,exoplanets}-v1.{0,1.0,1.1}.yaml
e il testo della guida studente (DO280-RHOCP4.18, cap. 1.2), che descrive il
flusso esatto: lo studente clona il repo Git dell'esercizio, fa checkout dei
tag v1.0 -> v1.1.0 -> v1.1.1 e applica i manifest via `oc apply -f .` nel
progetto declarative-manifests, poi forza il redeploy con
`oc rollout restart` quando un Secret cambia senza che il Deployment cambi.

Si gradua SOLO lo stato finale (dopo v1.1.1), non i passaggi intermedi:
e' lo stato piu' robusto da verificare (indipendente da quando lo studente
esegue il grading rispetto ai singoli `oc apply`) e i due soli valori che
cambiano tra le versioni - il tag immagine di exoplanets e lo user del
database - sono comunque solo raggiungibili passando per tutte le versioni
precedenti nel repo Git. Nota: database-v1.1.0.yaml esiste nei materiali ma
git-repo.sh NON lo applica mai (riga commentata "cp -v ... database-v1.1.0
.yaml"): al tag "second" il database resta alla v1.0, e salta direttamente
alla v1.1.1 al tag "third". Per questo non si verifica una versione
intermedia del database.

Il repo Git su GitLab (clone, tag, branch) non viene gradato: richiederebbe
credenziali/raggiungibilita' del server GitLab, mentre l'obiettivo didattico
verificabile e' lo stato finale delle risorse nel cluster.

Uso: declarative-manifests.py [nome-progetto]   (default: declarative-manifests)
"""

import base64
import os
import ssl
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "declarative-manifests"

# Sottostringhe di immagine (non l'intero registry/host, per restare
# indipendenti dal registry usato nell'ambiente) che identificano la
# versione finale (v1.1.1) attesa.
DATABASE_IMAGE_SUBSTR = "postgresql-13:1-7"
EXOPLANETS_IMAGE_SUBSTR = "exoplanets:v1.1.1"


def get_container(deployment, name):
    if deployment is None:
        return None
    containers = deployment["spec"]["template"]["spec"].get("containers", [])
    for c in containers:
        if c.get("name") == name:
            return c
    return containers[0] if containers else None


def decode_secret(secret, key):
    """I valori di stringData nel manifest arrivano dall'API come 'data'
    codificato in base64."""
    if secret is None:
        return None
    raw = secret.get("data", {}).get(key)
    if raw is None:
        return None
    try:
        return base64.b64decode(raw).decode("utf-8")
    except Exception:
        return None


def route_url(route, path=""):
    spec = route.get("spec", {})
    host = spec.get("host")
    if not host:
        return None
    scheme = "https" if spec.get("tls") else "http"
    return f"{scheme}://{host}/{path.lstrip('/')}"


def fetch_status(url, timeout=10):
    """GET read-only, ritorna solo lo status code (o None in caso di errore
    di rete). Non confrontiamo il corpo della risposta come in
    storage-configs.py: qui l'app e' dinamica (dipende dal database), non
    file statici di riferimento noti."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(url, timeout=timeout, context=ctx) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    # --- Database ---

    database_cm = oc_get_json("configmap", "database", "-n", project)
    with GradingStep("La ConfigMap 'database' e' configurata correttamente") as step:
        if database_cm is None:
            step.fail("ConfigMap 'database' non trovata")
        else:
            max_conn = database_cm.get("data", {}).get("POSTGRESQL_MAX_CONNECTIONS")
            if max_conn != "100":
                step.add_error(
                    f"POSTGRESQL_MAX_CONNECTIONS atteso '100', trovato '{max_conn}'"
                )

    database_secret = oc_get_json("secret", "database", "-n", project)
    with GradingStep(
        "Il Secret 'database' contiene le credenziali della versione finale (v1.1.1)"
    ) as step:
        if database_secret is None:
            step.fail("Secret 'database' non trovato")
        else:
            # database-user e' l'unico campo che cambia tra v1.1.0 e v1.1.1
            # (da "user" a "user1"): e' il marcatore piu' affidabile che lo
            # studente ha applicato l'ultima versione dei manifest.
            expected = {
                "database-name": "database",
                "database-user": "user1",
                "database-password": "password",
                "database-admin-password": "postgres",
            }
            for key, value in expected.items():
                actual = decode_secret(database_secret, key)
                if actual != value:
                    step.add_error(f"{key}: atteso '{value}', trovato '{actual}'")

    database_deploy = oc_get_json("deployment", "database", "-n", project)
    database_container = get_container(database_deploy, "postgresql")
    with GradingStep("Il Deployment 'database' e' pronto (1/1 repliche)") as step:
        if database_deploy is None:
            step.fail("Deployment 'database' non trovato")
        else:
            image = (database_container or {}).get("image", "")
            if DATABASE_IMAGE_SUBSTR not in image:
                step.add_error(
                    f"Immagine attesa con '{DATABASE_IMAGE_SUBSTR}', trovata '{image}'"
                )
            ready = database_deploy.get("status", {}).get("readyReplicas", 0)
            if not ready:
                step.add_error(
                    "Nessuna replica pronta: il Deployment potrebbe non essere "
                    "stato riavviato dopo l'aggiornamento del Secret (vedi "
                    "'oc rollout restart deployment/database' nella guida)"
                )

    database_svc = oc_get_json("service", "database", "-n", project)
    with GradingStep("Il Service 'database' espone la porta 5432") as step:
        if database_svc is None:
            step.fail("Service 'database' non trovato")
        else:
            ports = database_svc.get("spec", {}).get("ports", [])
            if not any(
                p.get("port") == 5432 and str(p.get("targetPort")) == "5432"
                for p in ports
            ):
                step.add_error("Nessuna porta 5432->5432 nel Service 'database'")

    # --- Exoplanets ---

    exo_cm = oc_get_json("configmap", "exoplanets", "-n", project)
    with GradingStep("La ConfigMap 'exoplanets' punta al database corretto") as step:
        if exo_cm is None:
            step.fail("ConfigMap 'exoplanets' non trovata")
        else:
            data = exo_cm.get("data", {})
            if data.get("DB_HOST") != "database":
                step.add_error(f"DB_HOST atteso 'database', trovato '{data.get('DB_HOST')}'")
            if data.get("DB_PORT") != "5432":
                step.add_error(f"DB_PORT atteso '5432', trovato '{data.get('DB_PORT')}'")

    exo_secret = oc_get_json("secret", "exoplanets", "-n", project)
    with GradingStep(
        "Il Secret 'exoplanets' contiene le credenziali della versione finale (v1.1.1)"
    ) as step:
        if exo_secret is None:
            step.fail("Secret 'exoplanets' non trovato")
        else:
            expected = {
                "DB_NAME": "database",
                "DB_USER": "user1",
                "DB_PASSWORD": "password",
                "DB_ADMIN_PASSWORD": "postgres",
            }
            for key, value in expected.items():
                actual = decode_secret(exo_secret, key)
                if actual != value:
                    step.add_error(f"{key}: atteso '{value}', trovato '{actual}'")

    exo_deploy = oc_get_json("deployment", "exoplanets", "-n", project)
    exo_container = get_container(exo_deploy, "exoplanets")
    with GradingStep(
        "Il Deployment 'exoplanets' usa l'immagine v1.1.1 ed e' pronto (1/1 repliche)"
    ) as step:
        if exo_deploy is None:
            step.fail("Deployment 'exoplanets' non trovato")
        else:
            image = (exo_container or {}).get("image", "")
            if EXOPLANETS_IMAGE_SUBSTR not in image:
                step.add_error(
                    f"Immagine attesa con '{EXOPLANETS_IMAGE_SUBSTR}', trovata '{image}'"
                )
            ready = exo_deploy.get("status", {}).get("readyReplicas", 0)
            if not ready:
                step.add_error(
                    "Nessuna replica pronta: probabile CrashLoopBackOff per mancato "
                    "'oc rollout restart deployment/exoplanets' dopo l'aggiornamento "
                    "del Secret (il pod carica le credenziali solo all'avvio)"
                )

    exo_svc = oc_get_json("service", "exoplanets", "-n", project)
    with GradingStep("Il Service 'exoplanets' espone la porta 8080") as step:
        if exo_svc is None:
            step.fail("Service 'exoplanets' non trovato")
        else:
            ports = exo_svc.get("spec", {}).get("ports", [])
            if not any(
                p.get("port") == 8080 and str(p.get("targetPort")) == "8080"
                for p in ports
            ):
                step.add_error("Nessuna porta 8080->8080 nel Service 'exoplanets'")

    exo_route = oc_get_json("route", "exoplanets", "-n", project)
    with GradingStep("La Route 'exoplanets' esiste e punta al Service corretto") as step:
        if exo_route is None:
            step.fail("Route 'exoplanets' non trovata")
        else:
            to_name = exo_route.get("spec", {}).get("to", {}).get("name")
            if to_name != "exoplanets":
                step.add_error(f"La Route punta al Service '{to_name}', atteso 'exoplanets'")

    with GradingStep("L'applicazione e' raggiungibile tramite la Route") as step:
        if exo_route is None:
            step.fail()
        else:
            url = route_url(exo_route)
            if url is None:
                step.add_error("La Route non ha ancora un host assegnato")
            else:
                status = fetch_status(url)
                if status != 200:
                    step.add_error(f"GET {url} -> {status} (atteso 200)")


if __name__ == "__main__":
    main()
