#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato manage-configure (DO432, GE 2.6
"Configure Access Control for Multicluster Management"), sprovvisto di
`lab grade` ufficiale (la classe ManageConfigure nel pacchetto do0012l
implementa solo start()/finish()).

La guida (testo ufficiale, pagine 87-99) fa fare un "giro completo" sui
managed cluster set: crea "production" e "stage" dalla web console, poi allo
step 10 li ELIMINA entrambi prima di lab finish. Gradare l'esistenza dei
cluster set stessi sarebbe quindi indistinguibile da non aver fatto nulla
(vedi CLAUDE.md sez.2 sul caso "giro completo").

Lo stato che INVECE sopravvive, perche' il testo non lo fa mai rimuovere, e'
l'insieme di ClusterRoleBinding creati via CLI allo step 5 con
`oc adm policy add-cluster-role-to-group` per i tre gruppi IdM
(production-administrators, stage-administrators, global-viewers). Questi
oggetti non sono di proprieta' del ManagedClusterSet (non hanno una
ownerReference verso di esso): cancellare i cluster set "production"/"stage"
rimuove le ClusterRole generate automaticamente da RHACM con quel nome, ma
NON le ClusterRoleBinding che li referenziano per nome, che restano nel
cluster (anche se "orfane", puntano a una ClusterRole non piu' esistente).
Sono quindi il solo segnale oggettivo e persistente del lavoro fatto in
questo esercizio, e vengono gradati sul hub cluster.

Nota: il ruolo "open-cluster-management:managedclusterset:view:global" e' su
un cluster set predefinito ("global"), mai cancellato dalla guida: la sua
ClusterRoleBinding resta valida (non orfana).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json_hub

LAB_NAME = "manage-configure"

# (nome atteso della ClusterRoleBinding, gruppo, ClusterRole referenziata)
# Il nome esatto della ClusterRoleBinding non e' documentato dalla guida (e'
# generato da `oc adm policy add-cluster-role-to-group`, che usa di norma lo
# stesso nome della ClusterRole): si cerca quindi per caratteristiche
# (roleRef + subject), non per nome fisso.
EXPECTED_BINDINGS = [
    ("production-administrators", "open-cluster-management:managedclusterset:admin:production"),
    ("production-administrators", "open-cluster-management:managedclusterset:view:stage"),
    ("stage-administrators", "open-cluster-management:managedclusterset:admin:stage"),
    ("global-viewers", "open-cluster-management:managedclusterset:view:global"),
]


def binding_matches(binding, group, role):
    if binding.get("roleRef", {}).get("name") != role:
        return False
    subjects = binding.get("subjects") or []
    return any(s.get("kind") == "Group" and s.get("name") == group for s in subjects)


def main():
    # Questo esercizio non usa un progetto: e' tutto su ClusterRoleBinding
    # cluster-scoped sul hub. L'argomento e' accettato solo per coerenza con
    # gli altri script, ma non viene usato.
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (hub cluster, nessun progetto)")

    bindings = oc_get_json_hub("clusterrolebindings")
    items = (bindings or {}).get("items", [])

    for group, role in EXPECTED_BINDINGS:
        with GradingStep(
            f"Il gruppo {group} ha il ruolo {role}"
        ) as step:
            if bindings is None:
                step.fail("Impossibile leggere le ClusterRoleBinding sul hub cluster")
            elif not any(binding_matches(b, group, role) for b in items):
                step.add_error(
                    f"Nessuna ClusterRoleBinding assegna il ruolo '{role}' al gruppo '{group}'"
                )


if __name__ == "__main__":
    main()
