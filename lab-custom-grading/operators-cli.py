#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato operators-cli, sprovvisto di
`lab grade` ufficiale (la classe OperatorsCli nel pacchetto do280 implementa
solo start()/finish(), non grade()).

L'esercizio installa il file-integrity-operator "a mano" (senza OperatorHub)
applicando manifest YAML con placeholder CHANGE_ME che lo studente deve
completare. Confrontando materials/labs/operators-cli/{operator-group,
subscription}.yaml con materials/solutions/operators-cli/{stessi file} si
ricavano i valori esatti attesi:
- OperatorGroup: namespace/targetNamespaces = openshift-file-integrity
- Subscription: channel "stable", installPlanApproval "Manual",
  name "file-integrity-operator", source "gls-catalog-cs",
  sourceNamespace "openshift-marketplace"
Questi valori sono confermati anche dal testo della guida studente (sezioni
2.2 "oc describe packagemanifest" e 3.2/3.4).

Il resto dell'esercizio (approvazione manuale dell'InstallPlan, creazione
della CR FileIntegrity "worker-fileintegrity" - gia' fornita completa in
worker-fileintegrity.yaml, non modificata dallo studente se non per
gracePeriod -, modifica di spec.config.gracePeriod a 60 per forzare un
fallimento al punto 5.3, modifica del filesystem del nodo con `oc debug
node/<nodo> -- touch /host/etc/foobar` al punto 5.5) viene verificato
guardando lo stato finale sul cluster: CSV Succeeded, CR FileIntegrity con
gracePeriod=60, una risorsa FileIntegrityNodeStatus per ciascun nodo
selezionato (nome atteso "<nome-CR>-<nodo>", es. worker-fileintegrity-
master01, come mostrato letteralmente nella guida al punto 5.4), e la
ConfigMap "aide-<nome-CR>-<nodo>-failed" che l'operatore crea quando rileva
la modifica al filesystem (punto 5.7) - unica prova oggettiva, senza dover
eseguire comandi sul nodo, che lo studente ha completato anche i passi
5.3-5.7 della guida. I nomi dei nodi non vengono ipotizzati: si ricavano
dinamicamente da spec.nodeSelector della CR FileIntegrity con `oc get nodes
-l ...`, dato che in alcuni ambienti (cluster compatti) anche un nodo master
puo' avere il ruolo worker.

Uso: operators-cli.py [nome-progetto]   (default: openshift-file-integrity)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "operators-cli"
NAMESPACE = "openshift-file-integrity"
OPERATOR_NAME = "file-integrity-operator"
FI_NAME = "worker-fileintegrity"
EXPECTED_SUBSCRIPTION = {
    "channel": "stable",
    "installPlanApproval": "Manual",
    "name": "file-integrity-operator",
    "source": "gls-catalog-cs",
    "sourceNamespace": "openshift-marketplace",
}
EXPECTED_GRACE_PERIOD = 60


def nodeselector_to_args(selector):
    """Converte uno spec.nodeSelector (dict) nell'argomento -l per `oc get
    nodes`, gestendo sia coppie chiave=valore sia chiavi con valore vuoto
    (solo esistenza della label), come node-role.kubernetes.io/worker: ""."""
    parts = []
    for k, v in (selector or {}).items():
        parts.append(f"{k}={v}" if v else k)
    return ",".join(parts)


