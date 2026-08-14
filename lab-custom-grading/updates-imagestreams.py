#!/usr/bin/env python3
"""
Grading "custom" per l'esercizio guidato updates-imagestreams, sprovvisto di
`lab grade` ufficiale (la classe UpdatesImagestreams nel pacchetto do180
implementa solo start()/finish(), non grade()).

L'esercizio non ha una cartella materials/solutions (e' puramente
imperativo, niente manifest YAML applicato da start() e nessun lab-start/):
start() si limita a creare il progetto e a rendere disponibile l'immagine
esterna redhattraining/versioned-hello:v1.0 (vedi do180/updates-imagestreams.py
e do180/materials/labs/updates-imagestreams/resources.txt). L'unico comando
di riferimento non ambiguo e':

    oc tag registry.ocp4.example.com:8443/redhattraining/versioned-hello:v1.0 \
        versioned-hello:v1.0

cioe' creare, nel progetto dello studente, un ImageStream "versioned-hello"
con un tag "v1.0" che referenzia quell'immagine esterna. Questo e' l'unico
stato finale permanente e univocamente determinato dall'esercizio: i comandi
successivi di resources.txt (`oc image info ...`, `oc get pod <POD_NAME> ...`)
sono di sola ispezione / usano un nome pod scelto liberamente dallo studente
(placeholder <POD_NAME>, non fissato dal materiale ufficiale) e spesso con
`oc run --rm`, quindi non lasciano necessariamente una risorsa persistente
verificabile a posteriori: non vengono gradati per evitare falsi negativi
su un esercizio comunque completato correttamente.

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


def find_tag(imagestream, tag_name):
    for tag in imagestream.get("spec", {}).get("tags", []) or []:
        if tag.get("name") == tag_name:
            return tag
    return None


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


if __name__ == "__main__":
    main()
