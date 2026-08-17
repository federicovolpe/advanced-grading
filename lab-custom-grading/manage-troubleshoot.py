#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato manage-troubleshoot (DO432, GE 2.8
"Troubleshoot Common Import Issues for Managed Clusters"), sprovvisto di
`lab grade` ufficiale (la classe ManageTroubleshoot nel pacchetto do0012l
implementa solo start()/finish()).

La guida (testo ufficiale, pagine 106-110) parte da un managed cluster con
residui di un precedente hub RHACM "decommissioned" (klusterlet e CRD
open-cluster-management.io preesistenti, applicati da start() via
apply_lab_yaml, vedi materials/labs/manage-troubleshoot/lab-start/*.yaml):
il primo tentativo di import fallisce con "AlreadyExists" sulla CRD
klusterlets.operator.open-cluster-management.io. Lo studente deve pulire
manualmente il managed cluster (cancellare klusterlet, i due namespace
open-cluster-management-agent[-addon], le CRD open-cluster-management.io) e
poi rieseguire il comando di import copiato dalla web console.

A differenza di manage-lifecycle (altro esercizio di import/detach di questo
capitolo, ma con un giro completo che detacha il cluster prima di finish),
qui la guida NON prevede alcun detach finale: il risultato voluto e
persistente e' un import riuscito. Il segnale oggettivo e' quindi la stessa
condizione che il modulo ufficiale rht_labs_acm.rhacm.rhacm_import_managed_cluster_steps()
attende dopo l'import: la risorsa ManagedCluster/managed-cluster sul hub con
le condition "ManagedClusterJoined" e "ManagedClusterConditionAvailable"
entrambe a True.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json_hub, project_exists_hub, condition_true

LAB_NAME = "manage-troubleshoot"
MANAGED_CLUSTER_NAME = "managed-cluster"
REQUIRED_CONDITIONS = ["ManagedClusterJoined", "ManagedClusterConditionAvailable"]


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (hub cluster)")

    with GradingStep(f"Il progetto {MANAGED_CLUSTER_NAME} esiste sul hub cluster") as step:
        if not project_exists_hub(MANAGED_CLUSTER_NAME):
            step.fail(f"Progetto '{MANAGED_CLUSTER_NAME}' non trovato sul hub cluster")

    managed_cluster = oc_get_json_hub("ManagedCluster", MANAGED_CLUSTER_NAME)

    with GradingStep(f"La risorsa ManagedCluster/{MANAGED_CLUSTER_NAME} esiste") as step:
        if managed_cluster is None:
            step.fail(
                f"ManagedCluster '{MANAGED_CLUSTER_NAME}' non trovata: il cluster "
                "non e' stato (ri)importato in RHACM"
            )

    for condition in REQUIRED_CONDITIONS:
        with GradingStep(f"La condition {condition} e' True") as step:
            if managed_cluster is None:
                step.fail()
            elif not condition_true(managed_cluster, condition):
                step.add_error(
                    f"La condition '{condition}' non e' True: l'import non e' "
                    "completo (klusterlet o CRD residue non rimosse correttamente?)"
                )


if __name__ == "__main__":
    main()
