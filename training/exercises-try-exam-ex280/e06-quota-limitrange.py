"""
Try-exam EX280, 6 — ResourceQuota e LimitRange
(tema: "CONFIGURE QUOTAS FOR PROJECT").

Il tema non dice se "memoria/CPU consumata da tutti i container" vada su
requests o limits: si accettano entrambe le forme (memory/requests.memory/
limits.memory, idem cpu). "1G" si accetta sia come 1G sia come 1Gi, che e'
come lo scrive la maggior parte delle soluzioni circolanti.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ex280_common import (
    CHAPTER, SETUP_TIMEOUT, GradingStep, oc_get_json, track_lock,
    require_cluster_admin, reset_owned_project, delete_owned_project,
    parse_quantity, run_cli,
)

SLUG = "e06"
PROJECT = "practice3"
QUOTA = "my-quota"
LIMITS = "my-limits"

TITLE = "6) ResourceQuota my-quota e LimitRange my-limits"

TASK = f"""\
Nel progetto {PROJECT}:

  Crea una ResourceQuota chiamata {QUOTA}:
    - la memoria consumata da tutti i container non supera 1G
    - la CPU di tutti i container non supera 2 core
    - al massimo 3 replication controller
    - al massimo 3 pod
    - al massimo 6 service

  Crea un LimitRange chiamato {LIMITS}:
    - memoria di un singolo pod tra 100Mi e 300Mi
    - CPU di un singolo pod tra 10m e 500m
    - CPU di un singolo container tra 10m e 500m, con request di
      default 100m
    - memoria di un singolo container tra 100Mi e 300Mi, con request
      di default 100Mi
"""

SOLUTION = f"""\
oc project {PROJECT}

oc create quota {QUOTA} \\
    --hard=memory=1G,cpu=2,replicationcontrollers=3,pods=3,services=6

cat > /tmp/limits.yaml <<'EOF'
apiVersion: v1
kind: LimitRange
metadata:
  name: {LIMITS}
spec:
  limits:
  - type: Pod
    min:
      cpu: 10m
      memory: 100Mi
    max:
      cpu: 500m
      memory: 300Mi
  - type: Container
    min:
      cpu: 10m
      memory: 100Mi
    max:
      cpu: 500m
      memory: 300Mi
    defaultRequest:
      cpu: 100m
      memory: 100Mi
EOF
oc apply -f /tmp/limits.yaml

oc describe quota {QUOTA}
oc describe limitrange {LIMITS}
"""

MI = 2**20


def _hard_value(hard, resource):
    for key in (resource, f"requests.{resource}", f"limits.{resource}"):
        if key in hard:
            return key, parse_quantity(hard[key])
    return None, None


def setup():
    require_cluster_admin()
    with track_lock():
        reset_owned_project(PROJECT, SLUG)


def _check_range(step, item, resource, lo, hi, label):
    lo_v = parse_quantity((item.get("min") or {}).get(resource))
    hi_v = parse_quantity((item.get("max") or {}).get(resource))
    if lo_v is None or abs(lo_v - lo) > 1e-6 * max(lo, 1):
        step.add_error(f"{label}: min.{resource} = {(item.get('min') or {}).get(resource)!r}")
    if hi_v is None or abs(hi_v - hi) > 1e-6 * max(hi, 1):
        step.add_error(f"{label}: max.{resource} = {(item.get('max') or {}).get(resource)!r}")


def grade():
    quota = oc_get_json("resourcequota", QUOTA, "-n", PROJECT)
    hard = ((quota or {}).get("spec") or {}).get("hard") or {}

    with GradingStep(f"La ResourceQuota {QUOTA} esiste") as step:
        if not quota:
            step.fail(f"ResourceQuota '{QUOTA}' non trovata in {PROJECT}")

    with GradingStep(f"{QUOTA}: memoria totale 1G, CPU totale 2 core") as step:
        key, mem = _hard_value(hard, "memory")
        if mem not in (1e9, 2**30):
            step.add_error(f"memoria: {key or 'memory'} = {hard.get(key) if key else None!r}")
        key, cpu = _hard_value(hard, "cpu")
        if cpu != 2:
            step.add_error(f"cpu: {key or 'cpu'} = {hard.get(key) if key else None!r}")

    with GradingStep(f"{QUOTA}: 3 replication controller, 3 pod, 6 service") as step:
        for key, expected in (("replicationcontrollers", 3), ("pods", 3), ("services", 6)):
            value = hard.get(key) or hard.get(f"count/{key}")
            if parse_quantity(value) != expected:
                step.add_error(f"{key} = {value!r}, atteso {expected}")

    lr = oc_get_json("limitrange", LIMITS, "-n", PROJECT)
    items = {i.get("type"): i for i in ((lr or {}).get("spec") or {}).get("limits") or []}

    with GradingStep(f"Il LimitRange {LIMITS} esiste") as step:
        if not lr:
            step.fail(f"LimitRange '{LIMITS}' non trovato in {PROJECT}")

    with GradingStep(f"{LIMITS}: per pod memoria 100Mi-300Mi, CPU 10m-500m") as step:
        pod = items.get("Pod")
        if not pod:
            step.fail("nessun limite di tipo Pod")
        else:
            _check_range(step, pod, "memory", 100 * MI, 300 * MI, "Pod")
            _check_range(step, pod, "cpu", 0.01, 0.5, "Pod")

    with GradingStep(f"{LIMITS}: per container memoria 100Mi-300Mi, CPU 10m-500m") as step:
        ctr = items.get("Container")
        if not ctr:
            step.fail("nessun limite di tipo Container")
        else:
            _check_range(step, ctr, "memory", 100 * MI, 300 * MI, "Container")
            _check_range(step, ctr, "cpu", 0.01, 0.5, "Container")

    with GradingStep(f"{LIMITS}: request di default per container 100m CPU, 100Mi memoria") as step:
        default = ((items.get("Container") or {}).get("defaultRequest")) or {}
        if abs((parse_quantity(default.get("cpu")) or 0) - 0.1) > 1e-9:
            step.add_error(f"defaultRequest.cpu = {default.get('cpu')!r}")
        if parse_quantity(default.get("memory")) != 100 * MI:
            step.add_error(f"defaultRequest.memory = {default.get('memory')!r}")


def cleanup():
    with track_lock():
        delete_owned_project(PROJECT, SLUG)


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
