#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato updates-imagestreams, sprovvisto di
`lab grade` ufficiale (la classe UpdatesImagestreams nel pacchetto do180
implementa solo start()/finish(), non grade()).

L'esercizio non ha una cartella materials/solutions ne' materials/labs (e'
puramente imperativo, niente manifest YAML applicato da start()): start() si
limita a creare il progetto "updates-imagestreams" e a rendere disponibile
l'immagine esterna registry.lab.example.com:8443/redhattraining/versioned-hello:v1.0
(vedi do180/exercises/updates_imagestreams.py e do180/common/images.py, dove
registry_api = "registry.lab.example.com:8443").

Il manuale attuale (RHOCP 4.22, sezione 7.6) chiede allo studente 3 azioni con
nomi/valori fissati in modo univoco, tutte gradate qui:

1. Creare l'ImageStream "versioned-hello" con il tag "v1.0" che referenzia
   quell'immagine esterna (`oc tag ... versioned-hello:v1.0`).
2. Abilitare la local lookup policy sull'ImageStream (`oc set image-lookup
   versioned-hello`), verificato nel manuale stesso con `oc set image-lookup`
   senza argomenti (colonna LOCAL a true).
3. Creare un Deployment di nome "version" che usa l'image stream tag
   (`oc create deployment version --image versioned-hello:v1.0`): il nome
   "version" e' letterale nel comando del manuale, non lasciato alla scelta
   dello studente.

Il passo 6 del manuale ("Confirm that both the deployment and the pod refer
to the image by its SHA ID") non aggiunge un'azione nuova: e' una semplice
conseguenza automatica dei passi 1-3 (l'admission controller di OpenShift
risolve l'immagine sul Deployment stesso, non solo sul Pod, appena
lookupPolicy.local e' true) - per questo il check sull'immagine del
Deployment accetta sia il riferimento gia' risolto (con "@sha256:") sia,
in subordine, il riferimento letterale "versioned-hello:v1.0" (nel caso
raro in cui la risoluzione non sia ancora avvenuta al momento del grading),
purche' in ogni caso punti chiaramente all'immagine versioned-hello.

Non vengono gradati (correttamente assenti anche nello script precedente):
i comandi di sola ispezione del manuale (`oc describe is`, `oc image info`,
`oc get pod ... -o jsonpath`) e il nome del pod, che e' generato
automaticamente dal ReplicaSet e cambia ad ogni rollout.

Uso: updates-imagestreams.py [nome-progetto]   (default: updates-imagestreams)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, oc_get_json, project_exists

LAB_NAME = "updates-imagestreams"
ISTREAM_NAME = "versioned-hello"
EXPECTED_TAG = "v1.0"
EXPECTED_SOURCE_SUBSTR = "redhattraining/versioned-hello:v1.0"
EXPECTED_IMAGE_SUBSTR = "redhattraining/versioned-hello"
DEPLOYMENT_NAME = "version"


def find_tag(imagestream, tag_name):
    for tag in imagestream.get("spec", {}).get("tags", []) or []:
        if tag.get("name") == tag_name:
            return tag
    return None


def deployment_images(deployment):
    containers = (
        deployment.get("spec", {})
        .get("template", {})
        .get("spec", {})
        .get("containers", [])
        or []
    )
    return [c.get("image", "") for c in containers]


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetto: {project})")

    with GradingStep(f"Il progetto {project} esiste") as step:
        if not project_exists(project):
            step.fail(f"Progetto '{project}' non trovato")

    imagestream = oc_get_json("imagestream", ISTREAM_NAME, "-n", project)

    with GradingStep(f"L'ImageStream '{ISTREAM_NAME}' esiste nel progetto") as step:
        if imagestream is None:
            step.fail(
                f"ImageStream '{ISTREAM_NAME}' non trovato nel progetto "
                f"(atteso da 'oc tag ... {ISTREAM_NAME}:{EXPECTED_TAG}')"
            )

    with GradingStep(
        f"Il tag '{EXPECTED_TAG}' punta all'immagine {EXPECTED_SOURCE_SUBSTR}"
    ) as step:
        if imagestream is None:
            step.fail()
        else:
            tag = find_tag(imagestream, EXPECTED_TAG)
            if tag is None:
                step.add_error(
                    f"Nessun tag '{EXPECTED_TAG}' definito in spec.tags "
                    f"dell'ImageStream '{ISTREAM_NAME}'"
                )
            else:
                source = tag.get("from") or {}
                if source.get("kind") != "DockerImage":
                    step.add_error(
                        f"Il tag '{EXPECTED_TAG}' non referenzia un'immagine "
                        f"esterna (from.kind: {source.get('kind')})"
                    )
                name = source.get("name", "")
                if EXPECTED_SOURCE_SUBSTR not in name:
                    step.add_error(
                        f"Il tag '{EXPECTED_TAG}' punta a '{name}', atteso "
                        f"un riferimento contenente '{EXPECTED_SOURCE_SUBSTR}'"
                    )

    with GradingStep(
        f"La local lookup policy e' abilitata su '{ISTREAM_NAME}' "
        f"(oc set image-lookup {ISTREAM_NAME})"
    ) as step:
        if imagestream is None:
            step.fail()
        else:
            local = (imagestream.get("spec", {}).get("lookupPolicy") or {}).get("local")
            if local is not True:
                step.add_error(
                    "spec.lookupPolicy.local non e' true su "
                    f"'{ISTREAM_NAME}' (atteso da 'oc set image-lookup "
                    f"{ISTREAM_NAME}')"
                )

    with GradingStep(
        f"Il Deployment '{DEPLOYMENT_NAME}' usa l'image stream tag "
        f"{ISTREAM_NAME}:{EXPECTED_TAG}"
    ) as step:
        deployment = oc_get_json("deployment", DEPLOYMENT_NAME, "-n", project)
        if deployment is None:
            step.fail(
                f"Deployment '{DEPLOYMENT_NAME}' non trovato nel progetto "
                f"(atteso da 'oc create deployment {DEPLOYMENT_NAME} "
                f"--image {ISTREAM_NAME}:{EXPECTED_TAG}')"
            )
        else:
            images = deployment_images(deployment)
            # Accetta sia il riferimento gia' risolto dall'admission
            # controller (con SHA, es. ".../versioned-hello@sha256:...")
            # sia, in subordine, il tag letterale "versioned-hello:v1.0"
            # (se la risoluzione non e' ancora avvenuta): in entrambi i
            # casi deve comunque puntare all'immagine versioned-hello.
            if not any(
                EXPECTED_IMAGE_SUBSTR in img or f"{ISTREAM_NAME}:{EXPECTED_TAG}" in img
                for img in images
            ):
                step.add_error(
                    f"Nessun container del Deployment '{DEPLOYMENT_NAME}' usa "
                    f"un'immagine riconducibile a '{ISTREAM_NAME}:{EXPECTED_TAG}' "
                    f"(immagini trovate: {images or 'nessuna'})"
                )


if __name__ == "__main__":
    main()
