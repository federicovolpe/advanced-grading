"""
Try-exam EX180, 9 — limita le risorse di un deployment: RAM massima e
millicpu massime.

Scostamenti dal tema annotato (scelte nostre): deployment api (httpd UBI 9),
progetto e valori (256Mi di memoria, 250m di CPU: il tema dice solo
"massima ram e massime millicpu", senza numeri).

Grading per risultato: i limiti si confrontano come quantita' (parse_quantity,
come in c6-02), quindi 250m e 0.25, o 256Mi e 268435456, sono equivalenti.
Le requests non sono richieste: se ci sono non devono superare i limiti
(l'API lo rifiuterebbe comunque; se mancano, Kubernetes le pone uguali ai
limiti). "Disponibile" vuol dire un pod pronto che ha davvero quei limiti:
un limite di memoria troppo basso (es. 256Ki) farebbe andare il pod nuovo
in OOMKilled mentre il vecchio resta disponibile.
"""
import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ex180_common import (  # noqa: F401
    CHAPTER, SETUP_TIMEOUT, GradingStep, oc, oc_get_json, parse_quantity, reset_project,
    delete_project, check_project, create_httpd_deployment, pod_spec, ready_pods, run_cli,
)

SLUG = "e09"
PROJECT = "ex180-e09"
TITLE = "9) Limita RAM e millicpu di un deployment"
APP = "api"
LIMITS = {"memory": "256Mi", "cpu": "250m"}

TASK = f"""\
Nel progetto {PROJECT} trovi il deployment {APP}.

Limita le risorse che il suo container puo' usare:
  - memoria (RAM) massima: {LIMITS['memory']}
  - CPU massima: {LIMITS['cpu']} (millicore)

Il deployment deve restare disponibile.
"""

SOLUTION = f"""\
oc project {PROJECT}
oc set resources deployment/{APP} --limits=memory={LIMITS['memory']},cpu={LIMITS['cpu']}
oc get deployment {APP} -o jsonpath='{{.spec.template.spec.containers[0].resources}}'; echo
oc get pods
"""


def _same(a, b):
    qa, qb = parse_quantity(a), parse_quantity(b)
    return qa is not None and qb is not None and math.isclose(qa, qb, rel_tol=1e-9)


def limit_problems(container):
    res = container.get("resources") or {}
    limits, requests = res.get("limits") or {}, res.get("requests") or {}
    errors = []
    for key, want in LIMITS.items():
        if not _same(limits.get(key), want):
            errors.append(f"limits.{key} = {limits.get(key)!r}, atteso {want}")
    for key in LIMITS:
        req, lim = parse_quantity(requests.get(key)), parse_quantity(limits.get(key))
        if req is not None and lim is not None and req > lim * (1 + 1e-9):
            errors.append(f"requests.{key} = {requests.get(key)!r} supera il limite")
    return errors


def setup():
    reset_project(PROJECT)
    create_httpd_deployment(APP, PROJECT)


def grade():
    check_project(PROJECT)
    dep = oc_get_json("deployment", APP, "-n", PROJECT)
    containers = pod_spec(dep).get("containers") or []

    with GradingStep(f"Il deployment {APP} esiste") as step:
        if not dep:
            step.fail(f"Deployment '{APP}' non trovato in {PROJECT}")

    with GradingStep(f"Limiti del container: memoria {LIMITS['memory']}, CPU {LIMITS['cpu']}") as step:
        if not containers:
            step.fail("Deployment (o container) non trovato")
        else:
            # Ogni container del deployment deve avere i limiti (di norma ce n'e' uno).
            for c in containers:
                for err in limit_problems(c):
                    step.add_error(f"container {c.get('name')}: {err}")

    with GradingStep(f"Il deployment {APP} e' disponibile con i nuovi limiti") as step:
        if not dep:
            step.fail("Deployment non trovato")
        elif not ready_pods(dep, PROJECT, lambda p: all(
                not limit_problems(c) for c in pod_spec(p).get("containers") or [])):
            step.fail("nessun pod Running e Ready con quei limiti (oc get pods, oc describe pod)")


def cleanup():
    delete_project(PROJECT)


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
