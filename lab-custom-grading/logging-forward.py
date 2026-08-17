#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato logging-forward (DO380, Cap. 6.2
"Configure Log Forwarding"), sprovvisto di `lab grade` ufficiale (la classe
LoggingForward implementa solo start()/finish()).

Specifica ricavata dal diff labs/solutions (clusterlogforwarder.yaml) in
materials/solutions/logging-forward/, che e' completo e non ambiguo (ogni
CHANGE_ME ha un solo valore plausibile): lo studente crea una CR
ClusterLogForwarder "log-to-syslog" in openshift-logging che inoltra i log
applicativi con label logging=critical, quelli infrastructure e quelli
audit verso un server syslog (utility.lab.example.com:514), usando il
ServiceAccount "log-collector".

Non gradate le ClusterRoleBinding RBAC del ServiceAccount (collect-*-logs):
la guida le crea con comandi CLI diretti senza un file di riferimento in
materials, ma sono un prerequisito implicito perche' il forwarder funzioni
- se mancano, la CR risultera' comunque in errore nelle sue condition, che
invece verifichiamo esplicitamente.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json

NAMESPACE = "openshift-logging"
CLF_NAME = "log-to-syslog"
SA_NAME = "log-collector"
SYSLOG_URL = "tcp://utility.lab.example.com:514"

EXPECTED_INPUT_LABEL = {"logging": "critical"}
EXPECTED_OUTPUTS = {
    "audit-syslog": "audit",
    "apps-syslog": "apps",
    "infra-syslog": "infra",
}
EXPECTED_PIPELINE_REFS = {
    "critical-apps-syslog": (["critical-apps"], ["apps-syslog"]),
    "infra-syslog": (["infrastructure"], ["infra-syslog"]),
    "audit-syslog": (["audit"], ["audit-syslog"]),
}


def main():
    print(f"🔧 Grading personalizzato per '{CLF_NAME}' ClusterLogForwarder (logging-forward)")

    clf = oc_get_json("clusterlogforwarder", CLF_NAME, "-n", NAMESPACE)
    with GradingStep(f"La CR ClusterLogForwarder '{CLF_NAME}' esiste con il ServiceAccount corretto") as step:
        if clf is None:
            step.fail(f"ClusterLogForwarder '{CLF_NAME}' non trovato in {NAMESPACE}")
        else:
            sa = clf.get("spec", {}).get("serviceAccount", {}).get("name")
            if sa != SA_NAME:
                step.add_error(f"serviceAccount.name atteso '{SA_NAME}' (trovato: {sa})")

    with GradingStep("L'input applicativo filtra i pod con label logging=critical") as step:
        if clf is None:
            step.fail()
        else:
            inputs = clf.get("spec", {}).get("inputs", [])
            match = next(
                (
                    i for i in inputs
                    if i.get("application", {}).get("selector", {}).get("matchLabels")
                    == EXPECTED_INPUT_LABEL
                ),
                None,
            )
            if match is None:
                step.add_error(
                    f"Nessun input 'application' con selector.matchLabels={EXPECTED_INPUT_LABEL} "
                    f"(input presenti: {[i.get('name') for i in inputs]})"
                )

    with GradingStep("Gli output syslog verso utility.lab.example.com:514 sono configurati") as step:
        if clf is None:
            step.fail()
        else:
            outputs = {o.get("name"): o for o in clf.get("spec", {}).get("outputs", [])}
            for name, msg_id in EXPECTED_OUTPUTS.items():
                out = outputs.get(name)
                if out is None:
                    step.add_error(f"Output '{name}' non trovato")
                    continue
                syslog = out.get("syslog", {})
                if syslog.get("url") != SYSLOG_URL:
                    step.add_error(f"Output '{name}': url atteso '{SYSLOG_URL}' (trovato: {syslog.get('url')})")
                if syslog.get("msgId") != msg_id:
                    step.add_error(f"Output '{name}': msgId atteso '{msg_id}' (trovato: {syslog.get('msgId')})")

    with GradingStep("Le pipeline collegano input critical-apps/infrastructure/audit ai relativi output syslog") as step:
        if clf is None:
            step.fail()
        else:
            pipelines = {p.get("name"): p for p in clf.get("spec", {}).get("pipelines", [])}
            for name, (in_refs, out_refs) in EXPECTED_PIPELINE_REFS.items():
                p = pipelines.get(name)
                if p is None:
                    step.add_error(f"Pipeline '{name}' non trovata")
                    continue
                if p.get("inputRefs") != in_refs:
                    step.add_error(f"Pipeline '{name}': inputRefs atteso {in_refs} (trovato: {p.get('inputRefs')})")
                if p.get("outputRefs") != out_refs:
                    step.add_error(f"Pipeline '{name}': outputRefs atteso {out_refs} (trovato: {p.get('outputRefs')})")

    with GradingStep(f"La CR e' riconciliata correttamente (condition Ready)") as step:
        if clf is None:
            step.fail()
        else:
            conditions = clf.get("status", {}).get("conditions", [])
            ready = next((c for c in conditions if c.get("type") == "Ready"), None)
            if ready is None or ready.get("status") != "True":
                step.add_error(
                    f"Condition 'Ready' non True (trovata: {ready}) — verificare RBAC del "
                    f"ServiceAccount '{SA_NAME}' (collect-application-logs/collect-audit-logs/"
                    "collect-infrastructure-logs)"
                )


if __name__ == "__main__":
    main()
