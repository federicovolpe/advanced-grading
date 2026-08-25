"""
Cap. 5 — Manage Storage for Application Configuration and Data
Gestisci storage non condiviso per repliche con un StatefulSet
(sezione 5.7 del manuale, "Manage Non-shared Storage with Stateful Sets").
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, oc_get_json, parse_quantity, ensure_project, run_cli

CHAPTER = "Cap. 5 — Manage Storage for Application Configuration and Data"
TITLE = "Crea uno StatefulSet con una PVC per replica"
PROJECT = "training-storage-statefulset"
IMAGE = "registry.access.redhat.com/ubi9/httpd-24:latest"
REPLICAS = 2
CLAIM_SIZE_GI = 1

TASK = f"""\
Nel progetto "{PROJECT}", crea uno StatefulSet chiamato "web" con
{REPLICAS} repliche usando l'immagine {IMAGE}. Ogni pod deve avere una
PersistentVolumeClaim individuale (non condivisa fra le repliche) di
{CLAIM_SIZE_GI}Gi, montata su /opt/app-root/src, generata da un
volumeClaimTemplate chiamato "web-storage".

A differenza di un Deployment, un volumeClaimTemplate crea una PVC
distinta per ciascuna replica (es. "web-storage-web-0",
"web-storage-web-1", ...), non una sola condivisa.

Salva questo contenuto in statefulset.yaml:

  apiVersion: apps/v1
  kind: StatefulSet
  metadata:
    name: web
  spec:
    serviceName: web
    replicas: {REPLICAS}
    selector:
      matchLabels:
        app: web-sts
    template:
      metadata:
        labels:
          app: web-sts
      spec:
        containers:
          - name: httpd-24
            image: {IMAGE}
            volumeMounts:
              - name: web-storage
                mountPath: /opt/app-root/src
    volumeClaimTemplates:
      - metadata:
          name: web-storage
        spec:
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: {CLAIM_SIZE_GI}Gi

Poi applicalo (1 comando):
  oc apply -f statefulset.yaml -n {PROJECT}
"""


def setup():
    ensure_project(PROJECT)


def grade():
    sts = oc_get_json("statefulset", "web", "-n", PROJECT)

    with GradingStep("Lo StatefulSet web esiste") as step:
        if not sts:
            step.fail("StatefulSet 'web' non trovato")

    with GradingStep(f"Tutte le {REPLICAS} repliche sono pronte") as step:
        if not sts:
            step.fail("StatefulSet 'web' non trovato")
        else:
            ready = sts.get("status", {}).get("readyReplicas", 0)
            if ready != REPLICAS:
                step.add_error(f"status.readyReplicas = {ready}, attese {REPLICAS}")

    with GradingStep(f"Ogni replica ha una PVC individuale di almeno {CLAIM_SIZE_GI}Gi") as step:
        pvcs = oc_get_json("pvc", "-n", PROJECT)
        items = (pvcs or {}).get("items", [])
        sts_pvcs = [p for p in items if p["metadata"]["name"].startswith("web-storage-web-")]
        if len(sts_pvcs) < REPLICAS:
            step.add_error(f"Trovate {len(sts_pvcs)} PVC con prefisso 'web-storage-web-', attese almeno {REPLICAS}")
        else:
            for pvc in sts_pvcs:
                name = pvc["metadata"]["name"]
                phase = pvc.get("status", {}).get("phase")
                requested = pvc.get("spec", {}).get("resources", {}).get("requests", {}).get("storage")
                if phase != "Bound":
                    step.add_error(f"{name}: status.phase = {phase!r}, attesa 'Bound'")
                if (parse_quantity(requested) or 0) < parse_quantity(f"{CLAIM_SIZE_GI}Gi"):
                    step.add_error(f"{name}: richiede {requested!r}, attesi almeno {CLAIM_SIZE_GI}Gi")


if __name__ == "__main__":
    run_cli(setup, grade)
