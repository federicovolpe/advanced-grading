#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato deploy-routes (RHOCP 4.22 / RHEL10),
sprovvisto di `lab grade` ufficiale (la classe DeployRoutes nel pacchetto
do180 implementa solo start()/finish(), non grade()).

RISCRITTO rispetto alla versione precedente di questo script: quella
versione assumeva nomi di app/service/route lasciati alla scelta dello
studente (gradati per caratteristiche, come storage-configs.py). Il testo
ATTUALE della guida (Cap. 4.8 "Scale and Expose Applications to External
Access", DO180-RHOCP4.22-en-1-20260730) impone invece nomi ESATTI per ogni
risorsa, riportati letteralmente nei comandi di esempio:

- Deployment satir-app e sakila-app, entrambi con l'immagine
  registry.lab.example.com:8443/redhattraining/do180-httpd-app:v1 (la
  stessa verificata da start() in do180/exercises/deploy_routes.py);
- Service satir-svc e sakila-svc, entrambi port=8080 e targetPort=8080;
- Route "satir" creata direttamente (`oc expose service satir-svc --name satir`);
- Ingress "ingr-sakila" verso sakila-svc:8080 (host
  ingr-sakila.apps.<dominio classroom>) — OpenShift genera automaticamente
  la Route corrispondente, riconoscibile dalla ownerReference di kind
  "Ingress" e nome "ingr-sakila";
- scale: sakila-app a 2 repliche, satir-app a 3 repliche;
- sticky session: annotazione ingress.kubernetes.io/affinity=cookie
  sull'ingress ingr-sakila, e router.openshift.io/cookie_name=hello sulla
  Route satir.

Il progetto e' "web-applications" (self.project nel modulo ufficiale,
diverso dal nome esercizio "deploy-routes" — confermato anche dall'output
di login riportato nella guida).

