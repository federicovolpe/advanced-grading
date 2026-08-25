"""
Cap. 6 — Configure Applications for Reliability
Configura l'autoscaling automatico di un Deployment con un HPA.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, oc, oc_get_json, reset_project, run_cli

CHAPTER = "Cap. 6 — Configure Applications for Reliability"
TITLE = "Configura l'autoscaling (HPA)"
PROJECT = "training-reliability-hpa"
IMAGE = "registry.access.redhat.com/ubi9/httpd-24:latest"
MIN_REPLICAS = 1
MAX_REPLICAS = 4
TARGET_CPU_PERCENT = 60

TASK = f"""\
Nel progetto "{PROJECT}" trovi il Deployment "web" (ha gia' una
resource request di CPU, necessaria all'HPA per calcolare la
percentuale). Crea un HorizontalPodAutoscaler per "web" con minimo
{MIN_REPLICAS}, massimo {MAX_REPLICAS} repliche e target CPU al
{TARGET_CPU_PERCENT}%.

Comando suggerito (1):
  oc autoscale deployment/web --min={MIN_REPLICAS} --max={MAX_REPLICAS} \\
      --cpu={TARGET_CPU_PERCENT}% -n {PROJECT}
"""


def setup():
    reset_project(PROJECT)
    oc("create", "deployment", "web", f"--image={IMAGE}", "-n", PROJECT, check=True)
    oc("set", "resources", "deployment/web", "--requests=cpu=100m", "-n", PROJECT, check=True)


def _target_cpu_percent(hpa):
    spec = hpa.get("spec", {})
    if "targetCPUUtilizationPercentage" in spec:  # autoscaling/v1
        return spec["targetCPUUtilizationPercentage"]
    for metric in spec.get("metrics", []) or []:  # autoscaling/v2
        if metric.get("type") == "Resource" and metric.get("resource", {}).get("name") == "cpu":
            return metric["resource"].get("target", {}).get("averageUtilization")
    return None


def grade():
    hpa = oc_get_json("hpa", "web", "-n", PROJECT)

    with GradingStep("Esiste un HPA chiamato web per il Deployment web") as step:
        if not hpa:
            step.fail("HPA 'web' non trovato")
        elif hpa.get("spec", {}).get("scaleTargetRef", {}).get("name") != "web":
            step.add_error("L'HPA non punta al Deployment 'web'")

    with GradingStep(f"minReplicas={MIN_REPLICAS} e maxReplicas={MAX_REPLICAS}") as step:
        if not hpa:
            step.fail("HPA 'web' non trovato")
        else:
            spec = hpa.get("spec", {})
            if spec.get("minReplicas") != MIN_REPLICAS:
                step.add_error(f"minReplicas = {spec.get('minReplicas')!r}, attese {MIN_REPLICAS}")
            if spec.get("maxReplicas") != MAX_REPLICAS:
                step.add_error(f"maxReplicas = {spec.get('maxReplicas')!r}, attese {MAX_REPLICAS}")

    with GradingStep(f"Il target di CPU e' {TARGET_CPU_PERCENT}%") as step:
        if not hpa:
            step.fail("HPA 'web' non trovato")
        else:
            target = _target_cpu_percent(hpa)
            if target != TARGET_CPU_PERCENT:
                step.add_error(f"Target CPU = {target!r}%, atteso {TARGET_CPU_PERCENT}%")


if __name__ == "__main__":
    run_cli(setup, grade)
