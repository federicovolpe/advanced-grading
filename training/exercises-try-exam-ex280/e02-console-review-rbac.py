"""
Try-exam EX280, 2 — gruppo, progetto con RoleBinding e quota
(tema: "CONFIGURE IDENTITY PROVIDER", punti 3-4).

Le RoleBinding si cercano per contenuto (ruolo + soggetto), non per nome:
`oc adm policy` e la web console le chiamano in modo diverso. La quota deve
contenere SOLO pods: 2 (il tema, svolto da console, dice di togliere tutto
il resto dal modello proposto).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ex280_common import (
    CHAPTER, SETUP_TIMEOUT, GradingStep, oc, oc_get_json, track_lock,
    OWNER_LABEL, require_cluster_admin, ensure_absent_project,
    check_project_exists, find_rolebinding, parse_quantity, run_cli,
)

SLUG = "e02"
PROJECT = "console-review"
GROUP = "app-team"
GROUP_USERS = ["developer", "dba"]

TITLE = "2) Gruppo app-team, progetto console-review, RoleBinding e quota"

TASK = f"""\
  - Crea il gruppo {GROUP} che contiene gli utenti {' e '.join(GROUP_USERS)}.
  - Crea il progetto {PROJECT}, con:
      - una role binding view per l'utente tester
      - una role binding edit per il gruppo {GROUP}
  - Imposta sul progetto una resource quota che limiti il progetto a
    due pod (e nient'altro).

Puoi lavorare da CLI o dalla web console (User Management -> Groups,
Administration -> ResourceQuotas).
"""

SOLUTION = f"""\
oc adm groups new {GROUP} {' '.join(GROUP_USERS)}

oc new-project {PROJECT}
oc adm policy add-role-to-user view tester -n {PROJECT}
oc adm policy add-role-to-group edit {GROUP} -n {PROJECT}

oc create quota {PROJECT}-quota --hard=pods=2 -n {PROJECT}

Verifica:
  oc get rolebindings -n {PROJECT} -o wide
  oc describe quota -n {PROJECT}
"""


def setup():
    require_cluster_admin()
    with track_lock():
        ensure_absent_project(PROJECT)
        oc("delete", "group", GROUP, "--ignore-not-found")


def grade():
    with GradingStep(f"Il gruppo {GROUP} contiene {', '.join(GROUP_USERS)}") as step:
        group = oc_get_json("group", GROUP)
        if not group:
            step.fail(f"Gruppo '{GROUP}' non trovato")
        else:
            members = group.get("users") or []
            for user in GROUP_USERS:
                if user not in members:
                    step.add_error(f"manca l'utente {user} (membri: {members})")

    check_project_exists(PROJECT)

    with GradingStep(f"L'utente tester ha il ruolo view in {PROJECT}") as step:
        if not find_rolebinding(PROJECT, "view", "User", "tester"):
            step.add_error("nessuna RoleBinding view -> User tester")

    with GradingStep(f"Il gruppo {GROUP} ha il ruolo edit in {PROJECT}") as step:
        if not find_rolebinding(PROJECT, "edit", "Group", GROUP):
            step.add_error(f"nessuna RoleBinding edit -> Group {GROUP}")

    with GradingStep(f"Una resource quota limita {PROJECT} a 2 pod (solo pods)") as step:
        quotas = (oc_get_json("resourcequota", "-n", PROJECT) or {}).get("items", [])
        hards = [q.get("spec", {}).get("hard") or {} for q in quotas]
        match = [h for h in hards if parse_quantity(h.get("pods")) == 2]
        if not quotas:
            step.fail("Nessuna ResourceQuota nel progetto")
        elif not match:
            step.add_error(f"nessuna quota con pods: 2 (trovate: {hards})")
        else:
            extra = sorted(set(match[0]) - {"pods"})
            if extra:
                step.add_error(f"la quota limita anche {extra}: lascia solo pods")


def cleanup():
    with track_lock():
        # Progetto e gruppo li crea lo studente, quindi non hanno l'etichetta
        # di proprieta': senza etichetta sono suoi; con, li ha gia' ricreati
        # il setup() dell'es. 3 (che gira in parallelo a questo cleanup).
        ns = oc_get_json("namespace", PROJECT)
        if ns and not (ns["metadata"].get("labels") or {}).get(OWNER_LABEL):
            oc("delete", "project", PROJECT, "--wait=false")
        group = oc_get_json("group", GROUP)
        if group and not (group["metadata"].get("labels") or {}).get(OWNER_LABEL):
            oc("delete", "group", GROUP, "--ignore-not-found")


if __name__ == "__main__":
    run_cli(setup, grade, cleanup)
