#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato gitops-admin (DO380, Cap. 4.4
"Deploy GitOps for Cluster Administration"), sprovvisto di `lab grade`
ufficiale.

Specifica ricavata da:
- materials/solutions/gitops-admin/console.yaml e ca-snippet.yaml (do380)
- testo della guida ufficiale, Cap. 4.4, punti 3-9 (pagine 296-302)

L'esercizio non usa un progetto omonimo: tutte le risorse gradate vivono
nel namespace di sistema openshift-gitops (istanza Argo CD di default) e
sono a livello cluster (Console). Il progetto "gitops-admin" non esiste
nel modulo ufficiale.

Uso: gitops-admin.py [ignorato]
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json

ARGOCD_NAMESPACE = "openshift-gitops"
EXPECTED_RBAC_LINE = "g, ocpadmins, role:admin"
EXPECTED_MOUNT_PATH = "/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem"
EXPECTED_SUBPATH = "ca-bundle.crt"
CA_CONFIGMAP = "cluster-root-ca-bundle"
EXPECTED_REPO_URL = "https://git.ocp4.example.com/developer/gitops-admin.git"
EXPECTED_PRODUCT_NAME = "Production"


def main():
    print("🔧 Grading personalizzato per 'gitops-admin'")

    argocd = oc_get_json("argocd", "openshift-gitops", "-n", ARGOCD_NAMESPACE)

    with GradingStep("L'istanza Argo CD di default e' presente") as step:
        if argocd is None:
            step.fail(
                f"Risorsa 'argocd/openshift-gitops' non trovata nel namespace "
                f"{ARGOCD_NAMESPACE} (operatore OpenShift GitOps non installato?)"
            )

    with GradingStep("Il gruppo ocpadmins ha il ruolo admin su Argo CD") as step:
        if argocd is None:
            step.fail()
        else:
            policy = argocd.get("spec", {}).get("rbac", {}).get("policy", "")
            if EXPECTED_RBAC_LINE not in policy:
                step.add_error(
                    f"La policy RBAC di Argo CD non contiene la riga "
                    f"'{EXPECTED_RBAC_LINE}'"
                )

    with GradingStep("Il repository server monta il CA bundle del classroom") as step:
        if argocd is None:
            step.fail()
        else:
            repo = argocd.get("spec", {}).get("repo", {})
            mounts = repo.get("volumeMounts") or []
            volumes = repo.get("volumes") or []
            mount_ok = any(
                m.get("mountPath") == EXPECTED_MOUNT_PATH
                and m.get("subPath") == EXPECTED_SUBPATH
                and m.get("name") == CA_CONFIGMAP
                for m in mounts
            )
            volume_ok = any(
                v.get("configMap", {}).get("name") == CA_CONFIGMAP for v in volumes
            )
            if not mount_ok:
                step.add_error(
                    f"spec.repo.volumeMounts non monta {CA_CONFIGMAP} su "
                    f"{EXPECTED_MOUNT_PATH} (subPath {EXPECTED_SUBPATH})"
                )
            if not volume_ok:
                step.add_error(
                    f"spec.repo.volumes non referenzia la configmap {CA_CONFIGMAP}"
                )

    configmap = oc_get_json("configmap", CA_CONFIGMAP, "-n", ARGOCD_NAMESPACE)

    with GradingStep(f"La configmap {CA_CONFIGMAP} inietta il CA bundle") as step:
        if configmap is None:
            step.fail(f"Configmap '{CA_CONFIGMAP}' non trovata in {ARGOCD_NAMESPACE}")
        else:
            labels = configmap.get("metadata", {}).get("labels") or {}
            if labels.get("config.openshift.io/inject-trusted-cabundle") != "true":
                step.add_error(
                    "Manca la label config.openshift.io/inject-trusted-cabundle=true"
                )

    application = oc_get_json(
        "application.argoproj.io", "gitops-admin", "-n", ARGOCD_NAMESPACE
    )

    with GradingStep("L'applicazione Argo CD gitops-admin e' configurata correttamente") as step:
        if application is None:
            step.fail("Application 'gitops-admin' non trovata in openshift-gitops")
        else:
            source = application.get("spec", {}).get("source", {})
            destination = application.get("spec", {}).get("destination", {})
            if source.get("repoURL") != EXPECTED_REPO_URL:
                step.add_error(
                    f"repoURL atteso {EXPECTED_REPO_URL} (trovato: {source.get('repoURL')})"
                )
            if source.get("path") != ".":
                step.add_error(f"path atteso '.' (trovato: {source.get('path')})")
            if destination.get("server") != "https://kubernetes.default.svc":
                step.add_error(
                    "destination.server atteso https://kubernetes.default.svc "
                    f"(trovato: {destination.get('server')})"
                )

    with GradingStep("L'applicazione gitops-admin e' sincronizzata e healthy") as step:
        if application is None:
            step.fail()
        else:
            status = application.get("status", {})
            sync_status = status.get("sync", {}).get("status")
            health_status = status.get("health", {}).get("status")
            if sync_status != "Synced":
                step.add_error(f"Sync status: {sync_status} (atteso Synced)")
            if health_status != "Healthy":
                step.add_error(f"Health status: {health_status} (atteso Healthy)")

    console = oc_get_json("consoles.operator.openshift.io", "cluster")

    with GradingStep("La console e' personalizzata con customProductName Production") as step:
        if console is None:
            step.fail("Risorsa 'consoles.operator.openshift.io/cluster' non trovata")
        else:
            product_name = (
                console.get("spec", {}).get("customization", {}).get("customProductName")
            )
            if product_name != EXPECTED_PRODUCT_NAME:
                step.add_error(
                    f"customProductName atteso '{EXPECTED_PRODUCT_NAME}' "
                    f"(trovato: {product_name})"
                )


if __name__ == "__main__":
    main()
