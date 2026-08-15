#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato network-ingress (DO280), sprovvisto
di `lab grade` ufficiale (la classe NetworkIngress nel pacchetto do280
implementa solo start()/finish(), non grade()).

Non esiste una cartella materials/solutions/network-ingress in cache, quindi
la specifica e' stata ricavata dal testo della guida studente (Chapter 4.2,
"Protect External Traffic with TLS") oltre che dai file di partenza in
materials/labs/network-ingress (todo-app-v1.yaml, todo-app-v2.yaml,
certs/openssl-commands.txt, certs/training.ext).

Stato finale atteso sul cluster, secondo la guida:
- todo-http: Deployment+Service (immagine todo-angular:v1.1, todo-app-v1.yaml)
  esposto da una Route SENZA TLS con hostname todo-http.apps.ocp4.example.com
  (step 2: "oc expose svc todo-http --hostname ...").
- Una Route edge temporanea viene creata allo step 3 solo a scopo didattico
  (per confrontare edge vs passthrough) e viene ESPLICITAMENTE cancellata
  allo step 3.8 ("oc delete route todo-https") prima di creare la versione
  passthrough: non viene quindi gradata, dato che nello stato finale non
  deve esistere.
- Un Secret TLS "todo-certs" (--cert training.crt --key training.key,
  generati con la CA "training" creata da start() via steps.gen_tls_ca)
  viene creato allo step 5.1.
- todo-https: Deployment+Service (immagine todo-angular:v1.2,
  todo-app-v2.yaml) che monta il secret todo-certs come volume "tls-certs"
  su /usr/local/etc/ssl/certs e espone la porta 8443, creato allo step 5.3.
