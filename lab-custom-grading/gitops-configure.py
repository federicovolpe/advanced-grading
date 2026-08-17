#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato gitops-configure (DO432/do0015l),
sprovvisto di `lab grade` ufficiale (la classe GitOpsConfigure implementa
solo start()/finish()).

Specifica ricavata dal testo della guida studente (PDF DO432-RHACM2.13,
Cap. 5.4 "Configure GitOps for Application Lifecycle Management in RHACM"):
lo studente crea un cluster set che raggruppa hub (local-cluster) e cluster
gestito (managed-cluster), lo lega al progetto "gitops-configure", applica
una policy di governance (generata da PolicyGenerator a partire dai file in
~/DO0015L/labs/gitops-configure/policy/) che installa l'operator OpenShift
GitOps su entrambi i cluster e configura l'istanza Argo CD, poi importa i
cluster in Argo CD applicando gitops-register.yaml (ManagedClusterSetBinding
+ Placement + GitOpsCluster in ns openshift-gitops).

Tutte le risorse RHACM/Argo CD create in questo esercizio vivono sull'hub
cluster (incluso lo stato di conformita' della policy sui cluster gestiti,
aggregato da RHACM in .status.status), quindi il grading gira interamente
con il contesto oc corrente, senza bisogno di autenticarsi sul cluster
gestito.

Uso: gitops-configure.py [nome-progetto]   (default: gitops-configure)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "gitops-configure"
GITOPS_NS = "openshift-gitops"


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(f"Il ManagedClusterSet '{LAB_NAME}' esiste") as step:
        cluster_set = oc_get_json("managedclusterset", LAB_NAME)
        if cluster_set is None:
            step.fail(f"ManagedClusterSet '{LAB_NAME}' non trovato")

    with GradingStep(
        f"Il cluster set e' legato al progetto {project} (namespace binding)"
    ) as step:
        binding = oc_get_json(
            "managedclustersetbinding", LAB_NAME, "-n", project
        )
        if binding is None:
            step.fail(
                f"ManagedClusterSetBinding '{LAB_NAME}' non trovato nel namespace {project}"
            )
        elif binding.get("spec", {}).get("clusterSet") != LAB_NAME:
            step.add_error(
                "Il binding non referenzia il cluster set "
                f"'{LAB_NAME}' (spec.clusterSet={binding.get('spec', {}).get('clusterSet')})"
            )

    with GradingStep(
        "La policy di governance per l'operator OpenShift GitOps e' Compliant "
        "su entrambi i cluster"
    ) as step:
        policy = oc_get_json("policy", LAB_NAME, "-n", project)
        if policy is None:
            step.fail(f"Policy '{LAB_NAME}' non trovata nel namespace {project}")
        else:
            statuses = policy.get("status", {}).get("status", []) or []
            by_cluster = {
                s.get("clustername"): s.get("compliant") for s in statuses
            }
            for cluster in ("local-cluster", "managed-cluster"):
                compliant = by_cluster.get(cluster)
                if compliant != "Compliant":
                    step.add_error(
                        f"Cluster '{cluster}': stato {compliant or 'non riportato'} "
                        "(atteso Compliant)"
                    )

    with GradingStep(
        "Il ManagedClusterSetBinding per l'import in Argo CD esiste "
        f"(namespace {GITOPS_NS})"
    ) as step:
        binding = oc_get_json(
            "managedclustersetbinding", LAB_NAME, "-n", GITOPS_NS
        )
        if binding is None:
            step.fail(
                f"ManagedClusterSetBinding '{LAB_NAME}' non trovato nel namespace {GITOPS_NS}"
            )
        elif binding.get("spec", {}).get("clusterSet") != LAB_NAME:
            step.add_error(
                "Il binding non referenzia il cluster set "
                f"'{LAB_NAME}' (spec.clusterSet={binding.get('spec', {}).get('clusterSet')})"
            )

    with GradingStep(
        "Il GitOpsCluster importa i cluster nell'istanza Argo CD dell'hub"
    ) as step:
        gitops_cluster = oc_get_json("gitopscluster", LAB_NAME, "-n", GITOPS_NS)
        if gitops_cluster is None:
            step.fail(f"GitOpsCluster '{LAB_NAME}' non trovato nel namespace {GITOPS_NS}")
        else:
            placement_ref = gitops_cluster.get("spec", {}).get("placementRef", {})
            if placement_ref.get("name") != LAB_NAME:
                step.add_error(
                    "Il GitOpsCluster non referenzia il Placement "
                    f"'{LAB_NAME}' (placementRef.name={placement_ref.get('name')})"
                )


if __name__ == "__main__":
    main()
