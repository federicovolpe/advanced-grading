#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato backup-oadp (DO380, Cap. 2.4:
"Deploy and Configure the OADP Operator"), sprovvisto di `lab grade`
ufficiale (la classe BackupOadp nel pacchetto do380 implementa solo
start()/finish(), non grade()).

Specifica ricavata dal testo integrale della guida (Cap. 2.4, passi 2-11):
- Operatore OADP installato nel namespace openshift-adp.
- ObjectBucketClaim "backup" (storageClassName openshift-storage.noobaa.io)
  nel namespace openshift-adp, in fase Bound — vedi
  materials/solutions/backup-oadp/obc-backup.yaml.
- Secret "cloud-credentials" nel namespace openshift-adp con le credenziali
  del bucket.
- DataProtectionApplication "oadp-backup" nel namespace openshift-adp, con
  nodeAgent abilitato e i plugin velero aws/openshift/csi.
- Deployment "velero" e DaemonSet "node-agent" pronti in openshift-adp.
- Almeno una BackupStorageLocation in fase "Available" (il nome esatto,
  es. "oadp-backup-1", è generato dall'operatore a partire dal nome della
  DPA — non è fisso, quindi si cerca per prefisso/esistenza, non per nome).

NON si grada l'oggetto Backup "backup-production" (materials/solutions/
backup-oadp/backup.yaml): il passo 12 della guida lo cancella esplicitamente
a fine esercizio con `velero delete backup`, quindi la sua assenza dopo il
completamento corretto dell'esercizio è lo stato atteso, non un fallimento.

Il progetto "backup-oadp" non esiste: questa guided exercise non crea un
proprio namespace (vedi backup-oadp.py ufficiale), lavora direttamente su
openshift-adp. Per questo il default del primo argomento CLI è
"openshift-adp" invece del nome esercizio.

Uso: backup-oadp.py [namespace-oadp]   (default: openshift-adp)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "backup-oadp"
DPA_NAME = "oadp-backup"
OBC_NAME = "backup"
OBC_STORAGECLASS = "openshift-storage.noobaa.io"
SECRET_NAME = "cloud-credentials"


def main():
    namespace = sys.argv[1] if len(sys.argv) > 1 else "openshift-adp"
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (namespace OADP: {namespace})")

    with GradingStep(f"Il progetto {namespace} esiste") as step:
        if not project_exists(namespace):
            step.fail(f"Progetto '{namespace}' non trovato")

    with GradingStep("L'operatore OADP è installato") as step:
        csvs = oc_get_json("csv", "-n", namespace)
        if csvs is None or not csvs.get("items"):
            step.fail(f"Nessun ClusterServiceVersion trovato in {namespace}")
        else:
            oadp_csv = next(
                (c for c in csvs["items"] if "oadp" in c["metadata"]["name"].lower()),
                None,
            )
            if oadp_csv is None:
                step.add_error("Nessun CSV dell'operatore OADP installato")
            elif oadp_csv.get("status", {}).get("phase") != "Succeeded":
                step.add_error(
                    "Il CSV dell'operatore OADP non è nella fase Succeeded "
                    f"(trovata: {oadp_csv.get('status', {}).get('phase')})"
                )

    with GradingStep(f"Il DataProtectionApplication '{DPA_NAME}' è configurato") as step:
        dpa = oc_get_json("dataprotectionapplication", DPA_NAME, "-n", namespace)
        if dpa is None:
            step.fail(f"DataProtectionApplication '{DPA_NAME}' non trovata")
        else:
            plugins = (
                dpa.get("spec", {})
                .get("configuration", {})
                .get("velero", {})
                .get("defaultPlugins", [])
            )
            for expected in ("aws", "openshift", "csi"):
                if expected not in plugins:
                    step.add_error(f"Plugin velero '{expected}' mancante in defaultPlugins")
            node_agent_enabled = (
                dpa.get("spec", {})
                .get("configuration", {})
                .get("nodeAgent", {})
                .get("enable")
            )
            if node_agent_enabled is not True:
                step.add_error("nodeAgent.enable non è impostato a true")

    with GradingStep("Il deployment velero e il daemonset node-agent sono pronti") as step:
        velero = oc_get_json("deployment", "velero", "-n", namespace)
        if velero is None:
            step.add_error("Deployment 'velero' non trovato")
        elif velero.get("status", {}).get("readyReplicas", 0) < 1:
            step.add_error("Il deployment 'velero' non ha repliche pronte")

        node_agent = oc_get_json("daemonset", "node-agent", "-n", namespace)
        if node_agent is None:
            step.add_error("DaemonSet 'node-agent' non trovato")
        elif node_agent.get("status", {}).get("numberReady", 0) < 1:
            step.add_error("Il daemonset 'node-agent' non ha pod pronti")

    with GradingStep("Esiste una BackupStorageLocation disponibile") as step:
        bsls = oc_get_json("backupstoragelocation", "-n", namespace)
        if bsls is None or not bsls.get("items"):
            step.fail(f"Nessuna BackupStorageLocation trovata in {namespace}")
        else:
            available = [
                b for b in bsls["items"]
                if b.get("status", {}).get("phase") == "Available"
            ]
            if not available:
                phases = [b.get("status", {}).get("phase") for b in bsls["items"]]
                step.add_error(
                    f"Nessuna BackupStorageLocation in fase Available (trovate: {phases})"
                )

    with GradingStep(f"L'ObjectBucketClaim '{OBC_NAME}' è configurata correttamente") as step:
        obc = oc_get_json("objectbucketclaim", OBC_NAME, "-n", namespace)
        if obc is None:
            step.fail(f"ObjectBucketClaim '{OBC_NAME}' non trovata")
        else:
            if obc.get("spec", {}).get("storageClassName") != OBC_STORAGECLASS:
                step.add_error(
                    f"storageClassName atteso '{OBC_STORAGECLASS}' "
                    f"(trovato: {obc.get('spec', {}).get('storageClassName')})"
                )
            if obc.get("status", {}).get("phase") != "Bound":
                step.add_error(
                    f"L'OBC non è in fase Bound (trovata: {obc.get('status', {}).get('phase')})"
                )

    with GradingStep(f"Il secret '{SECRET_NAME}' esiste") as step:
        secret = oc_get_json("secret", SECRET_NAME, "-n", namespace)
        if secret is None:
            step.fail(f"Secret '{SECRET_NAME}' non trovato in {namespace}")


if __name__ == "__main__":
    main()
