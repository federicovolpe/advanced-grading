#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato DO380 auth-sync (Cap. 1.6,
"Automate LDAP Group Synchronization"), sprovvisto di `lab grade` ufficiale.

Fonte principale: testo della guida studente (DO380-RHOCP4.18-en-2-20260525,
pag. 46-49), che riporta ogni comando eseguito dallo studente parola per
parola. materials/solutions/auth-sync/ nella cache esiste ma e' in parte
INCOERENTE con la guida (i file rhds-group-sa.yaml/rhds-cluster-role.yaml/
rhds-cluster-role-binding.yaml usano il namespace "auth-group-sync", che non
compare mai nel testo ne' viene creato da nessun comando o da start()):
seguito il testo della guida, piu' affidabile (stesso criterio gia'
applicato in appsec-prune.py per DO280). Tutte le risorse dei passi 3-6
vengono create nel progetto "auth-rhds-sync" (creato dallo studente al
passo 2.4 con `oc new-project auth-rhds-sync`), non nel progetto
dell'esercizio "auth-sync".

Il CronJob sincronizza il gruppo ogni minuto (schedule "*/1 * * * *"), quindi
lo stato del Group "administrators" e' verificabile "sul momento" (si veda
la nota in CLAUDE.md sui check dal vivo): dopo `lab finish`, che cancella il
progetto auth-rhds-sync e il gruppo administrators, e' corretto che tutto
torni FAIL.

