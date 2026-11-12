"""
Try-exam EX180, 5 — PVC da 24G con una storage class specifica.

Scostamenti dal tema annotato (scelte nostre): nome della PVC (data-pvc),
progetto e storage class (lvms-vg1, quella del classroom DO180 gia' usata
dall'esercizio di training c5-05: il tema dice solo "una classe specifica").

"24G" nel tema: in Kubernetes `24G` e' una quantita' DECIMALE (24·10^9 byte)
e `24Gi` binaria (24·2^30 byte, ~7% in piu'). Non sappiamo quale delle due
intendesse l'esame, quindi si accettano entrambe (confronto numerico con
parse_quantity, non sulla stringa).

Cosa NON si grada, e perche':
- lo stato Bound: con volumeBindingMode WaitForFirstConsumer (quello di LVMS)
  la PVC resta Pending finche' nessun pod la usa, ed e' giusto cosi'; e lo
  spazio libero del volume group del classroom per 24G e' ignoto;
- le access mode: il tema non le dice (ReadWriteOnce e' l'unica sensata con
  LVMS, ma non e' un requisito del compito).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ex180_common import (  # noqa: F401
    CHAPTER, SETUP_TIMEOUT, STORAGE_CLASS, GradingStep, oc, oc_get_json, parse_quantity,
    reset_project, delete_project, check_project, run_cli,
)

SLUG = "e05"
PROJECT = "ex180-e05"
TITLE = "5) PVC da 24G con una storage class specifica"
PVC = "data-pvc"
SIZE = "24G"
ACCEPTED = {parse_quantity("24G"): "24G", parse_quantity("24Gi"): "24Gi"}

TASK = f"""\
Nel progetto {PROJECT} crea una PersistentVolumeClaim di nome {PVC}
che richieda {SIZE} di spazio usando la storage class {STORAGE_CLASS}.

La PVC non deve per forza risultare Bound: con questa storage class resta
Pending finche' nessun pod la usa.
"""

SOLUTION = f"""\
oc project {PROJECT}
oc get storageclass                  # nomi e volumeBindingMode delle classi

cat <<'EOF' | oc apply -f -
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
      storage: {SIZE}
EOF

oc get pvc {PVC}                     # Pending (WaitForFirstConsumer) va bene
"""


def setup():
    reset_project(PROJECT)


def grade():
    check_project(PROJECT)
    pvc = oc_get_json("pvc", PVC, "-n", PROJECT)
    spec = (pvc or {}).get("spec") or {}

    with GradingStep(f"La PVC {PVC} esiste") as step:
        if not pvc:
            others = [p["metadata"]["name"] for p in (oc_get_json("pvc", "-n", PROJECT) or {}).get("items", [])]
            step.fail(f"PVC '{PVC}' non trovata in {PROJECT}"
                      + (f" (ci sono: {', '.join(others)})" if others else ""))

    with GradingStep(f"La PVC usa la storage class {STORAGE_CLASS}") as step:
        if not pvc:
            step.fail("PVC non trovata")
        elif spec.get("storageClassName") != STORAGE_CLASS:
            step.add_error(f"storageClassName = {spec.get('storageClassName')!r}")

    with GradingStep(f"La PVC richiede {SIZE} (si accetta anche 24Gi)") as step:
        requested = ((spec.get("resources") or {}).get("requests") or {}).get("storage")
        value = parse_quantity(requested)
        if not pvc:
            step.fail("PVC non trovata")
        elif not any(value is not None and abs(value - v) < 1 for v in ACCEPTED):
            step.add_error(f"resources.requests.storage = {requested!r}")

    with GradingStep("La PVC non e' in errore (Pending o Bound)") as step:
        phase = ((pvc or {}).get("status") or {}).get("phase")
        if not pvc:
            step.fail("PVC non trovata")
        elif phase not in ("Pending", "Bound"):
            step.add_error(f"status.phase = {phase!r}")


def cleanup():
    delete_project(PROJECT)


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
