"""
Cap. 5 — Manage Storage for Application Configuration and Data
Esternalizza la configurazione di un'app con una ConfigMap.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, oc, oc_get_json, find_running_pod, reset_project, run_cli

CHAPTER = "Cap. 5 — Manage Storage for Application Configuration and Data"
TITLE = "Configura un'app con una ConfigMap"
PROJECT = "training-config-map"
IMAGE = "registry.access.redhat.com/ubi9/ubi:latest"

TASK = f"""\
Nel progetto "{PROJECT}" trovi il Deployment "app". Crea una ConfigMap
chiamata "app-config" con la chiave GREETING=hello-training, poi
collegala come variabili d'ambiente del Deployment "app".

Comandi suggeriti (2):
  oc create configmap app-config --from-literal=GREETING=hello-training -n {PROJECT}
  oc set env deployment/app --from=configmap/app-config -n {PROJECT}
"""


def setup():
    reset_project(PROJECT)
    oc(
        "create", "deployment", "app", f"--image={IMAGE}", "-n", PROJECT,
        "--", "sleep", "infinity", check=True,
    )


def grade():
    cm = oc_get_json("configmap", "app-config", "-n", PROJECT)

    with GradingStep("La ConfigMap app-config esiste con la chiave giusta") as step:
        if not cm:
            step.fail("ConfigMap 'app-config' non trovata")
        elif (cm.get("data") or {}).get("GREETING") != "hello-training":
            step.add_error(f"data.GREETING = {(cm.get('data') or {}).get('GREETING')!r}")

    with GradingStep("Il Deployment app referenzia la ConfigMap come env") as step:
        dep = oc_get_json("deployment", "app", "-n", PROJECT)
        if not dep:
            step.fail("Deployment 'app' non trovato")
        else:
            containers = dep.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
            # "oc set env --from=configmap/X" crea una entry per-chiave in
            # env[].valueFrom.configMapKeyRef (NON envFrom.configMapRef, che
            # e' un'altra sintassi valida ma diversa) — accettiamo entrambe le
            # forme, verificato dal vivo cosa produce davvero il comando
            # suggerito prima di scrivere questo check.
            found = any(
                ref.get("configMapRef", {}).get("name") == "app-config"
                for c in containers
                for ref in c.get("envFrom", []) or []
            ) or any(
                e.get("valueFrom", {}).get("configMapKeyRef", {}).get("name") == "app-config"
                for c in containers
                for e in c.get("env", []) or []
            )
            if not found:
                step.add_error("Nessun container referenzia la ConfigMap 'app-config' (ne' envFrom ne' env[].valueFrom)")

    with GradingStep("La variabile GREETING e' visibile dentro il pod") as step:
        running = find_running_pod(PROJECT, "app=app")
        if not running:
            step.fail("Nessun pod del Deployment 'app' e' Running")
        else:
            import subprocess
            result = subprocess.run(
                ["oc", "exec", running["metadata"]["name"], "-n", PROJECT, "--", "printenv", "GREETING"],
                capture_output=True, text=True,
            )
            if result.stdout.strip() != "hello-training":
                step.add_error(f"printenv GREETING -> {result.stdout.strip()!r}")


if __name__ == "__main__":
    run_cli(setup, grade)
