"""
Grading personalizzato per 'workbench-custom' (AI0015L - Custom Workbench
Image).

`lab start` (ai0015l/exercises/workbench_custom.py) copia solo il
Containerfile fornito e crea il progetto; nessuna immagine/deployment e'
automatico. Il compito dello studente e' buildare il Containerfile e fare
il push dell'immagine risultante sul registry della classroom, con
esattamente questo nome:tag (confermato da `finish()`, che pulisce
esplicitamente `docker://registry.lab.example.com:8443/developer/custom-workbench:1.0`
via ai0015l/common/steps.py -> delete_registry_image_step).

NB: il check FAIL (immagine assente) e' verificato dal vivo; il caso PASS
(immagine realmente pushata) no, perche' richiederebbe buildare e pushare
un'immagine di test sul registry condiviso della classroom - skopeo_inspect_auth
ricalca comunque lo stesso meccanismo, gia' testato, di skopeo_inspect.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, project_exists, skopeo_inspect_auth

LAB_NAME = "workbench-custom"
REGISTRY_HOST = "registry.lab.example.com:8443"
IMAGE = "developer/custom-workbench:1.0"
REGISTRY_USER = "developer"
REGISTRY_PASSWORD = "developer"


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(
        f"L'immagine custom '{IMAGE}' e' stata pushata sul registry"
    ) as step:
        ok, _ = skopeo_inspect_auth(
            f"{REGISTRY_HOST}/{IMAGE}", REGISTRY_USER, REGISTRY_PASSWORD
        )
        if not ok:
            step.fail(f"Immagine '{REGISTRY_HOST}/{IMAGE}' non trovata sul registry")


if __name__ == "__main__":
    main()
