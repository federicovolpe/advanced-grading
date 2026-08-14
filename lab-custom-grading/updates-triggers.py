#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato updates-triggers, sprovvisto di
`lab grade` ufficiale (la classe UpdatesTriggers nel pacchetto do180
implementa solo start()/finish(), non grade()).

Questo esercizio non ha una cartella materials/solutions/updates-triggers/
(a differenza di reliability-probes/reliability-requests): non si applica
nessun file YAML aggiuntivo, il nocciolo dell'esercizio e' un comando
interattivo documentato in materials/labs/updates-triggers/resources.txt:

    oc set triggers deployment/version --from-image versioned-hello:1 \\
        --containers versioned-hello

che scrive sul deployment "version" l'annotazione
image.openshift.io/triggers (assente nello starter 20-web.yaml), abilitando
un aggiornamento automatico dell'immagine quando cambia l'ImageStreamTag
versioned-hello:1. Questo e' l'unico stato finale stabile e oggettivamente
verificabile prodotto dall'esercizio.

Le successive `oc tag ...` in resources.txt servono solo a *osservare* (via
curl_loop.sh) il rolling update scatenato dal trigger: non hanno un valore
finale univoco (dipende da quanti retag lo studente ha effettivamente
lanciato durante l'esplorazione), quindi NON vengono gradate qui per evitare
falsi negativi legati al momento in cui si lancia il grading.

Uso: updates-triggers.py [nome-progetto]   (default: updates-triggers)
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "updates-triggers"
DEPLOYMENT_NAME = "version"
CONTAINER_NAME = "versioned-hello"
EXPECTED_ISTAG = "versioned-hello:1"
TRIGGERS_ANNOTATION = "image.openshift.io/triggers"


def get_container(deployment, name=CONTAINER_NAME):
    containers = deployment["spec"]["template"]["spec"]["containers"]
    for c in containers:
        if c.get("name") == name:
            return c
    return containers[0] if containers else None


def get_image_triggers(deployment):
    """Ritorna la lista di trigger presente nell'annotazione
    image.openshift.io/triggers (quella scritta da `oc set triggers
    --from-image`), o None se l'annotazione manca o non e' JSON valido."""
    annotations = deployment.get("metadata", {}).get("annotations") or {}
    raw = annotations.get(TRIGGERS_ANNOTATION)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def find_matching_trigger(triggers):
    """Cerca, tra i trigger, quello ImageChange da versioned-hello:1 rivolto
    al container versioned-hello. Il controllo sul fieldPath e' volutamente
    permissivo (contiene il nome del container e termina con '.image') per
    non dipendere dall'esatta sintassi jsonpath generata da `oc`."""
    for trig in triggers:
        frm = trig.get("from", {}) or {}
        field_path = str(trig.get("fieldPath", ""))
        if (
            frm.get("kind") == "ImageStreamTag"
            and frm.get("name") == EXPECTED_ISTAG
            and CONTAINER_NAME in field_path
            and field_path.rstrip().endswith(".image")
        ):
            return trig
    return None


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    deployment = oc_get_json("deployment", DEPLOYMENT_NAME, "-n", project)
    container = None

    with GradingStep(f"Il deployment {DEPLOYMENT_NAME} esiste") as step:
        if deployment is None:
            step.fail(f"Deployment '{DEPLOYMENT_NAME}' non trovato nel progetto")
        else:
            container = get_container(deployment)
            if container is None:
                step.fail("Nessun container trovato nel deployment")

    with GradingStep(
        f"Il deployment {DEPLOYMENT_NAME} ha un trigger automatico di "
        f"ImageChange da {EXPECTED_ISTAG} per il container {CONTAINER_NAME}"
    ) as step:
        if deployment is None:
            step.fail()
        else:
            triggers = get_image_triggers(deployment)
            if not triggers:
                step.add_error(
                    f"Il deployment non ha l'annotazione '{TRIGGERS_ANNOTATION}' "
                    f"(usare 'oc set triggers deployment/{DEPLOYMENT_NAME} "
                    f"--from-image {EXPECTED_ISTAG} --containers {CONTAINER_NAME}')"
                )
            else:
                match = find_matching_trigger(triggers)
                if match is None:
                    step.add_error(
                        f"Nessun trigger ImageChange da '{EXPECTED_ISTAG}' trovato "
                        f"per il container '{CONTAINER_NAME}' "
                        f"(trigger presenti: {triggers})"
                    )
                else:
                    pause = str(match.get("pause", "false")).lower()
                    if pause == "true":
                        step.add_error(
                            "Il trigger esiste ma e' in pausa (pause: true): "
                            "deve essere automatico, non manuale"
                        )


if __name__ == "__main__":
    main()
