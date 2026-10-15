"""
Try-exam EX280, 9 — service account con SCC anyuid, scale e autoscaling
(ultima parte del tema: gitlab in practice1 — "prectice1" negli appunti).

L'immagine gitlab vera non e' nel registry del classroom: il "gitlab" qui
e' httpd con securityContext.runAsUser: 0, che come gitlab non puo' girare
con la SCC restricted-v2 di default (il ReplicaSet non riesce a creare i
pod: "unable to validate against any security context constraint") e
riparte solo quando il service account del deployment puo' usare anyuid.

Il punto 3 manca negli appunti (si passa da 2 a 4). Lo scale a 5 e l'HPA
si pestano i piedi: con l'HPA attivo e CPU bassa, dopo qualche minuto le
repliche scendono a 3. Per questo "scalato a 5" e' un check "gia' visto"
(ever_seen): basta che sia stato vero in un poll precedente.
"""
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ex280_common import (
    CHAPTER, SETUP_TIMEOUT, IMG_HTTPD, GradingStep, oc, oc_get_json, track_lock,
    require_cluster_admin, reset_owned_project, delete_owned_project,
    can_i, ever_seen, reset_seen, run_cli,
)

SLUG = "e09"
PROJECT = "practice1"
APP = "gitlab"
SA = "gitlab-sa"
MIN_REPLICAS, MAX_REPLICAS, CPU_PERCENT = 3, 10, 60

TITLE = "9) Service account con anyuid, scale e autoscaling"

TASK = f"""\
Nel progetto {PROJECT} c'e' l'applicazione {APP}, che non riesce a
partire.

  1. Crea un service account {SA} nel progetto {PROJECT}. Questo
     service account deve poter eseguire applicazioni con qualunque
     user id.
  2. L'applicazione {APP} deve usare il service account {SA}.
  3. Scala l'applicazione {APP} a 5 repliche.
  4. Configura l'autoscaling dell'applicazione {APP}:
       - repliche minime: {MIN_REPLICAS}
       - repliche massime: {MAX_REPLICAS}
       - soglia di utilizzo CPU: {CPU_PERCENT}%
"""

SOLUTION = f"""\
oc project {PROJECT}
oc get events --sort-by=.lastTimestamp      # "unable to validate against any security context constraint"

oc create serviceaccount {SA}
oc adm policy add-scc-to-user anyuid -z {SA}
oc set serviceaccount deployment/{APP} {SA}

oc get pods                                  # ora partono
oc get pod <pod> -o jsonpath='{{.metadata.annotations.openshift\\.io/scc}}'   # anyuid

oc scale deployment/{APP} --replicas 5
oc autoscale deployment/{APP} --min {MIN_REPLICAS} --max {MAX_REPLICAS} --cpu-percent {CPU_PERCENT}
oc get hpa
"""


def setup():
    require_cluster_admin()
    with track_lock():
        reset_seen(SLUG)
        reset_owned_project(PROJECT, SLUG)
        oc("create", "deployment", APP, f"--image={IMG_HTTPD}", "-n", PROJECT, check=True)
        oc("set", "resources", f"deployment/{APP}", "--requests=cpu=50m", "-n", PROJECT, check=True)
        oc("patch", "deployment", APP, "-n", PROJECT, "--type=merge", "-p", json.dumps(
            {"spec": {"template": {"spec": {"securityContext": {"runAsUser": 0}}}}}
        ), check=True)


def _target_cpu(hpa):
    spec = hpa.get("spec", {})
    if "targetCPUUtilizationPercentage" in spec:
        return spec["targetCPUUtilizationPercentage"]
    for metric in spec.get("metrics") or []:
        if metric.get("type") == "Resource" and metric.get("resource", {}).get("name") == "cpu":
            return metric["resource"].get("target", {}).get("averageUtilization")
    return None


def grade():
    sa_user = f"system:serviceaccount:{PROJECT}:{SA}"

    with GradingStep(f"Il service account {SA} esiste") as step:
        if not oc_get_json("serviceaccount", SA, "-n", PROJECT):
            step.fail(f"ServiceAccount '{SA}' non trovato in {PROJECT}")

    with GradingStep(f"{SA} puo' usare la SCC anyuid") as step:
        # Copre sia la RoleBinding creata da `oc adm policy add-scc-to-user`
        # sia un'aggiunta manuale a scc/anyuid .users.
        groups = ("system:serviceaccounts", f"system:serviceaccounts:{PROJECT}", "system:authenticated")
        if not can_i("use", "securitycontextconstraints.security.openshift.io/anyuid",
                     sa_user, groups=groups, namespace=PROJECT):
            step.add_error("permesso 'use' su scc/anyuid assente")

    dep = oc_get_json("deployment", APP, "-n", PROJECT)
    pod_spec = (((dep or {}).get("spec") or {}).get("template") or {}).get("spec") or {}
    with GradingStep(f"Il deployment {APP} usa il service account {SA}") as step:
        if not dep:
            step.fail(f"Deployment '{APP}' non trovato")
        elif pod_spec.get("serviceAccountName") != SA:
            step.add_error(f"serviceAccountName = {pod_spec.get('serviceAccountName')!r}")

    with GradingStep(f"I pod di {APP} girano con la SCC anyuid") as step:
        pods = (oc_get_json("pods", "-n", PROJECT, "-l", f"app={APP}") or {}).get("items", [])
        running = [p for p in pods if p.get("status", {}).get("phase") == "Running"
                   and not p["metadata"].get("deletionTimestamp")]
        if not running:
            step.fail("nessun pod Running (oc get events)")
        else:
            sccs = {p["metadata"].get("annotations", {}).get("openshift.io/scc") for p in running}
            if sccs != {"anyuid"}:
                step.add_error(f"SCC dei pod: {sorted(s or '?' for s in sccs)}")

    with GradingStep(f"{APP} e' stato scalato a 5 repliche") as step:
        now = ((dep or {}).get("spec") or {}).get("replicas") == 5
        if not ever_seen(SLUG, "scaled5", now):
            step.add_error(f"replicas = {((dep or {}).get('spec') or {}).get('replicas')!r}")

    hpa = oc_get_json("hpa", APP, "-n", PROJECT)
    with GradingStep(f"Un HPA per {APP}: min {MIN_REPLICAS}, max {MAX_REPLICAS}, CPU {CPU_PERCENT}%") as step:
        if not hpa:
            step.fail(f"HorizontalPodAutoscaler '{APP}' non trovato")
        else:
            spec = hpa.get("spec", {})
            if (spec.get("scaleTargetRef") or {}).get("name") != APP:
                step.add_error(f"scaleTargetRef = {spec.get('scaleTargetRef')!r}")
            if spec.get("minReplicas") != MIN_REPLICAS:
                step.add_error(f"minReplicas = {spec.get('minReplicas')!r}")
            if spec.get("maxReplicas") != MAX_REPLICAS:
                step.add_error(f"maxReplicas = {spec.get('maxReplicas')!r}")
            if _target_cpu(hpa) != CPU_PERCENT:
                step.add_error(f"target CPU = {_target_cpu(hpa)!r}%")


def cleanup():
    with track_lock():
        delete_owned_project(PROJECT, SLUG)


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