Non gradato: il ClusterRole potrebbe usare solo apiGroup "" o anche
"user.openshift.io" per la risorsa "groups" (il comando della guida usa
`--resource groups` senza specificare apiGroup, quindi il default e' "");
si verifica solo che il verbo set richiesto sia presente sulla risorsa
"groups", indipendentemente da come e' partizionato fra le regole.

Uso: auth-sync.py [nome-progetto-sync]   (default: auth-rhds-sync)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "auth-sync"
SYNC_NAMESPACE_DEFAULT = "auth-rhds-sync"

SA_NAME = "rhds-group-syncer"
CLUSTERROLE_NAME = "rhds-group-syncer"
SECRET_NAME = "rhds-secret"
CONFIGMAP_NAME = "rhds-config"
CRONJOB_NAME = "rhds-group-sync"
CRON_COMMAND_SNIPPET = "oc adm groups sync"

GROUP_NAME = "administrators"
GROUP_USER = "kristendelgado"

REQUIRED_VERBS = {"get", "list", "create", "update"}


def clusterrole_has_verbs_on_groups(clusterrole):
    """Verifica che, fra tutte le regole del ClusterRole, la risorsa
    'groups' abbia almeno i verbi richiesti (accorpando piu' regole)."""
    verbs_found = set()
    for rule in clusterrole.get("rules", []):
        resources = rule.get("resources", []) or []
        if "groups" in resources:
            verbs_found.update(rule.get("verbs", []) or [])
    return REQUIRED_VERBS.issubset(verbs_found)


def clusterrolebinding_grants(role_name, subject_kind, subject_name, subject_namespace=None):
    """Cerca fra tutti i ClusterRoleBinding uno che assegni `role_name` al
    subject indicato (nome non deterministico al 100%: la guida usa
    `oc adm policy add-cluster-role-to-user ... -z` che genera un nome
    prevedibile, ma si cerca comunque per caratteristiche, non per nome)."""
    all_crbs = oc_get_json("clusterrolebinding")
    if not all_crbs:
        return None
    for item in all_crbs.get("items", []):
        role_ref = item.get("roleRef", {})
        if role_ref.get("kind") != "ClusterRole" or role_ref.get("name") != role_name:
            continue
        for subj in item.get("subjects", []) or []:
            if subj.get("kind") != subject_kind or subj.get("name") != subject_name:
                continue
            if subject_namespace and subj.get("namespace") != subject_namespace:
                continue
            return item
    return None


def main():
    sync_project = sys.argv[1] if len(sys.argv) > 1 else SYNC_NAMESPACE_DEFAULT
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto sync: {sync_project})")

    with GradingStep(f"Il progetto {sync_project} esiste") as step:
        if not project_exists(sync_project):
            step.fail(f"Progetto '{sync_project}' non trovato")

    with GradingStep(
        f"Il service account {SA_NAME} esiste nel progetto {sync_project}"
    ) as step:
        if oc_get_json("sa", SA_NAME, "-n", sync_project) is None:
            step.fail(f"ServiceAccount '{SA_NAME}' non trovato in '{sync_project}'")

    with GradingStep(
        f"Il ClusterRole {CLUSTERROLE_NAME} concede get/list/create/update su groups"
    ) as step:
        clusterrole = oc_get_json("clusterrole", CLUSTERROLE_NAME)
        if clusterrole is None:
            step.fail(f"ClusterRole '{CLUSTERROLE_NAME}' non trovato")
        elif not clusterrole_has_verbs_on_groups(clusterrole):
            step.add_error(
                f"Il ClusterRole '{CLUSTERROLE_NAME}' non concede tutti i verbi "
                f"richiesti ({', '.join(sorted(REQUIRED_VERBS))}) sulla risorsa 'groups'"
            )

    with GradingStep(
        f"Il ClusterRole {CLUSTERROLE_NAME} e' assegnato al service account {SA_NAME}"
    ) as step:
        crb = clusterrolebinding_grants(
            CLUSTERROLE_NAME, "ServiceAccount", SA_NAME, sync_project
        )
        if crb is None:
            step.add_error(
                f"Nessun ClusterRoleBinding assegna il ClusterRole "
                f"'{CLUSTERROLE_NAME}' al ServiceAccount '{SA_NAME}' "
                f"(passo 3.3: 'oc adm policy add-cluster-role-to-user "
                f"{CLUSTERROLE_NAME} -z {SA_NAME}')"
            )

    with GradingStep(f"Il secret {SECRET_NAME} esiste con la chiave bindPassword") as step:
        secret = oc_get_json("secret", SECRET_NAME, "-n", sync_project)
        if secret is None:
            step.fail(f"Secret '{SECRET_NAME}' non trovato in '{sync_project}'")
        elif "bindPassword" not in (secret.get("data") or {}):
            step.add_error("Il secret non contiene la chiave 'bindPassword'")

    with GradingStep(
        f"La configmap {CONFIGMAP_NAME} esiste con le chiavi rhds-sync.yaml e ca.crt"
    ) as step:
        cm = oc_get_json("configmap", CONFIGMAP_NAME, "-n", sync_project)
        if cm is None:
            step.fail(f"ConfigMap '{CONFIGMAP_NAME}' non trovata in '{sync_project}'")
        else:
            data = cm.get("data") or {}
            missing = [k for k in ("rhds-sync.yaml", "ca.crt") if k not in data]
            if missing:
                step.add_error(f"Chiavi mancanti nella configmap: {', '.join(missing)}")
            elif "url: ldaps://rhds.ocp4.example.com:636" not in data.get("rhds-sync.yaml", ""):
                step.add_error(
                    "Il file rhds-sync.yaml nella configmap non punta a "
                    "'ldaps://rhds.ocp4.example.com:636'"
                )

    with GradingStep(
        f"Il cron job {CRONJOB_NAME} e' configurato per sincronizzare i gruppi ogni minuto"
    ) as step:
        cronjob = oc_get_json("cronjob", CRONJOB_NAME, "-n", sync_project)
        if cronjob is None:
            step.fail(f"CronJob '{CRONJOB_NAME}' non trovato in '{sync_project}'")
        else:
            spec = cronjob.get("spec", {})
            if spec.get("schedule") != "*/1 * * * *":
                step.add_error(
                    f"Schedule inatteso: '{spec.get('schedule')}' (atteso '*/1 * * * *')"
                )
            containers = (
                spec.get("jobTemplate", {})
                .get("spec", {})
                .get("template", {})
                .get("spec", {})
                .get("containers", [])
            )
            command_text = " ".join(
                str(c) for cont in containers for c in cont.get("command", [])
            )
            if CRON_COMMAND_SNIPPET not in command_text:
                step.add_error(
                    f"Nessun container del cron job esegue '{CRON_COMMAND_SNIPPET}'"
                )
            sa_used = (
                spec.get("jobTemplate", {})
                .get("spec", {})
                .get("template", {})
                .get("spec", {})
                .get("serviceAccountName")
            )
            if sa_used != SA_NAME:
                step.add_error(
                    f"Il cron job non usa il service account '{SA_NAME}' "
                    f"(trovato: '{sa_used}')"
                )

    with GradingStep(
        f"Il gruppo {GROUP_NAME} e' sincronizzato da LDAP e contiene {GROUP_USER}"
    ) as step:
        group = oc_get_json("group", GROUP_NAME)
        if group is None:
            step.fail(
                f"Group '{GROUP_NAME}' non trovato (il cron job non ha ancora "
                "sincronizzato, o non e' configurato correttamente)"
            )
        elif GROUP_USER not in (group.get("users") or []):
            step.add_error(
                f"L'utente '{GROUP_USER}' non e' membro del gruppo '{GROUP_NAME}' "
                f"(membri attuali: {group.get('users')})"
            )

    with GradingStep(
        f"Il gruppo {GROUP_NAME} ha il ClusterRole cluster-admin"
    ) as step:
        crb = clusterrolebinding_grants("cluster-admin", "Group", GROUP_NAME)
        if crb is None:
            step.add_error(
                f"Nessun ClusterRoleBinding assegna il ClusterRole 'cluster-admin' "
                f"al gruppo '{GROUP_NAME}' (passo 6.1: 'oc adm policy "
                f"add-cluster-role-to-group cluster-admin {GROUP_NAME}')"
            )


if __name__ == "__main__":
    main()
