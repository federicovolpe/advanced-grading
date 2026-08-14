#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato reliability-autoscaling, sprovvisto
di `lab grade` ufficiale (la classe ReliabilityAutoscaling nel pacchetto
do180 implementa solo start()/finish(), non grade()).

Confrontando i file di partenza e la soluzione ufficiale (loadtest.yml,
vedi do180/materials/labs/reliability-autoscaling e
do180/materials/solutions/reliability-autoscaling) l'UNICA differenza e'
l'aggiunta di risorse CPU al container "loadtest" del deployment omonimo:

    resources:
      requests:
        cpu: 25m
      limits:
        cpu: 100m

Questo script verifica quindi quello, ricalcando lo schema a GradingStep di
reliability-requests.py/reliability-limits.py.

L'HorizontalPodAutoscaler viene creato in modo imperativo dalla guida
ufficiale con:

    oc autoscale deployment/loadtest --min 2 --max 20 --cpu-percent 50

(valori confermati dal testo della guida studente). Anche questo viene
quindi gradato: minReplicas=2, maxReplicas=20, target CPU Utilization=50%
sulla risorsa "cpu" del Deployment/loadtest.

Uso: reliability-autoscaling.py [nome-progetto]   (default: reliability-autoscaling)
"""

import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "reliability-autoscaling"
CONTAINER_NAME = "loadtest"
EXPECTED_CPU_REQUEST_CORES = 0.025  # 25m, come nella soluzione ufficiale
EXPECTED_CPU_LIMIT_CORES = 0.1      # 100m, come nella soluzione ufficiale

# Fattori di conversione per i suffissi delle Quantity di Kubernetes:
# https://kubernetes.io/docs/reference/kubernetes-api/common-definitions/quantity/
_SUFFIXES = {
    "Ki": 2 ** 10, "Mi": 2 ** 20, "Gi": 2 ** 30, "Ti": 2 ** 40, "Pi": 2 ** 50, "Ei": 2 ** 60,
    "k": 10 ** 3, "K": 10 ** 3, "M": 10 ** 6, "G": 10 ** 9, "T": 10 ** 12, "P": 10 ** 15, "E": 10 ** 18,
    "m": 10 ** -3,
}


def parse_quantity(value):
    """Converte una stringa Quantity di Kubernetes (es. '25m', '0.1', '100m')
    nel numero corrispondente (unita' base, qui core di CPU). Solleva
    ValueError se il formato non e' riconosciuto."""
    text = str(value).strip()
    match = re.fullmatch(r"([+-]?[0-9]*\.?[0-9]+)(Ki|Mi|Gi|Ti|Pi|Ei|[kKMGTPE]|m)?", text)
    if not match:
        raise ValueError(f"formato non riconosciuto: {text}")
    number, suffix = match.groups()
    factor = _SUFFIXES[suffix] if suffix else 1
    return float(number) * factor


def get_container(deployment, name=CONTAINER_NAME):
    containers = deployment["spec"]["template"]["spec"]["containers"]
    for c in containers:
        if c.get("name") == name:
            return c
    return containers[0] if containers else None


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    deployment = oc_get_json("deployment", CONTAINER_NAME, "-n", project)
    container = None

    with GradingStep(f"Il deployment {CONTAINER_NAME} esiste") as step:
        if deployment is None:
            step.fail(f"Deployment '{CONTAINER_NAME}' non trovato nel progetto")
        else:
            container = get_container(deployment)
            if container is None:
                step.fail("Nessun container trovato nel deployment")

    with GradingStep(
        "Il container loadtest dichiara le risorse CPU necessarie "
        "per l'autoscaling (request 25m, limit 100m)"
    ) as step:
        if container is None:
            step.fail()
        else:
            resources = container.get("resources", {})
            requests = resources.get("requests", {})
            limits = resources.get("limits", {})
            cpu_request = requests.get("cpu")
            cpu_limit = limits.get("cpu")

            if cpu_request is None:
                step.add_error("Il container non definisce resources.requests.cpu")
            else:
                try:
                    if parse_quantity(cpu_request) != EXPECTED_CPU_REQUEST_CORES:
                        step.add_error(
                            f"resources.requests.cpu errato (trovato: {cpu_request}, "
                            "atteso l'equivalente di 25m)"
                        )
                except ValueError as e:
                    step.add_error(f"Valore di requests.cpu non valido ({cpu_request}): {e}")

            if cpu_limit is None:
                step.add_error("Il container non definisce resources.limits.cpu")
            else:
                try:
                    if parse_quantity(cpu_limit) != EXPECTED_CPU_LIMIT_CORES:
                        step.add_error(
                            f"resources.limits.cpu errato (trovato: {cpu_limit}, "
                            "atteso l'equivalente di 100m)"
                        )
                except ValueError as e:
                    step.add_error(f"Valore di limits.cpu non valido ({cpu_limit}): {e}")

    hpa = oc_get_json("hpa", CONTAINER_NAME, "-n", project)

    with GradingStep(
        "L'autoscaler orizzontale e' configurato correttamente "
        "(min 2, max 20, target CPU 50%)"
    ) as step:
        if hpa is None:
            step.fail(f"HorizontalPodAutoscaler '{CONTAINER_NAME}' non trovato nel progetto")
        else:
            spec = hpa.get("spec", {})
            target = spec.get("scaleTargetRef", {})
            if target.get("kind") != "Deployment" or target.get("name") != CONTAINER_NAME:
                step.add_error(
                    f"L'autoscaler non punta al deployment '{CONTAINER_NAME}' "
                    f"(trovato: {target.get('kind')}/{target.get('name')})"
                )
            if spec.get("minReplicas") != 2:
                step.add_error(f"minReplicas errato (trovato: {spec.get('minReplicas')}, atteso 2)")
            if spec.get("maxReplicas") != 20:
                step.add_error(f"maxReplicas errato (trovato: {spec.get('maxReplicas')}, atteso 20)")

            metrics = spec.get("metrics", [])
            cpu_metric = next(
                (m for m in metrics if m.get("type") == "Resource" and m.get("resource", {}).get("name") == "cpu"),
                None,
            )
            if cpu_metric is None:
                step.add_error("Nessuna metrica di tipo Resource/cpu configurata")
            else:
                target_util = cpu_metric["resource"].get("target", {}).get("averageUtilization")
                if target_util != 50:
                    step.add_error(
                        f"Target di utilizzo CPU errato (trovato: {target_util}%, atteso 50%)"
                    )


if __name__ == "__main__":
    main()
