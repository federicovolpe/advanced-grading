#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato reliability-requests, sprovvisto di
`lab grade` ufficiale (la classe ReliabilityRequests nel pacchetto do180
implementa solo start()/finish(), non grade()).

Confrontando i file di partenza e la soluzione ufficiale (long-load-deploy.yaml,
stesso deployment "long-load" di reliability-probes/reliability-review) l'unica
differenza e' l'aggiunta di una richiesta di memoria (resources.requests.memory:
1G) al container long-load. Questo script verifica solo quanto richiesto da
questa guided exercise, ricalcando lo schema a GradingStep di
reliability-probes.py e reliability-review.py.

Uso: reliability-requests.py [nome-progetto]   (default: reliability-requests)
"""

import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "reliability-requests"
EXPECTED_MEMORY_BYTES = 1_000_000_000  # 1G (decimale), come nella soluzione ufficiale

# Fattori di conversione per i suffissi delle Quantity di Kubernetes:
# https://kubernetes.io/docs/reference/kubernetes-api/common-definitions/quantity/
_SUFFIXES = {
    "Ki": 2 ** 10, "Mi": 2 ** 20, "Gi": 2 ** 30, "Ti": 2 ** 40, "Pi": 2 ** 50, "Ei": 2 ** 60,
    "k": 10 ** 3, "K": 10 ** 3, "M": 10 ** 6, "G": 10 ** 9, "T": 10 ** 12, "P": 10 ** 15, "E": 10 ** 18,
    "m": 10 ** -3,
}


def parse_quantity(value):
    """Converte una stringa Quantity di Kubernetes (es. '1G', '1000M', '1000000000')
    nel numero di byte corrispondente. Solleva ValueError se il formato non e'
    riconosciuto."""
    text = str(value).strip()
    match = re.fullmatch(r"([+-]?[0-9]*\.?[0-9]+)(Ki|Mi|Gi|Ti|Pi|Ei|[kKMGTPE]|m)?", text)
    if not match:
        raise ValueError(f"formato non riconosciuto: {text}")
    number, suffix = match.groups()
    factor = _SUFFIXES[suffix] if suffix else 1
    return float(number) * factor


def get_container(deployment, name="long-load"):
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

    deployment = oc_get_json("deployment", "long-load", "-n", project)
    container = None

    with GradingStep("Il deployment long-load esiste") as step:
        if deployment is None:
            step.fail("Deployment 'long-load' non trovato nel progetto")
        else:
            container = get_container(deployment)
            if container is None:
                step.fail("Nessun container trovato nel deployment")

    with GradingStep("Il container long-load dichiara la memoria richiesta (1G)") as step:
        if container is None:
            step.fail()
        else:
            requests = container.get("resources", {}).get("requests", {})
            memory = requests.get("memory")
            if memory is None:
                step.add_error("Il container non definisce resources.requests.memory")
            else:
                try:
                    if parse_quantity(memory) != EXPECTED_MEMORY_BYTES:
                        step.add_error(
                            f"Quantita' di memoria errata (trovato: {memory}, "
                            "atteso l'equivalente di 1G)"
                        )
                except ValueError as e:
                    step.add_error(f"Valore di memoria non valido ({memory}): {e}")


if __name__ == "__main__":
    main()
