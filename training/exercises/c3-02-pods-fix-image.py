"""
Cap. 3 — Run Applications as Containers and Pods
Troubleshooting: correggi un pod che non parte per un tag immagine sbagliato.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, oc, oc_get_json, reset_project, run_cli

CHAPTER = "Cap. 3 — Run Applications as Containers and Pods"
TITLE = "Correggi un pod rotto (troubleshooting)"
PROJECT = "training-pods-fix-image"
GOOD_IMAGE = "registry.access.redhat.com/ubi9/ubi:latest"
BAD_IMAGE = "registry.access.redhat.com/ubi9/ubi:no-such-tag"

TASK = f"""\
Nel progetto "{PROJECT}" c'e' un pod chiamato "broken" che non parte
(ImagePullBackOff) perche' usa un tag immagine inesistente. Correggilo
cambiando l'immagine in {GOOD_IMAGE}, cosi' che vada in Running.

Comando suggerito (1) — il container si chiama anch'esso "broken":
  oc set image pod/broken broken={GOOD_IMAGE} -n {PROJECT}
"""


def setup():
    reset_project(PROJECT)
    oc(
        "run", "broken",
        f"--image={BAD_IMAGE}",
        "-n", PROJECT,
        "--command", "--", "sleep", "infinity",
        check=True,
    )


def grade():
    pod = oc_get_json("pod", "broken", "-n", PROJECT)

    with GradingStep("Il pod broken usa un'immagine valida") as step:
        if not pod:
            step.fail("Pod 'broken' non trovato")
        else:
            containers = pod.get("spec", {}).get("containers", [])
            image = containers[0].get("image", "") if containers else ""
            if "no-such-tag" in image:
                step.add_error("Il tag immagine e' ancora quello sbagliato")

    with GradingStep("Il pod broken e' in esecuzione (Running)") as step:
        if not pod:
            step.fail("Pod 'broken' non trovato")
        elif (pod.get("status") or {}).get("phase") != "Running":
            statuses = (pod.get("status") or {}).get("containerStatuses", [])
            reason = ""
            if statuses:
                waiting = statuses[0].get("state", {}).get("waiting", {})
                reason = waiting.get("reason", "")
            step.add_error(f"Fase attuale: {(pod.get('status') or {}).get('phase')!r} ({reason})")


if __name__ == "__main__":
    run_cli(setup, grade)
