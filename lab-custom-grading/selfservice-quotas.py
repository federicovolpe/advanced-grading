#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato selfservice-quotas (DO280, capitolo
"Enabling Developer Self-service", sezione 6.2 "Project and Cluster
Quotas"), sprovvisto di `lab grade` ufficiale (la classe SelfserviceQuotas
implementa solo start()/finish(), non grade()).

Nota importante (guida studente unica fonte disponibile, cache di
materials/labs e materials/solutions per questo esercizio vuota): nonostante
il titolo della sezione parli di "Project AND Cluster Quotas", il testo
NON crea mai una ClusterResourceQuota. L'aspetto "cluster" illustrato e'
solo la capacita' condivisa del nodo (CPU allocabile), che limita lo
scheduling anche in namespace diversi da quello con la ResourceQuota -
non una risorsa cluster-scoped. Per la regola d'oro di questo repo, questo
script NON verifica alcuna ClusterResourceQuota: non e' richiesta
dall'esercizio e inventarla sarebbe un falso.

L'esercizio e' guidato passo-passo (non puramente esplorativo): gradua solo
le azioni esplicitamente richieste dal testo, con i valori letterali che
riporta:

- Punto 3: deployment "test" in selfservice-quotas, immagine
  hello-world-nginx, richiesta CPU = 1 (oc set resources ... --requests=cpu=1).
- Punto 8: ResourceQuota "one-cpu" in selfservice-quotas con
  spec.hard.requests.cpu = "1" (oc create quota one-cpu --hard=requests.cpu=1).
- Punto 9.1: test scalato a 8 repliche.
- Punto 9.2: deployment "test-2" in selfservice-quotas, stessa immagine,
  1 replica, SENZA richiesta di CPU (dimostra che la quota blocca anche
  pod che non specificano requests.cpu quando la quota lo richiede).
- Punto 10: progetto "test" (ricreato dopo essere stato cancellato al 6.6)
  con deployment "test-3", richiesta CPU = 1.

Non vengono verificati conteggi di pod Ready/Pending ne' l'uso corrente
della quota (status.used): dipendono dalla capacita' del nodo del cluster
specifico ("The CPU percentage value might be different in your cluster",
testualmente nella guida), quindi non sono valori oggettivi e stabili da
gradare.

Uso: selfservice-quotas.py [nome-progetto]   (default: selfservice-quotas)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "selfservice-quotas"
OTHER_PROJECT = "test"
QUOTA_NAME = "one-cpu"
EXPECTED_CPU_MILLI = 1000  # 1 CPU, come richiesto testualmente dalla guida


def cpu_to_millicores(value):
    """Converte una quantity CPU Kubernetes (es. '1', '1000m', '0.5') in
    millicores, oppure None se non parsabile."""
    if value is None:
        return None
    s = str(value).strip()
    try:
        if s.endswith("m"):
            return int(s[:-1])
        return int(round(float(s) * 1000))
    except ValueError:
        return None


def first_container(deployment):
    if deployment is None:
        return None
    containers = deployment["spec"]["template"]["spec"].get("containers", [])
    return containers[0] if containers else None


def cpu_request_of(container):
    if container is None:
        return None
    return container.get("resources", {}).get("requests", {}).get("cpu")


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(f"Il progetto {OTHER_PROJECT} esiste") as step:
        if not project_exists(OTHER_PROJECT):
            step.fail(
                f"Progetto '{OTHER_PROJECT}' non trovato (punto 10: va "
                "ricreato dopo la cancellazione del punto 6.6)"
            )

    # Punto 8: ResourceQuota one-cpu nel progetto principale.
    quota = oc_get_json("resourcequota", QUOTA_NAME, "-n", project)
    with GradingStep(
        f"La ResourceQuota '{QUOTA_NAME}' esiste con hard.requests.cpu=1"
    ) as step:
        if quota is None:
            step.fail(f"ResourceQuota '{QUOTA_NAME}' non trovata in '{project}'")
        else:
            hard = quota.get("spec", {}).get("hard", {})
            milli = cpu_to_millicores(hard.get("requests.cpu"))
            if milli != EXPECTED_CPU_MILLI:
                step.add_error(
                    "spec.hard.requests.cpu deve essere 1 CPU "
                    f"(trovato: {hard.get('requests.cpu')!r})"
                )

    # Punto 3: deployment "test" con richiesta di 1 CPU.
    test_dep = oc_get_json("deployment", "test", "-n", project)
    with GradingStep(
        "Il deployment 'test' in selfservice-quotas richiede 1 CPU"
    ) as step:
        if test_dep is None:
            step.fail("Deployment 'test' non trovato nel progetto")
        else:
            container = first_container(test_dep)
            milli = cpu_to_millicores(cpu_request_of(container))
            if milli != EXPECTED_CPU_MILLI:
                step.add_error(
                    "Il container del deployment 'test' deve richiedere 1 CPU "
                    f"(trovato: {cpu_request_of(container)!r})"
                )

    # Punto 9.1: test scalato a 8 repliche (ultima azione esplicita sul
    # deployment prima del Finish, nessuna istruzione lo riporta a 1).
    with GradingStep("Il deployment 'test' e' scalato a 8 repliche") as step:
        if test_dep is None:
            step.fail()
        else:
            replicas = test_dep.get("spec", {}).get("replicas")
            if replicas != 8:
                step.add_error(
                    f"spec.replicas del deployment 'test' deve essere 8 "
                    f"(trovato: {replicas})"
                )

    # Punto 9.2: deployment test-2 senza richiesta di CPU.
    test2_dep = oc_get_json("deployment", "test-2", "-n", project)
    with GradingStep(
        "Il deployment 'test-2' esiste in selfservice-quotas senza "
        "richiesta di CPU"
    ) as step:
        if test2_dep is None:
            step.fail("Deployment 'test-2' non trovato nel progetto")
        else:
            container = first_container(test2_dep)
            cpu_req = cpu_request_of(container)
            if cpu_req is not None:
                step.add_error(
                    "Il container del deployment 'test-2' non deve "
                    f"richiedere CPU (trovato: {cpu_req!r})"
                )

    # Punto 10: deployment test-3 nel progetto test, richiesta di 1 CPU.
    test3_dep = oc_get_json("deployment", "test-3", "-n", OTHER_PROJECT)
    with GradingStep(
        f"Il deployment 'test-3' nel progetto {OTHER_PROJECT} richiede 1 CPU"
    ) as step:
        if test3_dep is None:
            step.fail(f"Deployment 'test-3' non trovato nel progetto '{OTHER_PROJECT}'")
        else:
            container = first_container(test3_dep)
            milli = cpu_to_millicores(cpu_request_of(container))
            if milli != EXPECTED_CPU_MILLI:
                step.add_error(
                    "Il container del deployment 'test-3' deve richiedere "
                    f"1 CPU (trovato: {cpu_request_of(container)!r})"
                )


if __name__ == "__main__":
    main()
