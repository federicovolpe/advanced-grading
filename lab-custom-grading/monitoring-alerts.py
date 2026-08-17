#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato monitoring-alerts (DO380, Cap. 5.4
"Configure Alerts and Notifications"), sprovvisto di `lab grade` ufficiale
(la classe MonitoringAlerts implementa solo start()/finish(), il commento
"# Grading tasks / none" nel modulo ufficiale lo conferma esplicitamente).

Specifica ricavata dal testo della guida studente (Cap. 5.4, passi 2.1-3.1):
lo studente crea un receiver email "email" in Alertmanager (secret
alertmanager-main, chiave alertmanager.yaml, in openshift-monitoring) con i
valori esatti indicati nella guida, un route override (group_interval 2m,
repeat_interval 1m) e una regola di instradamento che invia a quel receiver
gli alert con alertname=PersistentVolumeUsageNearFull.

Non gradato: il "silence" dell'alert al passo 6 (dura solo 30 minuti per
esplicita scelta della guida, quindi e' un effetto voluto che scade da solo
durante l'esercizio, non uno stato finale da verificare) e la posta ricevuta
su utility (richiederebbe accesso SSH a un host fuori dal cluster OpenShift,
fuori standard per questo script).

Uso: monitoring-alerts.py [nome-progetto]   (default: monitoring-alerts)
"""

import sys
import os
import base64
import subprocess

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "monitoring-alerts"
MONITORING_NS = "openshift-monitoring"
SECRET_NAME = "alertmanager-main"
SECRET_KEY = "alertmanager.yaml"

EXPECTED_EMAIL_CONFIG = {
    "to": "ocp-admins@example.com",
    "from": "alerts@ocp4.example.com",
    "smarthost": "192.168.50.254:25",
    "auth_username": "smtp_training",
}
EXPECTED_ROUTE = {
    "group_interval": "2m",
    "repeat_interval": "1m",
}
EXPECTED_MATCH_ALERT = "PersistentVolumeUsageNearFull"


def load_alertmanager_config():
    secret = oc_get_json("secret", SECRET_NAME, "-n", MONITORING_NS)
    if secret is None:
        return None, "Secret 'alertmanager-main' non trovato in openshift-monitoring"
    raw = secret.get("data", {}).get(SECRET_KEY)
    if raw is None:
        return None, f"Chiave '{SECRET_KEY}' non trovata nel secret"
    try:
        decoded = base64.b64decode(raw).decode("utf-8")
        return yaml.safe_load(decoded), None
    except Exception as e:
        return None, f"Impossibile decodificare/parsare la configurazione: {e}"


def find_receiver(config, name):
    for r in config.get("receivers", []):
        if r.get("name") == name:
            return r
    return None


def find_route_to_email(config):
    for r in config.get("route", {}).get("routes", []):
        if r.get("receiver") == "email":
            return r
    return None


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    config, err = load_alertmanager_config()

    with GradingStep("La configurazione di Alertmanager e' leggibile") as step:
        if err:
            step.fail(err)

    receiver = None
    if config is not None:
        receiver = find_receiver(config, "email")

    with GradingStep("Il receiver 'email' e' configurato correttamente") as step:
        if config is None:
            step.fail()
        elif receiver is None:
            step.fail("Nessun receiver di nome 'email' trovato")
        else:
            email_configs = receiver.get("email_configs") or []
            if not email_configs:
                step.fail("Il receiver 'email' non ha email_configs")
            else:
                ec = email_configs[0]
                for key, expected in EXPECTED_EMAIL_CONFIG.items():
                    if str(ec.get(key)) != expected:
                        step.add_error(
                            f"{key}: atteso '{expected}', trovato '{ec.get(key)}'"
                        )

    with GradingStep("Il route override (group_interval/repeat_interval) e' corretto") as step:
        if config is None:
            step.fail()
        else:
            route = config.get("route", {})
            for key, expected in EXPECTED_ROUTE.items():
                if str(route.get(key)) != expected:
                    step.add_error(
                        f"{key}: atteso '{expected}', trovato '{route.get(key)}'"
                    )

    with GradingStep(
        f"L'alert {EXPECTED_MATCH_ALERT} e' instradato al receiver 'email'"
    ) as step:
        if config is None:
            step.fail()
        else:
            sub_route = find_route_to_email(config)
            if sub_route is None:
                step.fail("Nessuna route che punta al receiver 'email'")
            else:
                matchers = sub_route.get("matchers") or []
                if not any(EXPECTED_MATCH_ALERT in m for m in matchers):
                    step.add_error(
                        f"La route verso 'email' non include il matcher "
                        f"alertname={EXPECTED_MATCH_ALERT} (trovato: {matchers})"
                    )


if __name__ == "__main__":
    main()
