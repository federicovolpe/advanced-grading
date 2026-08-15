#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato non-http-multus, sprovvisto di
`lab grade` ufficiale (la classe NonHttpMultus nel pacchetto do280 implementa
solo start()/finish(), non grade()).

L'esercizio usa DUE progetti (vedi start()/finish() in do280/non-http-multus.py):
- non-http-multus: il progetto principale, dove lo studente configura una
  NetworkAttachmentDefinition Multus (strategia host-device sull'interfaccia
  ens4 del nodo) e la collega al deployment database-multus con l'annotazione
  k8s.v1.cni.cncf.io/networks.
- network-udn: dove lo studente crea (dalla web console, non da un manifest)
  una UserDefinedNetwork e applica deployment-udn.yaml, che riceve
  automaticamente la UDN come rete primaria (il namespace ha gia' la label
  k8s.ovn.org/primary-user-defined-network, applicata da lab-start e non
  toccata dallo studente: per questo non viene gradata).

Specifica dedotta da (in quest'ordine, come da CLAUDE.md):
1. Diff tra materials/labs/non-http-multus/network-attachment-definition.yaml
   (placeholder CHANGE_ME) e materials/solutions/.../network-attachment-definition.yaml
   (nome "custom", type "host-device", device "ens4", ipam static su
   192.168.51.10/24).
2. Il testo della guida studente (PDF), che conferma passo per passo:
   - l'annotazione k8s.v1.cni.cncf.io/networks: custom da aggiungere in
     spec.template.metadata.annotations del deployment database-multus
     (punto 6.2), verificabile anche funzionalmente tramite l'annotazione
     k8s.v1.cni.cncf.io/network-status del pod risultante (punto 6.5: interfaccia
     "net1" con IP 192.168.51.10, nome rete "<progetto>/custom");
   - la creazione, dalla console web, di una UserDefinedNetwork nel progetto
     network-udn con subnet 10.0.0.0/16 (punto 9.4), con le condizioni
     NetworkCreated e NetworkAllocationSucceeded a True (punto 9.5);
   - il deployment database-udn (punto 10.3) il cui pod risultante ottiene
     un'interfaccia sulla UDN (punto 11.1: interfaccia "ovn-udn1" con IP nella
     subnet 10.0.0.0/16, marcata come default).

Il nome esatto della UserDefinedNetwork non e' mai indicato nel testo estratto
dal PDF (viene creata da console, il campo "Name" non compare nel testo
catturato): per questo lo script NON assume un nome fisso, ma cerca fra tutte
le UserDefinedNetwork del progetto network-udn quella la cui subnet configurata
e' 10.0.0.0/16 (stesso pattern "cerca per caratteristiche" di storage-configs.py).

Uso: non-http-multus.py [progetto-principale] [progetto-udn]
     (default: non-http-multus, network-udn)
"""

import ipaddress
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "non-http-multus"
UDN_PROJECT_DEFAULT = "network-udn"

NAD_NAME = "custom"
NAD_TYPE = "host-device"
NAD_DEVICE = "ens4"
NAD_IPAM_TYPE = "static"
NAD_ADDRESS = "192.168.51.10/24"
NAD_IP = "192.168.51.10"

MULTUS_DEPLOYMENT = "database-multus"
MULTUS_ANNOTATION_KEY = "k8s.v1.cni.cncf.io/networks"
MULTUS_ANNOTATION_VALUE = NAD_NAME

UDN_DEPLOYMENT = "database-udn"
UDN_SUBNET = "10.0.0.0/16"

NETWORK_STATUS_ANNOTATION = "k8s.v1.cni.cncf.io/network-status"


def get_pods_for_deployment(project, deployment):
    """Trova i pod di un deployment tramite le matchLabels del selector,
    piu' affidabile di indovinare un nome-prefisso del ReplicaSet."""
    match_labels = deployment.get("spec", {}).get("selector", {}).get("matchLabels") or {}
    if not match_labels:
        return []
    selector = ",".join(f"{k}={v}" for k, v in match_labels.items())
    pods = oc_get_json("pod", "-n", project, "-l", selector)
    if not pods:
        return []
    return pods.get("items", [])


