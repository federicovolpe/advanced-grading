#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato appsec-prune (DO280), sprovvisto di
`lab grade` ufficiale (la classe AppsecPrune nel pacchetto do280 implementa
solo start()/finish(), non grade() - vedi do280/appsec-prune.py).

L'esercizio usa DUE progetti: quello di lavoro dello studente
("appsec-prune", dove va creato/completato configmap-prune.yaml e
cronjob-prune.yaml, e dove vanno impostati i permessi RBAC) e un progetto
"prune-apps" pre-popolato dallo start() con tre Deployment (nginx-ubi7/8/9)
che lo studente elimina manualmente al passo 2.4 della guida (cosi' il nodo
ha immagini "orfane" che il CronJob puo' rimuovere).

ATTENZIONE - discrepanza tra le fonti: materials/solutions/appsec-prune/
rbac-prune.yaml definisce un ServiceAccount "image-pruner-sa" + un Role
namespaced limitato a "use" della SCC privileged. Il testo della guida
studente (Capitolo 8.6, DO280-RHOCP4.18-en-1-20251205, pag. 372-378), pero',
NON fa mai riferimento a questo file e usa invece un percorso interamente
imperativo:
    oc create sa image-pruner
    oc adm policy add-scc-to-user privileged -z image-pruner
    oc adm policy add-cluster-role-to-user cluster-admin -z image-pruner
con `serviceAccountName: image-pruner` aggiunto al CronJob. Questo e' anche
coerente con l'errore mostrato nella guida ("cannot list resource nodes...
at the cluster scope"): lo script di maintenance fa `oc get nodes` e `oc
debug node/...`, risorse cluster-scoped, quindi serve un ClusterRoleBinding
(cluster-admin), non solo un Role namespaced come in rbac-prune.yaml. Il
file rbac-prune.yaml sembra quindi non allineato a questa revisione della
guida: seguendo la regola del progetto (la guida studente e' la fonte piu'
affidabile quando in conflitto con altri materiali), questo script grada il
percorso descritto nella guida, non rbac-prune.yaml. Anche il tag immagine
diverge (soluzione: origin-cli:4.14, guida: origin-cli:4.18): per questo il
controllo sull'immagine verifica solo la sottostringa "origin-cli", non il
tag esatto.

Uso: appsec-prune.py [nome-progetto] [nome-progetto-prune-apps]
     (default: appsec-prune, prune-apps)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "appsec-prune"
APPS_NAMESPACE = "prune-apps"

EXPECTED_CM_NAME = "maintenance"
# Frammenti chiave dello script di pruning richiesti dalla guida (passo 3.1):
# non pretendiamo un match byte-per-byte per tollerare differenze di
# whitespace/commenti, ma questi tre comandi sono la logica essenziale.
EXPECTED_CM_SNIPPETS = [
    "oc get nodes",
    "oc debug",
    "crictl rmi --prune",
]

EXPECTED_CRONJOB_NAME = "image-pruner"
EXPECTED_SCHEDULE = "*/4 * * * *"
EXPECTED_IMAGE_SUBSTR = "origin-cli"
EXPECTED_COMMAND_SUFFIX = "/opt/maintenance.sh"
EXPECTED_VOLUME_MOUNT = "/opt"
DEFAULT_SA_NAMES = {"default", ""}

EXPECTED_SCC_CLUSTERROLE = "system:openshift:scc:privileged"
EXPECTED_CLUSTER_ADMIN_ROLE = "cluster-admin"

# Deployment che lo studente deve eliminare in prune-apps al passo 2.4,
# cosi' che le relative immagini nginx diventino "orfane" per il pruning.
PRUNED_DEPLOYMENTS = ["nginx-ubi7", "nginx-ubi8", "nginx-ubi9"]


def get_container(cronjob, name="crictl"):
    containers = (
        cronjob["spec"]["jobTemplate"]["spec"]["template"]["spec"].get("containers")
        or []
    )
    for c in containers:
        if c.get("name") == name:
            return c
    return containers[0] if containers else None


def find_role_binding(project, role_kind, role_name, sa_name, sa_namespace):
    """Cerca, fra RoleBinding (namespaced) e ClusterRoleBinding, uno il cui
    roleRef punta a role_name (di tipo role_kind) e che ha fra i subjects il
    ServiceAccount indicato. `oc adm policy add-scc-to-user`/
    `add-cluster-role-to-user` non garantiscono un nome fisso al binding
    creato, quindi cerchiamo per contenuto, non per nome (come in
    storage-configs.py)."""
    kinds = ["rolebinding", "clusterrolebinding"] if role_kind is None else [role_kind]
    for kind in kinds:
        args = [kind] if kind == "clusterrolebinding" else [kind, "-n", project]
        bindings = oc_get_json(*args)
        if not bindings:
            continue
        for b in bindings.get("items", []):
            role_ref = b.get("roleRef", {})
            if role_ref.get("name") != role_name:
                continue
            for subj in b.get("subjects", []) or []:
                if (
                    subj.get("kind") == "ServiceAccount"
                    and subj.get("name") == sa_name
                    and (subj.get("namespace") in (sa_namespace, None, ""))
                ):
                    return b
    return None


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    apps_project = sys.argv[2] if len(sys.argv) > 2 else APPS_NAMESPACE
    print(
        f"🔧 Grading personalizzato per '{LAB_NAME}' "
        f"(progetto: {project}, progetto apps: {apps_project})"
    )

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    with GradingStep(f"Il progetto {apps_project} esiste") as step:
        if not project_exists(apps_project):
            step.fail(f"Progetto '{apps_project}' non trovato")

    # --- ConfigMap con lo script di pruning (passo 3.1/3.2) ---
    configmap = oc_get_json("configmap", EXPECTED_CM_NAME, "-n", project)
    with GradingStep(f"La ConfigMap '{EXPECTED_CM_NAME}' contiene lo script corretto") as step:
        if configmap is None:
            step.fail(f"ConfigMap '{EXPECTED_CM_NAME}' non trovata nel progetto {project}")
        else:
            script = (configmap.get("data") or {}).get("maintenance.sh", "")
            if not script:
                step.fail("La chiave 'maintenance.sh' e' assente o vuota nella ConfigMap")
            else:
                for snippet in EXPECTED_CM_SNIPPETS:
                    if snippet not in script:
                        step.add_error(
                            f"Nello script maintenance.sh manca '{snippet}'"
                        )

    # --- CronJob (passi 3.3/3.4 e 4.4/4.5) ---
    cronjob = oc_get_json("cronjob", EXPECTED_CRONJOB_NAME, "-n", project)
    container = None
    sa_name = None

    with GradingStep(f"Il CronJob '{EXPECTED_CRONJOB_NAME}' esiste") as step:
        if cronjob is None:
            step.fail(f"CronJob '{EXPECTED_CRONJOB_NAME}' non trovato nel progetto {project}")
        else:
            container = get_container(cronjob)
            if container is None:
                step.fail("Nessun container trovato nel jobTemplate del CronJob")

    with GradingStep("Lo schedule del CronJob e' corretto") as step:
        if cronjob is None:
            step.fail()
        else:
            schedule = cronjob["spec"].get("schedule")
            if schedule != EXPECTED_SCHEDULE:
                step.add_error(
                    f"schedule atteso '{EXPECTED_SCHEDULE}', trovato '{schedule}'"
                )

    with GradingStep("Il container del CronJob usa l'immagine e il comando corretti") as step:
        if container is None:
            step.fail()
        else:
            image = container.get("image", "")
            if EXPECTED_IMAGE_SUBSTR not in image:
                step.add_error(
                    f"L'immagine deve contenere '{EXPECTED_IMAGE_SUBSTR}' "
                    f"(trovata: '{image}')"
                )
            command = container.get("command") or []
            if not any(c.endswith(EXPECTED_COMMAND_SUFFIX) for c in command):
                step.add_error(
                    f"Il comando deve eseguire '{EXPECTED_COMMAND_SUFFIX}' "
                    f"(trovato: {command})"
                )

    with GradingStep("Il volume con la ConfigMap 'maintenance' e' montato su /opt") as step:
        if cronjob is None or container is None:
            step.fail()
        else:
            pod_spec = cronjob["spec"]["jobTemplate"]["spec"]["template"]["spec"]
            volumes = pod_spec.get("volumes") or []
            mounts = container.get("volumeMounts") or []
            mount_names = {
                m.get("name") for m in mounts if m.get("mountPath") == EXPECTED_VOLUME_MOUNT
            }
            has_volume = any(
                v.get("name") in mount_names
                and v.get("configMap", {}).get("name") == EXPECTED_CM_NAME
                for v in volumes
            )
            if not has_volume:
                step.add_error(
                    f"Nessun volume da ConfigMap '{EXPECTED_CM_NAME}' risulta montato "
                    f"su {EXPECTED_VOLUME_MOUNT}"
                )

    with GradingStep(
        "Il CronJob usa un ServiceAccount dedicato (non 'default')"
    ) as step:
        if cronjob is None:
            step.fail()
        else:
            pod_spec = cronjob["spec"]["jobTemplate"]["spec"]["template"]["spec"]
            sa_name = pod_spec.get("serviceAccountName")
            if sa_name in DEFAULT_SA_NAMES or sa_name is None:
                step.add_error(
                    "serviceAccountName non impostato (o lasciato 'default'): "
                    "il pod del CronJob fallira' per mancanza di permessi "
                    "(vedi passo 4.4 della guida)"
                )

    # --- ServiceAccount e RBAC (passi 4.1-4.4) ---
    with GradingStep("Il ServiceAccount usato dal CronJob esiste nel progetto") as step:
        if not sa_name or sa_name in DEFAULT_SA_NAMES:
            step.fail()
        elif oc_get_json("sa", sa_name, "-n", project) is None:
            step.fail(f"ServiceAccount '{sa_name}' non trovato nel progetto {project}")

    with GradingStep(
        f"Il ServiceAccount ha la SCC 'privileged' (ClusterRole {EXPECTED_SCC_CLUSTERROLE})"
    ) as step:
        if not sa_name or sa_name in DEFAULT_SA_NAMES:
            step.fail()
        else:
            binding = find_role_binding(
                project, None, EXPECTED_SCC_CLUSTERROLE, sa_name, project
            )
            if binding is None:
                step.add_error(
                    f"Nessun (Cluster)RoleBinding assegna '{EXPECTED_SCC_CLUSTERROLE}' "
                    f"al ServiceAccount '{sa_name}' (vedi passo 4.2: "
                    "'oc adm policy add-scc-to-user privileged -z <sa>')"
                )

    with GradingStep(
        f"Il ServiceAccount ha il ClusterRole '{EXPECTED_CLUSTER_ADMIN_ROLE}'"
    ) as step:
        if not sa_name or sa_name in DEFAULT_SA_NAMES:
            step.fail()
        else:
            binding = find_role_binding(
                project, "clusterrolebinding", EXPECTED_CLUSTER_ADMIN_ROLE, sa_name, project
            )
            if binding is None:
                step.add_error(
                    f"Nessun ClusterRoleBinding assegna '{EXPECTED_CLUSTER_ADMIN_ROLE}' "
                    f"al ServiceAccount '{sa_name}' (vedi passo 4.3: "
                    "'oc adm policy add-cluster-role-to-user cluster-admin -z <sa>'). "
                    "Necessario perche' lo script esegue 'oc get nodes'/'oc debug node' "
                    "(risorse cluster-scoped)."
                )

    # --- Pulizia dei Deployment nginx in prune-apps (passo 2.4) ---
    with GradingStep(
        f"I Deployment nginx-ubi7/8/9 sono stati eliminati in {apps_project}"
    ) as step:
        for name in PRUNED_DEPLOYMENTS:
            if oc_get_json("deployment", name, "-n", apps_project) is not None:
                step.add_error(
                    f"Deployment '{name}' ancora presente in '{apps_project}': "
                    "andava eliminato al passo 2.4 per rendere orfana la sua immagine"
                )


if __name__ == "__main__":
    main()
