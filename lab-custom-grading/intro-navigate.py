#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato intro-navigate, sprovvisto di
`lab grade` ufficiale (la classe IntroNavigate nel pacchetto do180
implementa solo start()/finish(), non grade()).

A differenza di altre guided exercise di questo corso, intro-navigate non
copia dei file "starter" in ~/DO180/labs/intro-navigate (quella cartella
non esiste nemmeno): start() si limita a (1) cancellare un eventuale
progetto residuo intro-navigate e (2) creare/popolare, tramite l'API di
GitLab, un repository git.ocp4.example.com/developer/intro-navigate.git
con il contenuto di materials/solutions/intro-navigate (un'app Spring Boot
con devfile.yaml + deploy.yaml). A differenza di intro-monitor (che invece
chiama ocp_project.create_project_dev_access_step per creare il progetto
per lo studente), qui il progetto NON viene pre-creato: e' lo studente a
doverlo creare e a importare quel repository dalla Developer perspective
della console web ("+Add" -> "Import from Git"), esplorando cosi' la
console (Topology, build, pod, log, terminal, ecc.).

Il devfile.yaml della soluzione applica letteralmente deploy.yaml come
componente "kubernetes-deploy": quel manifest (non un template, nomi e
valori fissi) e' percio' la specifica oggettiva di cio' che deve risultare
nel cluster una volta completato l'esercizio:
  - Deployment "my-java-springboot" con un container sulla porta 8081 e
    resources.requests cpu=10m/memory=180Mi, con il pod Ready.
  - Service "my-java-springboot-svc" che espone la porta 8081.
Questo script verifica solo questo (l'esito osservabile dell'importazione
dell'app), non il modo in cui lo studente ha navigato la console (che non
e' verificabile via API).

Uso: intro-navigate.py [nome-progetto]   (default: intro-navigate)
"""

import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "intro-navigate"
DEPLOYMENT_NAME = "my-java-springboot"
SERVICE_NAME = "my-java-springboot-svc"
EXPECTED_PORT = 8081
EXPECTED_CPU_REQUEST = "10m"
EXPECTED_MEMORY_REQUEST = "180Mi"

# Fattori di conversione per i suffissi delle Quantity di Kubernetes:
# https://kubernetes.io/docs/reference/kubernetes-api/common-definitions/quantity/
_SUFFIXES = {
    "Ki": 2 ** 10, "Mi": 2 ** 20, "Gi": 2 ** 30, "Ti": 2 ** 40, "Pi": 2 ** 50, "Ei": 2 ** 60,
    "k": 10 ** 3, "K": 10 ** 3, "M": 10 ** 6, "G": 10 ** 9, "T": 10 ** 12, "P": 10 ** 15, "E": 10 ** 18,
    "m": 10 ** -3,
}


def parse_quantity(value):
    """Converte una stringa Quantity di Kubernetes (es. '180Mi', '10m')
    in un numero (unita' di base: byte per la memoria, core per la CPU).
    Solleva ValueError se il formato non e' riconosciuto."""
    text = str(value).strip()
    match = re.fullmatch(r"([+-]?[0-9]*\.?[0-9]+)(Ki|Mi|Gi|Ti|Pi|Ei|[kKMGTPE]|m)?", text)
    if not match:
        raise ValueError(f"formato non riconosciuto: {text}")
    number, suffix = match.groups()
    factor = _SUFFIXES[suffix] if suffix else 1
    return float(number) * factor


def get_container(deployment):
    containers = deployment["spec"]["template"]["spec"]["containers"]
    for c in containers:
        if c.get("name") == "my-java-springboot":
            return c
    return containers[0] if containers else None


def check_quantity(step, label, actual, expected):
    if actual is None:
        step.add_error(f"{label} non definita")
        return
    try:
        if parse_quantity(actual) != parse_quantity(expected):
            step.add_error(f"{label} errata (trovato: {actual}, atteso: {expected})")
    except ValueError as e:
        step.add_error(f"{label} non valida ({actual}): {e}")


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    deployment = oc_get_json("deployment", DEPLOYMENT_NAME, "-n", project)
    container = None

    with GradingStep(
        f"Il deployment {DEPLOYMENT_NAME} (app importata da Git) esiste ed e' pronto"
    ) as step:
        if deployment is None:
            step.fail(f"Deployment '{DEPLOYMENT_NAME}' non trovato nel progetto")
        else:
            container = get_container(deployment)
            if container is None:
                step.add_error("Nessun container trovato nel deployment")
            ready = deployment.get("status", {}).get("readyReplicas", 0)
            if not ready:
                step.add_error(
                    f"Nessuna replica pronta per il deployment '{DEPLOYMENT_NAME}' "
                    "(il pod non e' Running/Ready)"
                )

    with GradingStep(f"Il container espone la porta {EXPECTED_PORT}") as step:
        if container is None:
            step.fail()
        else:
            ports = [p.get("containerPort") for p in container.get("ports", [])]
            if EXPECTED_PORT not in ports:
                step.add_error(
                    f"Porta del container errata (trovate: {ports}, "
                    f"attesa: {EXPECTED_PORT})"
                )

    with GradingStep("Il container richiede le risorse corrette (cpu/memory)") as step:
        if container is None:
            step.fail()
        else:
            requests = container.get("resources", {}).get("requests", {})
            check_quantity(step, "resources.requests.cpu", requests.get("cpu"), EXPECTED_CPU_REQUEST)
            check_quantity(step, "resources.requests.memory", requests.get("memory"), EXPECTED_MEMORY_REQUEST)

    service = oc_get_json("service", SERVICE_NAME, "-n", project)

    with GradingStep(f"Il service {SERVICE_NAME} espone la porta {EXPECTED_PORT}") as step:
        if service is None:
            step.fail(f"Service '{SERVICE_NAME}' non trovato nel progetto")
        else:
            ports = [p.get("port") for p in service.get("spec", {}).get("ports", [])]
            if EXPECTED_PORT not in ports:
                step.add_error(
                    f"Il Service '{SERVICE_NAME}' non espone la porta {EXPECTED_PORT} "
                    f"(porte trovate: {ports})"
                )


if __name__ == "__main__":
    main()
