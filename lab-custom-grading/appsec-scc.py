#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato appsec-scc (DO280), sprovvisto di
`lab grade` ufficiale (la classe AppsecScc nel pacchetto do280 implementa
solo start()/finish(), non grade()).

materials/labs/appsec-scc/ e materials/solutions/appsec-scc/ sono vuote in
cache: l'unica fonte disponibile e' il testo della guida studente (guided
exercise "Control Application Permissions with Security Context
Constraints"), da cui sono stati presi tutti i nomi/valori verificati qui:

- Deployment "gitlab" creato con `oc new-app --name gitlab --image
  registry.ocp4.example.com:8443/redhattraining/gitlab-ce:8.4.3-ce.0`
  (fallisce inizialmente perche' l'immagine richiede privilegi root).
- ServiceAccount "gitlab-sa" creato con `oc create sa gitlab-sa`.
- La SCC "anyuid" (built-in, non creata dallo studente) viene concessa al
  service account con `oc adm policy add-scc-to-user anyuid -z gitlab-sa`,
  che crea una RoleBinding nel namespace verso la ClusterRole
  "system:openshift:scc:anyuid".
- Il deployment viene aggiornato con `oc set serviceaccount deployment/
  gitlab gitlab-sa`, dopo di che il pod passa a Running.
- Il servizio viene esposto con `oc expose service/gitlab --port 80
  --hostname gitlab.apps.ocp4.example.com` (route di nome "gitlab").

Non essendo una SCC "custom" creata dallo studente (anyuid e' un oggetto
built-in del cluster, presente a prescindere da questo esercizio), NON si
gradua la sua sola esistenza: si verifica invece l'azione concreta dello
studente, cioe' che gitlab-sa abbia effettivamente ricevuto il permesso
(RoleBinding/ClusterRoleBinding verso la ClusterRole
system:openshift:scc:anyuid) e che il pod risultante sia stato ammesso sotto
quella SCC (annotazione openshift.io/scc, impostata da OpenShift stesso al
momento dell'ammissione del pod - un riscontro oggettivo, non un valore
inventato).

REGOLA D'ORO applicata: la guida non specifica un runAsUser/UID numerico
atteso (anyuid permette all'immagine di usare il proprio UID di default,
tipicamente root, ma non lo forza a un valore preciso) quindi quel campo
NON viene verificato: si verifica solo che la SCC applicata al pod sia
"anyuid" (annotazione), che e' il fatto oggettivo richiesto dall'esercizio.

Uso: appsec-scc.py [nome-progetto]   (default: appsec-scc)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "appsec-scc"
SA_NAME = "gitlab-sa"
SCC_NAME = "anyuid"
SCC_ROLE = f"system:openshift:scc:{SCC_NAME}"
DEPLOYMENT_NAME = "gitlab"
IMAGE_SUBSTR = "gitlab-ce"


def find_scc_role_binding(project, sa_name, role_name):
    """Cerca, tra le RoleBinding del progetto e le ClusterRoleBinding del
    cluster, una che leghi la ClusterRole system:openshift:scc:<scc> al
    service account indicato (comportamento di `oc adm policy
    add-scc-to-user <scc> -z <sa>`, che normalmente crea una RoleBinding
    namespaced ma su alcune versioni puo' generare una ClusterRoleBinding)."""
    def subjects_match(binding):
        role_ref = binding.get("roleRef", {})
        if role_ref.get("name") != role_name:
            return False
        for subj in binding.get("subjects", []) or []:
            if subj.get("kind") == "ServiceAccount" and subj.get("name") == sa_name:
                return True
        return False

    role_bindings = oc_get_json("rolebinding", "-n", project)
    if role_bindings:
        for rb in role_bindings.get("items", []):
            if subjects_match(rb):
                return rb

    cluster_role_bindings = oc_get_json("clusterrolebinding")
    if cluster_role_bindings:
        for crb in cluster_role_bindings.get("items", []):
            if subjects_match(crb):
                return crb

    return None


def find_route_for_service(project, service_name):
    routes = oc_get_json("route", "-n", project)
    if not routes or not service_name:
        return None
    for route in routes.get("items", []):
        if route.get("spec", {}).get("to", {}).get("name") == service_name:
            return route
    return None


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    sa = oc_get_json("sa", SA_NAME, "-n", project)
    with GradingStep(f"Il service account '{SA_NAME}' esiste") as step:
        if sa is None:
            step.fail(f"ServiceAccount '{SA_NAME}' non trovato nel progetto")

    binding = find_scc_role_binding(project, SA_NAME, SCC_ROLE)
    with GradingStep(
        f"La SCC '{SCC_NAME}' e' concessa al service account '{SA_NAME}'"
    ) as step:
        if sa is None:
            step.fail()
        elif binding is None:
            step.add_error(
                f"Nessuna RoleBinding/ClusterRoleBinding lega la ClusterRole "
                f"'{SCC_ROLE}' al service account '{SA_NAME}' "
                f"(atteso da 'oc adm policy add-scc-to-user {SCC_NAME} -z {SA_NAME}')"
            )

    deployment = oc_get_json("deployment", DEPLOYMENT_NAME, "-n", project)
    container = None
    with GradingStep(f"Il deployment '{DEPLOYMENT_NAME}' esiste e usa l'immagine gitlab-ce") as step:
        if deployment is None:
            step.fail(f"Deployment '{DEPLOYMENT_NAME}' non trovato nel progetto")
        else:
            containers = deployment["spec"]["template"]["spec"].get("containers", [])
            container = containers[0] if containers else None
            if container is None or IMAGE_SUBSTR not in container.get("image", ""):
                step.add_error(
                    f"Il container del deployment non usa un'immagine contenente "
                    f"'{IMAGE_SUBSTR}' (trovata: "
                    f"{container.get('image') if container else 'nessuna'})"
                )

    with GradingStep(
        f"Il deployment '{DEPLOYMENT_NAME}' usa il service account '{SA_NAME}'"
    ) as step:
        if deployment is None:
            step.fail()
        else:
            pod_spec = deployment["spec"]["template"]["spec"]
            sa_used = pod_spec.get("serviceAccountName") or pod_spec.get("serviceAccount")
            if sa_used != SA_NAME:
                step.add_error(
                    f"Il deployment usa il service account '{sa_used}', "
                    f"atteso '{SA_NAME}' (vedi 'oc set serviceaccount "
                    f"deployment/{DEPLOYMENT_NAME} {SA_NAME}')"
                )

    pods = oc_get_json("pod", "-n", project)
    gitlab_pod = None
    if pods and deployment is not None:
        for pod in pods.get("items", []):
            owner_refs = pod.get("metadata", {}).get("ownerReferences", []) or []
            labels = pod.get("metadata", {}).get("labels", {}) or {}
            # I pod del deployment appartengono a un ReplicaSet il cui nome
            # inizia con "<deployment>-"; in alternativa confrontiamo le
            # label del pod template.
            if any(
                ref.get("kind") == "ReplicaSet"
                and ref.get("name", "").startswith(f"{DEPLOYMENT_NAME}-")
                for ref in owner_refs
            ) or labels.get("deployment") == DEPLOYMENT_NAME:
                gitlab_pod = pod
                break

    with GradingStep(
        "Il pod dell'applicazione e' Running ed e' stato ammesso con la SCC 'anyuid'"
    ) as step:
        if deployment is None:
            step.fail()
        elif gitlab_pod is None:
            step.add_error(f"Nessun pod trovato per il deployment '{DEPLOYMENT_NAME}'")
        else:
            phase = gitlab_pod.get("status", {}).get("phase")
            if phase != "Running":
                step.add_error(f"Il pod ha fase '{phase}', atteso 'Running'")
            annotations = gitlab_pod.get("metadata", {}).get("annotations", {}) or {}
            applied_scc = annotations.get("openshift.io/scc")
            if applied_scc != SCC_NAME:
                step.add_error(
                    f"Il pod risulta ammesso con la SCC '{applied_scc}', "
                    f"atteso '{SCC_NAME}'"
                )

    # Verifica finale ("5. Verify that the gitlab application works" nella
    # guida): non blocchiamo il grading se la route non e' raggiungibile
    # subito, perche' l'immagine gitlab-ce impiega diversi minuti ad
    # avviarsi anche dopo che il pod passa a Running; il monitor rieseguira'
    # il check periodicamente.
    route = oc_get_json("route", DEPLOYMENT_NAME, "-n", project)
    if route is None:
        route = find_route_for_service(project, DEPLOYMENT_NAME)

    with GradingStep("L'applicazione gitlab e' esposta tramite una Route") as step:
        if deployment is None:
            step.fail()
        elif route is None:
            step.add_error(
                f"Nessuna Route trovata per il service '{DEPLOYMENT_NAME}' "
                f"(atteso da 'oc expose service/{DEPLOYMENT_NAME} --port 80')"
            )


if __name__ == "__main__":
    main()
