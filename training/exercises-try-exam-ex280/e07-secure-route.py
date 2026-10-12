"""
Try-exam EX280, 7 — route sicura (edge) con certificato self-signed
(tema: "CONFIGURE AND DEPLOY A SECURE ROUTE").

Il tema usa hello.apps.ocp4.example.com: qui l'host e' costruito sul
dominio delle route di QUESTO cluster (apps_domain()), altrimenti la
route non sarebbe raggiungibile. Il soggetto del certificato e' quello
del tema, con il CN adattato allo stesso modo.

setup() crea la premessa (deployment + service hello, nessuna route):
lo studente genera chiave/certificato e crea la route.
"""
import subprocess
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ex280_common import (
    CHAPTER, SETUP_TIMEOUT, IMG_HELLO, GradingStep, oc, oc_get_json, track_lock,
    require_cluster_admin, reset_owned_project, delete_owned_project,
    apps_domain, http_status, run_cli,
)

SLUG = "e07"
PROJECT = "practice3"
APP = "hello"
HOST = f"{APP}.{apps_domain()}"
SUBJECT = f"/C=US/ST=NC/L=Raleigh/O=RedHat/OU=RHT/CN={HOST}"

TITLE = "7) Route sicura per l'applicazione hello"

TASK = f"""\
Nel progetto {PROJECT} c'e' l'applicazione {APP} (deployment e service
gia' presenti).

  - Esponi l'applicazione con una route sicura chiamata {APP}.
  - Usa un certificato self-signed con soggetto
        {SUBJECT}
  - L'applicazione deve essere raggiungibile all'indirizzo
        https://{HOST}
"""

SOLUTION = f"""\
mkdir ~/certs && cd ~/certs
openssl genrsa -out {APP}.key 4096
openssl req -new -key {APP}.key -out {APP}.csr \\
    -subj "{SUBJECT}"
openssl x509 -req -in {APP}.csr -signkey {APP}.key \\
    -out {APP}.crt -days 1825

oc create route edge {APP} --service {APP} -n {PROJECT} \\
    --key {APP}.key --cert {APP}.crt --hostname {HOST}

curl -k https://{HOST}
curl -kv https://{HOST} 2>&1 | grep subject     # e' il tuo certificato?
"""


def setup():
    require_cluster_admin()
    with track_lock():
        reset_owned_project(PROJECT, SLUG)
        oc("create", "deployment", APP, f"--image={IMG_HELLO}", "-n", PROJECT, check=True)
        oc("expose", "deployment", APP, "--port=8080", "-n", PROJECT, check=True)


def _cert_subject(pem):
    result = subprocess.run(["openssl", "x509", "-noout", "-subject"],
                            input=pem, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def grade():
    route = oc_get_json("route", APP, "-n", PROJECT)
    spec = (route or {}).get("spec") or {}
    tls = spec.get("tls") or {}

    with GradingStep(f"La route {APP} esiste e punta al service {APP}") as step:
        if not route:
            step.fail(f"Route '{APP}' non trovata in {PROJECT}")
        elif (spec.get("to") or {}).get("name") != APP:
            step.add_error(f"punta a {(spec.get('to') or {}).get('name')!r}")

    with GradingStep(f"La route usa l'host {HOST}") as step:
        if spec.get("host") != HOST:
            step.add_error(f"host = {spec.get('host')!r}")

    with GradingStep("La route e' sicura, con terminazione edge") as step:
        if tls.get("termination") != "edge":
            step.add_error(f"termination = {tls.get('termination')!r}")

    with GradingStep(f"Il certificato della route ha CN={HOST}") as step:
        if not tls.get("certificate"):
            step.fail("nessun certificato nella route (userebbe quello di default del router)")
        else:
            subject = _cert_subject(tls["certificate"]) or ""
            if f"CN={HOST}" not in subject.replace(" = ", "="):
                step.add_error(f"soggetto: {subject or 'illeggibile'}")
        if tls.get("certificate") and not tls.get("key"):
            step.add_error("manca la chiave privata")

    with GradingStep(f"https://{HOST} risponde 200") as step:
        code = http_status(f"https://{HOST}/")
        if code != "200":
            step.add_error(f"HTTP {code}")


def cleanup():
    with track_lock():
        delete_owned_project(PROJECT, SLUG)


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
