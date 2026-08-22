#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato reliability-requests, sprovvisto di
`lab grade` ufficiale (la classe ReliabilityRequests nel pacchetto do180
implementa solo start()/finish(), non grade()).

ATTENZIONE (audit RHOCP 4.22 / RHEL10): lo script precedente confrontava
labs/ vs solutions/long-load-deploy.yaml e si fermava li', gradando una
resources.requests.memory di 1G (e per di piu' con un bug di unita': la
soluzione scrive "1Gi" = 1073741824 byte, ma la costante era 1_000_000_000,
cioe' "1G" decimale - le due non sono mai uguali). Leggendo il testo della
guida (sezione 6.6, unica fonte affidabile qui: il file YAML da solo non
basta) risulta che 1Gi e' solo un valore INTERMEDIO, usato al punto 2 per
dimostrare che 10 replica non entrano nel nodo per mancanza di memoria. Il
valore finale, quello che lo studente deve avere impostato a fine esercizio
(punto 3.2, "Set the resource request to 150Mi"), e' 150Mi - non compare in
nessun file di materiali perche' lo studente lo applica dal vivo con
`oc set resources`, non modificando di nuovo lo YAML. Il vecchio script
gradava quindi un valore transitorio e per giunta con l'unita' sbagliata:
uno studente che seguiva la guida alla lettera (150Mi) avrebbe sempre
ricevuto FAIL. Riscritto per gradare lo stato finale descritto dalla guida:
richiesta di memoria 150Mi, deployment scalato a 10 replica, tutte Running.

Non gradato (dettagli incidentali dello starter, invariati dallo studente):
immagine del container, probes, securityContext, Service/Route - gia'
applicati da long-load-deploy.yaml al punto 1 e non modificati in questo
esercizio.

Uso: reliability-requests.py [nome-progetto]   (default: reliability-requests)
"""

import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "reliability-requests"

# Valore finale richiesto dalla guida al punto 3.2: "Set the resource
# request to 150Mi" (non 1Gi, che e' solo lo stato intermedio del punto 2.1
# usato per esaurire deliberatamente la memoria del nodo).
EXPECTED_REPLICAS = 10

# Fattori di conversione per i suffissi delle Quantity di Kubernetes:
# https://kubernetes.io/docs/reference/kubernetes-api/common-definitions/quantity/
_SUFFIXES = {
    "Ki": 2 ** 10, "Mi": 2 ** 20, "Gi": 2 ** 30, "Ti": 2 ** 40, "Pi": 2 ** 50, "Ei": 2 ** 60,
    "k": 10 ** 3, "K": 10 ** 3, "M": 10 ** 6, "G": 10 ** 9, "T": 10 ** 12, "P": 10 ** 15, "E": 10 ** 18,
    "m": 10 ** -3,
}
EXPECTED_MEMORY_BYTES = 150 * _SUFFIXES["Mi"]  # 150Mi = 157286400 byte


def parse_quantity(value):
    """Converte una stringa Quantity di Kubernetes (es. '150Mi', '150000000')
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

    with GradingStep("Il container long-load richiede 150Mi di memoria") as step:
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
                            "atteso l'equivalente di 150Mi - vedi guida 6.6, punto 3.2)"
                        )
                except ValueError as e:
                    step.add_error(f"Valore di memoria non valido ({memory}): {e}")

    with GradingStep(
        f"Il deployment e' scalato a {EXPECTED_REPLICAS} replica, tutte in esecuzione"
    ) as step:
        if deployment is None:
            step.fail()
        else:
            spec_replicas = deployment.get("spec", {}).get("replicas")
            status = deployment.get("status", {})
            ready = status.get("readyReplicas", 0)
            available = status.get("availableReplicas", 0)
            if spec_replicas != EXPECTED_REPLICAS:
                step.add_error(
                    f"Il deployment ha {spec_replicas} replica richieste, "
                    f"attese {EXPECTED_REPLICAS} (guida 6.6, punto 3.3)"
                )
            if ready != EXPECTED_REPLICAS or available != EXPECTED_REPLICAS:
                step.add_error(
                    f"Non tutte le replica sono pronte/disponibili "
                    f"(ready={ready}, available={available}, attese {EXPECTED_REPLICAS}) - "
                    "con la memoria richiesta corretta il nodo deve poter schedulare "
                    "tutti i pod senza restare in Pending (guida 6.6, punto 3.4)"
                )


if __name__ == "__main__":
    main()
