#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato policies-deploy (DO432/do0013l,
Cap. 3.4 "Deploy Policies by Using the RHACM Governance Dashboard"),
sprovvisto di `lab grade` ufficiale.

Fonte della specifica: testo della guida studente (DO432-RHACM2.13-en-2)
Cap. 3.4, incrociato con policies-deploy.py (start()/finish()) e con
materials/{labs,solutions}/policies-deploy/*.sh.

La guida chiede di creare, dalla console RHACM, una Policy
"certificate-policy-console-ingress" (namespace policies-deploy) che
verifica la scadenza dei certificati in openshift-console e
openshift-ingress (< 300 ore), con una Placement/PlacementBinding
"certificate-policy-console-ingress-placement" verso tutti i cluster.
MA al passo 7 la guida chiede esplicitamente di CANCELLARE la policy (e le
risorse associate) prima di "lab finish": lo stato finale "corretto"
coincide quindi con quello iniziale (nessuna policy), quindi non è un
segnale gradabile in modo affidabile (vedi CLAUDE.md sez. 2, pattern
round-trip). Il segnale oggettivo e persistente fino a `lab finish()` (che
cancella il progetto e il Secret "router-cert") è invece la remediation del
passo 5: lo script remediate-cert.sh sostituisce il Secret TLS "router-cert"
in openshift-ingress con un certificato valido 365 giorni (il Secret
originale, creato da start()/create-cert.sh, scade dopo 1 giorno < 300 ore).
Verifichiamo quindi la scadenza del certificato, non la Policy transitoria.

Uso: policies-deploy.py [nome-progetto]   (default: policies-deploy)
"""

import base64
import datetime
import subprocess
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "policies-deploy"
CERT_SECRET = "router-cert"
CERT_NAMESPACE = "openshift-ingress"
MIN_HOURS_VALID = 300


def cert_not_after(secret):
    """Ritorna il datetime (UTC) di scadenza del certificato TLS nel
    Secret, o None se il Secret non ha un campo tls.crt valido."""
    tls_crt_b64 = secret.get("data", {}).get("tls.crt")
    if not tls_crt_b64:
        return None
    try:
        pem = base64.b64decode(tls_crt_b64)
    except Exception:
        return None
    result = subprocess.run(
        ["openssl", "x509", "-noout", "-enddate"],
        input=pem, capture_output=True,
    )
    if result.returncode != 0:
        return None
    # Output: "notAfter=Jan  1 00:00:00 2027 GMT"
    line = result.stdout.decode().strip()
    if not line.startswith("notAfter="):
        return None
    try:
        return datetime.datetime.strptime(
            line[len("notAfter="):], "%b %d %H:%M:%S %Y %Z"
        ).replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        return None


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(
        f"Il namespace {project} e' associato a un cluster set (ManagedClusterSetBinding)"
    ) as step:
        bindings = oc_get_json("managedclustersetbinding", "-n", project)
        if not bindings or not bindings.get("items"):
            step.add_error(
                f"Nessuna ManagedClusterSetBinding trovata nel namespace '{project}' "
                "(passo 2 della guida: bind del cluster set 'default' al namespace)"
            )

    with GradingStep(
        f"Il Secret TLS '{CERT_SECRET}' in {CERT_NAMESPACE} e' stato "
        "remediato (scadenza oltre 300 ore)"
    ) as step:
        secret = oc_get_json("secret", CERT_SECRET, "-n", CERT_NAMESPACE)
        if secret is None:
            step.fail(
                f"Secret '{CERT_SECRET}' non trovato nel namespace '{CERT_NAMESPACE}' "
                "(creato da 'lab start policies-deploy': l'esercizio e' stato avviato?)"
            )
        else:
            not_after = cert_not_after(secret)
            if not_after is None:
                step.add_error(
                    f"Impossibile leggere la data di scadenza del certificato "
                    f"nel Secret '{CERT_SECRET}'"
                )
            else:
                now = datetime.datetime.now(datetime.timezone.utc)
                hours_left = (not_after - now).total_seconds() / 3600
                if hours_left < MIN_HOURS_VALID:
                    step.add_error(
                        f"Il certificato scade tra {hours_left:.0f} ore "
                        f"(atteso >= {MIN_HOURS_VALID}h dopo la remediation con "
                        "remediate-cert.sh): certificato ancora non conforme"
                    )


if __name__ == "__main__":
    main()
