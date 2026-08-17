#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato manage-navigate (DO432, GE 2.4
"Navigate the RHACM Web Console"), sprovvisto di `lab grade` ufficiale (la
classe ManageNavigate nel pacchetto do0012l implementa solo start()/finish()).

La guida (testo ufficiale, pagine 71-81) fa deployare dallo start() un
deployment "mysqldb" nel progetto manage-navigate SUL MANAGED CLUSTER, con un
volume che referenzia una PVC inesistente ("my-volume"), causando un pod
bloccato in stato non pronto. Lo studente usa la RHACM web console (Search)
per individuare il problema e correggere il deployment, sostituendo il nome
della PVC con quella realmente esistente, "mysql-volume" (confermato dal
diff materials/labs vs materials/solutions del pacchetto do0012l: l'unica
differenza tra i due file e' spec.template.spec.volumes[].persistentVolumeClaim.claimName,
da "my-volume" a "mysql-volume").

Il deployment vive sul managed cluster (ocp4-mng), non sul hub: usa il
kubeconfig dedicato (vedi _common.MANAGED_KUBECONFIG).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json_managed, project_exists_managed

LAB_NAME = "manage-navigate"
EXPECTED_PVC = "mysql-volume"


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project}, managed cluster)")

    with GradingStep(f"Il progetto {project} esiste sul managed cluster") as step:
        if not project_exists_managed(project):
            step.fail(f"Progetto '{project}' non trovato sul managed cluster")

    deployment = oc_get_json_managed("deployment", "mysqldb", "-n", project)

    with GradingStep("Il deployment mysqldb punta alla PVC corretta") as step:
        if deployment is None:
            step.fail("Deployment 'mysqldb' non trovato nel progetto")
        else:
            volumes = deployment["spec"]["template"]["spec"].get("volumes", [])
            claim_names = [
                v["persistentVolumeClaim"]["claimName"]
                for v in volumes
                if "persistentVolumeClaim" in v
            ]
            if EXPECTED_PVC not in claim_names:
                step.add_error(
                    f"Il volume del deployment deve referenziare la PVC "
                    f"'{EXPECTED_PVC}' (trovato: {claim_names or 'nessuna PVC'})"
                )

    with GradingStep("Il pod mysqldb e' pronto (Running/Ready)") as step:
        pods = oc_get_json_managed("pods", "-n", project, "-l", "application=mysqldb")
        items = (pods or {}).get("items", [])
        if not items:
            step.fail("Nessun pod con label application=mysqldb trovato")
        else:
            pod = items[0]
            phase = pod.get("status", {}).get("phase")
            ready = any(
                c.get("type") == "Ready" and c.get("status") == "True"
                for c in pod.get("status", {}).get("conditions", []) or []
            )
            if phase != "Running" or not ready:
                step.add_error(
                    f"Il pod {pod.get('metadata', {}).get('name')} non e' Running/Ready "
                    f"(phase={phase})"
                )


if __name__ == "__main__":
    main()
