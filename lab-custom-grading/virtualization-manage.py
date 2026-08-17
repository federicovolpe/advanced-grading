#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato virtualization-manage (DO432, Cap.
6.6), sprovvisto di `lab grade` ufficiale (do0016l/virtualization-manage.py
implementa solo start()/finish()).

Specifica dal testo della guida (Cap. 6.6): lo studente crea un
ApplicationSet "virtualization-manage" (Argo server openshift-gitops) verso
il repo do0016l/virtualization-manage.git, path virtualization/manifests,
remote namespace "virt-manage", placement sul cluster set "gitops-configure"
(2 cluster). Questo deploya una VM "fedora" (Stopped di default) sia
sull'hub (local-cluster) sia sul managed cluster. Lo studente poi abilita le
VM actions in RHACM (annotazione virtual-machine-preview=true sul resource
"search" in open-cluster-management, SOLO sull'hub) e avvia la VM fedora
DAL SOLO cluster hub (la guida nota esplicitamente: "VM actions are
available only for the VM in the hub cluster").

Nota: openshift-cnv/HyperConverged e il progetto "virt-manage" sono
precondizioni create da start() su entrambi i cluster (vedi
virtualization-manage.py: apply_single_yaml(...,"hco.yaml") prima ancora
che lo studente inizi) — non li gradiamo, gradiamo solo cio' che la guida
chiede di fare: l'ApplicationSet, la VM fedora deployata, l'annotazione, e
lo stato Running della VM sull'hub.

Check "sul momento": valido solo prima di `lab finish virtualization-manage`
(finish() cancella l'ApplicationSet e il progetto virt-manage).

Uso: virtualization-manage.py   (nessun progetto: le risorse vivono in
openshift-gitops/virt-manage/open-cluster-management su entrambi i cluster)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import oc_get_json_kc, HUB_KUBECONFIG, MANAGED_KUBECONFIG, GradingStep

APPSET_NAME = "virtualization-manage"
REPO_SUFFIX = "do0016l/virtualization-manage.git"
EXPECTED_PATH = "virtualization/manifests"
EXPECTED_DEST_NS = "virt-manage"
VM_NAME = "fedora"


def _appset_sources(appset):
    tmpl_spec = appset.get("spec", {}).get("template", {}).get("spec", {})
    sources = tmpl_spec.get("sources") or []
    if not sources and tmpl_spec.get("source"):
        sources = [tmpl_spec["source"]]
    return sources, tmpl_spec.get("destination", {})


def vm_exists(kubeconfig, namespace, name):
    return oc_get_json_kc(kubeconfig, "vm", name, "-n", namespace) is not None


def main():
    print(f"🔧 Grading personalizzato per 'virtualization-manage'")

    appset = oc_get_json_kc(HUB_KUBECONFIG, "applicationset", APPSET_NAME, "-n", "openshift-gitops")
    with GradingStep(f"ApplicationSet '{APPSET_NAME}' configurato correttamente") as step:
        if appset is None:
            step.fail(f"ApplicationSet '{APPSET_NAME}' non trovato in openshift-gitops (hub)")
        else:
            sources, destination = _appset_sources(appset)
            if not any(REPO_SUFFIX in (s.get("repoURL") or "") for s in sources):
                step.add_error(f"Nessuna source punta a un repo '{REPO_SUFFIX}'")
            if not any((s.get("path") or "") == EXPECTED_PATH for s in sources):
                step.add_error(f"Nessuna source usa il path '{EXPECTED_PATH}'")
            if destination.get("namespace") != EXPECTED_DEST_NS:
                step.add_error(
                    f"Remote namespace atteso '{EXPECTED_DEST_NS}', "
                    f"trovato '{destination.get('namespace')}'"
                )

    with GradingStep(f"VM '{VM_NAME}' deployata sul cluster hub") as step:
        if not vm_exists(HUB_KUBECONFIG, EXPECTED_DEST_NS, VM_NAME):
            step.fail(f"VM '{VM_NAME}' non trovata in {EXPECTED_DEST_NS} (hub)")

    with GradingStep(f"VM '{VM_NAME}' deployata sul managed cluster") as step:
        if not vm_exists(MANAGED_KUBECONFIG, EXPECTED_DEST_NS, VM_NAME):
            step.fail(f"VM '{VM_NAME}' non trovata in {EXPECTED_DEST_NS} (managed cluster)")

    with GradingStep("VM actions abilitate in RHACM (annotazione sull'hub)") as step:
        search = oc_get_json_kc(
            HUB_KUBECONFIG, "search", "search-v2-operator", "-n", "open-cluster-management",
        )
        if search is None:
            step.fail("Resource 'search/search-v2-operator' non trovata")
        else:
            annotations = search.get("metadata", {}).get("annotations", {}) or {}
            if annotations.get("virtual-machine-preview") != "true":
                step.add_error(
                    "Annotazione 'virtual-machine-preview=true' non impostata "
                    "(oc annotate search search-v2-operator -n open-cluster-management "
                    "virtual-machine-preview='true')"
                )

    with GradingStep(f"VM '{VM_NAME}' avviata sul cluster hub") as step:
        vm = oc_get_json_kc(HUB_KUBECONFIG, "vm", VM_NAME, "-n", EXPECTED_DEST_NS)
        if vm is None:
            step.fail(f"VM '{VM_NAME}' non trovata in {EXPECTED_DEST_NS} (hub)")
        elif vm.get("status", {}).get("printableStatus") != "Running":
            step.add_error(
                f"Stato atteso 'Running', trovato "
                f"'{vm.get('status', {}).get('printableStatus')}'"
            )


if __name__ == "__main__":
    main()
