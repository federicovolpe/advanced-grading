#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato selfservice-projtemplate (DO280,
capitolo "Enabling Developer Self-service", sezione 6.6 "The Project
Template and the Self-provisioner Role"), sprovvisto di `lab grade`
ufficiale (la classe SelfserviceProjtemplate in do280 implementa solo
start()/finish(), non grade()).

A differenza della maggior parte degli esercizi DO180 in questo repo, qui
NON esiste un progetto OpenShift dedicato allo studente: start() copia i
file di lavoro in ~/DO280/labs/selfservice-projtemplate (solo filesystem
locale) e crea utenti/gruppo, ma non crea alcun namespace applicativo. Le
risorse da gradare sono tutte cluster-scoped o vivono in openshift-config:

- Un Template "project-request" nel namespace openshift-config, la cui
  struttura deve corrispondere a
  materials/solutions/selfservice-projtemplate/template.yaml: un oggetto
  Project (nome ${PROJECT_NAME}), una RoleBinding "admin" che lega la
  ClusterRole "admin" al gruppo "provisioners", e una LimitRange
  "max-memory" con default/defaultRequest/max di memoria a 1Gi per i
  Container (i valori di default/defaultRequest, non presenti nel
  limitrange.yaml di partenza incollato in ~/DO280/labs, vengono aggiunti
  dallo studente copiando l'output di `oc get limitrange max-memory -o
  yaml` come indicato al punto 8.2-8.3 della guida).
- La risorsa cluster projects.config.openshift.io/cluster, il cui
  spec.projectRequestTemplate.name deve puntare a quel template (punto 9.3).
- Il ClusterRoleBinding "self-provisioners" (nome confermato in
  do280.common.ocp.tasks.restore_selfprovisioner_clusterrole): il subject
  deve essere stato spostato dal gruppo di default
  "system:authenticated:oauth" al gruppo "provisioners" (punto 2.3), cosi'
  che solo i membri di quel gruppo possano auto-provisionarsi progetti.

I progetti temporanei usati durante l'esercizio (template-test, test)
vengono cancellati da cleanup()/finish() e non sono quindi gradati: sono
solo un banco di prova intermedio per lo studente, non lo stato finale
atteso.

Uso: selfservice-projtemplate.py [ignorato]
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json

LAB_NAME = "selfservice-projtemplate"
CRB_NAME = "self-provisioners"
CLUSTERROLE_NAME = "self-provisioner"
PROVISIONERS_GROUP = "provisioners"
DEFAULT_GROUP = "system:authenticated:oauth"
EXPECTED_MEMORY = "1Gi"


def find_object(template, kind):
    """Ritorna il primo oggetto di un dato kind nella lista objects del
    Template, o None se assente."""
    for obj in (template or {}).get("objects", []) or []:
        if obj.get("kind") == kind:
            return obj
    return None


def check_project_object(template, step):
    project_obj = find_object(template, "Project")
    if project_obj is None:
        step.add_error("Il template non definisce un oggetto Project")
        return
    name = project_obj.get("metadata", {}).get("name")
    if name != "${PROJECT_NAME}":
        step.add_error(
            "L'oggetto Project deve avere metadata.name = '${PROJECT_NAME}' "
            f"(trovato: {name!r})"
        )


def check_rolebinding_object(template, step):
    rb = find_object(template, "RoleBinding")
    if rb is None:
        step.add_error("Il template non definisce un oggetto RoleBinding")
        return
    role_ref = rb.get("roleRef", {})
    if role_ref.get("name") != "admin":
        step.add_error(
            "La RoleBinding deve referenziare la ClusterRole 'admin' "
            f"(trovato: {role_ref.get('name')!r})"
        )
    subjects = rb.get("subjects", []) or []
    has_provisioners = any(
        s.get("kind") == "Group" and s.get("name") == PROVISIONERS_GROUP
        for s in subjects
    )
    if not has_provisioners:
        step.add_error(
            "La RoleBinding deve avere come subject il gruppo "
            f"'{PROVISIONERS_GROUP}' (trovati: {subjects!r})"
        )
    namespace = rb.get("metadata", {}).get("namespace")
    if namespace != "${PROJECT_NAME}":
        step.add_error(
            "La RoleBinding deve essere creata in metadata.namespace = "
            f"'${{PROJECT_NAME}}' (trovato: {namespace!r})"
        )


def check_limitrange_object(template, step):
    lr = find_object(template, "LimitRange")
    if lr is None:
        step.add_error("Il template non definisce un oggetto LimitRange")
        return
    namespace = lr.get("metadata", {}).get("namespace")
    if namespace != "${PROJECT_NAME}":
        step.add_error(
            "La LimitRange deve essere creata in metadata.namespace = "
            f"'${{PROJECT_NAME}}' (trovato: {namespace!r})"
        )
    limits = lr.get("spec", {}).get("limits", []) or []
    container_limit = None
    for limit in limits:
        if limit.get("type") == "Container":
            container_limit = limit
            break
    if container_limit is None:
        step.add_error("La LimitRange non definisce un limite di type: Container")
        return
    for key in ("default", "defaultRequest", "max"):
        memory = container_limit.get(key, {}).get("memory")
        if memory != EXPECTED_MEMORY:
            step.add_error(
                f"Il limite '{key}.memory' deve essere {EXPECTED_MEMORY} "
                f"(trovato: {memory!r})"
            )


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    project_config = oc_get_json("projects.config.openshift.io", "cluster")
    template_name = None

    with GradingStep(
        "La risorsa projects.config.openshift.io/cluster referenzia un "
        "project template"
    ) as step:
        if project_config is None:
            step.fail(
                "Impossibile leggere projects.config.openshift.io/cluster "
                "(permessi insufficienti o cluster non raggiungibile)"
            )
        else:
            template_name = (
                project_config.get("spec", {})
                .get("projectRequestTemplate", {})
                .get("name")
            )
            if not template_name:
                step.add_error(
                    "spec.projectRequestTemplate.name non e' impostato: il "
                    "template di progetto di default e' ancora in uso"
                )

    template = None
    if template_name:
        template = oc_get_json(
            "template", template_name, "-n", "openshift-config"
        )

    with GradingStep(
        "Il template referenziato esiste nel namespace openshift-config"
    ) as step:
        if not template_name:
            step.fail()
        elif template is None:
            step.fail(
                f"Template '{template_name}' non trovato in openshift-config"
            )

    with GradingStep(
        "Il template definisce un oggetto Project con nome ${PROJECT_NAME}"
    ) as step:
        if template is None:
            step.fail()
        else:
            check_project_object(template, step)

    with GradingStep(
        "Il template concede il ruolo admin al gruppo provisioners sul "
        "nuovo progetto"
    ) as step:
        if template is None:
            step.fail()
        else:
            check_rolebinding_object(template, step)

    with GradingStep(
        "Il template imposta un limite di memoria di 1Gi per i container "
        "del nuovo progetto"
    ) as step:
        if template is None:
            step.fail()
        else:
            check_limitrange_object(template, step)

    crb = oc_get_json("clusterrolebinding", CRB_NAME)

    with GradingStep(
        f"Il ClusterRoleBinding '{CRB_NAME}' e' limitato al gruppo "
        f"'{PROVISIONERS_GROUP}'"
    ) as step:
        if crb is None:
            step.fail(f"ClusterRoleBinding '{CRB_NAME}' non trovato")
        else:
            role_ref = crb.get("roleRef", {})
            if role_ref.get("name") != CLUSTERROLE_NAME:
                step.add_error(
                    f"roleRef.name deve restare '{CLUSTERROLE_NAME}' "
                    f"(trovato: {role_ref.get('name')!r})"
                )
            subjects = crb.get("subjects", []) or []
            group_names = {
                s.get("name") for s in subjects if s.get("kind") == "Group"
            }
            if DEFAULT_GROUP in group_names:
                step.add_error(
                    f"Il subject di default '{DEFAULT_GROUP}' deve essere "
                    "rimosso: solo il gruppo 'provisioners' deve poter "
                    "auto-provisionarsi progetti"
                )
            if PROVISIONERS_GROUP not in group_names:
                step.add_error(
                    f"Il gruppo '{PROVISIONERS_GROUP}' deve essere il "
                    f"subject del ClusterRoleBinding (trovati: "
                    f"{group_names!r})"
                )


if __name__ == "__main__":
    main()
