#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato logging-central (DO380, Cap. 6.4
"Deploy Centralized Logging"), sprovvisto di `lab grade` ufficiale (la
classe LoggingCentral implementa solo start()/finish()).

Specifica ricavata dal diff labs/solutions in materials/solutions/logging-
central/ (nessuna ambiguita': ogni CHANGE_ME ha un solo valore plausibile,
e ocpdevs-role.yaml e' identico fra labs e solutions, quindi va applicato
cosi' com'e'). Lo studente crea, in openshift-logging: un ObjectBucketClaim
"loki-bucket-odf" (storage ODF/NooBaa), una LokiStack "logging-loki" che lo
usa, una ClusterLogForwarder "to-loki" che inoltra application/infra/audit
verso Loki tramite il ServiceAccount "log-collector", e uno UIPlugin
"logging" collegato alla stessa LokiStack. Nel progetto "testing-logs" crea
un RoleBinding "view-application-logs" che da' al gruppo "ocpdevs" il
ClusterRole "cluster-logging-application-view".
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

NAMESPACE = "openshift-logging"
TESTING_PROJECT = "testing-logs"

OBC_NAME = "loki-bucket-odf"
LOKISTACK_NAME = "logging-loki"
CLF_NAME = "to-loki"
UIPLUGIN_NAME = "logging"
ROLEBINDING_NAME = "view-application-logs"


def main():
    print(f"🔧 Grading personalizzato per la centralized logging stack (logging-central)")

    obc = oc_get_json("objectbucketclaim", OBC_NAME, "-n", NAMESPACE)
    with GradingStep(f"L'ObjectBucketClaim '{OBC_NAME}' esiste ed e' Bound") as step:
        if obc is None:
            step.fail(f"ObjectBucketClaim '{OBC_NAME}' non trovato in {NAMESPACE}")
        elif obc.get("status", {}).get("phase") != "Bound":
            step.add_error(f"Fase attesa 'Bound' (trovata: {obc.get('status', {}).get('phase')})")

    lokistack = oc_get_json("lokistack", LOKISTACK_NAME, "-n", NAMESPACE)
    with GradingStep(f"La LokiStack '{LOKISTACK_NAME}' esiste con lo storage secret corretto") as step:
        if lokistack is None:
            step.fail(f"LokiStack '{LOKISTACK_NAME}' non trovato in {NAMESPACE}")
        else:
            secret_name = lokistack.get("spec", {}).get("storage", {}).get("secret", {}).get("name")
            if secret_name != "logging-loki-odf":
                step.add_error(
                    f"storage.secret.name atteso 'logging-loki-odf' (trovato: {secret_name})"
                )
            conditions = lokistack.get("status", {}).get("conditions", [])
            ready = next((c for c in conditions if c.get("type") == "Ready"), None)
            if ready is None or ready.get("status") != "True":
                step.add_error(f"La LokiStack non e' Ready (condition: {ready})")

    clf = oc_get_json("clusterlogforwarder", CLF_NAME, "-n", NAMESPACE)
    with GradingStep(f"La ClusterLogForwarder '{CLF_NAME}' inoltra i log verso Loki") as step:
        if clf is None:
            step.fail(f"ClusterLogForwarder '{CLF_NAME}' non trovato in {NAMESPACE}")
        else:
            sa = clf.get("spec", {}).get("serviceAccount", {}).get("name")
            if sa != "log-collector":
                step.add_error(f"serviceAccount.name atteso 'log-collector' (trovato: {sa})")

            outputs = clf.get("spec", {}).get("outputs", [])
            loki_out = next((o for o in outputs if o.get("type") == "lokiStack"), None)
            if loki_out is None:
                step.add_error("Nessun output di tipo 'lokiStack' trovato")
            else:
                target = loki_out.get("lokiStack", {}).get("target", {})
                if target.get("name") != LOKISTACK_NAME:
                    step.add_error(
                        f"lokiStack.target.name atteso '{LOKISTACK_NAME}' (trovato: {target.get('name')})"
                    )

            pipelines = clf.get("spec", {}).get("pipelines", [])
            pipeline_ok = any(
                set(p.get("inputRefs", [])) >= {"infrastructure", "audit", "application"}
                and loki_out is not None
                and loki_out.get("name") in p.get("outputRefs", [])
                for p in pipelines
            )
            if not pipeline_ok:
                step.add_error(
                    "Nessuna pipeline che inoltra infrastructure+audit+application "
                    "verso l'output Loki"
                )

            conditions = clf.get("status", {}).get("conditions", [])
            ready = next((c for c in conditions if c.get("type") == "Ready"), None)
            if ready is None or ready.get("status") != "True":
                step.add_error(f"La CR non e' riconciliata correttamente (condition Ready: {ready})")

    uiplugin = oc_get_json("uiplugin", UIPLUGIN_NAME)
    with GradingStep(f"Lo UIPlugin '{UIPLUGIN_NAME}' e' collegato alla LokiStack '{LOKISTACK_NAME}'") as step:
        if uiplugin is None:
            step.fail(f"UIPlugin '{UIPLUGIN_NAME}' non trovato")
        else:
            lokistack_ref = uiplugin.get("spec", {}).get("logging", {}).get("lokiStack", {}).get("name")
            if lokistack_ref != LOKISTACK_NAME:
                step.add_error(
                    f"logging.lokiStack.name atteso '{LOKISTACK_NAME}' (trovato: {lokistack_ref})"
                )

    with GradingStep(f"Il progetto {TESTING_PROJECT} esiste") as step:
        if not project_exists(TESTING_PROJECT):
            step.fail(f"Progetto '{TESTING_PROJECT}' non trovato")

    rb = oc_get_json("rolebinding", ROLEBINDING_NAME, "-n", TESTING_PROJECT)
    with GradingStep(
        f"Il RoleBinding '{ROLEBINDING_NAME}' concede al gruppo 'ocpdevs' il ClusterRole corretto"
    ) as step:
        if rb is None:
            step.fail(f"RoleBinding '{ROLEBINDING_NAME}' non trovato nel progetto {TESTING_PROJECT}")
        else:
            role_ref = rb.get("roleRef", {})
            if role_ref.get("name") != "cluster-logging-application-view":
                step.add_error(
                    f"roleRef.name atteso 'cluster-logging-application-view' (trovato: {role_ref.get('name')})"
                )
            subjects = rb.get("subjects", [])
            if not any(s.get("kind") == "Group" and s.get("name") == "ocpdevs" for s in subjects):
                step.add_error("Nessun subject Group 'ocpdevs' trovato nel RoleBinding")


if __name__ == "__main__":
    main()
