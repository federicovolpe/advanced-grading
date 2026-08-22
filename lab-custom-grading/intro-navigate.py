#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato intro-navigate, sprovvisto di
`lab grade` ufficiale (la classe IntroNavigate nel pacchetto do180
implementa solo start()/finish(), non grade()).

Come in versione precedente, start() non copia file "starter" in
~/DO180/labs/intro-navigate (quella cartella non esiste): si limita a (1)
cancellare un eventuale progetto residuo intro-navigate e (2) popolare,
tramite l'API di GitLab, un repository
git.lab.example.com/developer/intro-navigate.git col contenuto di
materials/solutions/intro-navigate/intro-navigate (il sample ufficiale
devfile-sample-java-springboot-basic: devfile.yaml + Dockerfile +
deploy.yaml). E' lo studente a dover creare il progetto "intro-navigate" e
importare quel repository dalla Developer perspective ("+Add" -> "Import
from Git"), esplorando cosi' la console (Topology, Deployments, Services,
Routes, Pods, poi la Administrator perspective per Operators/Nodes/eventi).

RISCRITTO per RHOCP 4.22 / RHEL10: la sezione del manuale attuale (estratta
dal PDF corso) e' esplicita e ripetuta piu' volte sui nomi delle risorse
create dall'importazione, ed e' DIVERSA da quanto lo script precedente
assumeva:

  - 4.3 "the Topology page ... intro-navigate-git-app application"
  - 5.1/5.2 "the intro-navigate-git deployment"
  - 6.5 "Click intro-navigate-git to view the deployment details"
  - 7.1 "Networking > Services and click intro-navigate-git ..."
  - 7.2 "Networking > Routes and click intro-navigate-git ..."

Lo stesso nome base "intro-navigate-git" ricorre identico per Deployment,
Service E Route: e' la convenzione standard della console OpenShift per
"Import from Git" (suffisso "-git" aggiunto al nome del repository per il
componente creato, application grouping "<nome>-git-app"), NON i nomi
letterali "my-java-springboot"/"my-java-springboot-svc" del manifest
deploy.yaml del devfile. Il devfile.yaml del sample e' infatti quello
ufficiale devfile.io (vedi il suo README.md, che descrive il flusso
generico "outerloop" del devfile), e i valori nei suoi attributi
"deployment/cpuRequest: 10m", "deployment/memoryRequest: 180Mi",
"deployment/container-port: 8081" corrispondono esattamente ai campi
"Resource Limits"/porta che la console popola in automatico nel form di
Import from Devfile per generare IL SUO PROPRIO Deployment (con nome preso
dal campo "Name" del wizard, di default "<repo>-git"), non un'applicazione
letterale del manifest deploy.yaml. Per questo qui si verifica il
Deployment/Service/Route con nome "intro-navigate-git" (non piu'
"my-java-springboot"/"-svc"), ma si mantengono gli stessi valori attesi per
porta/cpu/memory del container, che restano quelli del devfile.

Aggiunta rispetto alla versione precedente: un check sulla Route, dato che
il manuale attuale la cita esplicitamente (punto 7.2) come parte del
percorso di verifica delle risorse create per l'app di esempio (Outcomes:
"Examine the resources that are created for the sample application").

Non gradato (non verificabile via API, o non richiesto in modo oggettivo):
la navigazione stessa della console (Operators, Nodes, Pods/Deployments a
livello di intero cluster nella Administrator perspective, punti 9.x) e il
login come utente admin — sono esplorazione pura, senza stato risultante
distinguibile da quello di un cluster su cui lo studente non ha fatto nulla.

Uso: intro-navigate.py [nome-progetto]   (default: intro-navigate)
"""

import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "intro-navigate"
# Nome base condiviso da Deployment/Service/Route: convenzione della console
# OpenShift per "Import from Git" ("<repo>-git"), vedi docstring sopra.
RESOURCE_NAME = "intro-navigate-git"
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
    """Ritorna il primo container del pod template. Il nome del container
    generato dalla console per un'importazione da Git non e' documentato dal
    manuale (a differenza del nome del Deployment stesso): non lo si
    assume, si prende semplicemente l'unico container presente."""
    containers = deployment["spec"]["template"]["spec"]["containers"]
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

    deployment = oc_get_json("deployment", RESOURCE_NAME, "-n", project)
    container = None

    with GradingStep(
        f"Il deployment {RESOURCE_NAME} (app importata da Git) esiste ed e' pronto"
    ) as step:
        if deployment is None:
            step.fail(f"Deployment '{RESOURCE_NAME}' non trovato nel progetto")
        else:
            container = get_container(deployment)
            if container is None:
                step.add_error("Nessun container trovato nel deployment")
            ready = deployment.get("status", {}).get("readyReplicas", 0)
            if not ready:
                step.add_error(
                    f"Nessuna replica pronta per il deployment '{RESOURCE_NAME}' "
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

    service = oc_get_json("service", RESOURCE_NAME, "-n", project)

    with GradingStep(f"Il service {RESOURCE_NAME} espone la porta {EXPECTED_PORT}") as step:
        if service is None:
            step.fail(f"Service '{RESOURCE_NAME}' non trovato nel progetto")
        else:
            ports = [p.get("port") for p in service.get("spec", {}).get("ports", [])]
            if EXPECTED_PORT not in ports:
                step.add_error(
                    f"Il Service '{RESOURCE_NAME}' non espone la porta {EXPECTED_PORT} "
                    f"(porte trovate: {ports})"
                )

    route = oc_get_json("route", RESOURCE_NAME, "-n", project)

    with GradingStep(f"La route {RESOURCE_NAME} espone il service") as step:
        if route is None:
            step.fail(f"Route '{RESOURCE_NAME}' non trovata nel progetto")
        else:
            to = route.get("spec", {}).get("to", {})
            if to.get("kind") != "Service" or to.get("name") != RESOURCE_NAME:
                step.add_error(
                    f"La route non punta al service '{RESOURCE_NAME}' "
                    f"(spec.to trovato: {to})"
                )


if __name__ == "__main__":
    main()
