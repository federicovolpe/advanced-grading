#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato reliability-limits, sprovvisto di
`lab grade` ufficiale (la classe ReliabilityLimits nel pacchetto do180
implementa solo start()/finish(), non grade()).

A differenza di reliability-requests/reliability-probes, per questo esercizio
non esiste una cartella materials/solutions/reliability-limits/ con un
manifest "risolto" da confrontare: il file di partenza
(materials/labs/reliability-limits/leakapp.yml) definisce di proposito un
limite di memoria troppo basso (resources.limits.memory: 35Mi) per un
container che alloca ~1MiB/sec, cosi' da farlo terminare in OOMKilled.
Il file resources.txt fornito con l'esercizio contiene il comando che lo
studente deve eseguire per correggere il problema:

    oc set resources deployment/leakapp --limits memory=600Mi

Questo script verifica quindi solo l'unico stato finale oggettivamente
verificabile richiesto dall'esercizio: che il limite di memoria del
container "leakapp" sia stato alzato ad almeno 600Mi (il valore suggerito
in resources.txt). Non verifica lo stato runtime del pod (Running/OOMKilled)
perche' il container alloca memoria indefinitamente: anche con un limite
piu' alto puo' finire OOMKilled se osservato molto tempo dopo l'esecuzione
del comando, quindi quel tipo di controllo sarebbe intrinsecamente instabile
nel tempo e non adatto al grading.

Uso: reliability-limits.py [nome-progetto]   (default: reliability-limits)
"""

import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "reliability-limits"
CONTAINER_NAME = "leakapp"
MINIMUM_MEMORY_LIMIT_BYTES = 600 * 2 ** 20  # 600Mi, come suggerito in resources.txt

# Fattori di conversione per i suffissi delle Quantity di Kubernetes:
# https://kubernetes.io/docs/reference/kubernetes-api/common-definitions/quantity/
_SUFFIXES = {
    "Ki": 2 ** 10, "Mi": 2 ** 20, "Gi": 2 ** 30, "Ti": 2 ** 40, "Pi": 2 ** 50, "Ei": 2 ** 60,
    "k": 10 ** 3, "K": 10 ** 3, "M": 10 ** 6, "G": 10 ** 9, "T": 10 ** 12, "P": 10 ** 15, "E": 10 ** 18,
    "m": 10 ** -3,
}


def parse_quantity(value):
    """Converte una stringa Quantity di Kubernetes (es. '600Mi', '35Mi')
    nel numero di byte corrispondente. Solleva ValueError se il formato non
    e' riconosciuto."""
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

    deployment = oc_get_json("deployment", "leakapp", "-n", project)
    container = None

    with GradingStep("Il deployment leakapp esiste") as step:
        if deployment is None:
            step.fail("Deployment 'leakapp' non trovato nel progetto")
        else:
            container = get_container(deployment)
            if container is None:
                step.fail("Nessun container trovato nel deployment")

    with GradingStep(
        "Il container leakapp ha un limite di memoria sufficiente (>= 600Mi)"
    ) as step:
        if container is None:
            step.fail()
        else:
            limits = container.get("resources", {}).get("limits", {})
            memory = limits.get("memory")
            if memory is None:
                step.add_error("Il container non definisce resources.limits.memory")
            else:
                try:
                    if parse_quantity(memory) < MINIMUM_MEMORY_LIMIT_BYTES:
                        step.add_error(
                            f"Limite di memoria insufficiente (trovato: {memory}, "
                            "atteso almeno l'equivalente di 600Mi, come suggerito "
                            "in resources.txt)"
                        )
                except ValueError as e:
                    step.add_error(f"Valore di memoria non valido ({memory}): {e}")


if __name__ == "__main__":
    main()
