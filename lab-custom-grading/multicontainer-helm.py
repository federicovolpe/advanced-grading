#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise multicontainer-helm (DO288), priva
di `lab grade` ufficiale (il modulo do288/multicontainer_helm.py implementa
solo start()/finish()).

Lo studente modifica il chart Helm locale in
~/DO288/labs/multicontainer-helm/expense-service (imposta postgres.user,
postgres.pass, postgres.db in values.yaml e incrementa la versione del
chart a 0.2.0), poi esegue `helm install --wait expense-service .` e infine
`helm upgrade --wait expense-service .`. Lo stato finale e' quindi
verificabile SOLO sul cluster (release Helm + risorse renderizzate), non sui
file locali.

Schema di `helm list -o json` (Helm v3, verificato leggendo il codice
sorgente di riferimento -- non e' stato possibile eseguire un test dal vivo
in questa sessione: la sessione oc/helm e' anonima, senza login al cluster,
e la policy di questo repo vieta comunque `helm install/upgrade` per
testare): ogni elemento della lista e' un dict con almeno le chiavi
"name", "namespace", "revision", "updated", "status", "chart" (stringa
"<nome-chart>-<versione>", es. "expense-service-0.2.0") e "app_version".
Usiamo "status" (valore "deployed") e "chart" (contiene la versione) per la
verifica sotto.

Specifica (fornita dall'utente, che ha letto guida ufficiale + NOTES.txt del
chart):
- Release Helm "expense-service" con status "deployed".
- Secret "postgresql": database-user="dbuser", database-password="mypass",
  database-name="sampledb" (valori fissi impostati in values.yaml, al posto
  di quelli casuali iniziali).
- Deployment "expense-service": status.availableReplicas >= 1.
- Route "expense-service" con host "expense-service.apps.ocp4.example.com".
- GET su .../expenses risponde con un array JSON.

Uso: multicontainer-helm.py [nome-progetto]   (default: multicontainer-helm)
"""

import base64
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, helm_get_json, http_get_json, oc_get_json, project_exists

LAB_NAME = "multicontainer-helm"
RELEASE = "expense-service"
DEPLOYMENT = "expense-service"
ROUTE = "expense-service"
SECRET = "postgresql"
EXPECTED_HOST = "expense-service.apps.ocp4.example.com"
EXPECTED_USER = "dbuser"
EXPECTED_PASSWORD = "mypass"
EXPECTED_DB = "sampledb"


def _b64decode(value):
    try:
        return base64.b64decode(value or "").decode("utf-8")
    except Exception:
        return None


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(f"La release Helm '{RELEASE}' e' 'deployed' (versione 0.2.0 del chart)") as step:
        releases = helm_get_json("list", "--filter", RELEASE, namespace=project)
        release = next((r for r in (releases or []) if r.get("name") == RELEASE), None)
        if not release:
            step.fail(f"Nessuna release Helm '{RELEASE}' trovata nel namespace '{project}'")
        else:
            if release.get("status") != "deployed":
                step.add_error(f"Status della release e' {release.get('status')!r}, atteso 'deployed'")
            chart = release.get("chart", "")
            if "0.2.0" not in chart:
                step.add_error(
                    f"Il campo 'chart' e' {chart!r}: non riporta la versione 0.2.0 attesa "
                    "dopo l'upgrade"
                )

    with GradingStep(f"Il Secret '{SECRET}' contiene le credenziali fisse impostate in values.yaml") as step:
        secret = oc_get_json("secret", SECRET, "-n", project)
        if not secret:
            step.fail(f"Secret '{SECRET}' non trovato")
        else:
            data = secret.get("data") or {}
            user = _b64decode(data.get("database-user"))
            password = _b64decode(data.get("database-password"))
            dbname = _b64decode(data.get("database-name"))
            if user != EXPECTED_USER:
                step.add_error(f"database-user e' {user!r}, atteso '{EXPECTED_USER}'")
            if password != EXPECTED_PASSWORD:
                step.add_error(f"database-password e' {password!r}, atteso '{EXPECTED_PASSWORD}'")
            if dbname != EXPECTED_DB:
                step.add_error(f"database-name e' {dbname!r}, atteso '{EXPECTED_DB}'")

    with GradingStep(f"Il Deployment '{DEPLOYMENT}' ha almeno una replica disponibile") as step:
        deployment = oc_get_json("deployment", DEPLOYMENT, "-n", project)
        if not deployment:
            step.fail(f"Deployment '{DEPLOYMENT}' non trovato")
        elif (deployment.get("status") or {}).get("availableReplicas", 0) < 1:
            step.add_error(f"Il Deployment '{DEPLOYMENT}' non ha replica disponibili")

    route = oc_get_json("route", ROUTE, "-n", project)
    with GradingStep(f"La Route '{ROUTE}' esiste con host '{EXPECTED_HOST}'") as step:
        if not route:
            step.fail(f"Route '{ROUTE}' non trovata")
        else:
            host = (route.get("spec") or {}).get("host", "")
            if host != EXPECTED_HOST:
                step.add_error(f"Host della Route e' {host!r}, atteso '{EXPECTED_HOST}'")

    with GradingStep("GET /expenses tramite la Route risponde con un array JSON") as step:
        if not route:
            step.fail(f"Route '{ROUTE}' non trovata")
        else:
            host = (route.get("spec") or {}).get("host", "")
            ok, body = http_get_json(f"http://{host}/expenses")
            if not ok:
                step.add_error(f"Nessuna risposta JSON valida da 'http://{host}/expenses'")
            elif not isinstance(body, list):
                step.add_error(f"La risposta non e' un array JSON (tipo: {type(body).__name__})")


if __name__ == "__main__":
    main()
