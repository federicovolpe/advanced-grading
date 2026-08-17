#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato policies-generator (DO432/do0013l,
Cap. 3.6 "Deploy Policies by Using Policy Generator"), sprovvisto di
`lab grade` ufficiale.

Fonte della specifica: testo della guida studente (DO432-RHACM2.13-en-2)
Cap. 3.6, incrociato con policies-generator.py (start()/finish()): a
differenza degli altri esercizi del capitolo, QUESTO non usa un progetto
"policies-generator" ma tre progetti creati da start()/finish() sia sul hub
che sul managed cluster: policies-developer (dove vive la Policy), e le due
"vittime" qa-policies/prod-policies che la policy deve far esistere.
Nessun materials/labs o materials/solutions per questo esercizio (la riga
fs.copy_materials_step e' commentata nel modulo): lo studente crea i file a
mano seguendo le tabelle della guida, quindi la specifica viene solo dal
testo.

La guida chiede di:
1. Bindare il namespace policies-developer al cluster set "default".
2. Creare, con PolicyGenerator, una Policy "policy-namespace" (namespace
   policies-developer) che richiede (musthave, severity medium) l'esistenza
   dei namespace qa-policies e prod-policies su tutti i cluster, con una
   Placement "placement-policy-namespace" + PlacementBinding
   "binding-policy-namespace".
3. Osservare le violazioni (remediationAction: inform iniziale).
4. Passare la policy a remediationAction: enforce e riapplicarla, cosi'
   RHACM crea i namespace mancanti sui cluster gestiti.

Il segnale piu' oggettivo per il passo 4 (l'esito finale voluto) e' lo
stato di compliance aggregato riportato dalla Policy stessa sul hub
(status.compliant / status.status[].compliant): non serve un kubeconfig
separato per il managed cluster, RHACM propaga li' lo stato. Verifichiamo
anche, quando il contesto oc corrente e' il hub, che i namespace risultino
creati localmente.

Uso: policies-generator.py [namespace-developer]  (default: policies-developer)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "policies-generator"
POLICY_NAME = "policy-namespace"
PLACEMENT_NAME = "placement-policy-namespace"
PLACEMENTBINDING_NAME = "binding-policy-namespace"
REQUIRED_NAMESPACES = {"qa-policies", "prod-policies"}


def find_namespace_musthave_names(policy):
    """Estrae i nomi di Namespace richiesti (complianceType musthave) dagli
    object-templates della ConfigurationPolicy annidata nella Policy."""
    names = set()
    for tmpl in policy.get("spec", {}).get("policy-templates", []) or []:
        obj_def = tmpl.get("objectDefinition", {}) or {}
        for ot in obj_def.get("spec", {}).get("object-templates", []) or []:
            if ot.get("complianceType") != "musthave":
                continue
            od = ot.get("objectDefinition", {}) or {}
            if od.get("kind") == "Namespace":
                name = od.get("metadata", {}).get("name")
                if name:
                    names.add(name)
    return names


def is_policy_compliant(policy):
    """True se la policy risulta Compliant (aggregato o su tutti i cluster
    riportati in status.status[])."""
    status = policy.get("status", {}) or {}
    if "compliant" in status:
        return status.get("compliant") == "Compliant"
    per_cluster = status.get("status", []) or []
    if not per_cluster:
        return None  # nessuna informazione ancora disponibile
    return all(c.get("compliant") == "Compliant" for c in per_cluster)


def main():
    ns = sys.argv[1] if len(sys.argv) > 1 else "policies-developer"
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (namespace: {ns})")

    with GradingStep(f"Il namespace {ns} esiste") as step:
        if not project_exists(ns):
            step.fail(f"Namespace '{ns}' non trovato")

    with GradingStep(
        f"Il namespace {ns} e' associato a un cluster set (ManagedClusterSetBinding)"
    ) as step:
        bindings = oc_get_json("managedclustersetbinding", "-n", ns)
        if not bindings or not bindings.get("items"):
            step.add_error(
                f"Nessuna ManagedClusterSetBinding trovata nel namespace '{ns}' "
                "(passo 2 della guida: bind del cluster set 'default')"
            )

    policy = oc_get_json("policy", POLICY_NAME, "-n", ns)

    with GradingStep(
        f"La Policy '{POLICY_NAME}' esiste e richiede i namespace {sorted(REQUIRED_NAMESPACES)}"
    ) as step:
        if policy is None:
            step.fail(f"Policy '{POLICY_NAME}' non trovata nel namespace '{ns}'")
        else:
            found = find_namespace_musthave_names(policy)
            missing = REQUIRED_NAMESPACES - found
            if missing:
                step.add_error(
                    f"La policy non richiede (musthave) i namespace: {sorted(missing)}"
                )

    with GradingStep(
        f"La Policy '{POLICY_NAME}' e' impostata su remediationAction: enforce"
    ) as step:
        if policy is None:
            step.fail()
        else:
            action = policy.get("spec", {}).get("remediationAction")
            if action != "enforce":
                step.add_error(
                    f"remediationAction e' '{action}' (atteso 'enforce' dopo il passo "
                    "8-9 della guida: la policy generata inizialmente in 'inform' va "
                    "corretta e riapplicata)"
                )

    with GradingStep(
        f"Placement '{PLACEMENT_NAME}' e PlacementBinding '{PLACEMENTBINDING_NAME}' esistono"
    ) as step:
        placement = oc_get_json("placement", PLACEMENT_NAME, "-n", ns)
        binding = oc_get_json("placementbinding", PLACEMENTBINDING_NAME, "-n", ns)
        if placement is None:
            step.add_error(f"Placement '{PLACEMENT_NAME}' non trovato")
        if binding is None:
            step.add_error(f"PlacementBinding '{PLACEMENTBINDING_NAME}' non trovato")

    with GradingStep(
        "La Policy risulta Compliant su tutti i cluster (i namespace mancanti "
        "sono stati creati dalla remediation)"
    ) as step:
        if policy is None:
            step.fail()
        else:
            compliant = is_policy_compliant(policy)
            if compliant is None:
                step.add_error(
                    "Nessuno stato di compliance ancora riportato dalla policy "
                    "(RHACM non ha ancora valutato i cluster gestiti)"
                )
            elif compliant is False:
                step.add_error(
                    "La policy non e' Compliant su tutti i cluster: verificare che "
                    "remediationAction sia 'enforce' e che la policy sia stata "
                    "riapplicata dopo la modifica"
                )

    # Riscontro aggiuntivo, solo se il contesto oc corrente e' il hub:
    # "qa-policies" e' gia' creato da start() anche sul hub (non e' un
    # segnale utile), ma "prod-policies" NON lo e' -> la sua presenza sul
    # hub e' evidenza diretta che l'enforce/remediation e' stato eseguito.
    with GradingStep(
        "Il namespace 'prod-policies' esiste sul cluster hub (remediation locale)"
    ) as step:
        if not project_exists("prod-policies"):
            step.add_error(
                "Namespace 'prod-policies' non trovato sul cluster hub "
                "(se questo controllo gira su un contesto diverso dal hub, "
                "ignorare: fa fede il controllo di compliance sopra)"
            )


if __name__ == "__main__":
    main()
