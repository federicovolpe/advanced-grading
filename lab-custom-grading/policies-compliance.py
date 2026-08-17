#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato policies-compliance (DO432/do0013l,
Cap. 3.8 "Deploy and Configure the Compliance Operator for Multiple Clusters
by Using RHACM"), sprovvisto di `lab grade` ufficiale.

Fonte della specifica: testo della guida (Cap. 3.8) incrociato con il diff
materials/labs vs materials/solutions/policies-compliance/policy-compliance-
operator-e8-scan.yaml (2 sole differenze: remediationAction inform->enforce
e il matchLabels del PlacementRule) e con policies-compliance.py
(finish() rimuove esplicitamente il ManagedClusterSet "apac" e riporta
managed-cluster sul clusterset "default": e' quindi lo studente, non
start(), a creare il cluster set "apac").

La guida chiede di:
1. Creare il progetto policies-compliance sul hub.
2. Creare un ManagedClusterSet "apac", assegnargli managed-cluster, e
   bindarlo al namespace policies-compliance.
3. Creare (da console) la Policy "policy-complianceoperator" per installare
   il Compliance Operator sui cluster del set apac, poi passarla a Enforce
   (la guida conferma esplicitamente che a quel punto diventa Compliant).
5. Creare (da CLI, con `oc create -f policy-compliance-operator-e8-scan.yaml
   -n policies-compliance`) la Policy "policy-e8-scan", editata per avere
   remediationAction: enforce e il PlacementRule "placement-policy-e8-scan"
   con clusterSelector su clusterset: apac.

Il "Compliance-suite-e8-result" della policy-e8-scan mostra sempre una
violazione per costruzione (usa mustnothave su eventuali ComplianceCheckResult
FAIL, e un cluster reale ha quasi certamente controlli E8 falliti): non
verifichiamo quindi lo stato Compliant complessivo di policy-e8-scan, solo
la sua configurazione (remediationAction/placement), come da guida.

Uso: policies-compliance.py [nome-progetto]  (default: policies-compliance)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "policies-compliance"
CLUSTERSET_NAME = "apac"
MANAGED_CLUSTER = "managed-cluster"
OPERATOR_POLICY = "policy-complianceoperator"
E8_POLICY = "policy-e8-scan"
E8_PLACEMENTRULE = "placement-policy-e8-scan"


def is_policy_compliant(policy):
    status = policy.get("status", {}) or {}
    if "compliant" in status:
        return status.get("compliant") == "Compliant"
    per_cluster = status.get("status", []) or []
    if not per_cluster:
        return None
    return all(c.get("compliant") == "Compliant" for c in per_cluster)


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(
        f"Il ManagedClusterSet '{CLUSTERSET_NAME}' esiste e contiene '{MANAGED_CLUSTER}'"
    ) as step:
        clusterset = oc_get_json("managedclusterset", CLUSTERSET_NAME)
        if clusterset is None:
            step.fail(f"ManagedClusterSet '{CLUSTERSET_NAME}' non trovato")
        else:
            cluster = oc_get_json("managedcluster", MANAGED_CLUSTER)
            label = (cluster or {}).get("metadata", {}).get("labels", {}).get(
                "cluster.open-cluster-management.io/clusterset"
            )
            if label != CLUSTERSET_NAME:
                step.add_error(
                    f"'{MANAGED_CLUSTER}' non risulta assegnato al clusterset "
                    f"'{CLUSTERSET_NAME}' (label attuale: {label!r})"
                )

    with GradingStep(
        f"Il namespace {project} e' associato al clusterset '{CLUSTERSET_NAME}'"
    ) as step:
        bindings = oc_get_json("managedclustersetbinding", "-n", project)
        if not bindings or not any(
            b.get("spec", {}).get("clusterSet") == CLUSTERSET_NAME
            for b in bindings.get("items", [])
        ):
            step.add_error(
                f"Nessuna ManagedClusterSetBinding verso '{CLUSTERSET_NAME}' "
                f"nel namespace '{project}'"
            )

    op_policy = oc_get_json("policy", OPERATOR_POLICY, "-n", project)

    with GradingStep(
        f"La Policy '{OPERATOR_POLICY}' e' impostata su enforce ed e' Compliant"
    ) as step:
        if op_policy is None:
            step.fail(f"Policy '{OPERATOR_POLICY}' non trovata nel namespace '{project}'")
        else:
            action = op_policy.get("spec", {}).get("remediationAction")
            if action != "enforce":
                step.add_error(
                    f"remediationAction e' '{action}' (atteso 'enforce': la guida "
                    "chiede di passare la policy da Inform a Enforce dalla console)"
                )
            compliant = is_policy_compliant(op_policy)
            if compliant is False:
                step.add_error(
                    "La policy non e' Compliant: il Compliance Operator non risulta "
                    f"installato su tutti i cluster del set '{CLUSTERSET_NAME}'"
                )
            elif compliant is None:
                step.add_error("Nessuno stato di compliance ancora riportato dalla policy")

    e8_policy = oc_get_json("policy", E8_POLICY, "-n", project)

    with GradingStep(f"La Policy '{E8_POLICY}' e' impostata su enforce") as step:
        if e8_policy is None:
            step.fail(f"Policy '{E8_POLICY}' non trovata nel namespace '{project}'")
        elif e8_policy.get("spec", {}).get("remediationAction") != "enforce":
            step.add_error(
                f"remediationAction e' '{e8_policy.get('spec', {}).get('remediationAction')}' "
                "(atteso 'enforce', vedi passo 5.2 della guida)"
            )

    with GradingStep(
        f"Il PlacementRule '{E8_PLACEMENTRULE}' seleziona il clusterset '{CLUSTERSET_NAME}'"
    ) as step:
        placementrule = oc_get_json("placementrule", E8_PLACEMENTRULE, "-n", project)
        if placementrule is None:
            step.fail(f"PlacementRule '{E8_PLACEMENTRULE}' non trovato")
        else:
            match_labels = (
                placementrule.get("spec", {})
                .get("clusterSelector", {})
                .get("matchLabels", {})
            )
            if match_labels.get("cluster.open-cluster-management.io/clusterset") != CLUSTERSET_NAME:
                step.add_error(
                    f"clusterSelector.matchLabels non seleziona il clusterset "
                    f"'{CLUSTERSET_NAME}' (trovato: {match_labels})"
                )


if __name__ == "__main__":
    main()
