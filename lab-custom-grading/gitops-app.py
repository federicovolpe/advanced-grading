#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato gitops-app (DO380, Cap. 4.6
"Manage Applications with OpenShift GitOps"), sprovvisto di `lab grade`
ufficiale.

Specifica ricavata da:
- materials/solutions/gitops-app/ (argocd-instance.yaml, etherpad-admin/
  rbac.yaml, secret.yaml, hooks/{presync,postsync}.yaml)
- testo della guida ufficiale, Cap. 4.6, punti 1-8 (pagine 312-320), che
  fornisce anche i valori non presenti nei materiali (nomi delle due
  Application Argo CD, URL dei repository, nuovo titolo dell'app Etherpad)

Lo studente crea una seconda istanza Argo CD "argocd" nel progetto
"gitops-app" (distinta da quella di default in openshift-gitops, gradata
separatamente da gitops-admin.py), il progetto "etherpad-devs" gestito da
questa istanza, due Application ("rbac-rule" per l'RBAC e "etherpad-app"
per il deployment), e due hook di sincronizzazione (backup-mariadb PreSync,
test-etherpad PostSync) che modificano anche il titolo dell'app Etherpad.

Non gradato: il contenuto del backup creato dall'hook PreSync nella PVC
"database-backup" (richiederebbe di eseguire un pod nel progetto per
leggere il filesystem, oltre lo scopo di un check verificabile con oc get).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

ARGOCD_PROJECT = "gitops-app"
APP_PROJECT = "etherpad-devs"

EXPECTED_TLS_TERMINATION = "reencrypt"
EXPECTED_RBAC_LINES = [
    "g, project-devs, role:project-devs",
    "g, project-admins, role:project-admins",
    "p, role:project-admins, applications, *, */*, allow",
]
EXPECTED_MOUNT_PATH = "/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem"

RBAC_APP_NAME = "rbac-rule"
ETHERPAD_APP_NAME = "etherpad-app"
RBAC_REPO_URL = "https://git.ocp4.example.com/project-admin/etherpad-admin.git"
ETHERPAD_REPO_URL = "https://git.ocp4.example.com/developer/etherpad-app.git"

EXPECTED_TITLE = "My test Etherpad app"


def main():
    print("🔧 Grading personalizzato per 'gitops-app'")

    argocd = oc_get_json("argocd", "argocd", "-n", ARGOCD_PROJECT)
    with GradingStep(f"L'istanza Argo CD custom esiste nel progetto {ARGOCD_PROJECT}") as step:
        if argocd is None:
            step.fail(f"ArgoCD 'argocd' non trovata nel progetto {ARGOCD_PROJECT}")
        else:
            termination = argocd.get("spec", {}).get("server", {}).get("route", {}).get(
                "tls", {}
            ).get("termination")
            if termination != EXPECTED_TLS_TERMINATION:
                step.add_error(
                    f"route.tls.termination atteso '{EXPECTED_TLS_TERMINATION}' "
                    f"(trovato: {termination})"
                )
            policy = argocd.get("spec", {}).get("rbac", {}).get("policy", "")
            for line in EXPECTED_RBAC_LINES:
                if line not in policy:
                    step.add_error(f"La policy RBAC non contiene la riga '{line}'")
            repo = argocd.get("spec", {}).get("repo", {})
            mounts = repo.get("volumeMounts") or []
            if not any(m.get("mountPath") == EXPECTED_MOUNT_PATH for m in mounts):
                step.add_error(
                    f"spec.repo.volumeMounts non monta il CA bundle su {EXPECTED_MOUNT_PATH}"
                )

    with GradingStep(f"Il progetto {APP_PROJECT} esiste ed e' gestito da questa istanza Argo CD") as step:
        if not project_exists(APP_PROJECT):
            step.fail(f"Progetto '{APP_PROJECT}' non trovato")
        else:
            ns = oc_get_json("namespace", APP_PROJECT)
            managed_by = ns.get("metadata", {}).get("labels", {}).get("argocd.argoproj.io/managed-by") if ns else None
            if managed_by != ARGOCD_PROJECT:
                step.add_error(
                    f"Label 'argocd.argoproj.io/managed-by' attesa '{ARGOCD_PROJECT}' "
                    f"(trovata: {managed_by})"
                )

    rbac_app = oc_get_json("application.argoproj.io", RBAC_APP_NAME, "-n", ARGOCD_PROJECT)
    with GradingStep(f"L'Application '{RBAC_APP_NAME}' punta al repo etherpad-admin ed e' sincronizzata") as step:
        if rbac_app is None:
            step.fail(f"Application '{RBAC_APP_NAME}' non trovata in {ARGOCD_PROJECT}")
        else:
            source = rbac_app.get("spec", {}).get("source", {})
            destination = rbac_app.get("spec", {}).get("destination", {})
            if source.get("repoURL") != RBAC_REPO_URL:
                step.add_error(f"repoURL atteso {RBAC_REPO_URL} (trovato: {source.get('repoURL')})")
            if destination.get("namespace") != APP_PROJECT:
                step.add_error(
                    f"destination.namespace atteso '{APP_PROJECT}' (trovato: {destination.get('namespace')})"
                )
            status = rbac_app.get("status", {})
            if status.get("sync", {}).get("status") != "Synced":
                step.add_error(f"Sync status: {status.get('sync', {}).get('status')} (atteso Synced)")

    rolebinding = oc_get_json("rolebinding", "developer-view", "-n", APP_PROJECT)
    with GradingStep(f"Il RoleBinding 'developer-view' concede 'view' al gruppo project-devs") as step:
        if rolebinding is None:
            step.fail(f"RoleBinding 'developer-view' non trovato nel progetto {APP_PROJECT}")
        else:
            role_ref = rolebinding.get("roleRef", {})
            subjects = rolebinding.get("subjects", [])
            if role_ref.get("name") != "view":
                step.add_error(f"roleRef.name atteso 'view' (trovato: {role_ref.get('name')})")
            if not any(s.get("kind") == "Group" and s.get("name") == "project-devs" for s in subjects):
                step.add_error("Nessun subject Group 'project-devs' trovato")

    etherpad_app = oc_get_json("application.argoproj.io", ETHERPAD_APP_NAME, "-n", ARGOCD_PROJECT)
    with GradingStep(f"L'Application '{ETHERPAD_APP_NAME}' punta al repo etherpad-app, Synced e Healthy") as step:
        if etherpad_app is None:
            step.fail(f"Application '{ETHERPAD_APP_NAME}' non trovata in {ARGOCD_PROJECT}")
        else:
            source = etherpad_app.get("spec", {}).get("source", {})
            destination = etherpad_app.get("spec", {}).get("destination", {})
            if source.get("repoURL") != ETHERPAD_REPO_URL:
                step.add_error(f"repoURL atteso {ETHERPAD_REPO_URL} (trovato: {source.get('repoURL')})")
            if destination.get("namespace") != APP_PROJECT:
                step.add_error(
                    f"destination.namespace atteso '{APP_PROJECT}' (trovato: {destination.get('namespace')})"
                )
            status = etherpad_app.get("status", {})
            sync_status = status.get("sync", {}).get("status")
            health_status = status.get("health", {}).get("status")
            if sync_status != "Synced":
                step.add_error(f"Sync status: {sync_status} (atteso Synced)")
            if health_status != "Healthy":
                step.add_error(f"Health status: {health_status} (atteso Healthy)")

    deployment = oc_get_json("deployment", "etherpad", "-n", APP_PROJECT)
    with GradingStep(f"Il deployment 'etherpad' e' pronto con il titolo aggiornato") as step:
        if deployment is None:
            step.fail(f"Deployment 'etherpad' non trovato nel progetto {APP_PROJECT}")
        else:
            status = deployment.get("status", {})
            if status.get("readyReplicas", 0) < 1:
                step.add_error("Il deployment 'etherpad' non ha repliche pronte")
            containers = deployment.get("spec", {}).get("template", {}).get("spec", {}).get(
                "containers", []
            )
            title_env = next(
                (
                    e.get("value")
                    for c in containers
                    for e in c.get("env", [])
                    if e.get("name") == "TITLE"
                ),
                None,
            )
            if title_env != EXPECTED_TITLE:
                step.add_error(
                    f"Variabile d'ambiente TITLE attesa '{EXPECTED_TITLE}' (trovata: {title_env!r})"
                )

    with GradingStep(f"Il secret 'mariadb' esiste nel progetto {APP_PROJECT}") as step:
        secret = oc_get_json("secret", "mariadb", "-n", APP_PROJECT)
        if secret is None:
            step.fail(f"Secret 'mariadb' non trovato nel progetto {APP_PROJECT}")

    with GradingStep(f"La PVC 'database-backup' esiste nel progetto {APP_PROJECT}") as step:
        pvc = oc_get_json("pvc", "database-backup", "-n", APP_PROJECT)
        if pvc is None:
            step.fail(f"PVC 'database-backup' non trovata nel progetto {APP_PROJECT}")


if __name__ == "__main__":
    main()
