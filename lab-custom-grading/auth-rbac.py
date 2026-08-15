#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato auth-rbac, sprovvisto di `lab grade`
ufficiale (la classe AuthRbac nel pacchetto do280 implementa solo
start()/finish(), non grade()).

materials/labs/auth-rbac e materials/solutions/auth-rbac sono vuote nella
cache di questa macchina: la specifica qui sotto viene interamente dal testo
della guida studente (DO280-RHOCP4.18-en-1-20251205, sezione 3.4 "Guided
Exercise: Define and Apply Permissions with RBAC", pag. 130-134), che
fortunatamente riporta ogni comando eseguito dallo studente parola per
parola. Riassunto della procedura gradata:

- Passo 2: rimuovere il cluster role self-provisioner dal gruppo virtuale
  system:authenticated:oauth (cancella il clusterrolebinding
  "self-provisioners"); passo 8: ripristinarlo con
  `oc adm policy add-cluster-role-to-group --rolebinding-name
  self-provisioners self-provisioner system:authenticated:oauth`. Lo stato
  FINALE atteso (dopo il passo 8) e' quindi identico a quello iniziale:
  self-provisioners esiste di nuovo.
- Passo 3: creare il progetto auth-rbac e assegnare il ruolo admin
  all'utente leader (`oc policy add-role-to-user admin leader`).
- Passo 4: creare i gruppi dev-group (membro: developer) e qa-group
  (membro: qa-engineer) con `oc adm groups new` / `add-users`.
- Passo 5: come utente leader, assegnare il ruolo edit al gruppo dev-group e
  il ruolo view al gruppo qa-group nel progetto auth-rbac
  (`oc policy add-role-to-group edit dev-group` / `view qa-group`).
- Passi 6-7: verifiche comportamentali (developer puo' fare deploy ma non
  gestire i permessi, qa-engineer puo' solo leggere) che dipendono dal login
  effettivo dei singoli utenti IDM durante l'esercizio, non da uno stato
  finale persistente e verificabile via `oc get` con il contesto admin:
  NON gradati qui, coerentemente con la regola d'oro (non inventare un modo
  di simulare il permesso se il testo non fornisce un riscontro oggettivo
  stabile - vedi nota in fondo al file).

I nomi di RoleBinding generati da `oc policy add-role-to-*` non sono
deterministici al 100% (il testo stesso mostra un esempio con suffisso
"-0" in caso di collisione, es. "admin-0"): per questo, come in
storage-configs.py, la ricerca avviene per caratteristiche (roleRef +
subject), non per nome fisso.

Uso: auth-rbac.py [nome-progetto]   (default: auth-rbac)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "auth-rbac"

SELFPROVISIONER_ROLE = "self-provisioner"
SELFPROVISIONER_GROUP = "system:authenticated:oauth"


def group_members(project_ignored, group_name):
    """Ritorna la lista utenti (campo 'users') del Group, o None se non
    esiste."""
    group = oc_get_json("group", group_name)
    if group is None:
        return None
    return group.get("users") or []


def find_rolebinding(rolebindings, role_name, subject_kind, subject_name):
    """Cerca, fra i RoleBinding del progetto, quello il cui roleRef punta al
    ClusterRole `role_name` e che ha fra i subjects quello indicato. Non
    assume il nome del RoleBinding, generato automaticamente da
    `oc policy add-role-to-*` e non deterministico in caso di collisioni
    (vedi esempio "admin-0" nella guida)."""
    if not rolebindings:
        return None
    for rb in rolebindings.get("items", []):
        role_ref = rb.get("roleRef", {})
        if role_ref.get("kind") != "ClusterRole" or role_ref.get("name") != role_name:
            continue
        for subj in rb.get("subjects", []) or []:
            if subj.get("kind") == subject_kind and subj.get("name") == subject_name:
                return rb
    return None


def find_clusterrolebinding(role_name, subject_kind, subject_name):
    """Come find_rolebinding, ma cerca fra i ClusterRoleBinding (usato per
    il ripristino di self-provisioners, passo 8)."""
    # Primo tentativo per nome esatto: il comando della guida usa
    # --rolebinding-name self-provisioners, quindi il nome e' deterministico
    # se lo studente segue la guida alla lettera.
    crb = oc_get_json("clusterrolebinding", "self-provisioners")
    if crb is not None:
        role_ref = crb.get("roleRef", {})
        if role_ref.get("name") == role_name:
            for subj in crb.get("subjects", []) or []:
                if subj.get("kind") == subject_kind and subj.get("name") == subject_name:
                    return crb
    # Fallback: cerca fra tutti i ClusterRoleBinding senza assumere il nome.
    all_crbs = oc_get_json("clusterrolebinding")
    if not all_crbs:
        return None
    for item in all_crbs.get("items", []):
        role_ref = item.get("roleRef", {})
        if role_ref.get("name") != role_name:
            continue
        for subj in item.get("subjects", []) or []:
            if subj.get("kind") == subject_kind and subj.get("name") == subject_name:
                return item
    return None


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(
        "Il gruppo dev-group esiste e contiene l'utente developer"
    ) as step:
        members = group_members(project, "dev-group")
        if members is None:
            step.fail("Group 'dev-group' non trovato")
        elif "developer" not in members:
            step.add_error(
                f"L'utente 'developer' non e' membro di dev-group "
                f"(membri attuali: {members})"
            )

    with GradingStep(
        "Il gruppo qa-group esiste e contiene l'utente qa-engineer"
    ) as step:
        members = group_members(project, "qa-group")
        if members is None:
            step.fail("Group 'qa-group' non trovato")
        elif "qa-engineer" not in members:
            step.add_error(
                f"L'utente 'qa-engineer' non e' membro di qa-group "
                f"(membri attuali: {members})"
            )

    rolebindings = oc_get_json("rolebinding", "-n", project)

    with GradingStep(
        "L'utente leader ha il ruolo admin sul progetto"
    ) as step:
        if rolebindings is None:
            step.fail(f"Impossibile leggere i RoleBinding nel progetto '{project}'")
        elif find_rolebinding(rolebindings, "admin", "User", "leader") is None:
            step.add_error(
                "Nessun RoleBinding assegna il ClusterRole 'admin' "
                "all'utente 'leader' nel progetto"
            )

    with GradingStep(
        "Il gruppo dev-group ha il ruolo edit sul progetto"
    ) as step:
        if rolebindings is None:
            step.fail()
        elif find_rolebinding(rolebindings, "edit", "Group", "dev-group") is None:
            step.add_error(
                "Nessun RoleBinding assegna il ClusterRole 'edit' "
                "al gruppo 'dev-group' nel progetto"
            )

    with GradingStep(
        "Il gruppo qa-group ha il ruolo view sul progetto"
    ) as step:
        if rolebindings is None:
            step.fail()
        elif find_rolebinding(rolebindings, "view", "Group", "qa-group") is None:
            step.add_error(
                "Nessun RoleBinding assegna il ClusterRole 'view' "
                "al gruppo 'qa-group' nel progetto"
            )

    with GradingStep(
        "I privilegi di creazione progetti sono stati ripristinati "
        "(cluster role binding self-provisioners)"
    ) as step:
        crb = find_clusterrolebinding(
            SELFPROVISIONER_ROLE, "Group", SELFPROVISIONER_GROUP
        )
        if crb is None:
            step.add_error(
                f"Nessun ClusterRoleBinding assegna il ClusterRole "
                f"'{SELFPROVISIONER_ROLE}' al gruppo "
                f"'{SELFPROVISIONER_GROUP}' (passo 8 della guida: "
                "'oc adm policy add-cluster-role-to-group --rolebinding-name "
                "self-provisioners self-provisioner system:authenticated:oauth')"
            )

    # NON gradato (nessun riscontro oggettivo stabile nel testo):
    # - che developer NON possa modificare i RoleBinding (passo 6.3) e che
    #   qa-engineer NON possa scalare il deployment (passo 7.2): sono
    #   verifiche comportamentali fatte dallo studente con il proprio login
    #   IDM, il cui esito dipende dai permessi gia' verificati sopra
    #   (assenza di RoleBinding aggiuntivi per questi utenti/gruppi) e non
    #   aggiungono un check indipendente senza autenticarsi come quegli
    #   utenti, cosa che questo script non fa per restare in sola lettura
    #   con le credenziali dell'utente che lancia `lab grade`.
    # - il deployment httpd creato da developer al passo 6.2: e' solo una
    #   dimostrazione dei permessi di edit gia' verificati sopra, non un
    #   requisito RBAC in se'; gradarlo rischierebbe di penalizzare chi ha
    #   completato la parte di RBAC ma non ha eseguito quel passo dimostrativo.


if __name__ == "__main__":
    main()