- Una Route "todo-https" con terminazione PASSTHROUGH (non edge!) verso il
  service todo-https:8443, hostname todo-https.apps.ocp4.example.com, creata
  allo step 6.1 ("oc create route passthrough todo-https --service
  todo-https --port 8443 ...").

In aggiunta ai controlli sulle risorse OpenShift, viene fatta una vera
richiesta HTTPS (GET, sola lettura) alla Route passthrough validando la
catena di certificati contro la CA "training-CA.pem" generata dallo start():
se il certificato non verifica con quella CA, la connessione TLS non sta
terminando sul pod applicativo (es. e' rimasta una route edge, o il
certificato montato non e' quello generato con openssl-commands.txt), quindi
e' un riscontro oggettivo e a basso rischio del punto centrale dell'esercizio
("Verify that the communication to the application is encrypted").

Uso: network-ingress.py [nome-progetto]   (default: network-ingress)
"""

import os
import ssl
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "network-ingress"

TODO_HTTP_IMAGE = "todo-angular:v1.1"
TODO_HTTP_HOST = "todo-http.apps.ocp4.example.com"

TODO_HTTPS_IMAGE = "todo-angular:v1.2"
TODO_HTTPS_HOST = "todo-https.apps.ocp4.example.com"
TODO_CERTS_SECRET = "todo-certs"
TLS_MOUNT_PATH = "/usr/local/etc/ssl/certs"

CA_CERT_FILE = os.path.expanduser(
    f"~/DO280/labs/{LAB_NAME}/certs/training-CA.pem"
)


def container_with_image(deployment, image_substr):
    if deployment is None:
        return None
    for c in deployment["spec"]["template"]["spec"].get("containers", []):
        if image_substr in c.get("image", ""):
            return c
    return None


def ready_replicas(deployment):
    return deployment.get("status", {}).get("readyReplicas", 0) if deployment else 0


def mounts_secret(deployment, container, secret_name, mount_path):
    """True se il container monta, al path indicato, un volume che punta al
    Secret dato (replica lo schema di todo-app-v2.yaml: volume 'tls-certs'
    da secret 'todo-certs' su /usr/local/etc/ssl/certs)."""
    if deployment is None or container is None:
        return False
    volumes = {
        v.get("name"): v
        for v in deployment["spec"]["template"]["spec"].get("volumes", []) or []
    }
    for vm in container.get("volumeMounts", []) or []:
        vol = volumes.get(vm.get("name"))
        if not vol:
            continue
        if vol.get("secret", {}).get("secretName") == secret_name and vm.get(
            "mountPath"
        ) == mount_path:
            return True
    return False


def fetch_verified(url, cafile, timeout=10):
    """GET read-only con verifica della catena di certificati contro la CA
    indicata. Ritorna (status, body) o (None, errore) se la connessione/
    verifica TLS fallisce."""
    ctx = ssl.create_default_context(cafile=cafile)
    try:
        with urllib.request.urlopen(url, timeout=timeout, context=ctx) as resp:
            return resp.status, None
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return None, str(e)


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    # --- todo-http: versione non cifrata (v1.1) ---
    dep_http = oc_get_json("deployment", "todo-http", "-n", project)
    svc_http = oc_get_json("service", "todo-http", "-n", project)

    with GradingStep(
        f"Il deployment todo-http usa l'immagine {TODO_HTTP_IMAGE} ed e' pronto"
    ) as step:
        if dep_http is None:
            step.fail("Deployment 'todo-http' non trovato")
        else:
            if container_with_image(dep_http, TODO_HTTP_IMAGE) is None:
                step.add_error(
                    f"Nessun container del deployment 'todo-http' usa "
                    f"un'immagine contenente '{TODO_HTTP_IMAGE}'"
                )
            if not ready_replicas(dep_http):
                step.add_error("Nessuna replica pronta per il deployment 'todo-http'")

    with GradingStep("Il service todo-http esiste") as step:
        if svc_http is None:
            step.fail("Service 'todo-http' non trovato")

    route_http = oc_get_json("route", "todo-http", "-n", project)
    with GradingStep(
        "La Route todo-http espone l'app in chiaro (senza TLS)"
    ) as step:
        if route_http is None:
            step.fail("Route 'todo-http' non trovata")
        else:
            spec = route_http.get("spec", {})
            host = spec.get("host", "")
            if not host.startswith("todo-http."):
                step.add_error(
                    f"Hostname della Route 'todo-http' inatteso: {host!r} "
                    f"(atteso un hostname tipo {TODO_HTTP_HOST})"
                )
            if spec.get("tls"):
                step.add_error(
                    "La Route 'todo-http' non dovrebbe avere terminazione TLS "
                    "(questa parte dell'esercizio serve a mostrare il "
                    "traffico non cifrato, poi intercettato con tcpdump)"
                )
            if spec.get("to", {}).get("name") != "todo-http":
                step.add_error(
                    "La Route 'todo-http' non punta al service 'todo-http'"
                )

    # --- Secret TLS con il certificato generato dalla CA "training" ---
    secret = oc_get_json("secret", TODO_CERTS_SECRET, "-n", project)
    with GradingStep(f"Il Secret TLS '{TODO_CERTS_SECRET}' esiste") as step:
        if secret is None:
            step.fail(f"Secret '{TODO_CERTS_SECRET}' non trovato")
        elif secret.get("type") != "kubernetes.io/tls":
            step.add_error(
                f"Il Secret '{TODO_CERTS_SECRET}' non e' di tipo "
                f"kubernetes.io/tls (trovato: {secret.get('type')})"
            )
        elif not secret.get("data", {}).get("tls.crt") or not secret.get(
            "data", {}
        ).get("tls.key"):
            step.add_error(
                f"Il Secret '{TODO_CERTS_SECRET}' non contiene sia tls.crt "
                "che tls.key"
            )

    # --- todo-https: versione cifrata (v1.2), monta il secret todo-certs ---
    dep_https = oc_get_json("deployment", "todo-https", "-n", project)
    container_https = container_with_image(dep_https, TODO_HTTPS_IMAGE)
    svc_https = oc_get_json("service", "todo-https", "-n", project)

    with GradingStep(
        f"Il deployment todo-https usa l'immagine {TODO_HTTPS_IMAGE} ed e' pronto"
    ) as step:
        if dep_https is None:
            step.fail("Deployment 'todo-https' non trovato")
        else:
            if container_https is None:
                step.add_error(
                    f"Nessun container del deployment 'todo-https' usa "
                    f"un'immagine contenente '{TODO_HTTPS_IMAGE}'"
                )
            if not ready_replicas(dep_https):
                step.add_error("Nessuna replica pronta per il deployment 'todo-https'")

    with GradingStep(
        f"Il deployment todo-https monta il Secret '{TODO_CERTS_SECRET}' "
        f"su {TLS_MOUNT_PATH}"
    ) as step:
        if dep_https is None or container_https is None:
            step.fail()
        elif not mounts_secret(
            dep_https, container_https, TODO_CERTS_SECRET, TLS_MOUNT_PATH
        ):
            step.add_error(
                f"Nessun volume mount da Secret '{TODO_CERTS_SECRET}' su "
                f"{TLS_MOUNT_PATH} trovato nel deployment 'todo-https'"
            )

    with GradingStep("Il service todo-https espone la porta 8443") as step:
        if svc_https is None:
            step.fail("Service 'todo-https' non trovato")
        else:
            ports = {p.get("port") for p in svc_https.get("spec", {}).get("ports", [])}
            if 8443 not in ports:
                step.add_error(
                    f"Il service 'todo-https' non espone la porta 8443 "
                    f"(porte trovate: {sorted(ports)})"
                )

    # --- Route passthrough (NON edge: la eventuale route edge dello step 3
    # va cancellata dallo studente prima di questo punto) ---
    route_https = oc_get_json("route", "todo-https", "-n", project)
    with GradingStep(
        "La Route todo-https usa terminazione TLS passthrough verso todo-https:8443"
    ) as step:
        if route_https is None:
            step.fail("Route 'todo-https' non trovata")
        else:
            spec = route_https.get("spec", {})
            termination = spec.get("tls", {}).get("termination")
            if termination != "passthrough":
                step.add_error(
                    f"Terminazione TLS della Route 'todo-https' inattesa: "
                    f"{termination!r} (attesa: 'passthrough'; la Route edge "
                    "creata al punto 3 dell'esercizio va cancellata prima di "
                    "creare quella passthrough al punto 6)"
                )
            if spec.get("to", {}).get("name") != "todo-https":
                step.add_error(
                    "La Route 'todo-https' non punta al service 'todo-https'"
                )
            target_port = str(
                spec.get("port", {}).get("targetPort", "")
            )
            if target_port not in ("8443", "https"):
                step.add_error(
                    f"La Route 'todo-https' non punta alla porta 8443/https "
                    f"del service (trovato: {target_port!r})"
                )
            host = spec.get("host", "")
            if not host.startswith("todo-https."):
                step.add_error(
                    f"Hostname della Route 'todo-https' inatteso: {host!r} "
                    f"(atteso un hostname tipo {TODO_HTTPS_HOST})"
                )

    with GradingStep(
        "Il traffico HTTPS verso la Route passthrough e' cifrato con il "
        "certificato firmato dalla CA 'training'"
    ) as step:
        if route_https is None or not route_https.get("spec", {}).get("host"):
            step.fail()
        elif not os.path.isfile(CA_CERT_FILE):
            step.add_error(
                f"CA di riferimento non trovata in {CA_CERT_FILE} (l'esercizio "
                "e' stato avviato con 'lab start network-ingress'?)"
            )
        else:
            host = route_https["spec"]["host"]
            status, err = fetch_verified(f"https://{host}/", CA_CERT_FILE)
            if status != 200:
                step.add_error(
                    f"GET https://{host}/ verificato contro {CA_CERT_FILE} "
                    f"non riuscito (status={status}, errore={err}). Se la "
                    "route e' ancora edge, o il secret todo-certs non monta "
                    "il certificato generato con openssl-commands.txt, la "
                    "verifica del certificato fallisce."
                )


if __name__ == "__main__":
    main()
