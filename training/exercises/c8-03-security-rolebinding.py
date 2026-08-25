"""
Extra — Sicurezza e RBAC (vedi c8-01-security-serviceaccount.py).
Concedi un ClusterRole a un utente dentro un progetto con una RoleBinding.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _training_common import GradingStep, oc_get_json, ensure_project, run_cli

CHAPTER = "Extra — Sicurezza e RBAC"
TITLE = "Concedi un ruolo con una RoleBinding"
PROJECT = "training-security-rolebinding"
USER = "jane"
CLUSTER_ROLE = "view"

TASK = f"""\
Nel progetto "{PROJECT}", crea una RoleBinding chiamata "view-binding"
che conceda il ClusterRole "{CLUSTER_ROLE}" all'utente "{USER}",
limitato a questo progetto (non a tutto il cluster).

Comando suggerito (1):
  oc create rolebinding view-binding --clusterrole={CLUSTER_ROLE} --user={USER} -n {PROJECT}
"""


def setup():
    ensure_project(PROJECT)


def grade():
    rb = oc_get_json("rolebinding", "view-binding", "-n", PROJECT)

    with GradingStep("La RoleBinding view-binding esiste") as step:
        if not rb:
            step.fail("RoleBinding 'view-binding' non trovata")

    with GradingStep(f"Concede il ClusterRole {CLUSTER_ROLE} all'utente {USER}") as step:
        if not rb:
            step.fail("RoleBinding 'view-binding' non trovata")
        else:
            role_ref = rb.get("roleRef", {})
            if role_ref.get("kind") != "ClusterRole" or role_ref.get("name") != CLUSTER_ROLE:
                step.add_error(f"roleRef = {role_ref!r}, attesa ClusterRole/{CLUSTER_ROLE}")
            subjects = rb.get("subjects", []) or []
            match = any(
                s.get("kind") == "User" and s.get("name") == USER for s in subjects
            )
            if not match:
                step.add_error(f"subjects = {subjects!r}, atteso un User {USER!r}")


if __name__ == "__main__":
    run_cli(setup, grade)
