#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato non-http-lb (DO280), sprovvisto di
`lab grade` ufficiale (la classe NonHttpLb nel pacchetto do280 implementa
solo start()/finish(); la sezione "Grading tasks" del modulo contiene
letteralmente solo il commento "# none").

Fonti usate (in ordine, come da CLAUDE.md):
- materials/labs/non-http-lb/virtual-rtsp-{1,2,3}.yaml: tre Deployment
  identici a meno di nome/env SOURCE_URL, ciascuno con containerPort 8554.
- materials/solutions/non-http-lb/metallb.yaml: IPAddressPool con range
  192.168.50.20-192.168.50.21 (2 soli indirizzi) usato da start() per
  configurare MetalLB PRIMA dell'esercizio: non e' la soluzione dello
  studente, ma da' il range atteso per gli external-IP.
- Testo guida studente (DO280-RHOCP4.18-en-1-20251205, cap. 5.2): lo
  studente crea, con `oc expose deployment/virtual-rtsp-N --type=LoadBalancer
  --target-port=8554`, un Service LoadBalancer per ciascun deployment.
  Poiche' il pool ha solo 2 indirizzi, lo stato finale descritto (punti 5.1
  e 5.2 della guida) e': il Service virtual-rtsp-1 viene eliminato per
  liberare il suo IP, che viene poi riassegnato al Service virtual-rtsp-3
  (rimasto <pending> finche' l'IP non si libera). Il Deployment
  virtual-rtsp-1 NON viene eliminato in questo punto (solo il suo Service):
  la rimozione di tutti i Deployment/Service/progetto avviene solo al punto
  6 delle istruzioni, subito prima di `lab finish` — quindi questo script va
  eseguito PRIMA di quel cleanup finale, sullo stato raggiunto dopo il
  punto 5.

Uso: non-http-lb.py [nome-progetto]   (default: non-http-lb)
"""

import ipaddress
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "non-http-lb"
EXPECTED_TARGET_PORT = "8554"
METALLB_NAMESPACE = "metallb-system"
# Fallback se non si riesce a leggere l'IPAddressPool dal cluster live (vedi
# materials/solutions/non-http-lb/metallb.yaml, applicato da start() tramite
# metallb.sh): il range e' fisso in quel manifest, non generato a runtime.
FALLBACK_POOL_RANGES = ["192.168.50.20-192.168.50.21"]

DEPLOYMENTS = ["virtual-rtsp-1", "virtual-rtsp-2", "virtual-rtsp-3"]
# Service attesi al termine del punto 5 della guida: solo rtsp-2 e rtsp-3
# devono avere ancora un Service LoadBalancer con IP esterno.
EXPECTED_LB_SERVICES = [
    ("virtual-rtsp-2", "roundabout"),
    ("virtual-rtsp-3", "intersection"),
]


def get_pool_ranges():
    """Legge gli indirizzi configurati nell'IPAddressPool di MetalLB dal
    cluster live; se non disponibile, usa il range noto dal manifest di
    preparazione dell'esercizio."""
    pools = oc_get_json("ipaddresspools.metallb.io", "-n", METALLB_NAMESPACE)
    ranges = []
    if pools:
        for item in pools.get("items", []):
            ranges.extend(item.get("spec", {}).get("addresses", []) or [])
    return ranges or FALLBACK_POOL_RANGES


def ip_in_ranges(ip, ranges):
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for r in ranges:
        r = r.strip()
        try:
            if "-" in r:
                start_s, end_s = r.split("-", 1)
                if ipaddress.ip_address(start_s.strip()) <= addr <= ipaddress.ip_address(end_s.strip()):
                    return True
            elif "/" in r:
                if addr in ipaddress.ip_network(r, strict=False):
                    return True
            elif addr == ipaddress.ip_address(r):
                return True
        except ValueError:
            continue
    return False


def is_ready(deployment):
    status = deployment.get("status", {})
    return status.get("readyReplicas", 0) >= 1


def external_ips(service):
    ingress = service.get("status", {}).get("loadBalancer", {}).get("ingress", []) or []
    return [i.get("ip") for i in ingress if i.get("ip")]


def has_target_port(service, port=EXPECTED_TARGET_PORT):
    for p in service.get("spec", {}).get("ports", []) or []:
        if str(p.get("targetPort")) == str(port):
            return True
    return False


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    pool_ranges = get_pool_ranges()

    for name in DEPLOYMENTS:
        with GradingStep(f"Il deployment {name} esiste ed e' pronto") as step:
            dep = oc_get_json("deployment", name, "-n", project)
            if dep is None:
                step.fail(f"Deployment '{name}' non trovato nel progetto")
            elif not is_ready(dep):
                step.add_error(
                    f"Nessuna replica pronta per il deployment '{name}' "
                    "(atteso 1/1 Ready)"
                )

    with GradingStep(
        "Il Service virtual-rtsp-1 e' stato eliminato per liberare l'IP "
        "(punto 5.1 della guida)"
    ) as step:
        svc1 = oc_get_json("service", "virtual-rtsp-1", "-n", project)
        if svc1 is not None:
            step.add_error(
                "Il Service 'virtual-rtsp-1' esiste ancora: va eliminato con "
                "'oc delete service/virtual-rtsp-1' per liberare l'IP e "
                "permettere l'assegnazione a virtual-rtsp-3"
            )

    for name, camera in EXPECTED_LB_SERVICES:
        with GradingStep(
            f"Il Service {name} (fotocamera {camera}) e' un LoadBalancer "
            f"su porta {EXPECTED_TARGET_PORT} con IP esterno da MetalLB"
        ) as step:
            svc = oc_get_json("service", name, "-n", project)
            if svc is None:
                step.fail(f"Service '{name}' non trovato nel progetto")
                continue
            if svc.get("spec", {}).get("type") != "LoadBalancer":
                step.add_error(
                    f"Il Service '{name}' non e' di tipo LoadBalancer "
                    f"(trovato: {svc.get('spec', {}).get('type')})"
                )
            if not has_target_port(svc):
                step.add_error(
                    f"Il Service '{name}' non espone la targetPort "
                    f"{EXPECTED_TARGET_PORT}"
                )
            selector = svc.get("spec", {}).get("selector") or {}
            if selector.get("app") != name:
                step.add_error(
                    f"Il selector del Service '{name}' non seleziona i pod "
                    f"del deployment '{name}' (selector: {selector})"
                )
            ips = external_ips(svc)
            if not ips:
                step.add_error(
                    f"Il Service '{name}' non ha ancora un external-IP "
                    "assegnato (status.loadBalancer.ingress vuoto)"
                )
            elif not any(ip_in_ranges(ip, pool_ranges) for ip in ips):
                step.add_error(
                    f"L'external-IP di '{name}' ({', '.join(ips)}) non "
                    f"rientra nel pool MetalLB configurato ({pool_ranges})"
                )


if __name__ == "__main__":
    main()
