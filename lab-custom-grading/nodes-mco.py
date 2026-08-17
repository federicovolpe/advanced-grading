#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato nodes-mco (DO380, Cap. 7.4
"Configure a Node with a Custom Configuration by Using the Machine
Configuration Operator"), sprovvisto di `lab grade` ufficiale (la classe
NodesMco implementa solo start()/finish()).

Specifica ricavata dal diff labs/solutions (custom-mcp.yaml, 99-custom-
chrony.bu) in materials/solutions/nodes-mco/: lo studente crea un
MachineConfigPool "custom" che seleziona i MachineConfig con role "custom"
(oltre a "worker") e i nodi con la label "node-role.kubernetes.io/custom"
(gia' applicata a worker01 da start(), non e' quindi farina del sacco dello
studente e non va gradata), e un MachineConfig "99-custom-chrony" (compilato
da Butane) che sovrascrive /etc/chrony.conf con un pool NTP pubblico.

Le risorse sono tutte cluster-scoped (MachineConfigPool/MachineConfig/Node),
nessun progetto OpenShift e' coinvolto.
"""

import sys
import os
import base64
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json

MCP_NAME = "custom"
MC_NAME = "99-custom-chrony"
MC_ROLE_LABEL = "machineconfiguration.openshift.io/role"
NODE_SELECTOR_LABEL = "node-role.kubernetes.io/custom"
EXPECTED_CHRONY_SNIPPET = "pool 0.rhel.pool.ntp.org"


def decode_ignition_file_contents(mc, path):
    """Cerca il file /etc/chrony.conf nello storage Ignition del MC e ne
    ritorna il contenuto decodificato, o None se non lo trova/decodifica."""
    files = mc.get("spec", {}).get("config", {}).get("storage", {}).get("files", [])
    for f in files:
        if f.get("path") != path:
            continue
        source = f.get("contents", {}).get("source", "")
        match = re.match(r"data:;base64,(.+)", source) or re.match(
            r"data:.*;base64,(.+)", source
        )
        if match:
            try:
                return base64.b64decode(match.group(1)).decode("utf-8")
            except Exception:
                return None
        return source or None
    return None


def main():
    print(f"🔧 Grading personalizzato per '{MCP_NAME}' MachineConfigPool (nodes-mco)")

    mcp = oc_get_json("machineconfigpool", MCP_NAME)
    with GradingStep(f"Il MachineConfigPool '{MCP_NAME}' esiste con i selettori corretti") as step:
        if mcp is None:
            step.fail(f"MachineConfigPool '{MCP_NAME}' non trovato")
        else:
            spec = mcp.get("spec", {})
            selector_values = (
                spec.get("machineConfigSelector", {})
                .get("matchExpressions", [{}])[0]
                .get("values", [])
            )
            if not ("worker" in selector_values and "custom" in selector_values):
                step.add_error(
                    "machineConfigSelector.matchExpressions[].values deve includere "
                    f"'worker' e 'custom' (trovato: {selector_values})"
                )
            node_labels = spec.get("nodeSelector", {}).get("matchLabels", {})
            if NODE_SELECTOR_LABEL not in node_labels:
                step.add_error(
                    f"nodeSelector.matchLabels deve includere '{NODE_SELECTOR_LABEL}' "
                    f"(trovato: {node_labels})"
                )

    mc = oc_get_json("machineconfig", MC_NAME)
    with GradingStep(f"Il MachineConfig '{MC_NAME}' esiste con la label e il contenuto corretti") as step:
        if mc is None:
            step.fail(f"MachineConfig '{MC_NAME}' non trovato")
        else:
            labels = mc.get("metadata", {}).get("labels", {})
            if labels.get(MC_ROLE_LABEL) != "custom":
                step.add_error(
                    f"Label '{MC_ROLE_LABEL}' deve valere 'custom' (trovato: {labels.get(MC_ROLE_LABEL)})"
                )
            content = decode_ignition_file_contents(mc, "/etc/chrony.conf")
            if content is None:
                step.add_error("Impossibile leggere il contenuto di /etc/chrony.conf dal MachineConfig")
            elif EXPECTED_CHRONY_SNIPPET not in content:
                step.add_error(
                    f"/etc/chrony.conf non contiene '{EXPECTED_CHRONY_SNIPPET}' (contenuto: {content!r})"
                )

    node = oc_get_json("node", "worker01")
    with GradingStep("Il nodo worker01 ha completato il rollout del MachineConfig ('Done')") as step:
        if node is None:
            step.fail("Nodo 'worker01' non trovato")
        else:
            state = node.get("metadata", {}).get("annotations", {}).get(
                "machineconfiguration.openshift.io/state"
            )
            if state != "Done":
                step.add_error(
                    f"Stato di rollout del MachineConfig su worker01: '{state}' (atteso 'Done' — "
                    "il rollout puo' richiedere alcuni minuti dopo l'applicazione)"
                )


if __name__ == "__main__":
    main()
