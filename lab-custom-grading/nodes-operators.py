#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato nodes-operators (DO380, Cap. 7.6
"Configure Nodes with Special Purpose Operators"), sprovvisto di `lab grade`
ufficiale (la classe NodesOperators implementa solo start()/finish()).

Specifica ricavata dal diff labs/solutions (stabledbCR.yaml) in
materials/solutions/nodes-operators/: lo studente crea una CR Tuned
"stabledb" in openshift-cluster-node-tuning-operator con un profilo custom
"stabledb-tuning" (transparent_hugepage=never) raccomandato ai nodi con la
label "node-role.kubernetes.io/stabledb" (gia' applicata a worker01da
start(), non e' quindi lavoro dello studente e non va gradata).

Le risorse sono cluster-scoped/nel progetto di sistema del Node Tuning
Operator, nessun progetto OpenShift dello studente e' coinvolto.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json

TUNING_NAMESPACE = "openshift-cluster-node-tuning-operator"
TUNED_NAME = "stabledb"
PROFILE_NAME = "stabledb-tuning"
NODE_LABEL = "node-role.kubernetes.io/stabledb"
NODE_NAME = "worker01"


def main():
    print(f"🔧 Grading personalizzato per '{TUNED_NAME}' Tuned CR (nodes-operators)")

    tuned = oc_get_json("tuned", TUNED_NAME, "-n", TUNING_NAMESPACE)
    with GradingStep(f"La CR Tuned '{TUNED_NAME}' esiste con profilo e recommend corretti") as step:
        if tuned is None:
            step.fail(f"Tuned '{TUNED_NAME}' non trovato in {TUNING_NAMESPACE}")
        else:
            spec = tuned.get("spec", {})
            profiles = spec.get("profile", [])
            profile = next((p for p in profiles if p.get("name") == PROFILE_NAME), None)
            if profile is None:
                step.add_error(f"Profilo '{PROFILE_NAME}' non trovato (profili presenti: "
                                f"{[p.get('name') for p in profiles]})")
            else:
                data = profile.get("data", "")
                if "transparent_hugepage=never" not in data:
                    step.add_error(
                        "Il profilo non contiene 'transparent_hugepage=never' "
                        f"(contenuto: {data!r})"
                    )

            recommends = spec.get("recommend", [])
            matches_label = any(
                m.get("label") == NODE_LABEL
                for r in recommends
                for m in r.get("match", [])
            )
            recommends_profile = any(r.get("profile") == PROFILE_NAME for r in recommends)
            if not matches_label:
                step.add_error(
                    f"Nessuna regola 'recommend' con match.label='{NODE_LABEL}'"
                )
            if not recommends_profile:
                step.add_error(
                    f"Nessuna regola 'recommend' che raccomanda il profilo '{PROFILE_NAME}'"
                )

    tuned_profile = oc_get_json("profile.tuned.openshift.io", NODE_NAME, "-n", TUNING_NAMESPACE)
    with GradingStep(f"Il nodo {NODE_NAME} ha applicato il profilo TuneD '{PROFILE_NAME}'") as step:
        if tuned_profile is None:
            step.fail(f"Profile TuneD per il nodo '{NODE_NAME}' non trovato")
        else:
            applied = tuned_profile.get("status", {}).get("tunedProfile")
            if applied != PROFILE_NAME:
                step.add_error(
                    f"Profilo applicato su {NODE_NAME}: '{applied}' (atteso '{PROFILE_NAME}' — "
                    "l'applicazione puo' richiedere qualche istante)"
                )


if __name__ == "__main__":
    main()
