#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato policies-troubleshoot (DO432/do0013l,
Cap. 3.12 "Troubleshoot Governance Issues"), sprovvisto di `lab grade`
ufficiale.

Fonte della specifica: testo della guida (Cap. 3.12) incrociato con i
manifest applicati da start() in materials/labs/policies-troubleshoot/*.yaml
(nessun materials/solutions per questo esercizio, e' un troubleshooting: la
"soluzione" e' il fix, non un file). start() applica deliberatamente una
configurazione ROTTA:

- Placement "production-scan-placement" (namespace policies-troubleshoot)
  con spec.clusterSets: [default] invece di [production-clusters]
  (placement.yaml).
- ManagedClusterSet "production-clusters" di tipo ExclusiveClusterSetLabel
  (production-clusterset.yaml) SENZA alcun membro: nessuno step di start()
  etichetta managed-cluster con il clusterset "production-clusters".

La guida chiede di correggere entrambi i problemi: impostare
clusterSets: [production-clusters] sul Placement, e assegnare
managed-cluster al cluster set production-clusters (dalla console, tramite
"Manage resource assignments" -> label
cluster.open-cluster-management.io/clusterset sul ManagedCluster). Il
risultato finale atteso (guida, passo 6.2) e' che la policy production-scan
riporti UNA violazione per il cluster managed-cluster (una scansione CIS
reale ha quasi certamente controlli falliti: la violazione e' il segnale di
successo, non di fallimento) e NESSUN'ALTRA voce di stato (in particolare
non local-cluster, che il placement rotto includeva erroneamente).

Uso: policies-troubleshoot.py [nome-progetto] (default: policies-troubleshoot)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "policies-troubleshoot"
PLACEMENT_NAME = "production-scan-placement"
POLICY_NAME = "production-scan"
CLUSTERSET_NAME = "production-clusters"
EXPECTED_CLUSTER = "managed-cluster"


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(
        f"Il Placement '{PLACEMENT_NAME}' usa il cluster set '{CLUSTERSET_NAME}' "
        "(non 'default')"
    ) as step:
        placement = oc_get_json("placement", PLACEMENT_NAME, "-n", project)
        if placement is None:
            step.fail(f"Placement '{PLACEMENT_NAME}' non trovato")
        else:
            cluster_sets = placement.get("spec", {}).get("clusterSets", [])
            if cluster_sets != [CLUSTERSET_NAME]:
                step.add_error(
                    f"spec.clusterSets e' {cluster_sets} (atteso: ['{CLUSTERSET_NAME}']): "
                    "il bug del passo 2.4 della guida non e' stato corretto"
                )

    with GradingStep(
        f"Il ManagedClusterSet '{CLUSTERSET_NAME}' contiene solo '{EXPECTED_CLUSTER}'"
    ) as step:
        clusterset = oc_get_json("managedclusterset", CLUSTERSET_NAME)
        if clusterset is None:
            step.fail(f"ManagedClusterSet '{CLUSTERSET_NAME}' non trovato")
        else:
            clusters = oc_get_json("managedcluster")
            members = [
                c["metadata"]["name"]
                for c in (clusters or {}).get("items", [])
                if c.get("metadata", {}).get("labels", {}).get(
                    "cluster.open-cluster-management.io/clusterset"
                )
                == CLUSTERSET_NAME
            ]
            if members != [EXPECTED_CLUSTER]:
                step.add_error(
                    f"I membri di '{CLUSTERSET_NAME}' sono {members} "
                    f"(atteso solo ['{EXPECTED_CLUSTER}']): passo 5 della guida "
                    "(assegnazione del cluster al cluster set) non completato/corretto"
                )

    with GradingStep(
        f"La Policy '{POLICY_NAME}' e' applicata solo a '{EXPECTED_CLUSTER}'"
    ) as step:
        policy = oc_get_json("policy", POLICY_NAME, "-n", project)
        if policy is None:
            step.fail(f"Policy '{POLICY_NAME}' non trovata nel namespace '{project}'")
        else:
            per_cluster = policy.get("status", {}).get("status", []) or []
            cluster_names = sorted(c.get("clustername") for c in per_cluster)
            if cluster_names != [EXPECTED_CLUSTER]:
                step.add_error(
                    f"La policy risulta applicata a {cluster_names} "
                    f"(atteso solo ['{EXPECTED_CLUSTER}']): il placement non e' ancora "
                    "correttamente ristretto, oppure RHACM non ha ancora "
                    "ripropagato lo stato (attendere qualche minuto)"
                )


if __name__ == "__main__":
    main()
