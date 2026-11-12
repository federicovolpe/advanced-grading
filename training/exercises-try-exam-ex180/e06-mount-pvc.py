"""
Try-exam EX180, 6 — monta su un deployment il volume della PVC precedente.

Il tema: "monta ad un deployment un pv creato con il PVC precedente". Il
setup() crea gia' la PVC (come se l'esercizio 5 fosse stato risolto) e un
deployment senza volumi; lo studente deve agganciare QUELLA PVC (non
crearne una nuova) al deployment.

Scostamenti dal tema annotato (scelte nostre):
- la PVC qui e' da 1Gi, non da 24G: lo spazio libero dello storage del
  classroom e' ignoto e la PVC deve diventare davvero Bound perche' il pod
  parta; nome (data-pvc) e storage class sono quelli dell'esercizio 5;
- nome del deployment (data-app), immagine (httpd UBI 9), mount path (/data)
  e progetto: il tema non li dice.

Grading per risultato: la PVC montata si cerca per contenuto (qualunque
nome abbia il volume), e "disponibile" vuol dire un pod Running/Ready che ha
davvero quella PVC nella sua spec — dopo `oc set volume` il pod vecchio
(senza volume) resta disponibile finche' il nuovo non parte, quindi
status.availableReplicas da solo direbbe PASS anche con una PVC che non si
lega mai.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ex180_common import (  # noqa: F401
    CHAPTER, SETUP_TIMEOUT, STORAGE_CLASS, GradingStep, oc, oc_get_json, apply_yaml,
    reset_project, delete_project, check_project, create_httpd_deployment,
    volume_mounts, mounted_at, ready_pods, run_cli,
)

SLUG = "e06"
PROJECT = "ex180-e06"
TITLE = "6) Monta la PVC su un deployment"
APP = "data-app"
PVC = "data-pvc"
SETUP_SIZE = "1Gi"
MOUNT = "/data"

TASK = f"""\
Nel progetto {PROJECT} trovi la PersistentVolumeClaim {PVC}
(storage class {STORAGE_CLASS}) e il deployment {APP}.

Monta il volume di quella PVC nel deployment {APP}, nella directory
{MOUNT} del container. Usa la PVC esistente: non crearne un'altra.

Alla fine la PVC deve risultare Bound e il deployment disponibile.
"""

SOLUTION = f"""\
oc project {PROJECT}
oc get pvc {PVC}                     # Pending: aspetta un pod che la usi

oc set volume deployment/{APP} --add --name=data \\
    --type=persistentVolumeClaim --claim-name={PVC} --mount-path={MOUNT}

oc get pvc {PVC}                     # ora Bound
oc get pods
oc exec deployment/{APP} -- df -h {MOUNT}
"""

PVC_YAML = f"""\
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {PVC}
spec:
  storageClassName: {STORAGE_CLASS}
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: {SETUP_SIZE}
"""


def setup():
    reset_project(PROJECT)
    apply_yaml(PVC_YAML, namespace=PROJECT)
    create_httpd_deployment(APP, PROJECT)


def _pod_has_pvc(pod):
    return mounted_at(pod, "persistentVolumeClaim", PVC, MOUNT) is not None


def grade():
    check_project(PROJECT)
    dep = oc_get_json("deployment", APP, "-n", PROJECT)

    with GradingStep(f"Il deployment {APP} monta la PVC {PVC} su {MOUNT}") as step:
        if not dep:
            step.fail(f"Deployment '{APP}' non trovato in {PROJECT}")
        elif not mounted_at(dep, "persistentVolumeClaim", PVC, MOUNT):
            found = volume_mounts(dep, "persistentVolumeClaim", PVC)
            others = [v.get("persistentVolumeClaim", {}).get("claimName")
                      for v in (((dep.get("spec") or {}).get("template") or {}).get("spec") or {}).get("volumes") or []
                      if v.get("persistentVolumeClaim")]
            if found:
                step.add_error(f"{PVC} montata su {', '.join(p for _c, p, _s in found)}, non su {MOUNT}")
            elif others:
                step.add_error(f"il deployment usa un'altra PVC ({', '.join(others)}), non {PVC}")
            else:
                step.add_error("nessuna PVC montata nel deployment")

    with GradingStep(f"La PVC {PVC} e' Bound") as step:
        pvc = oc_get_json("pvc", PVC, "-n", PROJECT)
        phase = ((pvc or {}).get("status") or {}).get("phase")
        if not pvc:
            step.fail(f"PVC '{PVC}' non trovata (e' stata cancellata? ricomincia l'esercizio)")
        elif phase != "Bound":
            step.add_error(f"status.phase = {phase!r} (nessun pod la usa ancora?)")

    with GradingStep(f"Il deployment {APP} e' disponibile con la PVC montata") as step:
        if not dep:
            step.fail("Deployment non trovato")
        elif not ready_pods(dep, PROJECT, _pod_has_pvc):
            step.fail(f"nessun pod Running e Ready con {PVC} su {MOUNT} "
                      "(oc get pods, oc describe pod, oc get events)")


def cleanup():
    delete_project(PROJECT)


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
