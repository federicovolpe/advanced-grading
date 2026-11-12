"""
Try-exam EX180, 8 — scala un deployment fino a 10 copie di un pod.

Scostamenti dal tema annotato (scelte nostre): deployment web (httpd UBI 9)
e progetto. Il setup() gli imposta richieste piccole (cpu 10m, memory 32Mi)
per non saturare il classroom con 10 repliche: non fanno parte del compito.

Si grada il RISULTATO della richiesta, spec.replicas == 10 (con `oc scale`,
`oc edit`, `oc patch` o un manifest: non importa), piu' almeno un pod
disponibile. NON si pretende che tutte e 10 le repliche siano pronte: la
capacita' del cluster del classroom (un SNO condiviso) e' ignota, e un pod
Pending per mancanza di risorse non e' un errore dello studente.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ex180_common import (  # noqa: F401
    CHAPTER, SETUP_TIMEOUT, GradingStep, oc, oc_get_json, reset_project, delete_project,
    check_project, create_httpd_deployment, available_replicas, run_cli,
)

SLUG = "e08"
PROJECT = "ex180-e08"
TITLE = "8) Scala un deployment a 10 repliche"
APP = "web"
REPLICAS = 10

TASK = f"""\
Nel progetto {PROJECT} trovi il deployment {APP}, con una sola replica.

Scalalo fino ad avere {REPLICAS} copie del suo pod.

(Non serve che tutte le {REPLICAS} repliche diventino pronte: dipende dalle
risorse libere del cluster. Ne basta almeno una disponibile.)
"""

SOLUTION = f"""\
oc project {PROJECT}
oc scale deployment/{APP} --replicas={REPLICAS}
oc get deployment {APP}              # READY x/{REPLICAS}
oc get pods
"""


def setup():
    reset_project(PROJECT)
    create_httpd_deployment(APP, PROJECT)
    oc("set", "resources", f"deployment/{APP}", "--requests=cpu=10m,memory=32Mi",
       "-n", PROJECT, check=True)


def grade():
    check_project(PROJECT)
    dep = oc_get_json("deployment", APP, "-n", PROJECT)
    spec = (dep or {}).get("spec") or {}
    status = (dep or {}).get("status") or {}

    with GradingStep(f"Il deployment {APP} esiste") as step:
        if not dep:
            step.fail(f"Deployment '{APP}' non trovato in {PROJECT}")

    with GradingStep(f"Il deployment {APP} chiede {REPLICAS} repliche") as step:
        if not dep:
            step.fail("Deployment non trovato")
        elif spec.get("replicas") != REPLICAS:
            step.add_error(f"spec.replicas = {spec.get('replicas')!r}")

    with GradingStep(f"Il deployment {APP} ha almeno una replica disponibile") as step:
        if not dep:
            step.fail("Deployment non trovato")
        elif not available_replicas(dep):
            step.fail(f"availableReplicas = 0 (pronte {status.get('readyReplicas') or 0}"
                      f"/{spec.get('replicas')}: oc get pods)")


def cleanup():
    delete_project(PROJECT)


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
