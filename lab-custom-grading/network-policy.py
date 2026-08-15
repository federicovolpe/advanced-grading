#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato network-policy (DO280), sprovvisto
di `lab grade` ufficiale (la classe NetworkPolicy nel pacchetto do280
implementa solo start()/finish(), non grade()).

Specifica dedotta confrontando materials/labs/network-policy/*.yaml (con i
placeholder CHANGE_ME) e materials/solutions/network-policy/*.yaml (diff =
spec), oltre al testo della guida studente (fornito dall'utente) per i nomi
di deployment/route/namespace creati imperativamente (non presenti in alcun
manifest): hello e test in network-policy, sample-app in different-namespace,
route "hello" verso il service "hello", e la label network=different-namespace
sul namespace different-namespace (applicata dall'utente admin al passo 9,
necessaria perche' allow-specific funzioni davvero).

L'esercizio usa DUE progetti (vedi start()/finish() in do280/network-policy.py):
"network-policy" (progetto principale) e "different-namespace" (usato per
dimostrare che l'isolamento funziona tra namespace).

Verifica principale: le tre NetworkPolicy richieste esistono nel progetto
network-policy con lo spec atteso (podSelector, ingress.from, ports).
Verifica secondaria (best-effort, non invasiva): esistenza del progetto/
namespace different-namespace, della sua label, e dei deployment/route usati
come bersaglio delle policy. Non viene fatto alcun test di connettivita' reale
(richiederebbe creare pod di test, troppo fragile/invasivo per un semplice
grading) - vedi Nota nel README di questo repo sullo stile dei check "black
box" solo quando non ci sono altre fonti oggettive.

Uso: network-policy.py [progetto-principale] [progetto-secondario]
     (default: network-policy, different-namespace)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "network-policy"
OTHER_PROJECT = "different-namespace"


def match_labels_selector(selector, expected_labels):
    """True se 'selector' (un podSelector/namespaceSelector) ha un matchLabels
    che contiene (almeno) tutte le coppie chiave/valore attese."""
    if not isinstance(selector, dict):
        return False
    match_labels = selector.get("matchLabels") or {}
    return all(match_labels.get(k) == v for k, v in expected_labels.items())


def find_ingress_rule(ingress_rules, ns_labels=None, pod_labels=None, port=None, protocol=None):
    """Cerca, tra le regole 'ingress' di una NetworkPolicy, una entry 'from'
    che soddisfi i selector richiesti e (se richiesta) porta/protocollo nella
    stessa regola. Ritorna la regola (dict) trovata, o None."""
    for rule in ingress_rules or []:
        for frm in rule.get("from", []) or []:
            if ns_labels is not None and not match_labels_selector(
                frm.get("namespaceSelector"), ns_labels
            ):
                continue
            if pod_labels is not None and not match_labels_selector(
                frm.get("podSelector"), pod_labels
            ):
                continue
            if port is not None:
                ports = rule.get("ports") or []
                if not any(
                    str(p.get("port")) == str(port)
                    and p.get("protocol", "TCP") == protocol
                    for p in ports
                ):
                    continue
            return rule
    return None


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    other_project = sys.argv[2] if len(sys.argv) > 2 else OTHER_PROJECT
    print(
        f"🔧 Grading personalizzato per '{LAB_NAME}' "
        f"(progetti: {project}, {other_project})"
    )

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(
        f"Il progetto {other_project} esiste "
        "(usato per verificare l'isolamento tra namespace)"
    ) as step:
        if not project_exists(other_project):
            step.fail(f"Progetto '{other_project}' non trovato")

    namespace = oc_get_json("namespace", other_project)
    with GradingStep(
        f"Il namespace {other_project} ha la label network={other_project}"
    ) as step:
        if namespace is None:
            step.fail(f"Impossibile leggere il namespace '{other_project}'")
        else:
            labels = namespace.get("metadata", {}).get("labels", {}) or {}
            if labels.get("network") != other_project:
                step.add_error(
                    f"Label 'network={other_project}' assente sul namespace "
                    f"(va applicata dall'utente admin con 'oc label namespace "
                    f"{other_project} network={other_project}': senza questa "
                    "label la NetworkPolicy allow-specific non riconosce il "
                    "namespace e il traffico da sample-app resta bloccato)"
                )

    # I deployment/route sotto sono creati imperativamente (nessun manifest),
    # nomi presi dal testo della guida studente: hello/test in network-policy,
    # sample-app in different-namespace, route "hello" -> service "hello".
    with GradingStep(
        "I deployment 'hello' e 'test' esistono nel progetto network-policy"
    ) as step:
        for name in ("hello", "test"):
            if oc_get_json("deployment", name, "-n", project) is None:
                step.add_error(f"Deployment '{name}' non trovato in {project}")

    with GradingStep(
        f"Il deployment 'sample-app' esiste nel progetto {other_project}"
    ) as step:
        if oc_get_json("deployment", "sample-app", "-n", other_project) is None:
            step.add_error(f"Deployment 'sample-app' non trovato in {other_project}")

    routes = oc_get_json("route", "-n", project)
    with GradingStep("Una Route espone il deployment hello (via il service hello)") as step:
        found = False
        if routes:
            for route in routes.get("items", []):
                if route.get("spec", {}).get("to", {}).get("name") == "hello":
                    found = True
                    break
        if not found:
            step.add_error(
                f"Nessuna Route punta al service 'hello' nel progetto {project} "
                "(atteso da 'oc expose service hello')"
            )

    # --- Le tre NetworkPolicy richieste dall'esercizio ---

    deny_all = oc_get_json("networkpolicy", "deny-all", "-n", project)
    with GradingStep(
        "La NetworkPolicy 'deny-all' nega tutto il traffico in ingresso ai pod"
    ) as step:
        if deny_all is None:
            step.fail(f"NetworkPolicy 'deny-all' non trovata in {project}")
        else:
            spec = deny_all.get("spec", {})
            pod_selector = spec.get("podSelector")
            if pod_selector != {}:
                step.add_error(
                    "podSelector deve essere vuoto ({}) per selezionare tutti "
                    f"i pod del progetto (trovato: {pod_selector})"
                )
            if spec.get("ingress"):
                step.add_error(
                    "La policy non deve definire regole 'ingress': "
                    "un deny-all valido nega tutto senza eccezioni"
                )

    allow_specific = oc_get_json("networkpolicy", "allow-specific", "-n", project)
    with GradingStep(
        "La NetworkPolicy 'allow-specific' consente il traffico da "
        f"sample-app ({other_project}) verso hello su TCP/8080"
    ) as step:
        if allow_specific is None:
            step.fail(f"NetworkPolicy 'allow-specific' non trovata in {project}")
        else:
            spec = allow_specific.get("spec", {})
            if not match_labels_selector(
                spec.get("podSelector"), {"deployment": "hello"}
            ):
                step.add_error(
                    "podSelector deve selezionare i pod con label "
                    "'deployment=hello' (trovato: "
                    f"{spec.get('podSelector')})"
                )
            rule = find_ingress_rule(
                spec.get("ingress"),
                ns_labels={"network": other_project},
                pod_labels={"deployment": "sample-app"},
                port=8080,
                protocol="TCP",
            )
            if rule is None:
                step.add_error(
                    "Nessuna regola 'ingress' consente traffico TCP/8080 da "
                    f"pod con label 'deployment=sample-app' nel namespace con "
                    f"label 'network={other_project}' (trovato: "
                    f"{spec.get('ingress')})"
                )

    allow_ingress = oc_get_json(
        "networkpolicy", "allow-from-openshift-ingress", "-n", project
    )
    with GradingStep(
        "La NetworkPolicy 'allow-from-openshift-ingress' consente il "
        "traffico dal router (ingress) verso hello"
    ) as step:
        if allow_ingress is None:
            step.fail(
                f"NetworkPolicy 'allow-from-openshift-ingress' non trovata "
                f"in {project}"
            )
        else:
            spec = allow_ingress.get("spec", {})
            if not match_labels_selector(
                spec.get("podSelector"), {"deployment": "hello"}
            ):
                step.add_error(
                    "podSelector deve selezionare i pod con label "
                    f"'deployment=hello' (trovato: {spec.get('podSelector')})"
                )
            rule = find_ingress_rule(
                spec.get("ingress"),
                ns_labels={"policy-group.network.openshift.io/ingress": ""},
            )
            if rule is None:
                step.add_error(
                    "Nessuna regola 'ingress' consente traffico da un "
                    "namespace con label "
                    "'policy-group.network.openshift.io/ingress=\"\"' "
                    f"(il namespace del router openshift-ingress; trovato: "
                    f"{spec.get('ingress')})"
                )


if __name__ == "__main__":
    main()
