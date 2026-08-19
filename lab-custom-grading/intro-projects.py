"""
Grading personalizzato per 'intro-projects' (AI0014L - Managing Projects).

Da testo guida studente (fornito dall'istruttore): lo studente crea il
progetto 'intro-projects' dalla dashboard RHOAI (gia' creato/eliminato da
`lab start`/`lab finish` in automatico - qui si grada lo stato PRIMA di
`lab finish`), poi aggiunge due permessi tramite la tab "Permissions":
- user1 con ruolo Contributor
- user2 con ruolo Admin

La dashboard RHOAI implementa i permessi di progetto con RoleBinding
OpenShift standard: Contributor -> ClusterRole 'edit', Admin -> ClusterRole
'admin' (convenzione nota della dashboard ODH/RHOAI). Non verificato dal
vivo contro un'azione reale della dashboard (richiederebbe automazione
browser), ma il RoleBinding sottostante e' un primitivo OpenShift standard.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "intro-projects"
EXPECTED_ROLES = {"user1": "edit", "user2": "admin"}


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep("user1 (Contributor) e user2 (Admin) hanno i permessi corretti") as step:
        bindings = oc_get_json("rolebindings", "-n", project)
        if not bindings:
            step.fail(f"Nessuna RoleBinding trovata nel progetto '{project}'")
        else:
            found_roles = {}
            for rb in bindings.get("items", []):
                role = rb.get("roleRef", {}).get("name")
                for subject in rb.get("subjects", []) or []:
                    if subject.get("kind") == "User" and subject.get("name") in EXPECTED_ROLES:
                        found_roles[subject.get("name")] = role

            for user, expected_role in EXPECTED_ROLES.items():
                actual_role = found_roles.get(user)
                if actual_role is None:
                    step.add_error(f"Nessun permesso trovato per l'utente '{user}'")
                elif actual_role != expected_role:
                    step.add_error(
                        f"'{user}' ha il ruolo '{actual_role}', atteso '{expected_role}'"
                    )


if __name__ == "__main__":
    main()
