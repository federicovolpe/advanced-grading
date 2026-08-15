#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato selfservice-ranges (DO280, capitolo
"Enabling Developer Self-service", sezione 6.4 "Per-Project Resource
Constraints: Limit Ranges"), sprovvisto di `lab grade` ufficiale (la classe
SelfserviceRanges implementa solo start()/finish(), non grade()).

materials/labs/selfservice-ranges e materials/solutions/selfservice-ranges
sono vuote nella cache di questa macchina: la specifica viene interamente dal
testo della guida studente (DO280-RHOCP4.18-en-1-20251205, pag. 265-275).

Valori esatti riportati nel testo (unica fonte disponibile):
- Punto 5.2: "The limit range sets a default memory request of 256 Mi and a
  default memory limit of 512 Mi." Il template YAML della console, mostrato
  in quel punto, definisce un limite per i container (non per i pod).
- Punto 10.3: la YAML del deployment "example" ricreato mostra un solo
  container di nome "container", immagine registry.access.redhat.com/
  ubi8/httpd-24, 3 repliche, resources: {} (la Deployment stessa resta
  invariata: e' il Pod, non il Deployment, che il limit range modifica).
- Punto 11.2: conferma indiretta osservando le metriche di un pod
  dell'esempio ricreato DOPO la creazione del limit range: "the request
  (256 MiB), and the limit (512 MiB)".

Il testo NON riporta alcun valore per CPU ne' alcun min/max per memory o
cpu (ne' a livello Container ne' Pod): per la regola d'oro di questo repo,
questi campi NON vengono gradati, per non rischiare di inventare requisiti
inesistenti.

L'esercizio si limita al progetto selfservice-ranges: il testo non modifica
mai il Project Template cluster-wide (projects.config.openshift.io) in
questa sezione — quell'argomento e' trattato in una guided exercise
successiva (selfservice-projtemplate) — quindi qui non viene verificato
nulla relativo al template di default dei nuovi progetti.

Uso: selfservice-ranges.py [nome-progetto]   (default: selfservice-ranges)
"""

import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "selfservice-ranges"
DEPLOYMENT_NAME = "example"
CONTAINER_NAME = "container"
EXPECTED_IMAGE_SUBSTR = "ubi8/httpd-24"
EXPECTED_REPLICAS = 3

EXPECTED_DEFAULT_REQUEST_MEMORY = "256Mi"  # punto 5.2
EXPECTED_DEFAULT_LIMIT_MEMORY = "512Mi"    # punto 5.2

# Fattori di conversione per i suffissi delle Quantity di Kubernetes (stessa
# utility di reliability-limits.py):
# https://kubernetes.io/docs/reference/kubernetes-api/common-definitions/quantity/
_SUFFIXES = {
    "Ki": 2 ** 10, "Mi": 2 ** 20, "Gi": 2 ** 30, "Ti": 2 ** 40, "Pi": 2 ** 50, "Ei": 2 ** 60,
    "k": 10 ** 3, "K": 10 ** 3, "M": 10 ** 6, "G": 10 ** 9, "T": 10 ** 12, "P": 10 ** 15, "E": 10 ** 18,
    "m": 10 ** -3,
}


def parse_quantity(value):
    """Converte una stringa Quantity di Kubernetes (es. '256Mi', '512Mi') nel
    numero di byte corrispondente. Solleva ValueError se il formato non e'
    riconosciuto."""
    text = str(value).strip()
    match = re.fullmatch(r"([+-]?[0-9]*\.?[0-9]+)(Ki|Mi|Gi|Ti|Pi|Ei|[kKMGTPE]|m)?", text)
    if not match:
        raise ValueError(f"formato non riconosciuto: {text}")
    number, suffix = match.groups()
    factor = _SUFFIXES[suffix] if suffix else 1
    return float(number) * factor


def quantities_equal(actual, expected):
    if actual is None:
        return False
    try:
        return parse_quantity(actual) == parse_quantity(expected)
    except ValueError:
        return False


def find_container_limit(limitrange):
    """Ritorna la voce di spec.limits con type == 'Container', o None."""
    for item in limitrange.get("spec", {}).get("limits", []) or []:
        if item.get("type") == "Container":
            return item
    return None


def get_container(deployment, name=CONTAINER_NAME):
    containers = deployment["spec"]["template"]["spec"]["containers"]
    for c in containers:
        if c.get("name") == name:
            return c
    return containers[0] if containers else None


def find_matching_pod_container(project):
    """Cerca, fra tutti i pod del progetto, un container con
    resources.requests.memory e resources.limits.memory che corrispondano
    esattamente ai valori attesi: conferma che il limit range e' stato
    applicato a un workload creato dopo la sua creazione (punti 7-9 della
    guida: cancellare il deployment 'example' e ricrearlo). Ritorna sempre
    una coppia (pod, container), (None, None) se non trovato."""
    pods = oc_get_json("pods", "-n", project)
    if not pods:
        return None, None
    for pod in pods.get("items", []):
        for container in pod.get("spec", {}).get("containers", []):
            resources = container.get("resources", {})
            requests = resources.get("requests", {})
            limits = resources.get("limits", {})
            if quantities_equal(
                requests.get("memory"), EXPECTED_DEFAULT_REQUEST_MEMORY
            ) and quantities_equal(
                limits.get("memory"), EXPECTED_DEFAULT_LIMIT_MEMORY
            ):
                return pod, container
    return None, None


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    # Punto 5: creazione del limit range con un limite di tipo Container.
    limitranges = oc_get_json("limitrange", "-n", project)
    container_limit = None

    with GradingStep(
        f"Esiste un LimitRange con un limite di tipo Container nel progetto {project}"
    ) as step:
        if not limitranges or not limitranges.get("items"):
            step.fail(f"Nessun LimitRange trovato nel progetto '{project}'")
        else:
            for lr in limitranges["items"]:
                container_limit = find_container_limit(lr)
                if container_limit is not None:
                    break
            if container_limit is None:
                step.fail(
                    "Nessun LimitRange nel progetto definisce un limite di "
                    "tipo 'Container'"
                )

    with GradingStep(
        f"Il LimitRange imposta defaultRequest.memory={EXPECTED_DEFAULT_REQUEST_MEMORY} "
        f"e default.memory={EXPECTED_DEFAULT_LIMIT_MEMORY} (punto 5.2 della guida)"
    ) as step:
        if container_limit is None:
            step.fail()
        else:
            default_request_mem = container_limit.get("defaultRequest", {}).get("memory")
            default_limit_mem = container_limit.get("default", {}).get("memory")
            if not quantities_equal(default_request_mem, EXPECTED_DEFAULT_REQUEST_MEMORY):
                step.add_error(
                    f"defaultRequest.memory atteso {EXPECTED_DEFAULT_REQUEST_MEMORY}, "
                    f"trovato: {default_request_mem!r}"
                )
            if not quantities_equal(default_limit_mem, EXPECTED_DEFAULT_LIMIT_MEMORY):
                step.add_error(
                    f"default.memory (limit) atteso {EXPECTED_DEFAULT_LIMIT_MEMORY}, "
                    f"trovato: {default_limit_mem!r}"
                )
            # Non gradati: eventuali min/max o valori di cpu, che il testo
            # della guida non riporta con numeri precisi (regola d'oro).

    # Punti 8-10: il deployment "example" viene ricreato dopo il limit range,
    # con la stessa immagine e lo stesso numero di repliche del primo giro.
    deployment = oc_get_json("deployment", DEPLOYMENT_NAME, "-n", project)
    container = None

    with GradingStep(
        f"Il deployment '{DEPLOYMENT_NAME}' esiste con l'immagine attesa"
    ) as step:
        if deployment is None:
            step.fail(f"Deployment '{DEPLOYMENT_NAME}' non trovato nel progetto")
        else:
            container = get_container(deployment)
            if container is None:
                step.fail("Nessun container trovato nel deployment")
            elif EXPECTED_IMAGE_SUBSTR not in container.get("image", ""):
                step.add_error(
                    f"L'immagine del container deve contenere "
                    f"'{EXPECTED_IMAGE_SUBSTR}' (trovata: {container.get('image')!r})"
                )
            replicas = deployment.get("spec", {}).get("replicas")
            if replicas != EXPECTED_REPLICAS:
                step.add_error(
                    f"spec.replicas del deployment deve essere "
                    f"{EXPECTED_REPLICAS} (trovato: {replicas})"
                )

    with GradingStep(
        "Un pod del deployment riflette i valori del limit range "
        "(punti 9.4/11.2 della guida: requests.memory="
        f"{EXPECTED_DEFAULT_REQUEST_MEMORY}, limits.memory="
        f"{EXPECTED_DEFAULT_LIMIT_MEMORY})"
    ) as step:
        pod, matched_container = find_matching_pod_container(project)
        if pod is None:
            step.add_error(
                "Nessun pod nel progetto ha un container con "
                f"requests.memory={EXPECTED_DEFAULT_REQUEST_MEMORY} e "
                f"limits.memory={EXPECTED_DEFAULT_LIMIT_MEMORY}: il "
                f"deployment '{DEPLOYMENT_NAME}' potrebbe non essere stato "
                "cancellato e ricreato DOPO la creazione del limit range "
                "(punti 7-9 della guida), oppure il limit range non ha i "
                "valori corretti"
            )


if __name__ == "__main__":
    main()
