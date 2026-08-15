#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato packaged-charts (DO280, capitolo
"Deploying Packaged Applications" - "2.4. Guided Exercise: Deploy Helm
Charts"), sprovvisto di `lab grade` ufficiale.

FONTE: in questa cache ne' materials/labs/packaged-charts/ ne'
materials/solutions/packaged-charts/ contengono file (entrambe vuote):
l'UNICA fonte disponibile e' stato il testo della guida studente. I valori
sotto sono stati ricavati riga per riga da li' (vedi commenti puntuali).

L'esercizio chiede di installare il chart "etherpad" del repository Helm
"do280-repo" (http://helm.ocp4.example.com/charts) due volte:

  - packaged-charts-development: release "example-app", installata in
    versione 0.0.6 e poi aggiornata (helm upgrade) alla versione 0.0.7.
    Stato finale atteso quindi: chart "etherpad-0.0.7" (guida, step 3.4).
  - packaged-charts-production: release "production", installata
    direttamente in versione 0.0.7 (guida, step 4.3), poi aggiornata via
    helm upgrade per portare le repliche a 3 (guida, step 5).

In entrambi i progetti il values.yaml richiesto dalla guida (step 2.2 e 4.2)
imposta:
    image.repository: registry.ocp4.example.com:8443/etherpad
    image.name: etherpad
    image.tag: 1.8.18
cioe' l'immagine finale nel pod e' sempre
registry.ocp4.example.com:8443/etherpad/etherpad:1.8.18 (stesso valore
usato dal grading ufficiale dell'esercizio "packaged-review", molto simile,
in do280/packaged-review.py -> grade_container()).

route.host e' l'unico altro valore custom richiesto nel values.yaml, diverso
fra i due progetti (guida step 2.2 e 4.2):
    development -> development-etherpad.apps.ocp4.example.com
    production  -> etherpad.apps.ocp4.example.com

Il defaultTitle di default del chart e' "Labs Etherpad" (mostrato in `helm
show values` allo step 2.1) e non viene sovrascritto dal values.yaml
richiesto: lo usiamo come nel grading ufficiale di packaged-review per
verificare "black box" che la route serva davvero l'app (non solo che
esista), senza dover ipotizzare markup HTML specifico.

Il numero di repliche del progetto production e' l'unico valore
esplicitamente numerico richiesto per uno stato finale (guida step 5.2:
"Add a replicaCount key with 3 as the value" + verifica coi 3 pod Running
allo step 5.4): lo verifichiamo sul deployment applicativo. Per il progetto
development la guida non chiede di modificare replicaCount (resta il
default 1 del chart), quindi li' verifichiamo solo che almeno un pod sia
pronto, senza pretendere un numero esatto.

NON verificato per mancanza di specifica nella guida (nessun dato concreto
da cui derivarlo, per rispettare la regola d'oro di CLAUDE.md):
- risorse (requests/limits) sui container: la guida packaged-charts, a
  differenza di packaged-review, non menziona alcun valore di resources.
- nome esatto delle risorse generate dal chart (Deployment/Route/Service):
  la guida mostra solo un esempio di route ("example-app-etherpad") e di
  pod ("production-etherpad-xxxxx"), compatibile con una convenzione
  "<release>-etherpad", ma non lo garantisce in modo esplicito per ogni
  possibile versione del chart: cerchiamo quindi le risorse per
  caratteristiche (immagine, host) invece che per nome fisso.
- revisione Helm (REVISION): la guida la mostra negli output di esempio ma
  non e' un requisito didattico dell'esercizio, e potrebbe differire in modo
  legittimo (es. installazioni ripetute durante il debug).
- terminazione TLS della route ("edge"): citata solo come nota informativa.

Non chiamiamo `helm list` con --kubeconfig esplicito (a differenza di
packaged-review.py, che usa il kubeconfig "magico" della libreria di
grading ufficiale Red Hat): qui contiamo sul contesto oc/helm gia' attivo
nella shell dello studente (stesso presupposto degli altri script di questo
repo, che usano `oc` senza specificare kubeconfig).

Uso: packaged-charts.py [prefisso-progetto]   (default: packaged-charts)
Il prefisso genera SEMPRE due progetti: <prefisso>-development e
<prefisso>-production, coerentemente con quanto fa start()/finish() del
modulo ufficiale do280/packaged-charts.py.
"""

import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.request

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "packaged-charts"

IMAGE_SUBSTR = "registry.ocp4.example.com:8443/etherpad/etherpad:1.8.18"
FINAL_CHART = "etherpad-0.0.7"
EXPECTED_TITLE = "Labs Etherpad"

DEV_SUFFIX = "development"
DEV_RELEASE = "example-app"
DEV_HOST = "development-etherpad.apps.ocp4.example.com"

PROD_SUFFIX = "production"
PROD_RELEASE = "production"
PROD_HOST = "etherpad.apps.ocp4.example.com"
PROD_REPLICAS = 3


def helm_list(namespace, release_filter):
    """Esegue `helm list --deployed -o=yaml --filter=^<release>$
    --namespace=<ns>` e ritorna la lista di release (puo' essere vuota), o
    None se il comando helm stesso fallisce (helm non installato, contesto
    non loggato, ecc. - distinto da "nessuna release trovata")."""
    command = [
        "helm", "list",
        "--deployed",
        "-o=yaml",
        f"--filter=^{release_filter}$",
        f"--namespace={namespace}",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    try:
        return yaml.safe_load(result.stdout) or []
    except yaml.YAMLError:
        return None


def find_app_deployment(project):
    """Cerca, fra tutti i Deployment del progetto, quello che usa
    l'immagine etherpad richiesta dalla guida (il nome della risorsa creata
    dal chart non e' garantito in ogni versione, vedi commento in testa)."""
    deployments = oc_get_json("deployment", "-n", project)
    if not deployments:
        return None, None
    for dep in deployments.get("items", []):
        for c in dep["spec"]["template"]["spec"].get("containers", []):
            if IMAGE_SUBSTR in c.get("image", ""):
                return dep, c
    return None, None


def find_route_by_host(project, host):
    routes = oc_get_json("route", "-n", project)
    if not routes:
        return None
    for route in routes.get("items", []):
        if route.get("spec", {}).get("host") == host:
            return route
    return None


def fetch(url, timeout=15):
    """GET read-only, certificato self-signed ignorato (come storage-configs.py)."""
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


def grade_namespace(project, release_name, expected_host, expected_replicas=None):
    """Esegue tutti i check relativi a un singolo progetto (development o
    production): esistenza progetto, release Helm, immagine del container,
    (eventuale) numero di repliche, route e raggiungibilita' dell'app."""
    tag = f"[{project}]"

    with GradingStep(f"{tag} Il progetto esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")
            return  # nessun altro check ha senso senza il progetto

    with GradingStep(
        f"{tag} La release Helm '{release_name}' e' deployata con il chart {FINAL_CHART}"
    ) as step:
        releases = helm_list(project, release_name)
        if releases is None:
            step.fail("Comando 'helm list' fallito (helm non disponibile o contesto non valido?)")
        elif len(releases) == 0:
            step.fail(f"Nessuna release Helm '{release_name}' deployata nel progetto '{project}'")
        else:
            chart = releases[0].get("chart", "")
            if chart != FINAL_CHART:
                step.add_error(
                    f"Chart installato: '{chart}' (atteso: '{FINAL_CHART}')"
                )

    deployment, container = find_app_deployment(project)

    with GradingStep(f"{tag} Il deployment usa l'immagine etherpad richiesta") as step:
        if deployment is None:
            step.fail(
                f"Nessun Deployment nel progetto usa un'immagine contenente '{IMAGE_SUBSTR}' "
                "(atteso da image.repository/image.name/image.tag nel values.yaml)"
            )

    if expected_replicas is not None:
        with GradingStep(f"{tag} Il deployment ha {expected_replicas} repliche pronte") as step:
            if deployment is None:
                step.fail()
            else:
                ready = deployment.get("status", {}).get("readyReplicas", 0)
                if ready != expected_replicas:
                    step.add_error(
                        f"Repliche pronte: {ready} (atteso: {expected_replicas}, "
                        "vedi replicaCount nel values.yaml)"
                    )
    else:
        with GradingStep(f"{tag} Il pod dell'applicazione e' pronto") as step:
            if deployment is None:
                step.fail()
            else:
                ready = deployment.get("status", {}).get("readyReplicas", 0)
                if not ready:
                    step.add_error("Nessuna replica pronta per il deployment")

    route = find_route_by_host(project, expected_host)

    with GradingStep(f"{tag} Esiste una route con host {expected_host}") as step:
        if route is None:
            step.fail(
                f"Nessuna route nel progetto '{project}' ha host '{expected_host}' "
                "(atteso da route.host nel values.yaml)"
            )

    with GradingStep(f"{tag} L'applicazione e' raggiungibile tramite la route") as step:
        if route is None:
            step.fail()
        else:
            url = f"https://{expected_host}/"
            status, body = fetch(url)
            if status != 200:
                step.add_error(f"GET {url} -> {status} (atteso 200)")
            elif EXPECTED_TITLE.encode() not in (body or b""):
                step.add_error(
                    f"La pagina servita da {url} non contiene '{EXPECTED_TITLE}' "
                    "(defaultTitle di default del chart etherpad)"
                )


def main():
    prefix = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    dev_project = f"{prefix}-{DEV_SUFFIX}"
    prod_project = f"{prefix}-{PROD_SUFFIX}"
    print(
        f"🔧 Grading personalizzato per '{LAB_NAME}' "
        f"(progetti: {dev_project}, {prod_project})"
    )

    grade_namespace(dev_project, DEV_RELEASE, DEV_HOST, expected_replicas=None)
    grade_namespace(prod_project, PROD_RELEASE, PROD_HOST, expected_replicas=PROD_REPLICAS)


if __name__ == "__main__":
    main()
