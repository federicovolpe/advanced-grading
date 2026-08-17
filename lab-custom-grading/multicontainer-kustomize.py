#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise multicontainer-kustomize (DO288),
priva di `lab grade` ufficiale (il modulo do288/multicontainer_kustomize.py
implementa solo start()/finish()).

Lo studente crea a mano la struttura Kustomize in
~/DO288/labs/multicontainer-kustomize/famous-kustomize/{base,overlays/dev,
overlays/prod}. Applica al cluster SOLO la base (`oc apply -k base`), che
crea un Deployment "famousapp-famouschart" (nome generato da un chart Helm
pre-esistente incluso in deployment.yaml, come riportato nella guida). Gli
overlay dev/prod non vengono mai applicati al cluster: la guida chiede solo
di verificarli in locale con `oc kustomize`, quindi li gradiamo leggendo i
file sul filesystem (render locale via oc_kustomize_docs, nessuna modifica).

Specifica (fornita dall'utente, che ha letto la guida ufficiale):
- Sul cluster: Deployment "famousapp-famouschart" con
  status.availableReplicas >= 1; una Route nel progetto risponde con successo
  su /random (contenuto variabile, una citazione random: verifichiamo solo
  che la richiesta HTTP abbia successo).
- Sui file locali (overlays/dev): un Deployment con .spec.replicas == 1 e
  container con resources.limits.memory == "128Mi" e
  resources.limits.cpu == "128m".
- Sui file locali (overlays/prod): un Deployment con .spec.replicas == 2 e
  container con resources.limits.memory == "256Mi" e
  resources.limits.cpu == "256m".
- Se le cartelle locali non esistono piu' (es. dopo `lab finish` o pulizia
  ambiente), oc_kustomize_docs ritorna lista vuota: i check locali devono
  fallire in modo pulito (FAIL con messaggio chiaro), non lanciare eccezioni.

Uso: multicontainer-kustomize.py [nome-progetto]  (default: multicontainer-kustomize)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, http_get, oc_get_json, oc_kustomize_docs, project_exists

LAB_NAME = "multicontainer-kustomize"
DEPLOYMENT = "famousapp-famouschart"
KUSTOMIZE_ROOT = os.path.expanduser(
    "~/DO288/labs/multicontainer-kustomize/famous-kustomize"
)


def _find_deployment(docs):
    return next((d for d in docs if (d or {}).get("kind") == "Deployment"), None)


def _first_container(deployment):
    containers = (
        ((deployment.get("spec") or {}).get("template") or {}).get("spec", {}).get("containers")
        or []
    )
    return containers[0] if containers else None


def _check_overlay(step, overlay_name, expected_replicas, expected_memory, expected_cpu):
    path = os.path.join(KUSTOMIZE_ROOT, "overlays", overlay_name)
    docs = oc_kustomize_docs(path)
    if not docs:
        step.fail(
            f"`oc kustomize {path}` non ha prodotto nessun manifest: cartella assente, "
            "malformata, oppure ambiente gia' pulito (lab finish)"
        )
        return
    deployment = _find_deployment(docs)
    if not deployment:
        step.add_error(f"Nessun Deployment trovato nel render di '{overlay_name}'")
        return
    replicas = (deployment.get("spec") or {}).get("replicas")
    if replicas != expected_replicas:
        step.add_error(f"'.spec.replicas' e' {replicas!r}, atteso {expected_replicas}")
    container = _first_container(deployment)
    if not container:
        step.add_error("Nessun container trovato nel Deployment renderizzato")
        return
    limits = (container.get("resources") or {}).get("limits") or {}
    if limits.get("memory") != expected_memory:
        step.add_error(f"resources.limits.memory e' {limits.get('memory')!r}, atteso '{expected_memory}'")
    if limits.get("cpu") != expected_cpu:
        step.add_error(f"resources.limits.cpu e' {limits.get('cpu')!r}, atteso '{expected_cpu}'")


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(f"Il Deployment '{DEPLOYMENT}' (base Kustomize) e' stato applicato al cluster") as step:
        deployment = oc_get_json("deployment", DEPLOYMENT, "-n", project)
        if not deployment:
            step.fail(f"Deployment '{DEPLOYMENT}' non trovato")
        elif (deployment.get("status") or {}).get("availableReplicas", 0) < 1:
            step.add_error(f"Il Deployment '{DEPLOYMENT}' non ha replica disponibili")

    with GradingStep("L'app risponde correttamente su /random tramite la Route") as step:
        routes = oc_get_json("route", "-n", project)
        items = (routes or {}).get("items") or []
        if not items:
            step.fail(f"Nessuna Route trovata nel progetto '{project}'")
        else:
            host = (items[0].get("spec") or {}).get("host", "")
            ok, _ = http_get(f"http://{host}/random")
            if not ok:
                step.add_error(f"Nessuna risposta valida da 'http://{host}/random'")

    with GradingStep("L'overlay locale 'overlays/dev' e' configurato correttamente (replicas=1, limits 128Mi/128m)") as step:
        _check_overlay(step, "dev", 1, "128Mi", "128m")

    with GradingStep("L'overlay locale 'overlays/prod' e' configurato correttamente (replicas=2, limits 256Mi/256m)") as step:
        _check_overlay(step, "prod", 2, "256Mi", "256m")


if __name__ == "__main__":
    main()