Il file di partenza (materials/labs/deploy-routes/lab-start/index.php),
incluso nell'immagine do180-httpd-app, stampa letteralmente
"Welcome to Red Hat Training, from $hostname": lo usiamo come riscontro
black-box end-to-end (Route/Ingress -> Service -> Deployment corretti),
verificando anche che $hostname inizi col nome del deployment atteso (il
nome del pod e' <deployment>-<hash>-<hash>), cosi' scopriamo anche un
service esposto per sbaglio verso l'app sbagliata.

Non gradato: il comportamento di stickiness delle sessioni via cookie
(curl -c/-b, confronto del pod servito) — il manuale lo usa solo come
dimostrazione didattica del comportamento del router una volta che
l'annotazione e' presente; non e' uno stato aggiuntivo che lo studente crea,
e testarlo dal vivo dipenderebbe dal timing del round-robin del router
(rischio di falsi negativi). Verificare le annotazioni stesse (il compito
esplicito dello studente) e' il riscontro oggettivo corretto.

Uso: deploy-routes.py [nome-progetto]   (default: web-applications)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists, http_get

LAB_NAME = "deploy-routes"
PROJECT = "web-applications"
EXPECTED_IMAGE = "redhattraining/do180-httpd-app:v1"
EXPECTED_TEXT = "Welcome to Red Hat Training, from"


def deployment_image(project, name):
    dep = oc_get_json("deployment", name, "-n", project)
    if not dep:
        return None
    containers = dep.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
    if not containers:
        return None
    return containers[0].get("image", "")


def route_url(route):
    spec = route.get("spec", {})
    host = spec.get("host")
    if not host:
        return None
    scheme = "https" if spec.get("tls") else "http"
    path = spec.get("path") or "/"
    return f"{scheme}://{host}{path}"


def route_serves_app(route, app_name):
    """True se la Route risponde in HTTP col testo atteso dell'immagine
    do180-httpd-app E il nome del pod che risponde comincia col nome del
    deployment atteso (rileva anche un service/route puntati per sbaglio
    sull'altra app, che userebbe la stessa immagine)."""
    url = route_url(route)
    if not url:
        return False
    ok, body = http_get(url, timeout=8)
    return ok and EXPECTED_TEXT in body and f"from {app_name}-" in body


def is_owned_by_ingress(route, ingress_name):
    owners = route.get("metadata", {}).get("ownerReferences", []) or []
    return any(o.get("kind") == "Ingress" and o.get("name") == ingress_name for o in owners)


def service_has_port_8080(project, name):
    svc = oc_get_json("service", name, "-n", project)
    if not svc:
        return None  # non trovato
    ports = svc.get("spec", {}).get("ports", []) or []
    return any(str(p.get("port")) == "8080" and str(p.get("targetPort")) == "8080" for p in ports)


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else PROJECT
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep("Il deployment satir-app usa l'immagine do180-httpd-app:v1") as step:
        image = deployment_image(project, "satir-app")
        if image is None:
            step.add_error("Deployment 'satir-app' non trovato")
        elif EXPECTED_IMAGE not in image:
            step.add_error(f"Immagine attuale '{image}', attesa che contenga '{EXPECTED_IMAGE}'")

    with GradingStep("Il deployment sakila-app usa l'immagine do180-httpd-app:v1") as step:
        image = deployment_image(project, "sakila-app")
        if image is None:
            step.add_error("Deployment 'sakila-app' non trovato")
        elif EXPECTED_IMAGE not in image:
            step.add_error(f"Immagine attuale '{image}', attesa che contenga '{EXPECTED_IMAGE}'")

    with GradingStep("Il deployment satir-app e' scalato a 3 repliche") as step:
        dep = oc_get_json("deployment", "satir-app", "-n", project)
        if not dep:
            step.add_error("Deployment 'satir-app' non trovato")
        elif dep.get("spec", {}).get("replicas") != 3:
            step.add_error(f"spec.replicas attuale: {dep.get('spec', {}).get('replicas')}, atteso 3")

    with GradingStep("Il deployment sakila-app e' scalato a 2 repliche") as step:
        dep = oc_get_json("deployment", "sakila-app", "-n", project)
        if not dep:
            step.add_error("Deployment 'sakila-app' non trovato")
        elif dep.get("spec", {}).get("replicas") != 2:
            step.add_error(f"spec.replicas attuale: {dep.get('spec', {}).get('replicas')}, atteso 2")

    with GradingStep("Il service satir-svc espone la porta 8080 (targetPort 8080)") as step:
        ok = service_has_port_8080(project, "satir-svc")
        if ok is None:
            step.add_error("Service 'satir-svc' non trovato")
        elif not ok:
            step.add_error("Nessuna porta 8080->8080 trovata su 'satir-svc'")

    with GradingStep("Il service sakila-svc espone la porta 8080 (targetPort 8080)") as step:
        ok = service_has_port_8080(project, "sakila-svc")
        if ok is None:
            step.add_error("Service 'sakila-svc' non trovato")
        elif not ok:
            step.add_error("Nessuna porta 8080->8080 trovata su 'sakila-svc'")

    with GradingStep("La Route 'satir' espone satir-svc e serve satir-app") as step:
        route = oc_get_json("route", "satir", "-n", project)
        if not route:
            step.add_error("Route 'satir' non trovata")
        else:
            to_name = route.get("spec", {}).get("to", {}).get("name")
            if to_name != "satir-svc":
                step.add_error(f"La Route punta al service '{to_name}', atteso 'satir-svc'")
            if not route_serves_app(route, "satir-app"):
                step.add_error(
                    f"La Route non risponde con il contenuto atteso di satir-app ({EXPECTED_TEXT!r} da satir-app-*)"
                )

    with GradingStep("L'ingress 'ingr-sakila' instrada verso sakila-svc:8080") as step:
        ingress = oc_get_json("ingress", "ingr-sakila", "-n", project)
        if not ingress:
            step.add_error("Ingress 'ingr-sakila' non trovato")
        else:
            rules = ingress.get("spec", {}).get("rules", []) or []
            matched = False
            for rule in rules:
                for path in (rule.get("http") or {}).get("paths", []) or []:
                    backend = (path.get("backend") or {}).get("service") or {}
                    if backend.get("name") == "sakila-svc" and (backend.get("port") or {}).get("number") == 8080:
                        matched = True
            if not matched:
                step.add_error("Nessuna regola dell'ingress instrada verso il service sakila-svc sulla porta 8080")

    with GradingStep("OpenShift ha generato la Route dall'ingress 'ingr-sakila' e serve sakila-app") as step:
        routes_data = oc_get_json("route", "-n", project)
        routes = routes_data.get("items", []) if routes_data else []
        ingress_routes = [r for r in routes if is_owned_by_ingress(r, "ingr-sakila")]
        if not ingress_routes:
            step.add_error("Nessuna Route generata dall'ingress 'ingr-sakila' trovata")
        elif not any(route_serves_app(r, "sakila-app") for r in ingress_routes):
            step.add_error(
                f"La Route generata dall'ingress non risponde con il contenuto atteso di sakila-app "
                f"({EXPECTED_TEXT!r} da sakila-app-*)"
            )

    with GradingStep("Sticky session abilitata sull'ingress 'ingr-sakila' (affinity=cookie)") as step:
        ingress = oc_get_json("ingress", "ingr-sakila", "-n", project)
        if not ingress:
            step.add_error("Ingress 'ingr-sakila' non trovato")
        else:
            annotations = ingress.get("metadata", {}).get("annotations", {}) or {}
            value = annotations.get("ingress.kubernetes.io/affinity")
            if value != "cookie":
                step.add_error(f"Annotazione 'ingress.kubernetes.io/affinity=cookie' mancante (trovato: {value!r})")

    with GradingStep("Sticky session abilitata sulla Route 'satir' (cookie_name=hello)") as step:
        route = oc_get_json("route", "satir", "-n", project)
        if not route:
            step.add_error("Route 'satir' non trovata")
        else:
            annotations = route.get("metadata", {}).get("annotations", {}) or {}
            value = annotations.get("router.openshift.io/cookie_name")
            if value != "hello":
                step.add_error(f"Annotazione 'router.openshift.io/cookie_name=hello' mancante (trovato: {value!r})")


if __name__ == "__main__":
    main()