def parse_network_status(pod):
    """Ritorna la lista decodificata dell'annotazione network-status del pod,
    o [] se assente/non parsabile (l'annotazione e' una stringa JSON, quindi
    va decodificata separatamente dal resto del manifest)."""
    raw = pod.get("metadata", {}).get("annotations", {}).get(NETWORK_STATUS_ANNOTATION)
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def pod_is_running_ready(pod):
    status = pod.get("status", {})
    if status.get("phase") != "Running":
        return False
    statuses = status.get("containerStatuses", []) or []
    return bool(statuses) and all(c.get("ready") for c in statuses)


def ip_in_subnet(ip_str, subnet_str):
    try:
        return ipaddress.ip_address(ip_str) in ipaddress.ip_network(subnet_str)
    except ValueError:
        return False


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    udn_project = sys.argv[2] if len(sys.argv) > 2 else UDN_PROJECT_DEFAULT
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetti: {project}, {udn_project})")

    # --- Parte 1: rete secondaria Multus (host-device) nel progetto principale ---

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    nad = oc_get_json("network-attachment-definition", NAD_NAME, "-n", project)

    with GradingStep(
        f"La NetworkAttachmentDefinition '{NAD_NAME}' esiste ed e' configurata correttamente"
    ) as step:
        if nad is None:
            step.fail(
                f"NetworkAttachmentDefinition '{NAD_NAME}' non trovata nel progetto {project}"
            )
        else:
            try:
                config = json.loads(nad["spec"]["config"])
            except (KeyError, json.JSONDecodeError):
                config = None
            if config is None:
                step.add_error("spec.config non e' un JSON valido")
            else:
                if config.get("type") != NAD_TYPE:
                    step.add_error(
                        f"type deve essere '{NAD_TYPE}' (trovato: {config.get('type')})"
                    )
                if config.get("device") != NAD_DEVICE:
                    step.add_error(
                        f"device deve essere '{NAD_DEVICE}' (trovato: {config.get('device')})"
                    )
                ipam = config.get("ipam", {}) or {}
                if ipam.get("type") != NAD_IPAM_TYPE:
                    step.add_error(
                        f"ipam.type deve essere '{NAD_IPAM_TYPE}' (trovato: {ipam.get('type')})"
                    )
                addresses = ipam.get("addresses", []) or []
                found_addr = any(a.get("address") == NAD_ADDRESS for a in addresses)
                if not found_addr:
                    step.add_error(
                        f"ipam.addresses deve contenere l'indirizzo '{NAD_ADDRESS}' "
                        f"(trovato: {addresses})"
                    )

    multus_dep = oc_get_json("deployment", MULTUS_DEPLOYMENT, "-n", project)

    with GradingStep(f"Il deployment {MULTUS_DEPLOYMENT} esiste") as step:
        if multus_dep is None:
            step.fail(f"Deployment '{MULTUS_DEPLOYMENT}' non trovato nel progetto {project}")

    with GradingStep(
        f"Il deployment {MULTUS_DEPLOYMENT} annota i pod con la rete '{NAD_NAME}'"
    ) as step:
        if multus_dep is None:
            step.fail()
        else:
            annotations = (
                multus_dep.get("spec", {})
                .get("template", {})
                .get("metadata", {})
                .get("annotations")
                or {}
            )
            value = annotations.get(MULTUS_ANNOTATION_KEY)
            if value != MULTUS_ANNOTATION_VALUE:
                step.add_error(
                    f"L'annotazione '{MULTUS_ANNOTATION_KEY}' nel template del pod deve "
                    f"valere '{MULTUS_ANNOTATION_VALUE}' (trovato: {value})"
                )

    with GradingStep(
        f"Il pod di {MULTUS_DEPLOYMENT} e' Running e usa realmente la rete secondaria"
    ) as step:
        if multus_dep is None:
            step.fail()
        else:
            pods = get_pods_for_deployment(project, multus_dep)
            if not pods:
                step.fail(f"Nessun pod trovato per il deployment '{MULTUS_DEPLOYMENT}'")
            else:
                pod = pods[0]
                if not pod_is_running_ready(pod):
                    step.add_error(
                        f"Il pod '{pod.get('metadata', {}).get('name')}' non e' Running/Ready"
                    )
                net_status = parse_network_status(pod)
                match = any(
                    entry.get("name", "").endswith(f"/{NAD_NAME}")
                    and NAD_IP in (entry.get("ips") or [])
                    for entry in net_status
                )
                if not match:
                    step.add_error(
                        f"L'annotazione '{NETWORK_STATUS_ANNOTATION}' non mostra "
                        f"un'interfaccia collegata a '{NAD_NAME}' con IP {NAD_IP} "
                        f"(trovato: {net_status})"
                    )

    # --- Parte 2: User Defined Network nel progetto network-udn ---

    with GradingStep(f"Il progetto {udn_project} esiste") as step:
        if not project_exists(udn_project):
            step.fail(f"Progetto '{udn_project}' non trovato")

    udns = oc_get_json("userdefinednetwork", "-n", udn_project)
    matching_udn = None
    if udns:
        for item in udns.get("items", []):
            # Non c'e' un nome atteso (creata da console): la individuiamo
            # cercando la subnet 10.0.0.0/16 richiesta dalla guida ovunque
            # compaia nello spec (layer2/layer3 secondo la topologia scelta).
            if UDN_SUBNET in json.dumps(item.get("spec", {})):
                matching_udn = item
                break

    with GradingStep(
        f"Esiste una UserDefinedNetwork nel progetto {udn_project} con subnet {UDN_SUBNET}"
    ) as step:
        if not udns or not udns.get("items"):
            step.fail(f"Nessuna UserDefinedNetwork trovata nel progetto {udn_project}")
        elif matching_udn is None:
            step.add_error(
                f"Nessuna UserDefinedNetwork ha la subnet {UDN_SUBNET} richiesta dalla guida"
            )

    with GradingStep(
        "La UserDefinedNetwork ha le condizioni NetworkCreated e NetworkAllocationSucceeded a True"
    ) as step:
        if matching_udn is None:
            step.fail()
        else:
            conditions = matching_udn.get("status", {}).get("conditions", []) or []
            by_type = {
                c.get("type", "").replace(" ", ""): c.get("status") for c in conditions
            }
            for expected in ("NetworkCreated", "NetworkAllocationSucceeded"):
                if by_type.get(expected) != "True":
                    step.add_error(
                        f"Condizione '{expected}' non a True (trovata: {by_type.get(expected)})"
                    )

    udn_dep = oc_get_json("deployment", UDN_DEPLOYMENT, "-n", udn_project)

    with GradingStep(f"Il deployment {UDN_DEPLOYMENT} esiste nel progetto {udn_project}") as step:
        if udn_dep is None:
            step.fail(f"Deployment '{UDN_DEPLOYMENT}' non trovato nel progetto {udn_project}")

    with GradingStep(
        f"Il pod di {UDN_DEPLOYMENT} e' Running e ha un'interfaccia sulla UDN ({UDN_SUBNET})"
    ) as step:
        if udn_dep is None:
            step.fail()
        else:
            pods = get_pods_for_deployment(udn_project, udn_dep)
            if not pods:
                step.fail(f"Nessun pod trovato per il deployment '{UDN_DEPLOYMENT}'")
            else:
                pod = pods[0]
                if not pod_is_running_ready(pod):
                    step.add_error(
                        f"Il pod '{pod.get('metadata', {}).get('name')}' non e' Running/Ready"
                    )
                net_status = parse_network_status(pod)
                match = any(
                    ip_in_subnet(ip, UDN_SUBNET)
                    for entry in net_status
                    for ip in (entry.get("ips") or [])
                )
                if not match:
                    step.add_error(
                        f"Nessuna interfaccia in '{NETWORK_STATUS_ANNOTATION}' ha un IP "
                        f"nella subnet {UDN_SUBNET} (trovato: {net_status})"
                    )


if __name__ == "__main__":
    main()
