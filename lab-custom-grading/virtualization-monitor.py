#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato virtualization-monitor (DO432, Cap.
6.8), sprovvisto di `lab grade` ufficiale (do0016l/virtualization-monitor.py
implementa solo start()/finish()).

L'intera guided exercise (Cap. 6.8) e' quasi tutta esplorazione read-only
delle dashboard Grafana di RHACM (Clusters Overview, Single Cluster View,
Virtual Machine Inventory, ecc.) su dati/VM create automaticamente da
start() (fedora-hub e rhel9-hub in sandbox-local-cluster; fedora-mng,
rhel9-mng, centos10-mng in sandbox-managed-cluster — vedi la tabella nella
guida e l'ApplicationSet "virtualization-monitor" applicato da start()
tramite materials/labs/virtualization-monitor/virtmon-appset.yaml). Nessuna
di queste VM preesistenti va gradata: sono precondizioni, non compiti dello
studente.

L'UNICA azione richiesta allo studente (punti 5.6/5.8 della guida) e':
avviare la VM "fedora-hub" (che parte Stopped) dalla console RHACM, cosi'
che la dashboard "Single Virtual Machine View" la mostri Running. Il punto
7.3 conferma lo stato finale atteso: "the dashboard displays a table with
the fedora-hub VM and the rhel9-hub VM. Both VMs show the running status."
Verifichiamo quindi solo questo: la VM fedora-hub in sandbox-local-cluster
sul cluster hub deve essere Running.

Check "sul momento": valido solo prima di `lab finish virtualization-monitor`
(finish() cancella l'ApplicationSet e i progetti sandbox-*).

Uso: virtualization-monitor.py   (nessun progetto: la VM vive in
sandbox-local-cluster sul cluster hub)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import oc_get_json_kc, HUB_KUBECONFIG, GradingStep

NAMESPACE = "sandbox-local-cluster"
VM_NAME = "fedora-hub"


def main():
    print(f"🔧 Grading personalizzato per 'virtualization-monitor'")

    with GradingStep(f"VM '{VM_NAME}' avviata (Running) sul cluster hub") as step:
        vm = oc_get_json_kc(HUB_KUBECONFIG, "vm", VM_NAME, "-n", NAMESPACE)
        if vm is None:
            step.fail(f"VM '{VM_NAME}' non trovata in {NAMESPACE} (hub)")
        elif vm.get("status", {}).get("printableStatus") != "Running":
            step.add_error(
                f"Stato atteso 'Running', trovato "
                f"'{vm.get('status', {}).get('printableStatus')}' "
                "(avviala da Infrastructure > Virtual machines nella console RHACM)"
            )


if __name__ == "__main__":
    main()