def find_csv(namespace, name_prefix):
    csvs = oc_get_json("csv", "-n", namespace)
    if not csvs:
        return None
    for csv in csvs.get("items", []):
        if csv["metadata"]["name"].startswith(name_prefix):
            return csv
    return None


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else NAMESPACE
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il namespace {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Namespace '{project}' non trovato")

    og = oc_get_json("operatorgroup", OPERATOR_NAME, "-n", project)
    with GradingStep("L'OperatorGroup e' configurato correttamente") as step:
        if og is None:
            step.fail(
                f"OperatorGroup '{OPERATOR_NAME}' non trovato nel namespace {project}"
            )
        else:
            targets = og.get("spec", {}).get("targetNamespaces") or []
            if targets != [project]:
                step.add_error(
                    f"spec.targetNamespaces deve essere ['{project}'] "
                    f"(trovato: {targets})"
                )

    sub = oc_get_json("subscription", OPERATOR_NAME, "-n", project)
    with GradingStep("La Subscription e' configurata correttamente") as step:
        if sub is None:
            step.fail(
                f"Subscription '{OPERATOR_NAME}' non trovata nel namespace {project}"
            )
        else:
            spec = sub.get("spec", {})
            for key, expected in EXPECTED_SUBSCRIPTION.items():
                found = spec.get(key)
                if found != expected:
                    step.add_error(
                        f"spec.{key} deve essere '{expected}' (trovato: '{found}')"
                    )

    csv = find_csv(project, OPERATOR_NAME)
    with GradingStep("L'operatore e' installato correttamente (CSV Succeeded)") as step:
        if csv is None:
            step.fail(
                f"Nessun ClusterServiceVersion '{OPERATOR_NAME}*' trovato: "
                "l'InstallPlan e' stato approvato con 'oc patch installplan ...'?"
            )
        else:
            phase = csv.get("status", {}).get("phase")
            if phase != "Succeeded":
                step.add_error(
                    f"CSV '{csv['metadata']['name']}' in fase '{phase}' "
                    "(atteso: 'Succeeded')"
                )

    fi = oc_get_json("fileintegrity", FI_NAME, "-n", project)
    with GradingStep(f"La risorsa FileIntegrity '{FI_NAME}' e' configurata") as step:
        if fi is None:
            step.fail(f"FileIntegrity '{FI_NAME}' non trovata nel namespace {project}")
        else:
            grace_period = fi.get("spec", {}).get("config", {}).get("gracePeriod")
            if grace_period != EXPECTED_GRACE_PERIOD:
                step.add_error(
                    f"spec.config.gracePeriod deve essere {EXPECTED_GRACE_PERIOD} "
                    f"(trovato: {grace_period}) - punto 5.3 della guida: "
                    "'oc edit fileintegrity' per forzare un fallimento"
                )

    worker_nodes = []
    if fi is not None:
        selector_args = nodeselector_to_args(fi.get("spec", {}).get("nodeSelector"))
        if selector_args:
            nodes = oc_get_json("nodes", "-l", selector_args)
            if nodes:
                worker_nodes = [n["metadata"]["name"] for n in nodes.get("items", [])]

    node_statuses = oc_get_json("fileintegritynodestatuses", "-n", project)
    with GradingStep(
        "L'operatore genera un FileIntegrityNodeStatus per i nodi selezionati"
    ) as step:
        if fi is None:
            step.fail()
        elif not worker_nodes:
            step.fail("Nessun nodo trovato con il nodeSelector della CR FileIntegrity")
        elif not node_statuses:
            step.add_error(
                "Nessuna risorsa FileIntegrityNodeStatus trovata "
                f"nel namespace {project} (puo' richiedere qualche minuto, "
                "vedi punto 5.4 della guida)"
            )
        else:
            names = {item["metadata"]["name"] for item in node_statuses.get("items", [])}
            for node in worker_nodes:
                # Nome atteso: <nome-CR>-<nodo>, es. worker-fileintegrity-master01
                # (vedi output letterale della guida al punto 5.4)
                if f"{FI_NAME}-{node}" not in names:
                    step.add_error(
                        f"Nessun FileIntegrityNodeStatus '{FI_NAME}-{node}' trovato"
                    )

    with GradingStep(
        "L'operatore rileva la modifica al filesystem del nodo (scan fallito)"
    ) as step:
        if fi is None or not worker_nodes:
            step.fail()
        else:
            configmaps = oc_get_json("configmap", "-n", project)
            failed_cms = set()
            if configmaps:
                failed_cms = {
                    cm["metadata"]["name"]
                    for cm in configmaps.get("items", [])
                    if cm["metadata"]["name"].startswith(f"aide-{FI_NAME}-")
                    and cm["metadata"]["name"].endswith("-failed")
                }
            if not any(
                f"aide-{FI_NAME}-{node}-failed" in failed_cms for node in worker_nodes
            ):
                step.add_error(
                    f"Nessuna ConfigMap 'aide-{FI_NAME}-<nodo>-failed' trovata: "
                    "verificare di aver eseguito 'oc debug node/<nodo> -- touch "
                    "/host/etc/foobar' e di aver atteso il nuovo scan (punti "
                    "5.3-5.7 della guida, puo' richiedere alcuni minuti)"
                )


if __name__ == "__main__":
    main()
