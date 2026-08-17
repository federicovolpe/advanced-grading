#!/usr/bin/env python3
"""
Grading "custom" per la LAB images-lab (Cap. 3), sprovvista di `lab grade`
ufficiale (la classe ImagesLab implementa solo start()/finish()).

I watch_items sono definiti direttamente nel modulo ufficiale
(do188/images-lab.py: test_registry_image_exists/test_container_pulled_and_
tagged/test_container_started), che verificano tramite `skopeo inspect`
(senza credenziali) che lo studente abbia:

- pushato l'immagine costruita dal Containerfile fornito
  (materials/labs/images-lab/Containerfile, ubi9/nginx che serve una index.html
  con la frase "It is pitch black...") sul registry della classroom, come
  "developer/images-lab:latest";
- taggato la stessa immagine anche come "developer/images-lab:grue" (stesso
  repo, tag diverso - verificato con una seconda skopeo inspect);
- avviato un container chiamato "images-lab" (qualunque stato, il modulo
  ufficiale controlla solo la presenza nel nome, non lo stato Running) che
  pubblica la porta 8080 e risponde con "It is pitch black. You are likely to
  be eaten by a grue." su http://localhost:8080.

Il registry della classroom (PodmanRegistries.CLASSROOM in
do188/common/podman/client.py) e' "registry.ocp4.example.com:8443".

Uso: images-lab.py   (nessun progetto OpenShift: solo Podman)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import GradingStep, http_get, podman_container, skopeo_inspect

LAB_NAME = "images-lab"
REGISTRY = "registry.ocp4.example.com:8443"
REGISTRY_USER = "developer"
CONTAINER = "images-lab"
HTTP_PORT = 8080
EXPECTED_TEXT = "It is pitch black. You are likely to be eaten by a grue."


def main():
    print(f"🔧 Grading personalizzato per '{LAB_NAME}'")

    with GradingStep(f"L'immagine e' stata pushata su {REGISTRY}/{REGISTRY_USER}/{LAB_NAME}:latest") as step:
        ok, _ = skopeo_inspect(f"{REGISTRY}/{REGISTRY_USER}/{LAB_NAME}:latest")
        if not ok:
            step.fail("skopeo inspect ha fallito (immagine non trovata o non pubblica)")

    with GradingStep(f"L'immagine e' taggata anche come {REGISTRY}/{REGISTRY_USER}/{LAB_NAME}:grue") as step:
        ok, _ = skopeo_inspect(f"{REGISTRY}/{REGISTRY_USER}/{LAB_NAME}:grue")
        if not ok:
            step.fail("skopeo inspect ha fallito per il tag 'grue'")

    with GradingStep(f"Il container '{CONTAINER}' esiste") as step:
        if podman_container(CONTAINER) is None:
            step.fail(f"Container '{CONTAINER}' non trovato")

    with GradingStep(f"http://localhost:{HTTP_PORT} risponde con il testo del grue") as step:
        ok, body = http_get(f"http://localhost:{HTTP_PORT}")
        if not ok:
            step.fail(f"La richiesta a http://localhost:{HTTP_PORT} e' fallita")
        elif EXPECTED_TEXT not in body:
            step.add_error("Il testo di risposta non corrisponde a quello atteso")


if __name__ == "__main__":
    main()
