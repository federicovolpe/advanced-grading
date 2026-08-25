"""
Cap. 5 — Manage Storage for Application Configuration and Data
Monta un Secret come volume in un Deployment.
"""
import subprocess
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, oc, oc_get_json, find_running_pod, reset_project, run_cli

CHAPTER = "Cap. 5 — Manage Storage for Application Configuration and Data"
TITLE = "Monta un Secret come volume"
PROJECT = "training-config-secret"
IMAGE = "registry.access.redhat.com/ubi9/ubi:latest"
MOUNT_PATH = "/etc/secret"

TASK = f"""\
Nel progetto "{PROJECT}" trovi il Deployment "app". Crea un Secret
chiamato "app-secret" con la chiave API_KEY=s3cr3t, poi montalo come
volume nel Deployment "app" nel path {MOUNT_PATH}.

Comandi suggeriti (2):
  oc create secret generic app-secret --from-literal=API_KEY=s3cr3t -n {PROJECT}
  oc set volume deployment/app --add --type=secret --secret-name=app-secret --mount-path={MOUNT_PATH} -n {PROJECT}
"""


def setup():
    reset_project(PROJECT)
    oc(
        "create", "deployment", "app", f"--image={IMAGE}", "-n", PROJECT,
        "--", "sleep", "infinity", check=True,
    )


def grade():
    secret = oc_get_json("secret", "app-secret", "-n", PROJECT)

    with GradingStep("Il Secret app-secret esiste con la chiave giusta") as step:
        if not secret:
            step.fail("Secret 'app-secret' non trovato")
        elif "API_KEY" not in (secret.get("data") or {}):
            step.add_error("Chiave 'API_KEY' assente dal Secret")

    with GradingStep(f"Il Secret e' montato nel Deployment app su {MOUNT_PATH}") as step:
        dep = oc_get_json("deployment", "app", "-n", PROJECT)
        if not dep:
            step.fail("Deployment 'app' non trovato")
        else:
            pod_spec = dep.get("spec", {}).get("template", {}).get("spec", {})
            secret_volumes = {
                v["name"] for v in pod_spec.get("volumes", []) or []
                if v.get("secret", {}).get("secretName") == "app-secret"
            }
            mounted = any(
                vm.get("mountPath") == MOUNT_PATH and vm.get("name") in secret_volumes
                for c in pod_spec.get("containers", [])
                for vm in c.get("volumeMounts", []) or []
            )
            if not mounted:
                step.add_error(f"Nessun volumeMount su {MOUNT_PATH} che referenzi 'app-secret'")

    with GradingStep("Il contenuto del Secret e' leggibile dentro il pod") as step:
        running = find_running_pod(PROJECT, "app=app")
        if not running:
            step.fail("Nessun pod del Deployment 'app' e' Running")
        else:
            result = subprocess.run(
                ["oc", "exec", running["metadata"]["name"], "-n", PROJECT,
                 "--", "cat", f"{MOUNT_PATH}/API_KEY"],
                capture_output=True, text=True,
            )
            if result.stdout.strip() != "s3cr3t":
                step.add_error(f"cat {MOUNT_PATH}/API_KEY -> {result.stdout.strip()!r} (stderr: {result.stderr.strip()})")


if __name__ == "__main__":
    run_cli(setup, grade)
