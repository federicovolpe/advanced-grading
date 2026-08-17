#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato observability-customize (DO432,
Cap. 4.4 "Customize the RHACM Observability Stack"), sprovvisto di
`lab grade` ufficiale. Il file del modulo ufficiale nel pacchetto do0014l si
chiama `obervability-customize.py` (TYPO nel nome del file, manca una "s"),
ma la classe ha `__LAB__ = "observability-customize"` (ortografia corretta,
verificato via grep): questo script si chiama quindi
`observability-customize.py`, come vuole `lab grade` (che usa __LAB__, non
il nome del modulo Python).

Specifica ricavata da materials/labs/observability-customize/
(custom-rules.yaml, platform-recording.yaml — nessuna materials/solutions
per questo esercizio, ma i due file di partenza contengono già i valori
finali, senza placeholder CHANGE_ME) e confermata dal testo della guida
studente (DO432-RHACM2.13-en-2, Cap. 4.4, pag. 264-268).

start() abilita già tutta la stack di observability (a differenza di
4.2/observability-enable, qui lo studente non la crea da zero): il compito
è creare due ConfigMap in open-cluster-management-observability (hub
cluster) — una regola di allerta custom e una recording rule custom.

**Check "sul momento"**: il testo della guida (punto 5, pag. 268) chiede
esplicitamente di cancellare l'oggetto MultiClusterObservability e il
namespace open-cluster-management-observability PRIMA di `lab finish`
(pulizia della stack, non delle sole ConfigMap create in questo esercizio).
Questo script è quindi valido solo mentre l'esercizio è in corso: dopo
quella cancellazione (e dopo lab finish) è corretto che il namespace non
esista più e che il grading risulti FAIL — non è un bug dello script (vedi
CLAUDE.md sez. 2, stesso pattern di pods-containers in DO180).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json_hub

LAB_NAME = "observability-customize"
NAMESPACE = "open-cluster-management-observability"


def _configmap_yaml_key(cm, key):
    return (cm or {}).get("data", {}).get(key, "")


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    with GradingStep(f"Il namespace {NAMESPACE} esiste sull'hub cluster") as step:
        if not oc_get_json_hub("namespace", NAMESPACE):
            step.fail(
                f"Namespace '{NAMESPACE}' non trovato: normale dopo il punto 5 "
                "della guida (cancellazione della stack) o dopo 'lab finish'"
            )

    with GradingStep("La ConfigMap thanos-ruler-custom-rules contiene la regola di allerta custom") as step:
        cm = oc_get_json_hub("configmap", "thanos-ruler-custom-rules", "-n", NAMESPACE)
        if not cm:
            step.fail("ConfigMap 'thanos-ruler-custom-rules' non trovata")
        else:
            rules = _configmap_yaml_key(cm, "custom_rules.yaml")
            if "ClusterCPUReq-60" not in rules:
                step.add_error("l'alerting rule 'ClusterCPUReq-60' non e' presente in custom_rules.yaml")
            if "severity: critical" not in rules:
                step.add_error("manca 'severity: critical' nella regola")
            if "kube_pod_container_resource_requests" not in rules:
                step.add_error("l'expr della regola non corrisponde a quella richiesta dalla guida")

    with GradingStep("La ConfigMap observability-metrics-custom-allowlist contiene la recording rule custom") as step:
        cm = oc_get_json_hub("configmap", "observability-metrics-custom-allowlist", "-n", NAMESPACE)
        if not cm:
            step.fail("ConfigMap 'observability-metrics-custom-allowlist' non trovata")
        else:
            metrics = _configmap_yaml_key(cm, "metrics_list.yaml")
            if "apiserver_request_duration_seconds:histogram_quantile_90" not in metrics:
                step.add_error(
                    "il record 'apiserver_request_duration_seconds:histogram_quantile_90' "
                    "non e' presente in metrics_list.yaml"
                )
            if "histogram_quantile(0.90" not in metrics:
                step.add_error("l'expr della recording rule non corrisponde a quella richiesta dalla guida")


if __name__ == "__main__":
    main()
