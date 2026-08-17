#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato virtualization-deploy (DO432, Cap.
6.4), sprovvisto di `lab grade` ufficiale (do0016l/virtualization-deploy.py
e' marcato "PLACEHOLDER SCRIPT. PLEASE UPDATE" e implementa solo start()/
finish(), non grade()).

Specifica ricavata dal testo della guida studente (DO432-RHACM2.13-en-2,
Cap. 6.4): lo studente crea un ApplicationSet Argo CD "openshift-virt" (Argo
server openshift-gitops) che punta al repo GitLab
do0016l/virtualization-deploy.git, path virtualization/manifests, remote
namespace openshift-cnv, con placement sul cluster set "gitops-configure"
(limit 2 cluster = hub + managed). Il risultato atteso e' l'operatore
OpenShift Virtualization installato e l'oggetto HyperConverged
kubevirt-hyperconverged in stato ReconcileComplete/Available/Upgradeable su
ENTRAMBI i cluster (la guida lo verifica esplicitamente al passo 4).

Non gradiamo il nome esatto della Placement generata dalla console (creata
in automatico dal wizard, nome non documentato in guida): verifichiamo
l'ApplicationSet per sorgente/destinazione dichiarate, e l'esito reale
sull'hub e sul managed cluster (piu' affidabile di un nome non specificato).

Uso: virtualization-deploy.py   (nessun progetto: le risorse gradate vivono
in openshift-gitops/openshift-cnv su entrambi i cluster, non in un progetto
per-esercizio)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import oc_get_json_kc, condition_true, HUB_KUBECONFIG, MANAGED_KUBECONFIG, GradingStep

APPSET_NAME = "openshift-virt"
REPO_SUFFIX = "do0016l/virtualization-deploy.git"
EXPECTED_PATH = "virtualization/manifests"
EXPECTED_DEST_NS = "openshift-cnv"


def _appset_sources(appset):
    spec = appset.get("spec", {})
    tmpl_spec = spec.get("template", {}).get("spec", {})
    sources = tmpl_spec.get("sources") or []
    if not sources and tmpl_spec.get("source"):
        sources = [tmpl_spec["source"]]
    return sources, tmpl_spec.get("destination", {})


def check_operator_and_hco(kubeconfig, label):
    with GradingStep(f"Operatore OpenShift Virtualization installato ({label})") as step:
        sub = oc_get_json_kc(
            kubeconfig, "subscription.operators.coreos.com",
            "kubevirt-hyperconverged", "-n", EXPECTED_DEST_NS,
        )
        if sub is None:
            step.fail("Subscription 'kubevirt-hyperconverged' non trovata in openshift-cnv")

    with GradingStep(f"HyperConverged sano ({label})") as step:
        hco = oc_get_json_kc(
            kubeconfig, "hyperconverged", "kubevirt-hyperconverged",
            "-n", EXPECTED_DEST_NS,
        )
        if hco is None:
            step.fail("Oggetto 'kubevirt-hyperconverged' non trovato in openshift-cnv")
        else:
            for cond in ("ReconcileComplete", "Available", "Upgradeable"):
                if not condition_true(hco, cond):
                    step.add_error(f"Condition '{cond}' non e' True")


def main():
    print(f"🔧 Grading personalizzato per 'virtualization-deploy'")

    appset = oc_get_json_kc(
        HUB_KUBECONFIG, "applicationset", APPSET_NAME, "-n", "openshift-gitops",
    )
    with GradingStep(f"ApplicationSet '{APPSET_NAME}' configurato correttamente") as step:
        if appset is None:
            step.fail(f"ApplicationSet '{APPSET_NAME}' non trovato in openshift-gitops (hub)")
        else:
            sources, destination = _appset_sources(appset)
            if not any(REPO_SUFFIX in (s.get("repoURL") or "") for s in sources):
                step.add_error(f"Nessuna source punta a un repo '{REPO_SUFFIX}'")
            if not any((s.get("path") or "") == EXPECTED_PATH for s in sources):
                step.add_error(f"Nessuna source usa il path '{EXPECTED_PATH}'")
            if destination.get("namespace") != EXPECTED_DEST_NS:
                step.add_error(
                    f"Remote namespace atteso '{EXPECTED_DEST_NS}', "
                    f"trovato '{destination.get('namespace')}'"
                )

    check_operator_and_hco(HUB_KUBECONFIG, "local-cluster / hub")
    check_operator_and_hco(MANAGED_KUBECONFIG, "managed-cluster")


if __name__ == "__main__":
    main()
