#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato observability-enable (DO432, Cap.
4.2 "Enable the RHACM Observability Stack"), sprovvisto di `lab grade`
ufficiale (la classe ObservabilityEnable nel pacchetto do0014l implementa
solo start()/finish(), non grade()).

Specifica ricavata incrociando due fonti:
- materials/labs/observability-enable/{obc.yaml,secret.yaml,mcobs.yaml} vs
  materials/solutions/observability-enable/{mcobs.yaml,obc.yaml} (manca
  solutions/secret.yaml, i suoi valori sono comunque dinamici per-sistema).
- Il testo della guida studente (DO432-RHACM2.13-en-2, Cap. 4.2, pag.
  250-255), che conferma gli stessi valori e aggiunge il passo 9 (label
  observability=disabled sul managed cluster), assente nei materiali.

Tutte le risorse vivono sull'HUB cluster (namespace
open-cluster-management-observability), tranne il controllo finale del
punto 9 che riguarda anche il managed cluster: uso oc_get_json_hub/
oc_get_json_managed (vedi _common.py) invece della sessione oc corrente,
perché lo studente alterna login fra i due cluster durante l'esercizio e un
monitor che gira ogni 30s potrebbe leggere lo stato mentre e' loggato
sull'altro cluster.

Il bucket S3 (nome/endpoint/credenziali in thanos-object-storage) e'
generato dinamicamente da ODF per ogni installazione (vedi guida, "The
BUCKET_NAME in the preceding output is different on your system"): non
gradiamo valori fissi per questi campi, solo che il secret esista con la
struttura giusta e referenzi davvero il bucket creato dall'OBC.
"""

import sys
import os
import base64
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json_hub, oc_get_json_managed

LAB_NAME = "observability-enable"
NAMESPACE = "open-cluster-management-observability"
MANAGED_CLUSTER_NAME = "managed-cluster"


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    with GradingStep(f"Il namespace {NAMESPACE} esiste sull'hub cluster") as step:
        ns = oc_get_json_hub("namespace", NAMESPACE)
        if not ns:
            step.fail(f"Namespace '{NAMESPACE}' non trovato sull'hub cluster")

    with GradingStep("Il secret multiclusterhub-operator-pull-secret esiste") as step:
        secret = oc_get_json_hub("secret", "multiclusterhub-operator-pull-secret", "-n", NAMESPACE)
        if not secret:
            step.fail("Secret 'multiclusterhub-operator-pull-secret' non trovato")
        elif secret.get("type") != "kubernetes.io/dockerconfigjson":
            step.add_error(f"type e' '{secret.get('type')}', atteso 'kubernetes.io/dockerconfigjson'")

    obc = None
    with GradingStep("L'ObjectBucketClaim thanos-obc e' Bound") as step:
        obc = oc_get_json_hub("objectbucketclaim", "thanos-obc", "-n", NAMESPACE)
        if not obc:
            step.fail("ObjectBucketClaim 'thanos-obc' non trovato")
        else:
            if obc.get("spec", {}).get("storageClassName") != "openshift-storage.noobaa.io":
                step.add_error(
                    f"storageClassName e' '{obc.get('spec', {}).get('storageClassName')}', "
                    "atteso 'openshift-storage.noobaa.io'"
                )
            if obc.get("status", {}).get("phase") != "Bound":
                step.add_error(f"phase e' '{obc.get('status', {}).get('phase')}', attesa 'Bound'")

    with GradingStep("Il secret thanos-object-storage e' configurato correttamente") as step:
        secret = oc_get_json_hub("secret", "thanos-object-storage", "-n", NAMESPACE)
        if not secret:
            step.fail("Secret 'thanos-object-storage' non trovato")
        elif secret.get("type") != "Opaque":
            step.add_error(f"type e' '{secret.get('type')}', atteso 'Opaque'")
        else:
            raw = secret.get("data", {}).get("thanos.yaml")
            if not raw:
                step.add_error("manca la chiave 'thanos.yaml' nel secret")
            else:
                try:
                    thanos_cfg = yaml.safe_load(base64.b64decode(raw))
                except Exception:
                    thanos_cfg = None
                if not thanos_cfg or thanos_cfg.get("type") != "s3":
                    step.add_error("il contenuto di thanos.yaml non e' una config S3 valida")
                else:
                    cfg = thanos_cfg.get("config", {})
                    if not cfg.get("bucket") or not cfg.get("endpoint"):
                        step.add_error("bucket/endpoint mancanti nella config S3")
                    if not cfg.get("access_key") or not cfg.get("secret_key"):
                        step.add_error("access_key/secret_key mancanti nella config S3")
                    # Il bucket referenziato deve essere davvero quello creato dall'OBC.
                    obc_configmap = oc_get_json_hub("configmap", "thanos-obc", "-n", NAMESPACE)
                    expected_bucket = (obc_configmap or {}).get("data", {}).get("BUCKET_NAME")
                    if expected_bucket and cfg.get("bucket") != expected_bucket:
                        step.add_error(
                            f"bucket referenziato ('{cfg.get('bucket')}') non corrisponde "
                            f"a quello creato dall'OBC ('{expected_bucket}')"
                        )

    with GradingStep("La MultiClusterObservability 'observability' e' configurata correttamente") as step:
        mcobs = oc_get_json_hub("multiclusterobservability", "observability")
        if not mcobs:
            step.fail("MultiClusterObservability 'observability' non trovata")
        else:
            spec = mcobs.get("spec", {})
            if spec.get("observabilityAddonSpec", {}).get("enableMetrics") is not True:
                step.add_error("observabilityAddonSpec.enableMetrics non e' 'true'")
            storage = spec.get("storageConfig", {})
            metric_storage = storage.get("metricObjectStorage", {})
            if metric_storage.get("key") != "thanos.yaml":
                step.add_error(f"metricObjectStorage.key e' '{metric_storage.get('key')}', atteso 'thanos.yaml'")
            if metric_storage.get("name") != "thanos-object-storage":
                step.add_error(
                    f"metricObjectStorage.name e' '{metric_storage.get('name')}', atteso 'thanos-object-storage'"
                )
            if storage.get("storageClass") != "nfs-storage":
                step.add_error(f"storageClass e' '{storage.get('storageClass')}', atteso 'nfs-storage'")
            for size_field in (
                "alertmanagerStorageSize", "compactStorageSize",
                "receiveStorageSize", "ruleStorageSize", "storeStorageSize",
            ):
                if storage.get(size_field) != "1Gi":
                    step.add_error(f"{size_field} e' '{storage.get(size_field)}', atteso '1Gi'")

    with GradingStep("Il deployment multicluster-observability-operator e' pronto") as step:
        deploy = oc_get_json_hub(
            "deployment", "multicluster-observability-operator", "-n", "open-cluster-management"
        )
        if not deploy:
            step.fail("Deployment 'multicluster-observability-operator' non trovato")
        elif not deploy.get("status", {}).get("readyReplicas"):
            step.add_error("il deployment non ha replica pronte")

    with GradingStep(f"Il managed cluster '{MANAGED_CLUSTER_NAME}' ha la label observability=disabled") as step:
        mc = oc_get_json_hub("managedcluster", MANAGED_CLUSTER_NAME)
        if not mc:
            step.fail(f"ManagedCluster '{MANAGED_CLUSTER_NAME}' non trovato")
        elif mc.get("metadata", {}).get("labels", {}).get("observability") != "disabled":
            step.fail(f"Label 'observability=disabled' assente su '{MANAGED_CLUSTER_NAME}'")


if __name__ == "__main__":
    main()
