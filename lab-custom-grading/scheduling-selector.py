#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato scheduling-selector (DO380, Cap. 3.5
"Configure Node Selectors and Taints"), sprovvisto di `lab grade` ufficiale
(la classe SchedulingSelector implementa solo start()/finish()).

Specifica ricavata dal testo integrale della guida ufficiale (pag. 229-238)
incrociato con il diff labs/solutions in materials/solutions/scheduling-
selector/. Le etichette rack/cpu sui nodi worker01/02/03 sono applicate da
start() (preesistenti, non gradate). Lo studente crea:
- nel progetto "scheduling-selector": i deployment "myapp" (2 repliche,
  nessun selettore) e "myapp-ns-fastcpu" (2 repliche, nodeSelector
  cpu=fast);
- il progetto "scheduling-ns" (annotazione node-selector cpu=standard,
  ruolo edit per developer) con i deployment "project-ns" (2 repliche) e
  "project-podsel" (2 repliche, nodeSelector rack=1);
- il taint type=mission-critical:NoSchedule su worker01 e worker03 (check
  "sul momento": finish() lo rimuove, quindi e' corretto che torni FAIL
  dopo `lab finish`, vedi CLAUDE.md sez.2);
- il progetto "scheduling-taint" con il deployment "myapp-taint-fastcpu"
  (2 repliche, nodeSelector cpu=fast, toleration type=mission-critical
  Equal NoSchedule) — l'ultima versione applicata deve avere la
  toleration e risultare Available (la guida fa cancellare e ricreare
  questo deployment, la prima versione senza toleration viene rimossa).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "scheduling-selector"
NS_PROJECT = "scheduling-ns"
TAINT_PROJECT = "scheduling-taint"
TAINTED_NODES = ["worker01", "worker03"]
EXPECTED_TAINT = {"key": "type", "value": "mission-critical", "effect": "NoSchedule"}


def deployment_ready(project, name, replicas=2):
    dep = oc_get_json("deployment", name, "-n", project)
    if dep is None:
        return None, f"Deployment '{name}' non trovato nel progetto {project}"
    status = dep.get("status", {})
    if status.get("readyReplicas", 0) < replicas:
        return dep, (
            f"Deployment '{name}' non ha {replicas} repliche pronte "
            f"(readyReplicas={status.get('readyReplicas', 0)})"
        )
    return dep, None


def has_node_selector(dep, key, value):
    selector = dep.get("spec", {}).get("template", {}).get("spec", {}).get("nodeSelector", {})
    return selector.get(key) == value


def has_toleration(dep, expected):
    tolerations = dep.get("spec", {}).get("template", {}).get("spec", {}).get("tolerations", [])
    return any(
        t.get("key") == expected["key"]
        and t.get("value") == expected["value"]
        and t.get("effect") == expected["effect"]
        for t in tolerations
    )


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(f"Deployment 'myapp' pronto nel progetto {project}") as step:
        _, err = deployment_ready(project, "myapp")
        if err:
            step.add_error(err)

    with GradingStep(f"Deployment 'myapp-ns-fastcpu' con nodeSelector cpu=fast pronto") as step:
        dep, err = deployment_ready(project, "myapp-ns-fastcpu")
        if err:
            step.add_error(err)
        elif dep and not has_node_selector(dep, "cpu", "fast"):
            step.add_error("Il deployment 'myapp-ns-fastcpu' non ha nodeSelector cpu=fast")

    ns = oc_get_json("namespace", NS_PROJECT)
    with GradingStep(f"Il progetto {NS_PROJECT} esiste con il node selector cpu=standard") as step:
        if ns is None:
            step.fail(f"Progetto '{NS_PROJECT}' non trovato")
        else:
            annotation = ns.get("metadata", {}).get("annotations", {}).get(
                "openshift.io/node-selector"
            )
            if annotation != "cpu=standard":
                step.add_error(
                    f"Annotazione 'openshift.io/node-selector' attesa 'cpu=standard' "
                    f"(trovata: {annotation})"
                )

    with GradingStep(f"Deployment 'project-ns' pronto nel progetto {NS_PROJECT}") as step:
        _, err = deployment_ready(NS_PROJECT, "project-ns")
        if err:
            step.add_error(err)

    with GradingStep(f"Deployment 'project-podsel' con nodeSelector rack=1 pronto") as step:
        dep, err = deployment_ready(NS_PROJECT, "project-podsel")
        if err:
            step.add_error(err)
        elif dep and not has_node_selector(dep, "rack", "1"):
            step.add_error("Il deployment 'project-podsel' non ha nodeSelector rack=1")

    with GradingStep(
        "I nodi worker01 e worker03 hanno il taint type=mission-critical:NoSchedule"
    ) as step:
        for node_name in TAINTED_NODES:
            node = oc_get_json("node", node_name)
            if node is None:
                step.add_error(f"Nodo '{node_name}' non trovato")
                continue
            taints = node.get("spec", {}).get("taints", []) or []
            if not any(
                t.get("key") == EXPECTED_TAINT["key"]
                and t.get("value") == EXPECTED_TAINT["value"]
                and t.get("effect") == EXPECTED_TAINT["effect"]
                for t in taints
            ):
                step.add_error(f"Taint 'type=mission-critical:NoSchedule' assente su {node_name}")

    with GradingStep(f"Il progetto {TAINT_PROJECT} esiste") as step:
        if not project_exists(TAINT_PROJECT):
            step.fail(f"Progetto '{TAINT_PROJECT}' non trovato")

    with GradingStep(
        "Deployment 'myapp-taint-fastcpu' con nodeSelector e toleration corretti, pronto"
    ) as step:
        dep, err = deployment_ready(TAINT_PROJECT, "myapp-taint-fastcpu")
        if err:
            step.add_error(err)
        elif dep:
            if not has_node_selector(dep, "cpu", "fast"):
                step.add_error("Il deployment 'myapp-taint-fastcpu' non ha nodeSelector cpu=fast")
            if not has_toleration(dep, EXPECTED_TAINT):
                step.add_error(
                    "Il deployment 'myapp-taint-fastcpu' non ha la toleration "
                    "type=mission-critical:NoSchedule"
                )


if __name__ == "__main__":
    main()
