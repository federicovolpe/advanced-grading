"""
Grading personalizzato per 'workbench-connections' (AI0015L - Use
Connections for Data Integrations).

Da testo guida studente: lo studente crea 3 connessioni (S3, OCI, URI) con
valori esatti dalla dashboard RHOAI. Una "connessione" RHOAI e' un Secret
OpenShift con label/annotazioni specifiche (schema confermato in
rht_labs_rhoai/data.py - create_data_connection - che replica esattamente
il formato che la dashboard genera per ciascun tipo):

- S3 ('minio'): annotazione opendatahub.io/connection-type=s3, stringData
  con bucket/endpoint/regione.
- OCI ('quay-registry'): annotazione opendatahub.io/connection-type-ref=
  oci-v1, tipo kubernetes.io/dockerconfigjson, dato OCI_HOST in base64.
- URI ('huggingface'): annotazione opendatahub.io/connection-type=uri, dato
  URI in base64.

Non verificato dal vivo l'aggancio delle 3 connessioni al workbench
'workbench-connections-wb' (step 6 della guida): il meccanismo esatto con
cui la dashboard collega una Connection a un Notebook non e' stato
confermato su cluster reale, quindi si gradano solo le 3 connessioni.
"""
import sys
import os
import base64

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "workbench-connections"


def _decode(secret, key):
    data = secret.get("data", {}) or {}
    if key not in data:
        return None
    try:
        return base64.b64decode(data[key]).decode()
    except Exception:
        return None


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep("La connessione S3 'minio' e' configurata correttamente") as step:
        secret = oc_get_json("secret", "minio", "-n", project)
        if not secret:
            step.fail("Secret 'minio' non trovato")
        else:
            data = secret.get("data", {}) or {}
            stringdata = secret.get("stringData", {}) or {}

            def field(key):
                if key in data:
                    return _decode(secret, key)
                return stringdata.get(key)

            if secret.get("metadata", {}).get("annotations", {}).get(
                "opendatahub.io/connection-type"
            ) != "s3":
                step.add_error("Manca l'annotazione opendatahub.io/connection-type=s3")
            if field("AWS_S3_BUCKET") != "workbench-connections-bucket":
                step.add_error(
                    f"AWS_S3_BUCKET e' '{field('AWS_S3_BUCKET')}', atteso "
                    "'workbench-connections-bucket'"
                )
            endpoint = field("AWS_S3_ENDPOINT") or ""
            if "minio-api-minio.apps.lab.example.com" not in endpoint:
                step.add_error(f"AWS_S3_ENDPOINT non punta all'endpoint MinIO atteso ({endpoint})")

    with GradingStep("La connessione OCI 'quay-registry' e' configurata correttamente") as step:
        secret = oc_get_json("secret", "quay-registry", "-n", project)
        if not secret:
            step.fail("Secret 'quay-registry' non trovato")
        else:
            if secret.get("type") != "kubernetes.io/dockerconfigjson":
                step.add_error(f"Tipo di secret '{secret.get('type')}', atteso kubernetes.io/dockerconfigjson")
            host = _decode(secret, "OCI_HOST")
            if host != "quay.io":
                step.add_error(f"OCI_HOST e' '{host}', atteso 'quay.io'")

    with GradingStep("La connessione URI 'huggingface' e' configurata correttamente") as step:
        secret = oc_get_json("secret", "huggingface", "-n", project)
        if not secret:
            step.fail("Secret 'huggingface' non trovato")
        else:
            uri = _decode(secret, "URI")
            expected = "hdfs://namenode.example.com:9000/data/dataset.parquet"
            if uri != expected:
                step.add_error(f"URI e' '{uri}', atteso '{expected}'")


if __name__ == "__main__":
    main()
