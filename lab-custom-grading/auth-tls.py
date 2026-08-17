#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato auth-tls (DO380, Cap. 1.11
"Authenticate with a Token and a Client Certificate by Using kubeconfig
Files"), sprovvisto di `lab grade` ufficiale (la classe AuthTls implementa
solo start()/finish()) e senza materials/solutions.

Specifica ricavata dal testo integrale della guida ufficiale (pag. 80-84):
lo studente crea la SA "health-robot" nel progetto "auth-tls" con il
ClusterRole "cluster-reader", una CRON job locale su workstation che esegue
ogni minuto ~/DO380/labs/auth-tls/cluster-health.sh (che scrive
/tmp/cluster.log quando ci sono pod pending/failed/unknown), il gruppo
"backdoor-administrators" con ClusterRole "cluster-admin", e una
CertificateSigningRequest "admin-backdoor-access" (CN=admin-backdoor,
O=backdoor-administrators, signerName kubernetes.io/kube-apiserver-client,
expirationSeconds 604800) approvata.

CHECK "SUL MOMENTO" (vedi CLAUDE.md sez.2): la CRON job e /tmp/cluster.log
sono un backdoor/monitoring attivo SOLO durante l'esercizio — finish()
rimuove esplicitamente sia il crontab dello studente sia il file temporaneo,
quindi e' corretto che questi due controlli tornino FAIL dopo `lab finish`.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists, command_ok, file_exists

LAB_NAME = "auth-tls"
SA_NAME = "health-robot"
CRON_COMMAND_SNIPPET = "auth-tls/cluster-health.sh"
GROUP_NAME = "backdoor-administrators"
CSR_NAME = "admin-backdoor-access"


def clusterrolebinding_grants(role, subject_kind, subject_name):
    """Cerca fra tutte le ClusterRoleBinding una che leghi il subject dato al ruolo dato."""
    result = oc_get_json("clusterrolebinding")
    if result is None:
        return False
    for crb in result.get("items", []):
        if crb.get("roleRef", {}).get("name") != role:
            continue
        for subj in crb.get("subjects", []) or []:
            if subj.get("kind") == subject_kind and subj.get("name") == subject_name:
                return True
    return False


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    sa = oc_get_json("serviceaccount", SA_NAME, "-n", project)
    with GradingStep(f"La ServiceAccount '{SA_NAME}' esiste nel progetto {project}") as step:
        if sa is None:
            step.fail(f"ServiceAccount '{SA_NAME}' non trovata nel progetto {project}")

    with GradingStep(f"La ServiceAccount '{SA_NAME}' ha il ClusterRole 'cluster-reader'") as step:
        sa_full_name = f"system:serviceaccount:{project}:{SA_NAME}"
        if not clusterrolebinding_grants("cluster-reader", "ServiceAccount", SA_NAME):
            step.add_error(
                f"Nessuna ClusterRoleBinding lega 'cluster-reader' alla ServiceAccount {sa_full_name}"
            )

    with GradingStep(
        "Il gruppo 'backdoor-administrators' esiste con il ClusterRole 'cluster-admin'"
    ) as step:
        group = oc_get_json("group", GROUP_NAME)
        if group is None:
            step.fail(f"Group '{GROUP_NAME}' non trovato")
        elif not clusterrolebinding_grants("cluster-admin", "Group", GROUP_NAME):
            step.add_error(
                f"Nessuna ClusterRoleBinding lega 'cluster-admin' al gruppo '{GROUP_NAME}'"
            )

    csr = oc_get_json("csr", CSR_NAME)
    with GradingStep(f"La CSR '{CSR_NAME}' e' approvata per admin-backdoor/backdoor-administrators") as step:
        if csr is None:
            step.fail(f"CSR '{CSR_NAME}' non trovata")
        else:
            spec = csr.get("spec", {})
            if spec.get("signerName") != "kubernetes.io/kube-apiserver-client":
                step.add_error(
                    f"signerName atteso 'kubernetes.io/kube-apiserver-client' (trovato: {spec.get('signerName')})"
                )
            if spec.get("expirationSeconds") != 604800:
                step.add_error(
                    f"expirationSeconds atteso 604800 (trovato: {spec.get('expirationSeconds')})"
                )
            conditions = csr.get("status", {}).get("conditions", [])
            if not any(c.get("type") == "Approved" for c in conditions):
                step.add_error("La CSR non risulta 'Approved'")
            if not csr.get("status", {}).get("certificate"):
                step.add_error("La CSR non ha ancora un certificato emesso (status.certificate vuoto)")

    with GradingStep(
        "[check sul momento, prima di 'lab finish'] La CRON job di cluster-health.sh e' attiva"
    ) as step:
        if not command_ok(f"crontab -l | grep -q '{CRON_COMMAND_SNIPPET}'"):
            step.add_error(
                f"Nessuna riga crontab per lo user corrente che esegua '{CRON_COMMAND_SNIPPET}'"
            )

    with GradingStep(
        "[check sul momento, prima di 'lab finish'] Il file /tmp/cluster.log esiste"
    ) as step:
        if not file_exists("/tmp/cluster.log"):
            step.add_error("File '/tmp/cluster.log' non trovato (la CRON job non e' ancora girata?)")


if __name__ == "__main__":
    main()
