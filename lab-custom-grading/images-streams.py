#!/usr/bin/env python3
"""
Grading "custom" per la guided exercise images-streams (DO288), priva di
`lab grade` ufficiale (il modulo do288/images_streams.py implementa solo
start()/finish()).

do288/images_streams.py.finish() cancella due progetti distinti:
`f"{self.__LAB__}-common"` e `f"{self.__LAB__}-app"` -> l'esercizio usa DUE
progetti OpenShift, non uno solo (a differenza della maggior parte degli
altri esercizi DO288).

Testo della guida: in "images-streams-common" lo studente crea un
ImageStream "hello-world" con un tag "latest" che punta inizialmente a
registry.ocp4.example.com:8443/redhattraining/hello-world-nginx; al passo 5
lo studente lo RI-tagga (`oc tag ... hello-world:latest`) verso
.../redhattraining/php-hello-dockerfile. In "images-streams-app" lo
studente lancia `oc new-app --name hello -i
images-streams-common/hello-world` (Deployment+Service "hello") e poi
`oc expose svc hello` (Route "hello"). Lo stato finale atteso e' quindi il
retag GIA' fatto: l'ImageStream punta a php-hello-dockerfile (non piu' a
hello-world-nginx) e la Route risponde con un testo che include "PHP
version" (il numero di patch esatto, es. "7.2.11", non e' garantito essere
sempre lo stesso, quindi non lo controlliamo).

Uso: images-streams.py [nome-progetto-base]   (default: images-streams)
Il nome-progetto-base viene usato per derivare i due progetti
"<base>-common" e "<base>-app", come fa lo start() ufficiale.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, http_get, oc_get_json, project_exists

LAB_NAME = "images-streams"
IMAGESTREAM = "hello-world"
DEPLOYMENT = "hello"
EXPECTED_IMAGE_SNIPPET = "php-hello-dockerfile"
STALE_IMAGE_SNIPPET = "hello-world-nginx"
EXPECTED_BODY = "PHP version"


def latest_tag_references(imagestream):
    """Ritorna l'insieme delle stringhe di riferimento immagine associate al
    tag 'latest', sia da spec.tags (dichiarazione) che da status.tags
    (risoluzione effettiva) -- cosi' il controllo funziona anche se uno dei
    due blocchi non e' ancora popolato."""
    refs = []
    for t in (imagestream.get("spec") or {}).get("tags", []) or []:
        if t.get("name") == "latest":
            refs.append((t.get("from") or {}).get("name", ""))
    for t in (imagestream.get("status") or {}).get("tags", []) or []:
        if t.get("tag") == "latest":
            for item in t.get("items", []) or []:
                refs.append(item.get("dockerImageReference", ""))
    return refs


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else LAB_NAME
    project_common = f"{base}-common"
    project_app = f"{base}-app"
    print(f"🔧 Grading personalizzato per '{LAB_NAME}' (progetti: {project_common}, {project_app})")

    with GradingStep(f"Il progetto {project_common} esiste") as step:
        if not project_exists(project_common):
            step.fail(f"Progetto '{project_common}' non trovato")

    with GradingStep(f"Il progetto {project_app} esiste") as step:
        if not project_exists(project_app):
            step.fail(f"Progetto '{project_app}' non trovato")

    imagestream = oc_get_json("imagestream", IMAGESTREAM, "-n", project_common)
    with GradingStep(
        f"L'ImageStream '{IMAGESTREAM}' e' stato ri-taggato verso {EXPECTED_IMAGE_SNIPPET}"
    ) as step:
        if imagestream is None:
            step.fail(f"ImageStream '{IMAGESTREAM}' non trovato nel progetto {project_common}")
        else:
            refs = latest_tag_references(imagestream)
            if not refs:
                step.add_error("Nessun tag 'latest' trovato sull'ImageStream")
            elif any(STALE_IMAGE_SNIPPET in r for r in refs) and not any(
                EXPECTED_IMAGE_SNIPPET in r for r in refs
            ):
                step.add_error(
                    f"Il tag 'latest' punta ancora a '{STALE_IMAGE_SNIPPET}' "
                    f"(riferimenti trovati: {refs}): il retag del passo 5 non e' stato fatto"
                )
            elif not any(EXPECTED_IMAGE_SNIPPET in r for r in refs):
                step.add_error(
                    f"Il tag 'latest' non punta a '{EXPECTED_IMAGE_SNIPPET}' "
                    f"(riferimenti trovati: {refs})"
                )

    with GradingStep(f"L'app '{DEPLOYMENT}' risponde correttamente tramite la Route") as step:
        route = oc_get_json("route", DEPLOYMENT, "-n", project_app)
        if not route:
            step.fail(f"Route '{DEPLOYMENT}' non trovata nel progetto {project_app}")
        else:
            host = (route.get("spec") or {}).get("host", "")
            ok, body = http_get(f"http://{host}")
            if not ok:
                step.fail(f"Nessuna risposta da '{host}'")
            elif EXPECTED_BODY not in body:
                step.add_error(
                    f"La risposta da '{host}' non contiene il testo atteso "
                    f"({EXPECTED_BODY!r}): risposta ottenuta: {body!r}"
                )


if __name__ == "__main__":
    main()
